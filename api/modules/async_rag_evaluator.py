import os
import json
import asyncio
import uuid
import time
import re
import csv
import random
import logging
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import (
    GEval, FaithfulnessMetric, AnswerRelevancyMetric, 
    ContextualPrecisionMetric, ContextualRecallMetric, 
    ContextualRelevancyMetric, HallucinationMetric, 
    ToxicityMetric, BiasMetric
)
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq
from fastapi.responses import FileResponse
from fastapi import UploadFile, BackgroundTasks

# Logger config
LOGGER_NAME = os.getenv("EVAL_LOGGER_NAME", "async_rag_evaluator")
EVAL_LOG_LEVEL = getattr(logging, os.getenv("EVAL_LOG_LEVEL", "INFO").upper(), logging.INFO)
logger = logging.getLogger(LOGGER_NAME)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
logger.setLevel(EVAL_LOG_LEVEL)

# Dict in RAM to track tasks
EVALUATION_TASKS = {}

# Output directory for evaluation CSVs (relative to repo root by default)
OUTPUT_DIR = os.getenv("EVAL_OUTPUT_DIR", "evaluation_results")
# Clean up CSVs older than this many seconds (default: 24 hours)
OUTPUT_CLEANUP_SECONDS = int(os.getenv("EVAL_OUTPUT_CLEANUP_SECONDS", 24 * 60 * 60))

# Retry configuration for LLM calls during evaluation (exponential backoff)
EVAL_RETRY_MAX_ATTEMPTS = int(os.getenv("EVAL_RETRY_MAX_ATTEMPTS", 4))
EVAL_RETRY_BASE_SECONDS = float(os.getenv("EVAL_RETRY_BASE_SECONDS", 2.0))
EVAL_RETRY_MAX_SECONDS = float(os.getenv("EVAL_RETRY_MAX_SECONDS", 40.0))
EVAL_RETRY_JITTER_SECONDS = float(os.getenv("EVAL_RETRY_JITTER_SECONDS", 1.0))

JUDGE_MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _cleanup_old_csvs():
    """Remove old evaluation CSVs to prevent disk growth."""
    now = time.time()
    if not os.path.isdir(OUTPUT_DIR):
        return

    for fname in os.listdir(OUTPUT_DIR):
        if not fname.endswith(".csv"):
            continue
        path = os.path.join(OUTPUT_DIR, fname)
        try:
            age = now - os.path.getmtime(path)
            if age > OUTPUT_CLEANUP_SECONDS:
                os.remove(path)
        except Exception:
            # Best effort cleanup; ignore errors
            pass

class CustomDeepEval(DeepEvalBaseLLM):
    def __init__(self, model):
        self.model = model
    def load_model(self):
        return self.model
    def generate(self, prompt: str) -> str:
        return self.model.invoke(prompt).content
    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)
    def get_model_name(self):
        return JUDGE_MODEL_NAME
    
def _extract_status_code(exc: Exception):
    for attr in ("status_code", "http_status", "code"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
    
    return None

def _extract_retry_after_seconds(exc: Exception):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None
    if headers:
        raw = headers.get("Retry-After") or headers.get("retry-after")
        if raw:
            try:
                return max(0.0, float(raw))
            except Exception:
                pass
    msg = str(exc).lower()
    m = re.search(r"retry[- ]?after[: ]+([0-9]+(?:\.[0-9]+)?)", msg)
    if m:
        try:
            return max(0.0, float(m.group(1)))
        except Exception:
            pass
    return None

def _is_retryable_llm_error(exc: Exception) -> bool:
    code = _extract_status_code(exc)
    if code == 429:
        return True
    if code in (500, 502, 503, 504):
        return True
    
    msg = str(exc).lower()
    retryable_tokens = [
        "429",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "timeout",
        "timed out",
        "connection reset",
        "service unavailable",
    ]
    
    return any(token in msg for token in retryable_tokens)

def _retry_delay_seconds(attempt: int, exc: Exception) -> float:
    # attempt: 1,2,3...
    
    retry_after = _extract_retry_after_seconds(exc)
    if retry_after is not None:
        base_delay = retry_after
    else:
        base_delay = min(
            EVAL_RETRY_MAX_SECONDS,
            EVAL_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
        )
    jitter = random.uniform(0, EVAL_RETRY_JITTER_SECONDS)
    return min(EVAL_RETRY_MAX_SECONDS, base_delay + jitter)

def _build_result_columns(metric_names: list) -> list:
    cols = ["Question", "Actual Answer", "Expected Output"]
    for m in metric_names:
        cols.append(f"{m} Score")
        cols.append(f"{m} Reason")
    return cols
def _append_result_row(file_path: str, row: dict, columns: list):
    file_exists = os.path.exists(file_path)
    with open(file_path, "a", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow({c: row.get(c, "") for c in columns})

def _metric_ok_without_error(res_row: dict, metric_name: str) -> bool:
    reason = str(res_row.get(f"{metric_name} Reason", "") or "").lower()
    score: float | None = res_row.get(f"{metric_name} Score", None)
    
    if "error evaluating" in reason:
        return False
    try: 
        float(score) # type: ignore
        return True
    except (ValueError, TypeError):
        return False

async def run_evaluation_task(
    task_id: str,
    results_data: list,
    golden_data: list,
    system_type: str,
    selected_metrics: list
):
    try:
        EVALUATION_TASKS[task_id]["status"] = "in_progress"

        # 1. Judge LLM config
        llm = ChatGroq(model=JUDGE_MODEL_NAME, temperature = 0)
        deepeval_model = CustomDeepEval(llm)

        # 2. Instantiate selected metrics
        active_metrics = []
        for m in selected_metrics:
            if m == "Correctness":
                active_metrics.append((m, GEval(
                    name="Correctness",
                    criteria="Determine whether the actual output is factually equivalent to the expected output.",
                    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
                    model=deepeval_model
                )))
            elif m == "Faithfulness":
                active_metrics.append((m, FaithfulnessMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "AnswerRelevancy":
                active_metrics.append((m, AnswerRelevancyMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "ContextualPrecision":
                active_metrics.append((m, ContextualPrecisionMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "ContextualRecall":
                active_metrics.append((m, ContextualRecallMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "ContextualRelevancy":
                active_metrics.append((m, ContextualRelevancyMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "Hallucination":
                active_metrics.append((m, HallucinationMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "Toxicity":
                active_metrics.append((m, ToxicityMetric(threshold=0.5, model=deepeval_model, include_reason=True)))
            elif m == "Bias":
                active_metrics.append((m, BiasMetric(threshold=0.5, model=deepeval_model, include_reason=True)))


        total_questions = len(results_data)

        # Cleanup old CSVs before running a new evaluation
        _ensure_output_dir()
        _cleanup_old_csvs()
        
        # Prepare output CSV file path once, then append rows incrementally
        filename = f"eval_{system_type}_{task_id[:8]}_{int(time.time())}.csv"
        file_path = os.path.join(OUTPUT_DIR, filename)
        metric_names = [name for name, _ in active_metrics]
        result_columns = _build_result_columns(metric_names)
        
        # Expose path from the beginning so partial progress can be inspected
        EVALUATION_TASKS[task_id]["file"] = file_path
        
        # 3. Iterate and evaluate asynchronously
        for i, res_item in enumerate(results_data):
            # Search GT corresponding in Golden dataset (same order asumption)
            q = res_item.get("question", res_item.get("query", ""))
            ans = res_item.get("answer", res_item.get("result", ""))

            # Get GT
            gt = next(
                (g["expected_output"] if "expected_output" in g else g["answer"] for g in golden_data if g.get("question") == q),
                "No GT found"
            )

            ctx = [gt] if system_type == "FT" else res_item.get("context", [])

            test_case = LLMTestCase(
                input=q,
                actual_output=ans,
                expected_output=gt,
                retrieval_context=ctx,
                context=ctx
            )

            res_row = {
                "Question": q,
                "Actual Answer": ans,
                "Expected Output": gt
            }

            for m_name, metric in active_metrics:
                last_error = None
                measured_ok = False
                attempts_done = 0
                
                for attempt in range(1, EVAL_RETRY_MAX_ATTEMPTS + 1):
                    attempts_done = attempt
                    try:
                        # metric.measure may perform blocking IO (LLM calls), so run it off the event loop
                        await asyncio.to_thread(metric.measure, test_case)
                        res_row[f"{m_name} Score"] = metric.score
                        res_row[f"{m_name} Reason"] = metric.reason
                        measured_ok = True
                        break
                    except Exception as e:
                        last_error = e
                        retryable = _is_retryable_llm_error(e)
                        if retryable and attempt < EVAL_RETRY_MAX_ATTEMPTS:
                            delay = _retry_delay_seconds(attempt, e)
                            logger.warning(
                                "task=%s q=%d/%d metric=%s retry=%d/%d delay=%.2fs error=%s",
                                task_id[:8], i + 1, total_questions, m_name,
                                attempt, EVAL_RETRY_MAX_ATTEMPTS, delay, str(e)[:240]
                            )
                            await asyncio.sleep(delay)
                            continue
                        logger.error(
                            "task=%s q=%d/%d metric=%s failed attempts=%d error=%s",
                            task_id[:8], i + 1, total_questions, m_name, attempts_done, str(e)[:240]
                        )
                        break
                
                if not measured_ok:
                    res_row[f"{m_name} Score"] = 0.0
                    if last_error is None:
                        res_row[f"{m_name} Reason"] = "Error evaluating: unknown error"
                    else:
                        res_row[f"{m_name} Reason"] = (
                            f"Error evaluating after {attempts_done} attempt(s): {str(last_error)}"
                        )
            
            # Incremental save: append one row per evaluated item
            _append_result_row(file_path, res_row, result_columns)
            
            EVALUATION_TASKS[task_id]["progress"] = f"{i+1}/{total_questions}"
            
            ok_metrics = []
            failed_metrics = []
            for metric_name, _ in active_metrics:
                if _metric_ok_without_error(res_row, metric_name):
                    ok_metrics.append(metric_name)
                else:
                    failed_metrics.append(metric_name)

            logger.info(
                "task=%s progress=%d/%d question=%s ok_metrics=%s failed_metrics=%s",
                task_id[:8],
                i + 1,
                total_questions,
                (q or "")[:120],
                ",".join(ok_metrics) if ok_metrics else "-",
                ",".join(failed_metrics) if failed_metrics else "-"
            )

            # opcional: exponer en status endpoint
            EVALUATION_TASKS[task_id]["last_question"] = q
            EVALUATION_TASKS[task_id]["last_ok_metrics"] = ok_metrics
            EVALUATION_TASKS[task_id]["last_failed_metrics"] = failed_metrics

            # Rate Limit
            if i < total_questions - 1:
                await asyncio.sleep(30)
        
        # 4. Mark completed
        EVALUATION_TASKS[task_id]["status"] = "completed"
        logger.info(
            "task=%s completed total_questions=%d output_csv=%s",
            task_id[:8], total_questions, file_path
        )
    
    except Exception as e:
        EVALUATION_TASKS[task_id]["status"] = "failed"
        EVALUATION_TASKS[task_id]["error"] = str(e)


async def start_system_evaluation(
    system_type: str,
    metrics_str: str,
    results_file: UploadFile,
    golden_file: UploadFile,
    background_tasks: BackgroundTasks
):
    """
    Start a model evaluation task.
    """
    try:
        res_content = await results_file.read()
        gold_content = await golden_file.read()
        results_data = json.loads(res_content.decode('utf-8'))
        golden_data = json.loads(gold_content.decode('utf-8'))
        
        try:
            selected_metrics = json.loads(metrics_str)
        except Exception:
            raise ValueError("Invalid metrics format")
            
        if not selected_metrics:
            raise ValueError("At least one metric must be selected")

        if system_type not in ["FT", "RAG"]:
            raise ValueError("system_type must be 'FT' or 'RAG'")
            
        # --- Validation Logic ---
        REQUIRED_FIELDS = {
            "Correctness": ["input", "actual_output", "expected_output"],
            "Faithfulness": ["actual_output", "retrieval_context"],
            "AnswerRelevancy": ["input", "actual_output"],
            "ContextualPrecision": ["input", "actual_output", "expected_output", "retrieval_context"],
            "ContextualRecall": ["input", "actual_output", "expected_output", "retrieval_context"],
            "ContextualRelevancy": ["input", "actual_output", "retrieval_context"],
            "Hallucination": ["actual_output", "context"],
            "Toxicity": ["input", "actual_output"],
            "Bias": ["input", "actual_output"]
        }

        if not results_data or not golden_data:
            raise ValueError("Empty datasets provided")
            
        first_res = results_data[0]
        has_input = "question" in first_res or "query" in first_res
        has_actual = "answer" in first_res or "result" in first_res
        has_context = "context" in first_res or system_type == "FT"
        
        q = first_res.get("question", first_res.get("query", ""))
        first_gt_item = next(
            (g for g in golden_data if g.get("question") == q), 
            None
        )
        has_expected = False
        if first_gt_item:
            has_expected = "expected_output" in first_gt_item or "answer" in first_gt_item

        for m in selected_metrics:
            reqs = REQUIRED_FIELDS.get(m, [])
            if "input" in reqs and not has_input:
                raise ValueError(f"Metric '{m}' requires 'input' (question/query field) in results JSON.")
            if "actual_output" in reqs and not has_actual:
                raise ValueError(f"Metric '{m}' requires 'actual_output' (answer/result field) in results JSON.")
            if "expected_output" in reqs and not has_expected:
                raise ValueError(f"Metric '{m}' requires 'expected_output' (expected_output/answer field matching question) in golden JSON.")
            if ("retrieval_context" in reqs or "context" in reqs) and not has_context:
                raise ValueError(f"Metric '{m}' requires 'context' field in results JSON.")
        
        task_id = str(uuid.uuid4())
        EVALUATION_TASKS[task_id] = {
            "status": "starting",
            "progress": "0/0",
            "file": None,
            "type": system_type
        }

        # Run background task
        background_tasks.add_task(
            run_evaluation_task,
            task_id,
            results_data,
            golden_data,
            system_type,
            selected_metrics
        )

        return {
            "task_id": task_id,
            "message": "Evaluation started successfully. Poll /status for progress."
        }
    except Exception as e:
        raise ValueError(f"Error parsing validation files: {str(e)}")

async def get_evaluation_task_status(task_id: str):
    """
    Get the status of a model evaluation task.
    """
    try:
        task = EVALUATION_TASKS.get(task_id)
        if not task:
            raise ValueError("Task not found")
        return task
    except Exception as e:
        raise ValueError(f"Error getting model validation status: {str(e)}")

async def download_evaluation_results(task_id: str):
    task = EVALUATION_TASKS.get(task_id)
    if not task or task["status"] != "completed" or not task["file"]:
        raise ValueError("Results not ready or task failed")

    file_path = task["file"]

    if not os.path.exists(file_path):
        raise ValueError("CSV File missing from server")
    
    return FileResponse(path=file_path, filename=file_path, media_type='text/csv')