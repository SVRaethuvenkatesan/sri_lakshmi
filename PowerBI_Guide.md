# Phase 5: Power BI — Full Guide

Everything from connecting your data through the final dashboard. Phase 4 (SQL) is done — this assumes clean data already sitting in PostgreSQL or as _clean CSVs.

## 5.1 Connect to your data

**Option A — PostgreSQL directly (stronger portfolio story: one connected pipeline)**
Power BI Desktop → Home ribbon → Get Data → More... → search "PostgreSQL"
You need the Npgsql driver installed separately first — Power BI's PostgreSQL connector doesn't bundle it. If the connector fails silently or can't find a driver, this is almost always why. Download from Npgsql's official releases.
Enter server (localhost), database (sri_lakshmi), and choose Import mode, not DirectQuery — your data is a static 4-year history, not something that needs live re-querying on every click.
Select all 12 tables (11 + fact_sales_quarantine) and load.

**Option B — Import the _clean CSVs directly**
Get Data → Text/CSV, one at a time, or Folder if all 11 files sit in one directory
Simpler, no live dependency on Postgres running — reasonable choice if you want the .pbix file to open standalone

Either way, load all 12 tables, including `fact_sales_quarantine` as its own table.

## 5.2 Power Query — light pass only

Python already did the actual cleaning. This step is verification, not re-cleaning:

In Power Query Editor, click through each table and confirm the data type icon on each column header matches intent:
- Dates → Date (not Text — this bites people constantly, especially with CSV imports)
- net_amount, unit_price, etc. → Fixed Decimal Number
- product_id, customer_id, etc. → Whole Number
- Power BI's auto-detection is frequently wrong on first import — don't assume it guessed correctly just because it didn't error
- Rename any table Power BI mangled (e.g., fact_sales (2)) back to the clean name
- Don't merge tables here. Each of the 12 stays separate — relationships get built in Model view, not Power Query. Merging defeats the star schema.
- Close & Apply

## 5.3 Model view — build the relationships

Go to the Model view (left sidebar, the icon that looks like connected boxes).

Drag to connect, one direction, `fact_sales` → each dimension:
- `fact_sales[product_id]` → `dim_product[product_id]`
- `fact_sales[customer_id]` → `dim_customer[customer_id]`
- `fact_sales[employee_id]` → `dim_employee[employee_id]`
- `fact_sales[store_id]` → `dim_store[store_id]`
- `fact_sales[date_id]` → `dim_date[date_id]`
- `fact_sales[promotion_id]` → `dim_promotion[promotion_id]`

Also connect the other fact tables to their relevant dimensions:
- `fact_stock[product_id]`, `fact_purchase_order[product_id]` → `dim_product[product_id]`
- `fact_opex[store_id]` → `dim_store[store_id]`

Leave `fact_sales_quarantine` unconnected — it's for its own summary card, not for joining into the main model (its foreign keys are, by definition, the ones that failed validation).

Check each relationship is one-to-many (dimension side = one, fact side = many) and single direction — Power BI defaults to this correctly most of the time, but verify rather than assume.

## 5.4 DAX measures — create a dedicated measure table first

Modeling tab → New Table, name it `_Measures`, formula: `_Measures = {1}` (a dummy table just to hold measures cleanly, not scattered across real tables). Then Modeling tab → New Measure for each of these:

### Core sales
```dax
Total Revenue = SUM(fact_sales[net_amount])

Avg Basket Value = DIVIDE([Total Revenue], DISTINCTCOUNT(fact_sales[invoice_number]))

YoY Growth % = 
VAR CurrYear = [Total Revenue]
VAR PrevYear = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[date_id]))
RETURN DIVIDE(CurrYear - PrevYear, PrevYear)

Category Contribution % = DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALL(dim_product[category])))

Digital Payment % = DIVIDE(CALCULATE([Total Revenue], fact_sales[payment_mode] = "UPI"), [Total Revenue])
```

### Brand & pricing
```dax
Price Tier Mix % = DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALL(dim_product[price_tier])))

Named Brand Revenue Share = 
DIVIDE(
    CALCULATE([Total Revenue], dim_product[brand_name] <> "Unbranded", dim_product[brand_name] <> "House Brand"), 
    [Total Revenue])
```

### Customers
```dax
Top 20 Customer Revenue Share = 
VAR Top20 = TOPN(20, VALUES(dim_customer[customer_id]), [Total Revenue])
RETURN DIVIDE(CALCULATE([Total Revenue], Top20), [Total Revenue])
```

### Inventory & supply chain
```dax
Stock Turnover Ratio = DIVIDE(SUM(fact_sales[quantity]), AVERAGE(fact_stock[stock_on_hand]))

Stockout Rate = 
DIVIDE(CALCULATE(COUNTROWS(fact_stock), fact_stock[event_type] = "Stockout"), COUNTROWS(fact_stock))

PO Delay Rate = 
DIVIDE(
    CALCULATE(COUNTROWS(fact_purchase_order), fact_purchase_order[actual_delivery_date] > fact_purchase_order[expected_delivery_date]), 
    COUNTROWS(fact_purchase_order))
```

### Costs & profitability
```dax
Total OPEX = SUM(fact_opex[amount])

Gross Margin = 
SUMX(fact_sales, fact_sales[quantity] * (RELATED(dim_product[unit_price]) - RELATED(dim_product[unit_cost])))

Gross Margin % = DIVIDE([Gross Margin], [Total Revenue])

Operating Margin = [Gross Margin] - [Total OPEX]

Operating Margin % = DIVIDE([Operating Margin], [Total Revenue])

Revenue per Employee = 
DIVIDE([Total Revenue], 
    CALCULATE(SUM(fact_opex[headcount]), fact_opex[expense_type] IN {"Salary-Permanent", "Salary-Seasonal"}))
```

### Data quality (put this on the dashboard itself, not just in a log)
```dax
Quarantine Rate = 
DIVIDE(COUNTROWS(fact_sales_quarantine), COUNTROWS(fact_sales_quarantine) + COUNTROWS(fact_sales))
```

## 5.5 The 9 dashboard pages

For each: what it answers, and which of the 30 stakeholder questions it's defensible against if asked "why does this page exist."

| Page | Key visuals | Measures used |
|---|---|---|
| 1 | Executive Summary | KPI cards, 4-year revenue trend line (2020-21 gap shown honestly, not hidden), category donut | Total Revenue, YoY Growth %, Avg Basket Value |
| 2 | Seasonality & Festivals | Month × year heatmap, Aadi discount overlay | Total Revenue, Discount Impact |
| 3 | Category Deep-Dive | Silks / Men's / Women's / Kids / Textiles trend lines | Category Contribution %, YoY Growth % |
| 4 | Brand Performance | Price-tier mix over time, named-brand share | Price Tier Mix %, Named Brand Revenue Share |
| 5 | Inventory & Stock Health | Stockout timeline, PO delay by hub, dead-stock table | Stock Turnover Ratio, Stockout Rate, PO Delay Rate |
| 6 | Customer Analytics | Top-20 table, Pareto/concentration chart, customer-type split | Top 20 Customer Revenue Share |
| 7 | COVID Impact | Pre/post comparison, Jan-Feb 2022 caution window detail, payment-mode shift | Digital Payment %, Category Contribution % (filtered) |
| 8 | Competitor Benchmarking | Static reference table/chart vs. Maharaja/Anantham/Saravana Stores | (reference data, not live measures) |
| 9 | Costs & Profitability | OPEX breakdown, gross/operating margin trend, revenue-per-employee | Gross Margin %, Operating Margin %, Revenue per Employee, Quarantine Rate |

Build in this order — page 1 first (it's the simplest sanity check that your measures and relationships actually work), page 9 last (it depends on the most tables being correctly related).

## 5.6 Common failure points, before you hit them
- A visual shows blank or (Blank) → almost always a relationship pointing the wrong direction, or a measure referencing a table that isn't actually related to what's on the visual
- YoY Growth % shows blank for 2022 → correct behavior, not a bug — SAMEPERIODLASTYEAR has nothing to compare against 2022 since 2021 doesn't exist in dim_date
- Gross Margin looks wrong → check `dim_product[unit_cost]` and `[unit_price]` loaded as Decimal, not Text — a text-typed number multiplies as an error or a blank, not a wrong number, so this one usually shows up loud

## 5.7 The professional way — not just the steps, the habits

1. **Hide technical columns from the report view**: Right-click `product_id`, `customer_id`, `employee_id`, `store_id`, `promotion_id`, `date_id` in every table → Hide in Report View. End users (or an interviewer clicking through your dashboard) should see Item Name and Brand, never a raw foreign key. Keep them visible in Model view where relationships live — just hidden from anyone building or viewing a visual.

2. **Organize measures into Display Folders, not one flat list**: Right-click each measure → Properties → Display Folder: group into Sales, Profitability, Inventory, Customer, Data Quality. A `_Measures` table with 18 measures in one undifferentiated list is exactly what marks a first draft — folders are what a reviewer expects to see.

3. **Add a Description to every measure**: Same Properties panel — one sentence explaining what it calculates and why. Revenue per Employee should say "Total revenue divided by active headcount that month — used to check whether the Deepavali staffing surge is actually revenue-efficient." Anyone opening this file cold — including you, in six months — shouldn't have to reverse-engineer the DAX to know what a measure is for.

4. **Consistent formatting, set once, not per-visual**: Set each measure's format string at the measure level (currency with ₹ symbol for revenue fields, percentage with 1 decimal for rate fields) rather than fixing it separately on every visual that uses it. Inconsistent decimal places or currency symbols across pages is the fastest way a dashboard reads as unfinished.

5. **Apply a real theme, not the default palette**: View tab → Themes → pick one, or build a custom JSON theme matching a consistent color logic (e.g., teal for data-engineering-related pages, amber for BI/profitability pages — the same scheme already used in your workflow diagram). Default Power BI colors are instantly recognizable as "didn't customize this."

6. **Validate against SQL before trusting a visual**: Every number on the dashboard should be checkable against the Phase 4 SQL queries. Pick 2-3 measures, cross-reference the visual's number against the equivalent SQL query's output. If they don't match, the bug is in the DAX or the relationships — not something to notice for the first time when someone else asks about it.

7. **Version control for a binary file**: `.pbix` is binary — git can't diff it meaningfully. Professional practice: dated filenames or folder snapshots at real milestones (`sri_lakshmi_v1_dashboard_complete.pbix`), not relying on git history the way you would for the Python scripts.

8. **Publish, don't just keep it local**: A `.pbix` sitting on your laptop isn't a finished deliverable in a real job — the professional endpoint is publishing to the Power BI Service (app.powerbi.com, free tier is enough) so it's a shareable link, not a file someone has to be sent and open themselves.
