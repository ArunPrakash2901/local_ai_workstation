# MatFinOg Research Notebook

## 1. Notebook Metadata
- **notebook_id:** `NB-P--2-vE-EbqBI-20260521`
- **created_at:** `2026-05-21T10:00:00Z`
- **source_prompt_id:** `P--2-vE-EbqBI-research_paper_to_backtest_workflow-2`
- **source_workflow_id:** `research_paper_to_backtest_workflow`
- **source_topic_ids:** `["research_paper_replication", "backtesting_and_validation"]`
- **source_video_id:** `-2-vE-EbqBI`
- **source_title:** `Is it really TRUE that ORDERFLOW trading cannot be AUTOMATED?`
- **source_url:** `https://www.youtube.com/watch?v=-2-vE-EbqBI`
- **human_owner:** `HUMAN_REQUIRED`
- **status:** `draft_learning_note`

## 2. Research Framing
- **Learning Objective:** Understand the requirements and methodology for validating an orderflow trading hypothesis out-of-sample.
- **Source Idea in My Own Words:** When optimizing strategy parameters in-sample, we must validate those exact parameters on unseen, out-of-sample data to ensure the performance is robust and not just overfitted to historical noise.
- **What is Being Investigated:** The mechanism of splitting data into in-sample optimization sets and out-of-sample validation sets for quantitative research.
- **What is NOT Being Claimed:** This notebook does not claim that orderflow trading is profitable or that any specific parameters are valid.
- **Why This Matters for Learning:** Prevents curve-fitting and establishes a statistically sound foundation for any future hypothesis testing.

## 3. Evidence and Source Grounding
- **Source Evidence Snippet:**
  > "...ple. Optimize the strategy in sample to find the parameters that maximize your performance and then validate the parameters that you have found out of sample to minimize the risk of overfeitting. And once you..."
- **Related Prompt Text:** "How can the methodology described here be validated using out-of-sample data to ensure robustness?"
- **Related Workflow:** `research_paper_to_backtest_workflow`
- **Related Topic Tags:** `["research_paper_replication", "backtesting_and_validation"]`
- **Additional Sources Required:** Standard texts on quantitative backtesting (e.g., Marcos Lopez de Prado's Advances in Financial Machine Learning) regarding out-of-sample validation.
- **Source Quality Notes:** The source provides high-level structural advice on quantitative workflows.

## 4. Hypothesis Discipline
- **Possible Research Question:** What is the optimal ratio of in-sample to out-of-sample data when evaluating intraday orderflow metrics?
- **Testable Hypothesis Draft:** Strategies optimized on 70% in-sample data will show less than a 50% drop in Sharpe Ratio on the remaining 30% out-of-sample data, compared to their in-sample performance, if the underlying phenomenon is stationary.
- **Required Data:** High-frequency, tick-level orderflow data.
- **Assumptions:** Orderflow patterns exhibit some degree of stationarity across the chosen timeframes.
- **Unknowns:** The specific market regimes present in the hypothetical out-of-sample data.
- **Failure Conditions:** If the out-of-sample Sharpe Ratio drops below 0 or degrades completely compared to the in-sample period.

## 5. Validation Plan
- **Data Checks Required:** Check for missing ticks, proper timezone alignments, and split integrity.
- **Backtest Requirements (If Later Approved):** Strict separation of training (in-sample) and testing (out-of-sample) periods. No overlapping rolling windows without proper embargoes.
- **Robustness Checks:** Walk-forward optimization analysis.
- **Risk Checks:** Maximum drawdown metrics across both in-sample and out-of-sample periods.
- **Lookahead/Survivorship Bias Checks:** Ensure out-of-sample data is strictly chronologically subsequent to in-sample data.
- **Transaction Cost/Slippage Considerations:** Must include simulated exchange fees and bid-ask spread crossing costs.
- **Human Approval Required Before Implementation:** YES - required before any data is acquired or tests run.

## 6. Safety Boundary
**WARNING AND DISCLAIMER:**
- This notebook is **NOT** financial advice.
- This notebook does **NOT** contain trading signals.
- This notebook does **NOT** recommend trades.
- This notebook does **NOT** authorize backtests.
- This notebook does **NOT** authorize broker execution.
- This notebook does **NOT** authorize live trading.

## 7. Next Action
Select ONE allowed action (delete others):
- [x] keep as learning note
- [ ] request human review
- [ ] request research plan draft
- [ ] request data requirement analysis
- [ ] reject/archive
- [ ] promote to future quant research backlog only after human approval

**FORBIDDEN NEXT ACTIONS (DO NOT USE):**
- place trade
- generate trading signal
- create broker order
- run live trading automation
- present as investment recommendation
