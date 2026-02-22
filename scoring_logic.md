# Stability Scoring Methodology

The "Financial Stability Benchmarking" chart provides a normalized score (0-100) for four key financial indicators. A score of **60** represents the "Healthy Threshold" or industry standard.

## 1. Liquidity (Current Ratio)
*   **Metric**: `Current Assets / Current Liabilities`
*   **Benchmark**: **1.20**
*   **Calculation**: `(Current Ratio / 1.2) * 60`
*   **Assessment**: A current ratio of 1.2 means the company has 20% more current assets than liabilities. If this value is `0.00`, it typically indicates missing data in the report or a severe liquidity crisis.

## 2. Solvency (Debt to Equity)
*   **Metric**: `Total Liabilities / Total Shareholder Equity`
*   **Benchmark**: **2.00**
*   **Calculation**: 
    *   If Ratio ≤ 2.0: `60 + ((2.0 - Ratio) / 2.0) * 40` (Excellent stability)
    *   If Ratio > 2.0: `60 - ((Ratio - 2.0) / 2.0) * 60` (Rising risk)
*   **Assessment**: Values below 2.0 are considered manageable for most industries.

## 3. Market Risk (Beta)
*   **Metric**: Stock volatility relative to the S&P 500.
*   **Benchmark**: **1.30**
*   **Calculation**:
    *   If Beta ≤ 1.3: `60 + ((1.3 - Beta) / 1.3) * 40`
    *   If Beta > 1.3: `60 - ((Beta - 1.3) / 1.3) * 60`
*   **Assessment**: Lower Beta indicates higher stability. A beta of 1.0 matches the market; 1.3 is the threshold for "High Volatility".

## 4. Confidence (Ownership)
*   **Metric**: Percentage of stock held by Insiders (Founders/Executives).
*   **Benchmark**: **10%** (Revised from 50%)
*   **Calculation**: `(Ownership % / 10) * 60`
*   **Assessment**: High insider ownership suggests alignment between management and shareholders. For large-cap stocks like IBM, 5-10% is significant; 50% is rare outside of founder-led startups.

---

> [!NOTE]
> **Data Sources**: These values are fetched in real-time from the **Alpha Vantage OVERVIEW API**. If a value is missing (N/A), the score defaults to 0.
