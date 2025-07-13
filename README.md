# Sri Lakshmi Textiles — Retail Analytics Pipeline

A full data pipeline I built end to end: Python for generating and cleaning the data, PostgreSQL for the warehouse, Power BI for the dashboard. It analyzes 4 years of sales for a small textile shop in Tamil Nadu, comparing life before COVID (2018-19) to after (2022-23).

`Python` `pandas` `NumPy` `PostgreSQL` `SQL` `Power BI` `DAX` `Power Query`

---

## Why this project exists

The original sales records for this shop were lost to a technical failure. Rather than drop the idea, I rebuilt a realistic dataset from scratch, calibrated against the real turnover figures the shop actually reported, and grounded in things that are genuinely true about the business - the Tamil festival calendar, where the shop actually sources its silk and readymade garments from, even a real cyclone that hit the district in November 2018. Then I deliberately broke parts of it on purpose: 26 different kinds of data problems, so I'd have something real to build an actual cleaning pipeline against, not just a tidy CSV that never needed fixing.

## What's actually in here

- Around 697,000 transactions across the 4 years, calibrated to roughly Rs.8cr/year revenue before COVID and Rs.6cr/year after
- A proper star schema in PostgreSQL - 12 tables, real foreign keys, a dedicated quarantine table for anything I couldn't confidently fix rather than just deleting it
- 26 anomaly types spread across 11 files, each with a known, verified count so I could actually check whether my cleaning script caught what it was supposed to
- A 6-stage wrangling process (Discovery, Structuring, Cleaning, Enriching, Validating, Publishing) where nothing gets silently dropped
- 18 DAX measures in Power BI feeding a multi-page dashboard

## A few things I actually found

Aadi (a Tamil month, roughly July to August) is the lowest-revenue month every single year - no weddings happen then - but it's also when discounts run highest, so it's not a dead month, it's a discount-driven one.

Deepavali is the single biggest month every year, by a wide margin.

There isn't one stockout risk, there are two, and they're unrelated. Silk from Kanchipuram takes 20 to 45 days to arrive since it's handloom and artisan-limited, which threatens the Thai wedding season if you order late. Sarees from Surat take 18 to 30 days just from the interstate freight, which threatens Deepavali instead.

I could actually measure the COVID reopening dip instead of just assuming it happened. Silk sales dropped to about 18 to 19 percent of revenue in Jan-Feb 2022, against over 30 percent in the same months pre-COVID.

One finding I didn't expect going in: during the Deepavali staffing surge, headcount goes up 2.33x but revenue only goes up something like 1.5 to 1.8x. So revenue per employee probably drops during the busiest month rather than improving. I left that as an open question on the dashboard instead of deciding it for the reader.

## Stack

Python (pandas, NumPy) -> PostgreSQL -> Power BI (Power Query + DAX)

## About the data

Worth saying plainly: this isn't a live export from a real POS system. It's a reconstructed dataset - the numbers and patterns are calibrated to match what was actually true about this business, and grounded in real facts wherever I could check them, but it's synthetic data built to demonstrate the pipeline itself, not scraped or exported from anywhere.

---

Sri Vishnu Ram Aethu Venkatesan
[LinkedIn](https://www.linkedin.com/in/sri-vishnu-ram-aethu-venkatesan-3028a532a) | srivishnuram3@gmail.com
