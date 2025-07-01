-- Sri Lakshmi Textiles star schema -- final version
-- Incorporates: quarantine table (Phase 3/4 lesson), sentinel employee row noted below
 
CREATE TABLE dim_date (
    date_id            DATE PRIMARY KEY,
    year               INT,
    month              INT,
    day                INT,
    day_of_week        VARCHAR(10),
    is_weekend_sunday  BOOLEAN,
    tamil_month        VARCHAR(15),
    festival_name      VARCHAR(30),
    season_tag         VARCHAR(20)
);
 
CREATE TABLE dim_store (
    store_id   INT PRIMARY KEY,
    store_name VARCHAR(40),
    store_type VARCHAR(20),
    location   VARCHAR(40)
);
 
CREATE TABLE dim_product (
    product_id        INT PRIMARY KEY,
    category          VARCHAR(20) NOT NULL,
    subcategory       VARCHAR(20),
    item_name         VARCHAR(60) NOT NULL,
    brand_name        VARCHAR(50) NOT NULL,
    price_tier        VARCHAR(15) NOT NULL,
    manufacturing_hub VARCHAR(20) NOT NULL,
    distribution_hub  VARCHAR(20),
    lead_time_days    INT NOT NULL,
    unit_cost         NUMERIC(10,2) NOT NULL,
    unit_price        NUMERIC(10,2) NOT NULL,
    hsn_code          VARCHAR(8),
    gst_rate          NUMERIC(4,2)
);
 
CREATE TABLE dim_customer (
    customer_id         INT PRIMARY KEY,
    customer_type       VARCHAR(20),
    home_area           VARCHAR(30),
    first_purchase_date DATE,
    preferred_category  VARCHAR(20),
    customer_tenure_days INT
);
 
CREATE TABLE dim_employee (
    employee_id      INT PRIMARY KEY,
    role             VARCHAR(40),
    employment_type  VARCHAR(15),
    monthly_salary   NUMERIC(10,2),
    join_date        DATE,
    store_id         INT REFERENCES dim_store(store_id)
);
 
CREATE TABLE dim_promotion (
    promotion_id    INT PRIMARY KEY,
    promotion_name  VARCHAR(50),
    start_date      DATE,
    end_date        DATE,
    target_category VARCHAR(20),
    discount_pct    NUMERIC(5,2)
);
 
CREATE TABLE fact_sales (
    transaction_id VARCHAR(20),
    invoice_number VARCHAR(20),
    date_id        DATE REFERENCES dim_date(date_id),
    store_id       INT REFERENCES dim_store(store_id),
    employee_id    INT REFERENCES dim_employee(employee_id),
    product_id     INT REFERENCES dim_product(product_id),
    customer_id    INT REFERENCES dim_customer(customer_id),
    promotion_id   INT REFERENCES dim_promotion(promotion_id),
    quantity       INT,
    unit_price     NUMERIC(10,2),
    discount_pct   NUMERIC(5,2),
    gross_amount   NUMERIC(12,2),
    net_amount     NUMERIC(12,2),
    payment_mode   VARCHAR(10),
    gross_margin   NUMERIC(12,2),
    is_wholesale_bulk BOOLEAN,
    is_high_value  BOOLEAN
);
 
-- Quarantine: rows Cleaning couldn't confidently fix. No FKs on purpose --
CREATE TABLE fact_sales_quarantine (
    transaction_id     VARCHAR(20),
    invoice_number     VARCHAR(20),
    date_id            DATE,
    store_id           INT,
    employee_id        INT,
    product_id         INT,
    customer_id        INT,
    promotion_id       INT,
    quantity           INT,
    unit_price         NUMERIC(10,2),
    discount_pct       NUMERIC(5,2),
    gross_amount       NUMERIC(12,2),
    net_amount         NUMERIC(12,2),
    payment_mode       VARCHAR(10),
    gross_margin       NUMERIC(12,2),
    is_wholesale_bulk  BOOLEAN,
    is_high_value      BOOLEAN,
    quarantine_reason  VARCHAR(200)
);
 
CREATE TABLE fact_stock (
    stock_event_id  INT PRIMARY KEY,
    date_id         DATE,
    product_id      INT REFERENCES dim_product(product_id),
    event_type      VARCHAR(15),
    quantity_change NUMERIC(10,2),
    stock_on_hand   NUMERIC(10,2)
);
 
CREATE TABLE fact_purchase_order (
    po_id                  INT PRIMARY KEY,
    product_id             INT REFERENCES dim_product(product_id),
    order_date             DATE,
    expected_delivery_date DATE,
    actual_delivery_date   DATE,
    quantity_ordered       INT,
    quantity_received      NUMERIC(10,2),
    po_status              VARCHAR(20),
    days_to_deliver        NUMERIC(10,2)
);
 
CREATE TABLE fact_payment_settlement (
    settlement_id        INT PRIMARY KEY,
    date_id               DATE,
    payment_mode          VARCHAR(10),
    gross_amount_settled  NUMERIC(12,2),
    settlement_status     VARCHAR(15)
);
 
CREATE TABLE fact_opex (
    opex_id       INT PRIMARY KEY,
    month         DATE,
    expense_type  VARCHAR(25),
    amount        NUMERIC(12,2),
    headcount     NUMERIC(10,2),
    store_id      INT REFERENCES dim_store(store_id)
);
