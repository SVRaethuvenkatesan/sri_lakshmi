import pandas as pd
import numpy as np
import warnings
import pathlib

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# Dynamic path resolution to run from anywhere
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / 'data' / 'raw'
CLEAN_DIR = BASE_DIR / 'data' / 'clean'
QUAR_DIR = BASE_DIR / 'data' / 'quarantine'

print("Starting Data Wrangling Stage 1: Discovery Profiler...")
files = {
    'fact_sales': 'fact_sales.csv', 'dim_product': 'dim_product.csv', 'dim_employee': 'dim_employee.csv',
    'dim_promotion': 'dim_promotion.csv', 'fact_purchase_order': 'fact_purchase_order.csv',
    'fact_stock': 'fact_stock.csv', 'dim_customer': 'dim_customer.csv',
    'fact_payment_settlement': 'fact_payment_settlement.csv', 'dim_store': 'dim_store.csv', 'fact_opex': 'fact_opex.csv'
}
dfs = {name: pd.read_csv(RAW_DIR / filename) for name, filename in files.items()}
raw_counts = {name: len(df) for name, df in dfs.items()}

# =========================================================
# STAGE 2: STRUCTURING
# =========================================================
print("\nStarting Data Wrangling Stage 2: Structuring...")

print("1. Converting Dates securely...")
date_cols = {
    'fact_sales': ['date_id'], 'dim_employee': ['join_date'],
    'dim_promotion': ['start_date', 'end_date'], 'fact_purchase_order': ['order_date', 'actual_delivery_date'],
    'dim_customer': ['first_purchase_date'], 'fact_payment_settlement': ['date_id']
}
for df_name, cols in date_cols.items():
    for col in cols:
        dfs[df_name][col] = pd.to_datetime(dfs[df_name][col], errors='coerce')
        nat_count = dfs[df_name][col].isna().sum()
        if nat_count > 0:
            print(f"   [Warning] {nat_count:,} NaT values produced in {df_name}.{col} during datetime conversion.")

print("2. Casting to Pandas Nullable Int64 to prevent silent float upcasting...")
dfs['fact_sales']['employee_id'] = dfs['fact_sales']['employee_id'].astype('Int64')
dfs['fact_sales']['store_id'] = dfs['fact_sales']['store_id'].astype('Int64')
dfs['fact_sales']['promotion_id'] = dfs['fact_sales']['promotion_id'].astype('Int64')

print("3. Casting discrete text columns to Category dtype...")
dfs['dim_product']['category'] = dfs['dim_product']['category'].astype('category')
dfs['fact_sales']['payment_mode'] = dfs['fact_sales']['payment_mode'].astype('category')
dfs['dim_employee']['role'] = dfs['dim_employee']['role'].astype('category')

print("4. Enforcing Cross-File key consistency (Safely avoiding float upcast)...")
for df_name in ['fact_sales', 'dim_product', 'fact_purchase_order', 'fact_stock']:
    dfs[df_name]['product_id'] = dfs[df_name]['product_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

print("5. Verifying the Grain...")
grain_violations = dfs['fact_sales'].duplicated(subset=['transaction_id', 'product_id'], keep=False).sum()
print(f"   [Verification] fact_sales grain violations found: {grain_violations:,} rows break the (transaction_id + product_id) grain.")

# =========================================================
# STAGE 3: CLEANING (Single Table Fixes)
# =========================================================
print("\nStarting Data Wrangling Stage 3: Cleaning (Single-Table)...")
quarantine_dfs = {'fact_sales': pd.DataFrame()}
values_corrected = {name: 0 for name in dfs.keys()}

# --- 1. Duplicate Handling ---
dups_sales = dfs['fact_sales'].duplicated(keep='first').sum()
dfs['fact_sales'] = dfs['fact_sales'].drop_duplicates(keep='first')
print(f"Dropped {dups_sales:,} exact full-row duplicates from fact_sales.")

# --- 2. Missing & Invalid Values ---
missing_pm = dfs['fact_sales']['payment_mode'].isna().sum()
if 'Unknown' not in dfs['fact_sales']['payment_mode'].cat.categories:
    dfs['fact_sales']['payment_mode'] = dfs['fact_sales']['payment_mode'].cat.add_categories(['Unknown'])
dfs['fact_sales']['payment_mode'] = dfs['fact_sales']['payment_mode'].fillna('Unknown')
print(f"Imputed {missing_pm:,} missing payment_mode values with 'Unknown'.")

missing_emp = dfs['fact_sales']['employee_id'].isna().sum()
dfs['fact_sales']['employee_id'] = dfs['fact_sales']['employee_id'].fillna(-1)
print(f"Imputed {missing_emp:,} missing employee_id values with sentinel -1.")

dfs['fact_sales']['payment_mode'] = dfs['fact_sales']['payment_mode'].astype(str)
normalized = dfs['fact_sales']['payment_mode'].str.strip().str.upper()
canonical = {'CASH': 'Cash', 'CARD': 'Card', 'UPI': 'UPI'}
mask = normalized.isin(canonical.keys()) & ~dfs['fact_sales']['payment_mode'].isin(['Cash', 'Card', 'UPI', 'Unknown'])
count_pm = mask.sum()
dfs['fact_sales'].loc[mask, 'payment_mode'] = normalized[mask].map(canonical)
dfs['fact_sales']['payment_mode'] = dfs['fact_sales']['payment_mode'].astype('category')
print(f"Corrected {count_pm:,} whitespace/case typos in payment_mode using normalized canonical mapping.")

dfs['dim_product']['brand_name'] = dfs['dim_product']['brand_name'].astype(str).str.strip()
brand_typos = 0
for bad, good in {"ramraj cotton": "Ramraj Cotton", "rcm": "RCM", "sp apparels": "SP Apparels", "CO-OPTEX": "Co-optex"}.items():
    mask = dfs['dim_product']['brand_name'] == bad
    brand_typos += mask.sum()
    dfs['dim_product'].loc[mask, 'brand_name'] = good
print(f"Corrected {brand_typos} targeted brand_name typos in dim_product.")

# --- 3. Outliers (Statistical) ---
master_prices = dfs['dim_product'].set_index('product_id')['unit_price']
mapped_master_prices = dfs['fact_sales']['product_id'].map(master_prices)
glitch_mask = dfs['fact_sales']['unit_price'] < (0.05 * mapped_master_prices)
dfs['fact_sales'].loc[glitch_mask, 'unit_price'] = mapped_master_prices[glitch_mask]
print(f"Corrected {glitch_mask.sum():,} low currency-glitch price outliers using ratio-check against dim_product.")

fat_finger_count = 0
def cap_quant(group):
    global fat_finger_count
    q99 = group['quantity'].quantile(0.99)
    if pd.isna(q99): q99 = group['quantity'].max()
    outliers = group['quantity'] > q99
    fat_finger_count += outliers.sum()
    group.loc[outliers, 'quantity'] = int(q99)
    return group
dfs['fact_sales'] = dfs['fact_sales'].groupby('product_id', group_keys=False).apply(cap_quant)
print(f"Capped exactly {fat_finger_count} 'fat finger' quantities per product at 99th percentile.")

def cap_salary(group):
    q3 = group['monthly_salary'].quantile(0.75)
    iqr = q3 - group['monthly_salary'].quantile(0.25)
    upper = q3 + 1.5 * iqr
    outliers = group['monthly_salary'] > upper
    group.loc[outliers, 'monthly_salary'] = upper
    return group
sal_before = (dfs['dim_employee']['monthly_salary'] > 30000).sum()
dfs['dim_employee'] = dfs['dim_employee'].groupby('role', group_keys=False).apply(cap_salary)
sal_after = (dfs['dim_employee']['monthly_salary'] > 30000).sum()
print(f"Capped {sal_before - sal_after} salary outliers using IQR bounds per role.")

# --- The Remaining Single-Table Fixes ---
dfs['fact_sales']['discount_pct'] = dfs['fact_sales']['discount_pct'].clip(0, 100)

dfs['fact_sales']['gross_amount_calc'] = (dfs['fact_sales']['unit_price'] * dfs['fact_sales']['quantity']).round(2)
gross_mask = abs(dfs['fact_sales']['gross_amount'] - dfs['fact_sales']['gross_amount_calc']) > 0.01
dfs['fact_sales'].loc[gross_mask, 'gross_amount'] = dfs['fact_sales'].loc[gross_mask, 'gross_amount_calc']

dfs['fact_sales']['net_amount_calc'] = (dfs['fact_sales']['gross_amount'] * (1 - dfs['fact_sales']['discount_pct'] / 100)).round(2)
math_mask = abs(dfs['fact_sales']['net_amount'] - dfs['fact_sales']['net_amount_calc']) > 0.01
dfs['fact_sales'].loc[math_mask, 'net_amount'] = dfs['fact_sales'].loc[math_mask, 'net_amount_calc']
print(f"Corrected {gross_mask.sum():,} gross_amount and {math_mask.sum():,} net_amount math mismatches.")
dfs['fact_sales'] = dfs['fact_sales'].drop(columns=['gross_amount_calc', 'net_amount_calc'])

cost_mask = dfs['dim_product']['unit_cost'] > dfs['dim_product']['unit_price']
dfs['dim_product'].loc[cost_mask, 'unit_cost'] = (dfs['dim_product'].loc[cost_mask, 'unit_price'] * 0.7).round(2)
print(f"Corrected {cost_mask.sum()} instances where unit_cost > unit_price in dim_product.")

valid_gst = [0.0, 5.0, 12.0, 18.0, 28.0]
gst_mask = ~dfs['dim_product']['gst_rate'].isin(valid_gst)
dfs['dim_product'].loc[gst_mask, 'gst_rate'] = 18.0
print(f"Corrected {gst_mask.sum()} invalid GST rates to default 18.0%.")

future_join = dfs['dim_employee']['join_date'] > pd.to_datetime('2023-12-31')
dfs['dim_employee'].loc[future_join, 'join_date'] = pd.Timestamp('2023-01-01')
print(f"Corrected {future_join.sum()} future join_dates in dim_employee.")

swap_mask = dfs['dim_promotion']['end_date'] < dfs['dim_promotion']['start_date']
dfs['dim_promotion'].loc[swap_mask, ['start_date', 'end_date']] = dfs['dim_promotion'].loc[swap_mask, ['end_date', 'start_date']].values
print(f"Corrected {swap_mask.sum()} swapped start/end dates in dim_promotion.")

out_range = (dfs['dim_promotion']['discount_pct'] > 100) | (dfs['dim_promotion']['discount_pct'] < 0)
dfs['dim_promotion'].loc[out_range, 'discount_pct'] = dfs['dim_promotion']['discount_pct'].clip(0, 100)
print(f"Clipped {out_range.sum()} out-of-range discount percentages in dim_promotion.")

dfs['fact_purchase_order']['quantity_ordered'] = pd.to_numeric(dfs['fact_purchase_order']['quantity_ordered'], errors='coerce')
dfs['fact_purchase_order']['quantity_received'] = pd.to_numeric(dfs['fact_purchase_order']['quantity_received'], errors='coerce')
qty_mask = dfs['fact_purchase_order']['quantity_received'] > dfs['fact_purchase_order']['quantity_ordered']
dfs['fact_purchase_order'].loc[qty_mask, 'quantity_received'] = dfs['fact_purchase_order'].loc[qty_mask, 'quantity_ordered']
print(f"Capped {qty_mask.sum()} POs where quantity_received > quantity_ordered.")

po_swap = dfs['fact_purchase_order']['actual_delivery_date'] < dfs['fact_purchase_order']['order_date']
dfs['fact_purchase_order'].loc[po_swap, ['order_date', 'actual_delivery_date']] = dfs['fact_purchase_order'].loc[po_swap, ['actual_delivery_date', 'order_date']].values
print(f"Corrected {po_swap.sum()} swapped order/delivery dates in fact_purchase_order.")

# --- fact_stock Anomaly 20: Isolated Spikes in stock_on_hand ---
dfs['fact_stock'] = dfs['fact_stock'].sort_values(['product_id', 'date_id', 'stock_event_id'])
stock_diff = dfs['fact_stock'].groupby('product_id')['stock_on_hand'].diff()
stock_error = (stock_diff - dfs['fact_stock']['quantity_change']).round(2)
next_error = stock_error.groupby(dfs['fact_stock']['product_id']).shift(-1)
valid_rows = dfs['fact_stock']['event_type'] != 'Stockout'
spike_mask = valid_rows & (stock_error >= 20) & (stock_error <= 80) & (
    (next_error <= -20) & (next_error >= -100) | next_error.isna()
)
dfs['fact_stock'].loc[spike_mask, 'stock_on_hand'] -= stock_error[spike_mask]
print(f"Corrected {spike_mask.sum()} isolated reconciliation spikes in fact_stock.stock_on_hand.")
dfs['fact_stock'] = dfs['fact_stock'].sort_index()

# Track all value-level corrections
values_corrected['fact_sales'] += count_pm + glitch_mask.sum() + fat_finger_count + gross_mask.sum() + math_mask.sum()
values_corrected['dim_product'] += brand_typos + cost_mask.sum() + gst_mask.sum()
values_corrected['dim_employee'] += (sal_before - sal_after) + future_join.sum()
values_corrected['dim_promotion'] += swap_mask.sum() + out_range.sum()
values_corrected['fact_purchase_order'] += qty_mask.sum() + po_swap.sum()
values_corrected['fact_stock'] += spike_mask.sum()


# =========================================================
# STAGE 4: ENRICHING (Derived Columns & Flags)
# =========================================================
print("\nStarting Data Wrangling Stage 4: Enriching...")

# 1. Derived P&L Columns in fact_sales
sales_enriched = dfs['fact_sales'].merge(dfs['dim_product'][['product_id', 'unit_cost']], on='product_id', how='left')
sales_enriched.index = dfs['fact_sales'].index
dfs['fact_sales']['gross_margin'] = (dfs['fact_sales']['net_amount'] - (sales_enriched['unit_cost'] * dfs['fact_sales']['quantity'])).round(2)
print("Computed 'gross_margin' in fact_sales using dim_product.unit_cost.")

# 2. Derived Performance Metrics in fact_purchase_order
dfs['fact_purchase_order']['days_to_deliver'] = (dfs['fact_purchase_order']['actual_delivery_date'] - dfs['fact_purchase_order']['order_date']).dt.days
print("Computed 'days_to_deliver' in fact_purchase_order.")


# 4. Business-Rule Driven Flags in fact_sales
dfs['fact_sales']['is_wholesale_bulk'] = dfs['fact_sales']['quantity'] >= 50
p95_net_amount = dfs['fact_sales']['net_amount'].quantile(0.95)
dfs['fact_sales']['is_high_value'] = dfs['fact_sales']['net_amount'] > p95_net_amount
print(f"Flagged 'is_wholesale_bulk' and 'is_high_value' (>{p95_net_amount:,.2f}) in fact_sales.")


# =========================================================
# STAGE 5: CROSS-TABLE VALIDATION & QUARANTINE
# =========================================================
print("\nStarting Data Wrangling Stage 5: Cross-Table Validation...")

first_sales = dfs['fact_sales'].groupby('customer_id')['date_id'].min()
cust_mismatch = dfs['dim_customer']['customer_id'].map(first_sales) < dfs['dim_customer']['first_purchase_date']
dfs['dim_customer'].loc[cust_mismatch, 'first_purchase_date'] = dfs['dim_customer']['customer_id'].map(first_sales)
print(f"Reconciled {cust_mismatch.sum()} inconsistent first_purchase_dates in dim_customer against fact_sales.")

# Recompute Time-Based Enrichment after date correction
dfs['dim_customer']['customer_tenure_days'] = (pd.to_datetime('2023-12-31') - dfs['dim_customer']['first_purchase_date']).dt.days
print("Recomputed 'customer_tenure_days' in dim_customer based on corrected dates.")

def q_sales(mask, reason):
    if mask.sum() > 0:
        q_df = dfs['fact_sales'][mask].copy()
        q_df['quarantine_reason'] = reason
        quarantine_dfs['fact_sales'] = pd.concat([quarantine_dfs['fact_sales'], q_df])
        dfs['fact_sales'] = dfs['fact_sales'][~mask]
    return mask.sum()

o_emp = q_sales(~dfs['fact_sales']['employee_id'].isin(dfs['dim_employee']['employee_id']) & (dfs['fact_sales']['employee_id'] != -1), 'Orphan Employee ID')
o_store = q_sales(~dfs['fact_sales']['store_id'].isin(dfs['dim_store']['store_id']), 'Orphan Store ID')
o_prod = q_sales(~dfs['fact_sales']['product_id'].isin(dfs['dim_product']['product_id']), 'Orphan Product ID')
leak = q_sales(dfs['fact_sales']['date_id'] >= pd.to_datetime('2024-01-01'), 'Future Date (Data Leakage)')

godown_staff = dfs['dim_employee'][dfs['dim_employee']['role'] == 'Stock/Godown Staff']['employee_id']
g_staff = q_sales(dfs['fact_sales']['employee_id'].isin(godown_staff), 'Billed by Godown Staff')

sales_promo = dfs['fact_sales'].merge(dfs['dim_promotion'][['promotion_id', 'start_date', 'end_date']], on='promotion_id', how='left')
sales_promo.index = dfs['fact_sales'].index
p_viol_mask = (sales_promo['date_id'] < sales_promo['start_date']) | (sales_promo['date_id'] > sales_promo['end_date'])
p_viol = q_sales(p_viol_mask, 'Promo Outside Valid Date Range')

print(f"Quarantined sales rows: {o_emp} Orphan Emp, {o_store} Orphan Store, {o_prod} Orphan Prod, {leak} Data Leakage, {g_staff} Godown Staff Billing, {p_viol} Invalid Promo Dates.")

if not quarantine_dfs['fact_sales'].empty:
    quarantine_dfs['fact_sales'].to_csv(QUAR_DIR / "quarantined_fact_sales.csv", index=False)
    print(f"Saved {len(quarantine_dfs['fact_sales']):,} total unrecoverable rows to 'quarantined_fact_sales.csv'.")

print("--- Aggregate Reconciliations ---")
# 1. Settlement vs Sales
# Need to make sure both sides are cleanly grouped
dfs['fact_payment_settlement']['payment_mode'] = dfs['fact_payment_settlement']['payment_mode'].astype(str).str.strip().str.title()
# Match our clean payment modes
pm_map = {'Upi': 'UPI', 'Cash': 'Cash', 'Card': 'Card'}
dfs['fact_payment_settlement']['payment_mode'] = dfs['fact_payment_settlement']['payment_mode'].map(pm_map).fillna(dfs['fact_payment_settlement']['payment_mode'])

daily_sales = dfs['fact_sales'].groupby(['date_id', 'payment_mode'], observed=True)['net_amount'].sum().reset_index()
settlement_agg = dfs['fact_payment_settlement'].groupby(['date_id', 'payment_mode'], observed=True)['gross_amount_settled'].sum().reset_index()
settlement_sales = settlement_agg.merge(daily_sales, on=['date_id', 'payment_mode'], how='left')
mismatch_mask = abs(settlement_sales['gross_amount_settled'] - settlement_sales['net_amount'].fillna(0)) > 0.01
print(f"Flagged {mismatch_mask.sum()} daily settlement aggregates in fact_payment_settlement that drift from actual fact_sales net_amount.")

# 2. Opex Headcount vs dim_employee
if 'headcount' in dfs['fact_opex'].columns:
    dfs['dim_employee']['join_month'] = dfs['dim_employee']['join_date'].dt.to_period('M')
    dfs['fact_opex']['month_dt'] = pd.to_datetime(dfs['fact_opex']['month'], format='%b-%y', errors='coerce')
    if dfs['fact_opex']['month_dt'].isna().all(): 
        # Fallback if format is different
        dfs['fact_opex']['month_dt'] = pd.to_datetime(dfs['fact_opex']['month'], errors='coerce')
        
    dfs['fact_opex']['month_period'] = dfs['fact_opex']['month_dt'].dt.to_period('M')
    def get_active(period):
        if pd.isna(period): return 0
        return (dfs['dim_employee']['join_month'] <= period).sum()
    
    dfs['fact_opex']['true_headcount'] = dfs['fact_opex']['month_period'].apply(get_active)
    hc_mask = (dfs['fact_opex']['headcount'].notna()) & (dfs['fact_opex']['headcount'] != dfs['fact_opex']['true_headcount'])
    print(f"Flagged {hc_mask.sum()} months in fact_opex where reported headcount drifts from true dim_employee active count.")
    dfs['fact_opex'].drop(columns=['month_dt', 'month_period', 'true_headcount'], inplace=True, errors='ignore')
    dfs['dim_employee'].drop(columns=['join_month'], inplace=True, errors='ignore')

print("--- Final Assertions (Pipeline Integrity) ---")
is_sale = dfs['fact_sales']['quantity'] >= 0
is_return = dfs['fact_sales']['quantity'] < 0
assert (dfs['fact_sales'].loc[is_sale, 'net_amount'] <= dfs['fact_sales'].loc[is_sale, 'gross_amount']).all(), "CRITICAL BUG: net_amount > gross_amount found for positive sales!"
assert (dfs['fact_sales'].loc[is_return, 'net_amount'] >= dfs['fact_sales'].loc[is_return, 'gross_amount']).all(), "CRITICAL BUG: net_amount < gross_amount found for returns!"
assert (dfs['fact_sales']['discount_pct'] >= 0).all() and (dfs['fact_sales']['discount_pct'] <= 100).all(), "CRITICAL BUG: discount_pct out of bounds!"
assert dfs['fact_sales']['product_id'].isin(dfs['dim_product']['product_id']).all(), "CRITICAL BUG: Orphan product_ids bypassed Quarantine!"
print("All strict pipeline assertions passed. The data is internally sound.")

# =========================================================
# STAGE 6: PUBLISHING
# =========================================================
print("\n" + "="*85)
print("FINAL PIPELINE SUMMARY (STAGE 6: PUBLISHING)")
print("="*85)
total_raw = sum(raw_counts.values())
total_clean = sum(len(df) for df in dfs.values())
total_quarantined = sum(len(df) for df in quarantine_dfs.values())
total_dropped = total_raw - total_clean - total_quarantined
total_values_corrected = sum(values_corrected.values())

print(f"Total Raw Rows Processed:    {total_raw:,}")
print(f"Total Clean Rows Exported:   {total_clean:,}")
print(f"Total Rows Quarantined:      {total_quarantined:,}")
print(f"Total Rows Dropped/Deduped:  {total_dropped:,}")
print(f"Total Values Corrected:      {total_values_corrected:,}\n")

print("Detailed Table Breakdown:")
print(f"{'Table':<25} | {'In':<8} | {'Out':<8} | {'Quarantined':<12} | {'Dropped':<8} | {'Values Corrected'}")
print("-" * 85)
for name in dfs.keys():
    q_count = len(quarantine_dfs[name]) if name in quarantine_dfs else 0
    d_count = raw_counts[name] - len(dfs[name]) - q_count
    v_count = values_corrected.get(name, 0)
    print(f"{name:<25} | {raw_counts[name]:<8,} | {len(dfs[name]):<8,} | {q_count:<12,} | {d_count:<8,} | {v_count:<8,}")
print("="*85 + "\n")

# Export all pristine datasets
for name, df in dfs.items():
    df.to_csv(CLEAN_DIR / f"{name}_clean.csv", index=False)

print("PUBLISHING COMPLETE! Exported 11 pristine CSVs.")
