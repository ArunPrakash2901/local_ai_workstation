# PRD: Quant Trading Workstation (Updated)

**Version:** 2.0.0
**Status:** DRAFT (MatFinOg-Grounded)
**Owner:** Human Operator / Senior Quant Architect
**Scope:** Research and Paper-Trading Factory

---

## 1. Executive Summary
The Quant Trading Workstation is a specialized lane within the **D:\_ai_brain** control plane. Evolving from its initial focus on execution, it is now designed as a comprehensive, human-supervised quantitative research workstation. It helps transform learning sources, research papers, market-structure ideas, and hypothesis prompts into validated research workflows.

**Core Principle:** AI proposes, Human approves, Software executes.

---

## 2. Product Vision
To provide a local, transparent, and safe environment for developing institutional-grade quantitative strategies. The system acts as a rigorous research coach, enforcing disciplined workflows, risk-first validation, and robust hypothesis testing without the risk of autonomous live capital deployment.

---

## 3. Problem Statement
Developing quantitative strategies often lacks structure, leading to rushed formulation without proper validation, execution analysis, or risk-first thinking. Existing tools fail to provide a structured research scaffold, resulting in overfitting and look-ahead bias. There is a need for a local tool that enforces rigor, organizes research prompts, and validates ideas before they reach a backtester.

---

## 4. Target User
The **Workstation Operator**, acting as a Quant Researcher and Portfolio Manager. They require AI assistance to organize research, replicate papers, and specify strategies while maintaining absolute manual control over risk and execution gates.

---

## 5. MVP Goals
- **Research Idea Intake:** Structured templates for capturing market inefficiencies and academic claims.
- **Strategy Factory:** A repeatable process for taking a hypothesis to a validated strategy specification.
- **Split-Brain Architecture:** Strict separation between generative AI reasoning and deterministic backtesting.
- **Data Lineage:** Traceable data from source to signal.
- **Safety Gates:** Hard human approval points for every promotion level and research phase.
- **MatFinOg Integration:** Utilizing corpus-derived workflows (Risk-First Review, Microstructure Review, Paper Replication) as core system scaffolds.

---

## 6. Non-Goals
- **Trading Bot functionality**
- **Signal Generator functionality**
- **Financial Advisor functionality**
- **Autonomous Execution System**
- **Live Trading Automation:** No capital will be deployed.
- **High-Frequency Trading (HFT)**

---

## 7. Supported Core Workflows (MatFinOg-Inspired)
1. **Market Inefficiency Hypothesis Intake:** Capturing structural constraints and testable ideas.
2. **Research Paper Replication:** Scaffolding the extraction and testing of academic claims.
3. **Risk-First Strategy Review:** Mandatory checklists evaluating sizing, protection, and risk.
4. **Execution/Microstructure Review:** Assessing slippage, spread, and liquidity prior to backtesting.
5. **Strategy Specification:** Drafting YAML/Markdown contracts for human approval.
6. **Walk-Forward Validation:** Testing strategy robustness.
7. **Paper Trading Simulation:** Real-time simulation with daily reconciliation.

---

## 8. Roles & Responsibilities

### AI Responsibilities (Generative)
- Organizing research prompts and drafting structural outlines.
- Converting human intuition into technical specs.
- Extracting testable logic from research papers.
- Highlighting missing validation steps.
- Drafting post-trade review memos.

### Deterministic System Responsibilities (Safety-Critical)
- Enforcing workflow sequences and human approval gates.
- Blocking progression if mandatory risk/validation questions are unanswered.
- Data ingestion and validation (Data Contracts).
- Backtest engine execution.
- Risk limit enforcement (Risk Policy).
- Audit logging and safety tagging.

### Human Responsibilities (Governance)
- Approving all research plans and hypothesis contracts.
- Approving strategy specifications.
- Answering and signing off on all risk and validation checklists.
- Approving promotion to backtest/paper levels.
- Final review of all AI-generated interpretations.

---

## 9. Success Metrics
- **Reproducibility:** 100% of backtests can be reproduced from the experiment manifest.
- **Safety:** Zero instances of generated financial advice, signals, or broker logic. Zero live trades.
- **Rigor:** 100% completion rate for required risk and microstructure checklists before backtesting.
- **Efficiency:** Streamlined translation from research paper/idea to testable strategy spec.

---

## 10. MVP Risks
- **Overfitting:** Despite scaffolding, users may still overfit. (Mitigation: Out-of-sample validation enforcement).
- **AI Hallucination:** AI may hallucinate risk metrics or paper details. (Mitigation: Human-in-the-loop review queue for all generative outputs).
- **Scope Creep:** Temptation to connect live brokers. (Mitigation: Absolute prohibition in the MVP architecture).

---

## 11. Open Questions
- How to best integrate the MatFinOg CLI browser (read-only) seamlessly into the active research formulation UI/TUI?
- What specific statistical measures should be mandatory in the Microstructure Review checklist?
