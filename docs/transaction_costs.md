# Transaction-Cost Engine Specification & Verified Schedules

This document specifies the transaction-cost model implemented in `packages/core/kairos_core/costs.py` for **Indian NSE Cash Equities Intraday Trading**.

---

## 1. Scope & Supported Transaction Types

* **Market Segment:** National Stock Exchange of India (NSE) Capital Market (Cash Equity).
* **Product Type:** Intraday (MIS / Margin Intraday Square-off).
* **Transaction Legs:**
  * **Long Intraday:** Buy order (entry), followed by Sell order (square-off) on the same trading day.
  * **Short Intraday:** Sell order (short entry), followed by Buy order (cover square-off) on the same trading day.
* **Operating Currency:** Indian Rupee (`INR` / `₹`).
* **Arithmetic Precision:** Arbitrary-precision financial arithmetic via Python's standard `decimal.Decimal` module (eliminating binary IEEE-754 floating-point inaccuracies).

---

## 2. Statutory, Regulatory & Exchange Charges

The cost engine models all six standard components of Indian equity transaction friction, distinguishing legally verified rates from configurable assumptions:

| Charge | Statutory Authority / Primary Source | Verified Rate | Applicable Leg & Base | Verification Date & Status |
| :--- | :--- | :--- | :--- | :--- |
| **STT** (Securities Transaction Tax) | Income Tax Department / Finance Act (Chapter VII) | **0.025%** (`0.00025`) | **SELL leg turnover only** (Buy leg is exempt) | Confirmed (Unchanged in Union Budget 2024 for cash intraday) |
| **Exchange Txn Charge** | National Stock Exchange (NSE) / SEBI Circular `SEBI/HO/MRD/TPD-1/P/CIR/2024/92` | **₹2.97 per lakh** (`0.00297%` / `0.0000297`) | **Both BUY and SELL** turnover | Confirmed (Effective Oct 1, 2024 under SEBI "True to Label" mandate) |
| **SEBI Turnover Fee** | SEBI (Stock Brokers) Regulations, 1992 (Schedule III) | **₹10 per crore** (`0.0001%` / `0.000001`) | **Both BUY and SELL** turnover | Confirmed |
| **Stamp Duty** | Indian Stamp Act, 1899 (amended via Finance Act 2019) | **0.003%** (`0.00003` / ₹300 per crore) | **BUY leg turnover only** (Sell leg is exempt) | Confirmed (Uniform nationwide rate effective July 1, 2020) |
| **GST** (Goods & Services Tax) | Central & State GST Acts / CBIC Guidance | **18.0%** (`0.18`) | **Brokerage + Exchange Txn Charges + SEBI Fees** | Confirmed (Statutory taxes STT and Stamp Duty are strictly excluded) |
| **Brokerage** | Contractual broker tariff schedule | Configurable (e.g., lower of 0.03% or ₹20/order) | Per executed order / leg turnover | Configurable parameter (varies by broker) |
| **IPFT** (Investor Protection Fund) | NSE circulars | Configurable (`additional_charges_rate`, default `0.00`) | Both legs turnover | Provisional / Configurable |

---

## 3. Verified Sources & Statutory References

1. **Exchange Transaction Charges (True-to-Label Flat Fee):**
   * *Source:* SEBI Circular No. `SEBI/HO/MRD/TPD-1/P/CIR/2024/92` dated July 1, 2024.
   * *NSE Implementation:* Circular Ref No. `NSE/INSP/64256` / press circular on revised charges effective October 1, 2024.
   * *Mandate:* Discontinued volume-based rebate slabs and established a uniform flat rate of **₹2.97 per lakh** (`0.00297%`) for the cash equity segment.
2. **Securities Transaction Tax (STT):**
   * *Source:* Government of India, Ministry of Finance, Department of Revenue / Income Tax Act, 1961.
   * *Rule:* For non-delivery equity intraday transactions, STT is payable at **0.025%** by the seller on the value of the sale transaction.
3. **Stamp Duty:**
   * *Source:* Ministry of Finance Notification, The Indian Stamp (Collection of Stamp-Duty through Stock Exchanges, Clearing Corporations and Depositories) Rules, 2019 (effective July 1, 2020).
   * *Rule:* Levied at **0.003%** on the buyer on the transfer of securities other than delivery.
4. **Goods and Services Tax (GST):**
   * *Source:* Central Board of Indirect Taxes and Customs (CBIC).
   * *Rule:* Standard 18% GST applies to fees for services (brokerage commissions and transaction levies). Taxes (STT and Stamp Duty) are sovereign levies and do not form part of the taxable base for GST.

---

## 4. Brokerage Tariff Configuration

Because brokerage varies across brokers and plans, `BrokerageConfig` supports four distinct tariff models:

1. **`PERCENT_WITH_CAP` (Default Discount Broker):**
   $$\text{Brokerage} = \max(\text{min\_per\_order}, \min(\text{rate} \times \text{turnover}, \text{per\_order\_cap}))$$
   *Example (Angel One / Zerodha standard):* `rate = Decimal("0.0003")` (0.03%), `per_order_cap = Decimal("20.00")`, `min_per_order = Decimal("0.00")`.
2. **`FLAT_PER_ORDER`:**
   $$\text{Brokerage} = \text{per\_order\_cap}$$
   *Example:* Fixed ₹20 per executed order regardless of volume.
3. **`PERCENT_OF_TURNOVER`:**
   $$\text{Brokerage} = \text{rate} \times \text{turnover}$$
   *Example (Traditional percentage broker):* Flat 0.05% or 0.10% without cap.
4. **`ZERO`:**
   $$\text{Brokerage} = 0$$
   *Example:* Zero-brokerage promotional plans.

---

## 5. Rounding Conventions

Indian retail contract notes calculate statutory levies down to two decimal places (paise) using standard financial rounding (`ROUND_HALF_UP`). 

`RoundingPolicy` supports three modes:
1. **`ROUND_EACH_COMPONENT` (Default):** Quantizes each individual fee component (brokerage, STT, exchange charges, SEBI fees, stamp duty, GST, slippage) to `0.01` with `ROUND_HALF_UP`. The explicit total is the exact sum of these rounded components.
2. **`ROUND_TOTAL_ONLY`:** Maintains unrounded `Decimal` values throughout all component evaluations, rounding only the final aggregate explicit charges and all-in friction to `0.01`.
3. **`NO_ROUNDING`:** Preserves exact fractional decimal precision without quantization (useful for quantitative simulation analysis).

---

## 6. Slippage Accounting & Double-Counting Prevention

Execution slippage is the adverse difference between the benchmark/reference price (e.g., signal price, bar close) and the executed fill price.

### Convention:
* **BUY Leg:** Adverse execution fills *higher* than reference price:
  $$\text{Slippage Monetary Impact} = (\text{Fill Price} - \text{Reference Price}) \times \text{Quantity} \ge 0$$
* **SELL Leg:** Adverse execution fills *lower* than reference price:
  $$\text{Slippage Monetary Impact} = (\text{Reference Price} - \text{Fill Price}) \times \text{Quantity} \ge 0$$

### Basis Points Modeling (`estimate_slippage`):
When estimating slippage in basis points ($1 \text{ bps} = 0.0001 = 0.01\%$):
* $\text{Estimated Buy Fill} = \text{Ref Price} \times \left(1 + \frac{\text{bps}}{10000}\right)$
* $\text{Estimated Sell Fill} = \text{Ref Price} \times \left(1 - \frac{\text{bps}}{10000}\right)$

### Prevention of Double Counting:
1. **Explicit Charges:** Sum of brokerage, STT, exchange charges, SEBI fees, stamp duty, and GST.
2. **Slippage Impact:** The adverse price execution penalty.
3. **All-In Friction:** $\text{Explicit Charges} + \text{Slippage Impact}$.
4. **Gross P&L at Fill:** Calculated using effective fill prices:
   $$\text{Gross P\&L (Long)} = (\text{Exit Fill Price} - \text{Entry Fill Price}) \times \text{Quantity}$$
5. **Net P&L:**
   $$\text{Net P\&L} = \text{Gross P\&L at Fill} - \text{Explicit Charges}$$
   > **Critical Rule:** Because $\text{Gross P\&L at Fill}$ already incorporates the adverse fill price difference, **slippage is not subtracted again**. Doing so would penalize the trade twice for execution friction.

---

## 7. Fully Worked Reference Example

### Scenario:
* **Trade:** Long intraday trade on 20 shares of stock $X$.
* **Entry:** BUY 20 shares @ ₹500.00 (Reference = Fill).
* **Exit:** SELL 20 shares @ ₹505.00 (+1.00% gross price movement).
* **Brokerage Config:** Lower of 0.03% or ₹20.00.
* **Verified Schedule:** `CostConfig.default_nse_intraday()` (Oct 1, 2024).

### Step-by-Step Intermediate Calculations:

#### 1. Buy Leg (Entry):
* **Turnover:** $20 \times 500.00 = ₹10,000.00$
* **Brokerage:** $\min(10,000.00 \times 0.0003, 20.00) = \min(3.00, 20.00) = ₹3.00$
* **STT:** $₹0.00$ (exempt on buy leg)
* **Exchange Txn Charge:** $10,000.00 \times 0.0000297 = 0.297 \to ₹0.30$
* **SEBI Turnover Fee:** $10,000.00 \times 0.000001 = 0.01 \to ₹0.01$
* **Stamp Duty:** $10,000.00 \times 0.00003 = 0.30 \to ₹0.30$
* **GST Base:** $\text{Brokerage } (3.00) + \text{Exchange } (0.30) + \text{SEBI } (0.01) = ₹3.31$
* **GST (18%):** $3.31 \times 0.18 = 0.5958 \to ₹0.60$
* **Buy Explicit Charges:** $3.00 + 0.00 + 0.30 + 0.01 + 0.30 + 0.60 = \mathbf{₹4.21}$

#### 2. Sell Leg (Exit):
* **Turnover:** $20 \times 505.00 = ₹10,100.00$
* **Brokerage:** $\min(10,100.00 \times 0.0003, 20.00) = \min(3.03, 20.00) = ₹3.03$
* **STT:** $10,100.00 \times 0.00025 = 2.525 \to ₹2.53$
* **Exchange Txn Charge:** $10,100.00 \times 0.0000297 = 0.29997 \to ₹0.30$
* **SEBI Turnover Fee:** $10,100.00 \times 0.000001 = 0.0101 \to ₹0.01$
* **Stamp Duty:** $₹0.00$ (exempt on sell leg)
* **GST Base:** $\text{Brokerage } (3.03) + \text{Exchange } (0.30) + \text{SEBI } (0.01) = ₹3.34$
* **GST (18%):** $3.34 \times 0.18 = 0.6012 \to ₹0.60$
* **Sell Explicit Charges:** $3.03 + 2.53 + 0.30 + 0.01 + 0.00 + 0.60 = \mathbf{₹6.47}$

#### 3. Combined Round-Trip Totals:
* **Combined Turnover:** $10,000.00 + 10,100.00 = ₹20,100.00$
* **Total Explicit Charges:** $4.21 + 6.47 = \mathbf{₹10.68}$
* **Gross P&L:** $(505.00 - 500.00) \times 20 = \mathbf{₹100.00}$
* **Realized Net P&L:** $100.00 - 10.68 = \mathbf{₹89.32}$
* **Friction Drag:** $10.68 / 100.00 = 10.68\%$ of gross profit consumed by trading friction.

---

## 8. Known Limitations

1. **Broker Contract Note Aggregation:** Real contract notes aggregate all trades executed during a session. Certain brokers calculate stamp duty and GST across the day's aggregated ledger rather than on an isolated trade-by-trade basis, which can lead to fractional 1–2 paise rounding differences across a full day.
2. **Call & Trade Charges:** Broker administrative fees (such as auto-square-off charges of ₹50 + GST if positions are not closed before 15:15 IST) are operational penalties and are not modeled in basic trade execution friction.
3. **Auction / Short Delivery Risk:** Intraday short positions that fail to square off due to lower circuit locks face exchange auction penalties (typically 20%+). The recommender engine will guard against circuit locks in subsequent risk modules.

---

## 9. How Future Systems Reuse This Engine

The cost engine is purely functional, stateless, and thread-safe. Both the historical backtesting engine and the live paper trading worker import the shared methods directly from `kairos_core`:

```python
from decimal import Decimal
from kairos_core.costs import (
    CostConfig,
    TransactionLeg,
    TransactionSide,
    calculate_round_trip_costs,
)

# 1. Instantiate the verified schedule (shared across backtest and live)
config = CostConfig.default_nse_intraday(slippage_bps=Decimal("2.0"))

# 2. Define opening and closing trade legs
entry = TransactionLeg(side=TransactionSide.BUY, quantity=10, price=Decimal("1500.00"))
exit_leg = TransactionLeg(side=TransactionSide.SELL, quantity=10, price=Decimal("1515.00"))

# 3. Calculate exact transaction friction and net return
breakdown = calculate_round_trip_costs(entry, exit_leg, config)

print(f"Explicit Charges: ₹{breakdown.explicit_charges}")
print(f"Slippage Impact:  ₹{breakdown.slippage_impact}")
print(f"Realized Net P&L: ₹{breakdown.net_pnl}")
```
