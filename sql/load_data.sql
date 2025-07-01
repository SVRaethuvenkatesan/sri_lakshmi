-- 1. TRUNCATE tables to ensure a perfectly clean reload (respecting FK constraints)
TRUNCATE TABLE fact_sales, fact_stock, fact_purchase_order, fact_payment_settlement, fact_opex, fact_sales_quarantine RESTART IDENTITY CASCADE;
TRUNCATE TABLE dim_employee, dim_store, dim_product, dim_customer, dim_promotion, dim_date RESTART IDENTITY CASCADE;

-- 2. COPY the clean datasets into PostgreSQL
\copy dim_date FROM 'e:/sri_lakshmi/data/raw/dim_date.csv' DELIMITER ',' CSV HEADER;
\copy dim_store FROM 'e:/sri_lakshmi/data/clean/dim_store_clean.csv' DELIMITER ',' CSV HEADER;
\copy dim_product FROM 'e:/sri_lakshmi/data/clean/dim_product_clean.csv' DELIMITER ',' CSV HEADER;
\copy dim_customer FROM 'e:/sri_lakshmi/data/clean/dim_customer_clean.csv' DELIMITER ',' CSV HEADER;
\copy dim_employee FROM 'e:/sri_lakshmi/data/clean/dim_employee_clean.csv' DELIMITER ',' CSV HEADER;
\copy dim_promotion FROM 'e:/sri_lakshmi/data/clean/dim_promotion_clean.csv' DELIMITER ',' CSV HEADER;

-- CRITICAL SENTINEL ROW (Do this BEFORE loading fact_sales!)
-- fact_sales uses employee_id = -1 as the sentinel for "missing" after cleaning.
-- Without this row, the FK constraint rejects every one of those rows.
INSERT INTO dim_employee (employee_id, role, employment_type, monthly_salary, join_date, store_id)
VALUES (-1, 'Unknown', 'Unknown', NULL, NULL, NULL);

\copy fact_sales FROM 'e:/sri_lakshmi/data/clean/fact_sales_clean.csv' DELIMITER ',' CSV HEADER;
\copy fact_sales_quarantine FROM 'e:/sri_lakshmi/data/quarantine/quarantined_fact_sales.csv' DELIMITER ',' CSV HEADER;
\copy fact_stock FROM 'e:/sri_lakshmi/data/clean/fact_stock_clean.csv' DELIMITER ',' CSV HEADER;
\copy fact_purchase_order FROM 'e:/sri_lakshmi/data/clean/fact_purchase_order_clean.csv' DELIMITER ',' CSV HEADER;
\copy fact_payment_settlement FROM 'e:/sri_lakshmi/data/clean/fact_payment_settlement_clean.csv' DELIMITER ',' CSV HEADER;
\copy fact_opex FROM 'e:/sri_lakshmi/data/clean/fact_opex_clean.csv' DELIMITER ',' CSV HEADER;

-- Load Complete!
