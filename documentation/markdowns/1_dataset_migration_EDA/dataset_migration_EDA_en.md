# Introduction

In the [previous article](../0_dataset_migration_intro/dataset_migration_intro_en.md), I introduced a proposed change for a Level 1 IT support ticket resolution system: switching from synthetically generated data — which may be too rigid for evaluation purposes — to real data extracted from forums on the topic of interest.

Whenever we work with a real-world dataset, we must conduct an exploratory analysis to confirm or reject the hypothesis that it is useful for the problem at hand. That is what this report covers.

The analysis documented here was performed using the Jupyter Notebook available [here](../../notebooks/eda_stackexchange_corpus.ipynb).

# Initial Data Analysis: Do We Have Enough Data for All Categories?

### Volume by Community

<center>

| Community | Pairs |
|-----------|-------|
| superuser | 17425 |
| askubuntu | 9975 |
| serverfault | 7969 |
| apple | 6696 |
| unix | 6173 |
| security | 3069 |
| android | 2830 |
| dba | 2502 |
| webapps | 1906 |
| sharepoint | 1691 |
| networkengineering | 476 |
| devops | 53 |

</center>

The table shows that the number of threads per community is highly uneven. For example, the `devops` community has only 53 threads, while `superuser` has 20,000. This raises the question of whether we have enough data for all categories and whether data quality is adequate for the problem we want to solve.

### Is the Data Sufficient?

However, the fact that only two communities have fewer than 1,000 threads suggests that most categories are well represented and that the system should be able to answer Level 1 IT support questions with decent performance. Later we will evaluate what to do with `devops` and `networking` — the two communities with fewer than 1,000 threads — to see if we can improve answer quality in those categories.

# Question and Answer Lengths

### Global Distribution

We analyzed the lengths of questions and answers to determine:
- Typical length ranges per community
- Whether there are extreme outliers that justify length-based filtering
- Whether, in a dataset already filtered for non-standout answers (less than 100 upvote gap between best and worst), very short answers still persist. If so, we might be retrieving low-quality question-answer pairs in semantic search that only add noise to the generation stage.

<div align="center">

<table>
<tr>
<td>

| Statistic | title_body |
|-----------:|-----------:|
| count | 60765.00 |
| mean | 761.03 |
| std | 630.83 |
| min | 47.00 |
| 25% | 354.00 |
| 50% | 563.00 |
| 75% | 928.00 |
| max | 4199.00 |

</td>
<td>

| Statistic | upvoted_answer |
|-----------:|---------------:|
| count | 60765.00 |
| mean | 759.20 |
| std | 1064.64 |
| min | 0.00 |
| 25% | 244.00 |
| 50% | 467.00 |
| 75% | 887.00 |
| max | 30141.00 |

</td>
</tr>
</table>

</div>

Without diving into community-level breakdowns just yet, we observe that question and answer lengths are quite heterogeneous, with very similar means: around 760 characters. The interesting part emerges when we analyze the distributions: the standard deviation of answers is significantly higher than that of questions. This makes sense, as problem descriptions tend to be more structured than the resulting answers, which can range from highly complex to as simple as "turn your access point off and on again."

Given the high standard deviation, it is also necessary to look at other distribution metrics such as quartiles. Looking at the interquartile range, we confirm the above: answer length is more unpredictable than question length. However, when we look at medians, something curious emerges: the typical question is 100 characters longer than the typical answer (563 vs 467), which goes against the intuition that questions are shorter than answers.

How can this happen? Let's look at the maxima of each distribution: while questions cap out at around 4,000 characters, answers reach up to 30,000. This pulls the mean upward relative to the median, indicating that we are dealing with a non-symmetric answer distribution (most samples to the left of the mean, with a few uncommon ones to the right).

<center>

| Percentile | Question (chars) | Answer (chars) | Difference |
|---|---|---|---|
| P25 | 354 | 244 | +110 |
| **P50 (median)** | **563** | **467** | **+96** |
| P75 | 928 | 887 | +41 |
| Max | 4,199 | 30,141 | **-25,942** |

</center>

### An Unexpected Finding: The Log-Normal

The shape of the answer distribution — a long right tail with most samples to the left — suggested a log-normal distribution. We fitted a log-normal to the answer lengths and applied the Kolmogorov-Smirnov test to validate the fit. The result: $p = 0.04$. We cannot reject the hypothesis that answers follow a log-normal distribution at a 95% confidence level, though it is borderline. It is a reasonable approximation, not a certainty.

Why does this matter? Because we can plan inference costs without having executed a single query. The 75th percentile of answers is at 887 characters. 75% of the queries we make to the system will retrieve answers below this threshold. If we used a cheap model (llama-3.1-8b-instant, ~$0.05/M tokens) for that 75% and reserved a more expensive one (llama-4-scout, ~$0.20/M tokens) for the remaining 25%, the estimated cost per 1,000 queries would drop from $0.12 (always expensive) to $0.04 (hybrid). A saving of ~68%.

We are not deciding which model to use. This is a marginal note: when the time comes to put this into production, the data already gives us a starting point for the cost discussion.

### Asymmetry and Implications for Chunking

Looking at the table above, 75% of questions are under 1,000 characters, and the absolute maximum is 4,199 characters. This suggests that using a chunk size of 1,000 characters, most questions would fit in a single chunk, while the longest ones would split into at most 4 chunks. Defining a chunking strategy for the ingestion stage can build on this finding — something to validate when the time comes.

# Differences in Question and Answer Lengths by Community

### Observations by Community

The first interesting point to analyze is the median length of questions and answers across different communities. Looking at the table below, communities with more technical names (such as `dba`, `serverfault`, and `security`) stand out for having longer typical questions and/or answers. On the other hand, `webapps`, `android`, and `apple` stand out for having the lowest question-to-answer length ratio.

<center>

| Longer questions | Longer answers | Shorter pairs |
|---|---|---|
| dba: 800 | security: 996 | webapps: 418 / 344 |
| serverfault: 703 | dba: 686 | android: 496 / 354 |
| security: 689 | networkengineering: 602 | apple: 492 / 427 |

</center>

All of this points to something coherent: communities with more technical names discuss more technical topics and therefore tend to have longer questions and answers than those where generalist problems are discussed.

<div align="center">

| Community | total_pairs | mean_q_len | median_q_len | mean_a_len | median_a_len |
|----------:|------------:|-----------:|-------------:|-----------:|-------------:|
| superuser | 17425 | 720.4 | 557.0 | 723.6 | 454.0 |
| askubuntu | 9975 | 734.6 | 513.0 | 715.7 | 423.0 |
| serverfault | 7969 | 939.6 | 703.0 | 689.1 | 441.0 |
| apple | 6696 | 635.4 | 492.0 | 656.3 | 427.0 |
| unix | 6173 | 785.5 | 573.0 | 862.7 | 545.0 |
| security | 3069 | 865.5 | 689.0 | 1402.8 | 996.0 |
| android | 2830 | 629.2 | 495.5 | 549.0 | 354.0 |
| dba | 2502 | 1048.6 | 799.5 | 1115.9 | 686.0 |
| webapps | 1906 | 525.6 | 418.0 | 525.5 | 344.0 |
| sharepoint | 1691 | 764.2 | 555.0 | 592.3 | 394.0 |
| networkengineering | 476 | 790.8 | 558.0 | 981.9 | 601.5 |
| devops | 53 | 778.1 | 750.0 | 983.2 | 634.0 |

</div>

### Histograms and Box Plots

<div align="center">

![Question length histogram](images/question_len_histogram.png)
&emsp;&emsp;
![Answer length histogram](images/answer_len_histogram.png)

</div>

Looking at the charts, we can confirm what the distribution data already suggested: we are dealing with non-symmetric distributions with long right tails. This is more evident in answers than in questions, where most samples lie to the left of the mean and a few lie to the right. The same can be observed in the following box plots.

<center>

![Boxplot of question lengths](images/boxplot_len_questions.png)
&emsp;&emsp;
![Boxplot of answer lengths](images/boxplot_len_answers.png)

</center>

# Technical Term Detection

### Methodology

To detect the presence of technical content, we use **three independent binary signals**, each applied via a regular expression:

<center>

| Signal | What it detects | Where it is applied |
|-------|--------------|-------------------|
| `has_error_code` | Hexadecimal error codes (`0x...`), error numbers (`Error 123`), and `ERROR:` prefix | Question (`title_body`) |
| `has_numbered_steps` | Numbered steps (`1.`, `2.`), bullets, "Step N:", "First:", "Then:" | Answer (`upvoted_answer`) |
| `has_tech_terms` | Dictionary of 48 IT terms (server, network, database, docker, kubernetes, firewall, vpn, ssh, api, deploy, cluster, linux, windows, etc.) | Question (`title_body`) |

</center>

### Results

<center>

![Percentage of question-answer pairs with technical terms](images/tech_terms_community.png)

</center>

We would expect the dataset to have a high percentage of technical question-answer pairs, since we selected those relevant to IT support. Furthermore, communities with more technical names should have a higher percentage of technical pairs than more generalist communities.

<center>

![Percentage of question-answer pairs with error codes and/or numbered steps](images/error_codes_numbered.png)

</center>

On the other hand, the definitions used to detect technical terms are fairly strict, so we expect the percentage of technical pairs to be below 100% across all communities.

### Interpretation

The charts confirm our expectations: the average technical term presence across the entire dataset is approximately 70%, and generally, more technical communities have a higher percentage of technical pairs than generalist ones — something we suspected in the previous section. Regarding the other technicality proxies, we can see that error code presence is low across all communities and much lower in generalist communities. As for the anomalous behavior of the `devops` community in the chart, let us refrain from comment: the low number of pairs is behind its inconsistency with the rest.

In summary: this is a dataset with a high percentage of technical question-answer pairs, indicating that the system should be able to answer Level 1 IT support questions with good performance. Additionally, if we wanted to filter by more technical or more generalist communities, this analysis gives us candidates to consider.

# Category and Community Overlap

### The devops Case

As mentioned at the beginning, where we presented the table showing the number of threads per community, the `devops` community has dangerously low numbers: only 53 examples. With these figures, we could consider that a community-level filter might not be sufficient to obtain relevant results, or at least not for `devops`. Doing so could ultimately yield worse answers than those obtained for better-represented communities.

<center>

![Percentage of question-answer pairs with technical terms in the devops community](images/devops_content.png)

</center>

The hypothesis that other communities are relevant for answering questions about a topic that is also a community name is what we set out to test, and the charts above represent this. We can see that a non-negligible number of communities contain occurrences of concepts that could be useful for `devops` topics (see the notebook for more details on the concepts). In fact, using those concepts, the number of question-answer pairs containing DevOps concepts is 2,174, indicating that **98% of relevant documents lie outside the community with the same name**.

### Topic Coverage Heatmap

<center>

![Topic coverage heatmap](images/heatmap_coverage_community.png)

</center>

This applies not only to `devops` but also to other categories like *Security*, as can be seen in the heatmap above, which analyzed the coverage of concepts from other categories that match Stack Exchange community names but appear within differently named communities. Thus, security concepts also find networking concepts that could be relevant for analyzing a question on that topic, providing another argument against ever implementing a community-level filter.

### Implications for Metadata Filtering

In short: the fact that `devops` has few examples does not prevent us from having a successful system for answering questions on that topic. However, this analysis tells us something important for the future: if we were to filter by Stack Exchange community to obtain only threads relevant to an IT support problem, such a metadata filter would discard useful information.

# A Composite Technical Quality Index

### Definition

So far, we have measured the presence of technical terms, error codes, and numbered steps separately. Combining them into a single index can give us a more comprehensive view of the technical quality of the dataset. With this idea in mind, we propose the simple metric `score_tech`: an indicator ranging from 0 to 5 that sums the binary signals of the presence of these concepts in a question-answer pair.

$$score\_tech = has\_error\_code + has\_numbered\_steps + good\_question\_length + long\_enough\_answer + has\_tech\_terms$$

The following table describes the 5 components of the index:

<center>

| Element | Description |
|---------|-------------|
| has_error_code | Does the question contain an error code? |
| has_numbered_steps | Does the answer contain numbered steps? |
| good_question_length | Is the question between 50 and 1,500 characters? |
| long_enough_answer | Is the answer longer than 200 characters? |
| has_technical_terms | Does it contain technical terms? |

</center>

### Distribution and Threshold Ablation

Using this metric, we can define a threshold to filter out low-quality technical pairs. For example, if we set a threshold of 3, we would only keep pairs that have at least 3 out of the 5 index elements.

<div align="center">

| score | count | percentage |
|------:|------:|-----------:|
| 0 | 60 | 0.1 |
| 1 | 4887 | 8.0 |
| 2 | 24656 | 40.6 |
| 3 | 29262 | 48.2 |
| 4 | 1880 | 3.1 |
| 5 | 20 | 0.0 |

</div>

The global mean is 2.46, with a median of 3. 91.9% of pairs score above 2. If we were to filter out all samples scoring below 2 on this index, we would lose only 8.1% of the corpus, with communities that have less technical names being the most affected, as shown in the per-community table below.

<div align="center">

| Community | Mean | Median | Min | Max | Count |
|----------:|-----:|-------:|----:|----:|------:|
| superuser | 2.50 | 3.0 | 0 | 5 | 17425 |
| askubuntu | 2.64 | 3.0 | 0 | 5 | 9975 |
| serverfault | 2.57 | 3.0 | 0 | 5 | 7969 |
| apple | 2.30 | 2.0 | 0 | 5 | 6696 |
| unix | 2.55 | 3.0 | 0 | 4 | 6173 |
| security | 2.49 | 2.0 | 0 | 4 | 3069 |
| android | 2.04 | 2.0 | 0 | 4 | 2830 |
| dba | 2.49 | 3.0 | 0 | 4 | 2502 |
| webapps | 1.88 | 2.0 | 0 | 4 | 1906 |
| sharepoint | 2.13 | 2.0 | 0 | 4 | 1691 |
| networkengineering | 2.51 | 3.0 | 0 | 4 | 476 |
| devops | 2.74 | 3.0 | 2 | 4 | 53 |

</div>

If we set the threshold at 3, the situation becomes more critical, as we would lose nearly half of the dataset. Beyond this point, filtering by this index becomes unfeasible, as we would discard question-answer pairs that could still be useful for the system.

<center>

![Score_tech distribution and heatmap by community](images/score_tech_distribution_and_heatmap.png)

</center>

The conclusion is clear: `score_tech` confirms that the corpus is decidedly technical, but filtering by it may not be the best idea. If we are looking for answers for Level 1 support, some may be of low complexity. If we implement a cutoff as low as 2 on this index, we would lose a significant portion of the information from the communities that help resolve those issues.

# Outlier Identification

### Hard Filter: Short Answers

When we analyze data quality and encounter freely given forum answers, we might question the quality of potential responses to trivial questions that contain no relevant or in-depth information. For example, if someone asks how to restart an access point and the answer is "turn your access point off and on again," is it useful for the system we are building? It should not be. A mitigating factor here is the filtering already applied by the dataset authors, which removes answers that do not stand out in quality (less than 100 upvote gap between best and worst). However, one may question whether this heuristic is effective enough to guarantee high-quality question-answer pairs.

To answer this, we analyzed question and answer lengths and concluded that there is room for filtering based on answers, since questions already have a limit set by the platform (4,096 characters for the question body). Therefore, we propose two filters: one that removes question-answer pairs where the answer is shorter than 50 characters — because they are too short to contain useful information — and another that removes pairs where the answer length exceeds the third quartile plus 3 times the interquartile range (Tukey's strict criterion). How many pairs would we lose if we implemented these cuts?

```
Answers below 50 chars (to discard): 604 (0.99%)
IQR: 643 chars
Q3 + 3×IQR far-outlier fence: 2,816 chars
Answers exceeding far fence (documented, retained): 2009 (3.31%)
```

As shown above, only 1% of question-answer pairs have short answers, indicating that the dataset compilers' filtering is good but not perfect.

# Outlier Analysis

### Classification by Content

To verify whether this information is useful or not, we also set out to analyze these outliers to understand whether they are long due to content or whether they are noise without relevant technical value. To this end, we took two approaches: one based on searching for key terms using regular expressions, and another based on the `score_tech` metric defined earlier.

```
=== Content type of answers exceeding Tukey far fence ===

  code_block_with_config           0 (  0.0%)  
  configuration                  146 (  7.3%)  ███
  code_block                      86 (  4.3%)  ██
  log_or_traceback                21 (  1.0%)  
  detailed_prose               1,756 ( 87.4%)  ███████████████████████████████████████████

--- Example: code_block_with_config ---

--- Example: configuration ---
```

The keyword search yields unpromising results: 87.4% of atypically long answers contain neither code, configurations, nor logs. This does not mean they are irrelevant — only that they do not fit those three structural patterns. To determine their technical value, we need another tool.

### Verification with score_tech

To investigate technical relevance, we had previously built the `score_tech` metric, which was more comprehensive than the key terms that searched for code, logs, and configurations.

```
         === score_tech: Outliers vs Rest of Corpus ===
  Outliers (> 2,816 chars):            mean=2.75  median=3.0  n=2,009
  Rest of corpus:                      mean=2.45  median=3.0  n=58,756
  Global:                              mean=2.46  median=3.0  n=60,765
```

<center>

![Score Tech outliers vs rest](images/score_tech_outliers_vs_rest.png)

</center>

Looking at the chart above, we see that the outlier average for this indicator is 2.75, while the average for the rest of the dataset is 2.45, which is consistent with the bar chart showing that outliers have higher `score_tech` values than the rest.

### Sensitivity Analysis: What If We Remove the Length Signals?

Nevertheless, one could argue that the construction of the metric is biased by the very conditions that define an outlier. To address this, we attempted to remove the length-based signals one by one: the answer length bonus (`long_enough_answer`) and the presence of numbered steps in the answer (`has_numbered_steps`). The results show that the relationship between means does not invert: the rest of the data still has a lower mean than the outliers, although the gap narrows with each removal.

<center>

| Score | Range | Outliers | Rest | Δ |
|---|---|---|---|---|
| Full `score_tech` | 0-5 | 2.75 | 2.45 | +0.30 |
| No length bias | 0-3 | 0.93 | 0.75 | +0.18 |
| Question-only | 0-2 | 0.738 | 0.718 | +0.021 |

</center>

In summary: in the worst case, the outliers are as good as the rest of the dataset. Removing them could mean losing valuable information for the system, so implementing a length-based cutoff is not recommended.

# Conclusions and Decisions

### Summary of Findings

The first conclusion is that the dataset is remarkably clean and of notable quality: despite being information extracted from the web, the filtering applied by the original dataset compilers ensures that the question-answer pairs maintain a high quality level according to the various metrics we have obtained and constructed in this exploratory analysis.

Furthermore, answer length is sufficient to allow the system to generate quality responses without being overwhelmed, finding only 3.31% atypically long answers. These atypical answers are not noise — they are as good as the rest of the dataset. Filtering by excessive answer length is not recommended.

Having communities with few examples does not prevent us from having a successful system, since other communities contain relevant information for the topic of interest, as demonstrated in the case of `devops`. Filtering by community may not be the best idea.

Two collateral findings emerged from the analysis: the answer distribution is approximately log-normal, suggesting a hybrid model routing strategy with an estimated ~68% cost savings; and a chunk size of 1,000 characters would keep ~75% of questions in a single chunk.

### Concrete Decisions

* **Full ingestion with a single minimal filter**: 60,765 pairs, removing only the 604 with answers < 50 characters.
* **Do not filter by `score_tech`**: 91.9% of pairs score ≥ 2, and filtering would eliminate diversity without clear quality gain.
* **Do not filter by community**: 98% of DevOps content is outside the `devops` community.
* **Evaluate hybrid model routing** based on answer length (collateral finding, not a design decision).

# Next Steps

With the corpus ready for ingestion, the next steps are:

1. Extend `TicketModel` with Stack Exchange fields (backward compatible).
2. Create an ingestion script with `--dry-run` mode.
3. Load ~60K pairs into Pinecone namespace `kb-se-all`.
4. Build the `qa_pairs` collection in MongoDB.
5. Rebuild the BM25 index.
6. Translate HyDE prompts and KB categories to English.
7. Preserve synthetic data as `kb-synthetic-legacy`.
