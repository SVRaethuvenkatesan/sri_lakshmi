# Enterprise Data Wrangling & Quality Pipeline

A complete, production-grade Data Engineering pipeline built to wrangle, clean, and validate a highly messy, multi-table enterprise dataset (Sri Lakshmi Textiles).

Unlike standard tutorials that rely on simple `.dropna()` calls, this project demonstrates how to handle **real-world data corruption**—from mathematical staleness and cross-table referential integrity failures, to hidden running-balance spikes and zero-clamping drifts.

## 🏗️ Architecture: The 6-Stage Framework

This pipeline strictly adheres to the 6-stage industry standard for data wrangling, ensuring that no data is enriched or validated until it is structurally and statistically sound.

1. **Discovery:** Automated profiling of the raw data (shape, missingness, distribution).
2. **Structuring:** Enforcing strict data types (Pandas `Nullable Int64`, `category`, explicit `datetime`) and verifying the target granularity (e.g., `transaction_id + product_id`).
3. **Cleaning:** Targeted resolution of anomalies.
    - Mathematical reconciliation (Gross vs. Net amounts respecting negative returns logic).
    - IQR and 99th-percentile capping for fat-finger quantity errors and salary outliers.
    - Advanced isolated spike detection on continuous running balances (excluding natural `Stockout` clamping drifts).
    - Canonical mapping for whitespace/case categorical typos.
4. **Enriching:** Calculating derived P&L columns (`gross_margin`), SLA performance (`days_to_deliver`), and business flags (`is_wholesale_bulk`).
5. **Validating:** Enforcing cross-table integrity.
    - Validating facts against dimension tables (identifying Orphan Employees, Orphan Stores).
    - Aggregate reconciliation (ensuring Daily Settlement totals match individual Sales receipts).
6. **Publishing:** Exporting fully typed, pristine `_clean.csv` files alongside a detailed `quarantined_fact_sales.csv` and a completely transparent pipeline summary reporting exact *Values Corrected*.

## 🛡️ The Quarantine System

A core philosophy of this pipeline is that **data is never silently dropped**. 

Rows with unrecoverable logic errors (e.g., a sale billed to a `store_id` that doesn't exist, or sales leaking from a future date) are strictly isolated and routed to a dedicated `quarantined_fact_sales.csv` artifact along with their `quarantine_reason`. This ensures analysts know *exactly* what was excluded and why.

## 📂 Repository Structure

```text
├── data/
│   ├── raw/                 # The 11 messy input CSVs
│   ├── clean/               # The 11 pristine output CSVs
│   └── quarantine/          # Isolated, unrecoverable data
├── src/
│   └── data_wrangling.py    # The master 6-Stage ETL script
├── sql/
│   ├── schema.sql           # PostgreSQL Star Schema definition
│   ├── load_data.sql        # COPY commands for bulk loading
│   └── analytics_queries.sql
├── PowerBI_Guide.md         # Full implementation guide for the Power BI dashboard
├── .gitignore               
└── README.md
```

## 🚀 How to Run

1. Ensure Python 3.8+ and `pandas` are installed.
2. Run the master pipeline script:
```bash
python src/data_wrangling.py
```
3. The pipeline will output a comprehensive `FINAL PIPELINE SUMMARY` to the console detailing exact row counts and values corrected, and write the pristine datasets to `data/clean/`.
