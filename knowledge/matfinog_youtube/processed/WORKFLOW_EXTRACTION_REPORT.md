# MatFinOg Workflow Extraction Report
Generated: 2026-05-21 16:13:48

## Purpose
Deterministic extraction of reusable workflow patterns and research prompt candidates from the tagged MatFinOg transcript corpus.

## Files Inspected
- `canonical_transcripts.jsonl`
- `transcript_topic_tags.jsonl`
- `workflow_taxonomy.yaml`

## Processing Summary
- Canonical transcripts processed: 154
- Workflow taxonomy entries: 8
- Videos matched to workflows: 103
- Low-confidence/unknown videos: 51
- Research prompt candidates generated: 366

## Workflow Distribution
| Workflow ID | Video Count | Keywords Matched | Phrases Matched |
|-------------|-------------|------------------|-----------------|
| research_paper_to_backtest_workflow | 42 | 13 | 13 |
| market_inefficiency_hypothesis_workflow | 56 | 33 | 33 |
| risk_first_strategy_review_workflow | 59 | 52 | 52 |
| execution_microstructure_review_workflow | 29 | 37 | 37 |
| ai_assisted_quant_learning_workflow | 52 | 38 | 38 |
| workstation_module_candidate_workflow | 56 | 43 | 43 |
| psychological_process_and_discipline_workflow | 18 | 20 | 20 |
| unknown_or_low_confidence_workflow | 51 | 0 | 0 |

## Prompt Type Distribution
| Prompt Type | Count |
|-------------|-------|
| replication_question | 12 |
| validation_question | 71 |
| risk_review_question | 70 |
| workflow_design_question | 106 |
| workstation_feature_question | 59 |
| research_question | 48 |

## Example Research Prompt Candidates
- **replication_question**: "What specific data points and parameters would be required to replicate the core claims mentioned in this video?" (Source: Is it really TRUE that ORDERFLOW trading cannot be AUTOMATED?)
- **validation_question**: "How can the methodology described here be validated using out-of-sample data to ensure robustness?" (Source: Is it really TRUE that ORDERFLOW trading cannot be AUTOMATED?)
- **risk_review_question**: "What specific risk checks and drawdown limits should be defined before promoting this concept to a strategy candidate?" (Source: Is it really TRUE that ORDERFLOW trading cannot be AUTOMATED?)
- **risk_review_question**: "How does the proposed risk management approach handle tail events or extreme market conditions?" (Source: Is it really TRUE that ORDERFLOW trading cannot be AUTOMATED?)
- **validation_question**: "What metrics (e.g., slippage, fill rate) should be tracked to measure the execution quality of this workflow?" (Source: Is it really TRUE that ORDERFLOW trading cannot be AUTOMATED?)

## Safety & Compliance
- **Financial Advice Generated:** No
- **Trading Signals Generated:** No
- **Broker/Bot Logic Generated:** No
- **Live Trading Automation:** No

This extraction layer is strictly for educational research and workstation workflow planning.

## Limitations
- Deterministic matching relies on keyword presence and may miss context.
- Scoring threshold is simple and may need tuning.
- "Unknown" videos represent content that doesn't fit the current workflow taxonomy.

## Conclusion
The workflow extraction was successful. It is safe to proceed to PRD and planning synthesis.
