import os
import json
import asyncio
import uuid
import pandas as pd
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq
from fastapi.responses import FileResponse
from fastapi import UploadFile, BackgroundTasks

# Dict in RAM to track tasks
EVALUATION_TASKS = {}

JUDGE_MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

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

async def run_evaluation_task(
    task_id: str,
    results_data: list,
    golden_data: list,
    system_type: str
):
    try:
        EVALUATION_TASKS[task_id]["status"] = "in_progress"

        # 1. Judge LLM config
        llm = ChatGroq(model=JUDGE_MODEL_NAME, temperature = 0)
        deepeval_model = CustomDeepEval(llm)

        # 2. Metrics
        correctness_metric = GEval(
            name="Correctness",
            criteria="Determine whether the actual output is factually equivalent to the expected output.",
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=deepeval_model
        )

        total_questions = len(results_data)
        results = []

        # 3. Iterate and evaluate asynchronously
        for i, res_item in enumerate(results_data):
            # Search GT corresponding in Golden dataset (same order asumption)
            q = res_item.get("question", res_item.get("query", ""))
            ans = res_item.get("answer", res_item.get("result", ""))

            # Get GT
            gt = next(
                (g["expected_output"] if "expected_output" in g else g["answer"] for g in golden_data if g.get("question" == q, "No GT found")
            ))

            test_case = LLMTestCase(
                input=q,
                actual_output=ans,
                expected_output=gt,
                retrieval_context=["Conocimiento de Fine-Tuning"] if system_type == "FT" else res_item.get("context", [])
            )

            try:
                # Execute metric
                correctness_metric.measure(test_case)
                score = correctness_metric.score
                reason = correctness_metric.reason
            except Exception as e:
                score = 0.0
                reason = f"Error evaluating: {str(e)}"

            results.append({
                "Question": q,
                "Actual Answer": ans,
                "Expected Output": gt,
                "Correctness Score": score,
                "Judge reason": reason
            })

            EVALUATION_TASKS[task_id]["progress"] = f"{i+1}/{total_questions}"

            # Rate Limit
            if i < total_questions - 1:
                await asyncio.sleep(30)
        
        # 3. Finish and save CSV
        filename = f"eval_{system_type}_{task_id[:8]}.csv"
        pd.DataFrame(results).to_csv(filename, index=False)

        EVALUATION_TASKS[task_id]["status"] = "completed"
        EVALUATION_TASKS[task_id]["file"] = filename
    
    except Exception as e:
        EVALUATION_TASKS[task_id]["status"] = "failed"
        EVALUATION_TASKS[task_id]["error"] = str(e)


async def start_system_evaluation(
    system_type: str,
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

        if system_type not in ["FT", "RAG"]:
            raise ValueError("system_type must be 'FT' or 'RAG'")
        
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
            system_type
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