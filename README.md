# Sri Lakshmi Textiles — Retail Analytics Pipeline

A full data pipeline I built end to end: Python for generating and cleaning the data, PostgreSQL for the warehouse, Power BI for the dashboard. It analyzes 4 years of sales for a small textile shop in Tamil Nadu, comparing life before COVID (2018-19) to after (2022-23).

`Python` `pandas` `NumPy` `PostgreSQL` `SQL` `Power BI` `DAX` `Power Query`

---

## Architecture

Python -> PostgreSQL -> Power BI, three real stages.

ETL, properly ordered: Python handles Extract and Transform first, a 6-stage pipeline (Discovery, Structuring, Cleaning, Enriching, Validating, Publishing), before anything gets Loaded into PostgreSQL. Nothing enters the database until it has already passed validation. Fixing bad data inside a live database is far messier than fixing it before it arrives, so the order matters.

## Data model, OLAP star schema

The warehouse is a star schema, built for OLAP (fast, aggregate-heavy analytical reads) rather than OLTP (many small transactional writes). fact_sales sits at the center with roughly 697K rows, one per line item, surrounded by six dimensions (dim_product, dim_customer, dim_employee, dim_date, dim_promotion, dim_store), four supporting fact tables (fact_stock, fact_purchase_order, fact_payment_settlement, fact_opex), and a quarantine table for anything that failed validation.

It is deliberately denormalized. dim_product is not split into separate category, brand, and hub tables. That is the correct call for OLAP: fewer joins, faster aggregates, which is what Power BI actually needs at query time.

## Why this project exists

The original sales records for this shop were lost to a technical failure. Rather than drop the idea, I rebuilt a realistic dataset from scratch, calibrated against the real turnover figures the shop actually reported, and grounded in things that are genuinely true about the business, the Tamil festival calendar, where the shop actually sources its silk and readymade garments from, even a real cyclone that hit the district in November 2018. Then I deliberately broke parts of it on purpose, 26 different kinds of data problems, so I would have something real to build an actual cleaning pipeline against.

## What is actually in here

Around 697,000 transactions across the 4 years, calibrated to roughly Rs.8cr per year revenue before COVID and Rs.6cr per year after. 26 anomaly types spread across 11 files, each with a known, verified count so I could check whether my cleaning script caught what it was supposed to. 18 DAX measures in Power BI feeding a multi-page dashboard.

## A few things I actually found

Aadi, a Tamil month roughly July to August, is the lowest-revenue month every single year since no weddings happen then, but it is also when discounts run highest, so it is not a dead month, it is a discount-driven one.

Deepavali is the single biggest month every year, by a wide margin.

There is not one stockout risk, there are two, and they are unrelated. Silk from Kanchipuram takes 20 to 45 days since it is handloom and artisan-limited, threatening the Thai wedding season if you order late. Sarees from Surat take 18 to 30 days just from interstate freight, threatening Deepavali instead.

One finding I did not expect going in: during the Deepavali staffing surge, headcount goes up 2.33x but revenue only goes up something like 1.5 to 1.8x. Revenue per employee probably drops during the busiest month rather than improving. I left that as an open question on the dashboard instead of deciding it for the reader.

## About the data

The engineering here is real. I designed the schema, wrote the full ETL pipeline, and built the cleaning and validation logic myself. What is reconstructed is the underlying data, the shop's original point-of-sale records were lost, so the dataset is rebuilt and calibrated against the real figures the business reported, not pulled from a live feed. Stated plainly so there is no ambiguity about what is simulated and what is genuinely engineered.

---

Sri Vishnu Ram Aethu Venkatesan
[LinkedIn](https://www.linkedin.com/in/sri-vishnu-ram-aethu-venkatesan-3028a532a) | srivishnuram3@gmail.com
