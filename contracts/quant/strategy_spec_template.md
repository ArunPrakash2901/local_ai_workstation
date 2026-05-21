# Strategy Specification: [STRATEGY_ID]

**Version:** 1.0.0  
**Owner:** [OPERATOR_NAME]  
**Status:** draft_spec

---

## 1. Hypothesis
*Clearly describe the market intuition or anomaly being exploited.*
> Example: "Small-cap momentum tends to persist for 2-4 weeks after a breakout."

---

## 2. Universe Definition
- **Primary Assets:** [List of symbols or ETF tickers]
- **Market:** [e.g., US_ETF, US_EQUITY]
- **Liquidity Filter:** [e.g., Avg Daily Volume > $10M]

---

## 3. Signal Generation
- **Primary Indicator:** [e.g., 20-day EMA]
- **Secondary Filters:** [e.g., Volume trend, RSI]
- **Data Frequency:** [e.g., Daily, Hourly]
- **Calculated Features:**
  - [Feature Name]: [Formula/Logic]

---

## 4. Execution Rules (Logic)

### Entry Rules
- **Condition 1:** [Measurable condition]
- **Condition 2:** [Measurable condition]
- **Action:** [e.g., Buy at Next Open]

### Exit Rules (Profit/Loss)
- **Stop Loss:** [e.g., 2% from entry]
- **Take Profit:** [e.g., 5% from entry]
- **Time-based Exit:** [e.g., After 10 bars]

### Rebalancing
- **Frequency:** [e.g., Daily at Close]
- **Weighting:** [e.g., Equal weight, Vol-weighted]

---

## 5. Risk & Constraints
- **Max Position Size:** [% of NAV]
- **Max Portfolio Gross Exposure:** [% of NAV]
- **Max Correlation:** [Max allowed correlation between any two assets]
- **Kill-Switch Trigger:** [Max drawdown at strategy level]

---

## 6. Cost Model
- **Estimated Commissions:** [e.g., $0.005/share]
- **Estimated Slippage:** [e.g., 1bp]

---

## 7. Mandatory Validation
- [ ] Walk-Forward (60/40 Split)
- [ ] Stress Test (2020 COVID)
- [ ] Parameter Sensitivity (Monte Carlo)

---

## 8. Anti-Hallucination Notes
- **Source of Data:** [UNKNOWN/VERIFIED]
- **Look-ahead Check:** [PASSED/PENDING]
- **Survivorship Check:** [PASSED/PENDING]
