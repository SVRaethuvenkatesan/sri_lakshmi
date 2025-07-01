-- ==============================================================================
-- SRI LAKSHMI TEXTILES: VERIFICATION & ANALYTICS
-- ==============================================================================

-- 1. Pipeline Verification (Confirming the Cleaned Data Loaded Correctly)
-- Expect roughly: fact_sales ≈ 694,932 · quarantine ≈ 274 · dim_product = 126 · dim_employee = 61
SELECT 'fact_sales' AS tbl, COUNT(*) FROM fact_sales
UNION ALL SELECT 'fact_sales_quarantine', COUNT(*) FROM fact_sales_quarantine
UNION ALL SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL SELECT 'dim_employee', COUNT(*) FROM dim_employee;


-- ==============================================================================
-- 4.2 Analytics — The Real Business Questions
-- ==============================================================================

-- 1. Top 20 Customers by Revenue
SELECT c.customer_id, c.customer_type, c.home_area,
       SUM(f.net_amount) AS total_revenue,
       RANK() OVER (ORDER BY SUM(f.net_amount) DESC) AS revenue_rank
FROM fact_sales f 
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_type, c.home_area
ORDER BY revenue_rank LIMIT 20;

-- 2. Monthly Category Revenue with YoY (Window Function)
WITH monthly AS (
    SELECT EXTRACT(YEAR FROM d.date_id) AS year, EXTRACT(MONTH FROM d.date_id) AS month,
           p.category, SUM(f.net_amount) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY 1, 2, p.category
)
SELECT year, month, category, revenue,
       LAG(revenue, 12) OVER (PARTITION BY category, month ORDER BY year) AS prior_year_revenue,
       ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (PARTITION BY category, month ORDER BY year))
             / NULLIF(LAG(revenue, 12) OVER (PARTITION BY category, month ORDER BY year), 0), 1) AS yoy_pct
FROM monthly 
ORDER BY category, year, month;
-- Note: 2020-21 gap means real YoY only exists for 2019→2018 and 2023→2022.

-- 3. Multi-hub Lead-Time / PO Delay Risk
SELECT p.manufacturing_hub, COUNT(*) AS total_pos,
       COUNT(*) FILTER (WHERE po.actual_delivery_date > po.expected_delivery_date) AS delayed_pos,
       ROUND(100.0 * COUNT(*) FILTER (WHERE po.actual_delivery_date > po.expected_delivery_date) / COUNT(*), 1) AS delay_rate_pct
FROM fact_purchase_order po 
JOIN dim_product p ON po.product_id = p.product_id
GROUP BY p.manufacturing_hub 
ORDER BY delay_rate_pct DESC;

-- 4. Master Join (Sales + Customer + Product + Stock)
SELECT d.tamil_month, d.season_tag, c.customer_type, p.category, p.item_name, p.brand_name,
       f.quantity, f.net_amount, f.payment_mode, st.stock_on_hand
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
JOIN dim_customer c ON f.customer_id = c.customer_id
JOIN dim_product p ON f.product_id = p.product_id
LEFT JOIN fact_stock st ON st.product_id = f.product_id AND st.date_id = f.date_id
ORDER BY d.date_id LIMIT 1000;

-- 5. Revenue per Employee (Normal vs. Deepavali Surge)
WITH monthly_revenue AS (
    SELECT DATE_TRUNC('month', date_id) AS month, SUM(net_amount) AS revenue 
    FROM fact_sales GROUP BY 1
),
monthly_headcount AS (
    SELECT month, SUM(headcount) AS total_headcount 
    FROM fact_opex
    WHERE expense_type IN ('Salary-Permanent','Salary-Seasonal') 
    GROUP BY month
)
SELECT r.month, r.revenue, h.total_headcount, 
       ROUND(r.revenue / NULLIF(h.total_headcount,0), 0) AS revenue_per_employee
FROM monthly_revenue r 
JOIN monthly_headcount h ON r.month = h.month 
ORDER BY r.month;

-- 6. Full Operating Margin by Month
WITH revenue AS (
    SELECT DATE_TRUNC('month', d.date_id) AS month, 
           SUM(f.net_amount) AS revenue, 
           SUM(f.quantity * p.unit_cost) AS cogs
    FROM fact_sales f 
    JOIN dim_date d ON f.date_id = d.date_id 
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY 1
),
opex AS (
    SELECT month, SUM(amount) AS total_opex 
    FROM fact_opex 
    GROUP BY month
)
SELECT r.month, r.revenue, r.cogs, 
       (r.revenue - r.cogs) AS gross_margin, 
       o.total_opex,
       (r.revenue - r.cogs - o.total_opex) AS operating_margin,
       ROUND(100.0 * (r.revenue - r.cogs - o.total_opex) / NULLIF(r.revenue,0), 1) AS operating_margin_pct
FROM revenue r 
JOIN opex o ON r.month = o.month 
ORDER BY r.month;
