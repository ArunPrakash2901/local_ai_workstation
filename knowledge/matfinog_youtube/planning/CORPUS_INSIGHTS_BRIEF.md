# Corpus Insights Brief

## Purpose of the Corpus
The MatFinOg YouTube corpus was ingested to map and extract recurring quant research workflows, discipline frameworks, and learning modules. The purpose is to ground the design of a local, safe AI-assisted quantitative research and paper-trading module. 

## Corpus Processing Status
- **Canonical Transcripts Processed:** 154
- **Workflow Taxonomy Entries:** 8
- **Videos Matched to Workflows:** 103
- **Low-Confidence / Unknown Videos:** 51
- **Research Prompt Candidates Generated:** 366

## Major Topic Distribution
Based on `topic_index.csv`:
- Risk Management: 35 videos
- General Market Commentary: 29 videos
- Execution and Microstructure: 29 videos
- Backtesting and Validation: 25 videos
- Options and Protection: 21 videos
- Trading Psychology and Process: 18 videos
- AI Assisted Research Workflow: 13 videos
- Research Paper Replication: 6 videos
- Market Structure Inefficiency: 6 videos
- Crypto Market Structure: 3 videos
- Unknown/Uncategorized: 53 videos

## Major Workflow Distribution
Based on `workflow_index.csv`:
- **Risk-First Strategy Review:** 59 videos
- **Market Inefficiency Hypothesis:** 56 videos
- **Workstation Module Candidate:** 56 videos
- **AI-Assisted Quant Learning:** 52 videos
- **Research Paper to Backtest:** 42 videos
- **Execution Microstructure Review:** 29 videos
- **Psychological Process and Discipline:** 18 videos
- **Unknown/Low Confidence:** 51 videos

## Prompt Type Distribution
Out of 366 prompt candidates:
- Workflow Design Question: 106
- Validation Question: 71
- Risk Review Question: 70
- Workstation Feature Question: 59
- Research Question: 48
- Replication Question: 12

## Strongest Workstation-Relevant Themes
The corpus strongly supports building tools around **risk-first reviews** and **hypothesis validation**. The significant presence of prompts focused on workflow design and risk checks indicates that the workstation should provide scaffolding that forces the user to answer risk and validation questions *before* formulating strategy code. The "Research Paper to Backtest" workflow provides a clear structural blueprint for a feature.

## Gaps and Limitations
- The corpus does not provide granular code for live execution.
- It is heavily weighted towards conceptual frameworks rather than complete out-of-the-box strategies.
- 51 videos are categorized as low confidence, meaning noise exists in the data and deterministic matching has limits.

## What the Corpus Supports
- Learning and research workflow planning.
- Designing prompt scaffolds for validating hypotheses.
- Structuring paper-trading risk analysis.
- Understanding the psychological discipline of quant research.

## What the Corpus Does NOT Support
- Direct trade generation.
- Real-time market prediction.
- Providing specific financial advice.
- Supplying pre-built, foolproof strategies.

## Safety Boundaries
- **No financial advice generated.**
- **No trading signals generated.**
- **No investment recommendations generated.**
- **No broker logic generated.**
- **No bot logic generated.**
- **No live trading automation generated.**
