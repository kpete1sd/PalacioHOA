
import streamlit as st
import pandas as pd
import numpy as np
import math
import io
import base64
import matplotlib.pyplot as plt

st.set_page_config(page_title="HOA 5-Year Budget Scenario Simulator", layout="wide")

# ---------- Helpers ----------

def currency(x):
    try:
        return f"${x:,.0f}"
    except Exception:
        return x

def amortization_payment(principal, annual_rate, years):
    if principal <= 0 or years <= 0:
        return 0.0
    r = annual_rate / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r)**n) / ((1 + r)**n - 1)

def loan_schedule(principal, annual_rate, years, start_year, sim_years):
    """Return dict of year -> (principal_paid, interest_paid, ending_balance, annual_payment)."""
    if principal <= 0 or years <= 0:
        return {y: (0,0,0,0) for y in sim_years}
    monthly_pmt = amortization_payment(principal, annual_rate, years)
    balance = principal
    schedule = {}
    # distribute 12 monthly payments per year
    for y in sim_years:
        if y < start_year or y >= start_year + years:
            # before loan start or after maturity
            schedule[y] = (0, 0, max(0, balance), 0)
            continue
        principal_paid_yr = 0.0
        interest_paid_yr = 0.0
        for m in range(12):
            interest = balance * (annual_rate / 12.0)
            principal_paid = max(0, monthly_pmt - interest)
            if principal_paid > balance:
                principal_paid = balance
                monthly_actual = interest + principal_paid
            else:
                monthly_actual = monthly_pmt
            interest_paid_yr += interest
            principal_paid_yr += principal_paid
            balance -= principal_paid
            if balance <= 1e-6:
                balance = 0.0
                break
        schedule[y] = (principal_paid_yr, interest_paid_yr, max(0, balance), monthly_pmt*12 if balance>0 else principal_paid_yr+interest_paid_yr)
    return schedule

def download_link(df, filename, link_text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

# ---------- Sidebar: Scenario Controls ----------

st.sidebar.header("Scenario Controls")

preset = st.sidebar.selectbox(
    "Preset",
    ["Base Case", "Catch-Up (dues+loan)", "High Inflation", "Aggressive Reserves"]
)

homes = st.sidebar.number_input("Number of Homes", min_value=1, value=420, step=1)
start_year = st.sidebar.number_input("Start Year", min_value=2025, value=2026, step=1)
years = st.sidebar.slider("Projection Horizon (years)", 3, 10, 5)
sim_years = list(range(start_year, start_year + years))

st.sidebar.markdown("---")
st.sidebar.subheader("Operating & Inflation")
inflation = st.sidebar.number_input("Operating Inflation (annual %)", min_value=0.0, value=3.0, step=0.1, format="%.1f")/100.0

st.sidebar.markdown("---")
st.sidebar.subheader("Dues Strategy")
starting_dues = st.sidebar.number_input("Starting Monthly Dues per Home ($)", min_value=0.0, value=300.0, step=5.0)
dues_step_pct = st.sidebar.number_input("Annual Dues Increase (%)", min_value=0.0, value=5.0, step=0.5, format="%.1f")/100.0
dues_step_years = st.sidebar.text_input("Years to apply dues increase (comma-separated)", value="2026,2027,2028,2029,2030")

st.sidebar.markdown("---")
st.sidebar.subheader("Reserves")
reserve_start = st.sidebar.number_input("Starting Reserve Balance ($)", min_value=0.0, value=1_000_000.0, step=50_000.0)
reserve_interest = st.sidebar.number_input("Reserve Earnings Rate (annual %)", min_value=0.0, value=2.0, step=0.1, format="%.1f")/100.0
reserve_contrib_mode = st.sidebar.selectbox("Reserve Contribution Mode", ["Per-Home/Month", "Fixed Annual"])
reserve_contrib_value = st.sidebar.number_input("Reserve Contribution Value ($)", min_value=0.0, value=75.0, step=5.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Fully Funded Balance (FFB)")
ffb_start = st.sidebar.number_input("Starting Fully Funded Balance ($)", min_value=0.0, value=1_250_000.0, step=50_000.0)
ffb_growth = st.sidebar.number_input("FFB Growth/Inflation (annual %)", min_value=0.0, value=3.0, step=0.1, format="%.1f")/100.0

st.sidebar.markdown("---")
st.sidebar.subheader("Special Assessment")
sa_year = st.sidebar.number_input("Assessment Year", min_value=start_year, value=start_year, step=1)
sa_mode = st.sidebar.selectbox("Assessment Mode", ["Per-Home Amount", "Total Amount"])
sa_value = st.sidebar.number_input("Assessment Value ($)", min_value=0.0, value=0.0, step=1000.0)

st.sidebar.markdown("---")
st.sidebar.subheader("HOA Loan")
loan_amount = st.sidebar.number_input("Loan Amount ($)", min_value=0.0, value=0.0, step=100_000.0)
loan_rate = st.sidebar.number_input("Loan Interest Rate (annual %)", min_value=0.0, value=6.5, step=0.1, format="%.1f")/100.0
loan_term_years = st.sidebar.number_input("Loan Term (years)", min_value=0, value=10, step=1)
loan_start = st.sidebar.number_input("Loan Start Year", min_value=start_year, value=start_year+1, step=1)
loan_fee = st.sidebar.number_input("One-Time Loan Origination Fee ($)", min_value=0.0, value=0.0, step=1000.0)

# Apply Presets
if preset == "Catch-Up (dues+loan)":
    dues_step_pct = 0.08
    dues_step_years = ",".join(str(y) for y in sim_years)
    loan_amount = 2_000_000.0
    loan_rate = 0.065
    loan_term_years = 10
    loan_start = sim_years[0]
    sa_value = 0.0
elif preset == "High Inflation":
    inflation = 0.06
elif preset == "Aggressive Reserves":
    reserve_contrib_mode = "Per-Home/Month"
    reserve_contrib_value = 125.0

# ---------- Operating Budget Input (Upload or Sample) ----------

st.header("HOA 5-Year Budget Scenario Simulator")
left, right = st.columns([2,1])

with left:
    st.subheader("Operating Budget (Baseline Year)")
    st.write("Upload your operating budget CSV (columns: Category, AnnualAmountUSD) or edit the table below.")

    uploaded = st.file_uploader("Upload Operating Budget CSV", type=["csv"])
    if uploaded:
        op_df = pd.read_csv(uploaded)
    else:
        op_df = pd.DataFrame({
            "Category": [
                "Landscaping","Water & Irrigation","Insurance","Utilities (Electric/Gas)",
                "Management & Admin","Staffing (Ops & Golf)","Repairs & Maintenance","Pool Ops & Chemicals",
                "Tennis/Pickleball/Basketball","Clubhouse Ops","Security/Access Control","Contingency"
            ],
            "AnnualAmountUSD": [380000,240000,220000,105000,125000,210000,140000,60000,30000,55000,45000,35000]
        })
    op_df = st.data_editor(op_df, num_rows="dynamic", key="op_edit")

with right:
    st.subheader("Capital Projects")
    st.write("Define major projects (Year, Name, Cost, Optional Phase %)")
    cap_projects = st.data_editor(
        pd.DataFrame({
            "Year":[sim_years[1] if len(sim_years)>1 else sim_years[0],
                    sim_years[2] if len(sim_years)>2 else sim_years[-1]],
            "Project":["Golf Irrigation Overhaul","Creek Stabilization Phase 1"],
            "CostUSD":[1_200_000, 1_250_000],
            "PhasePercent":[100, 50]
        }),
        num_rows="dynamic",
        key="cap_edit"
    )
    st.caption("Tip: Use multiple rows to phase large projects over several years (e.g., two rows for Creek Phase 1 & 2).")

# ---------- Build Projection ----------

# Dues plan
try:
    dues_years_set = set(int(y.strip()) for y in dues_step_years.split(",") if y.strip())
except Exception:
    dues_years_set = set(sim_years)

dues_by_year = {}
for i, y in enumerate(sim_years):
    if i == 0:
        dues_by_year[y] = starting_dues
    else:
        prev = dues_by_year[sim_years[i-1]]
        if y in dues_years_set:
            dues_by_year[y] = prev * (1 + dues_step_pct)
        else:
            dues_by_year[y] = prev

# Operating by year
op_base_total = float(op_df["AnnualAmountUSD"].sum())
op_by_year = {}
for i, y in enumerate(sim_years):
    if i == 0:
        op_by_year[y] = op_base_total
    else:
        op_by_year[y] = op_by_year[sim_years[i-1]] * (1 + inflation)

# Fully Funded Balance by year (simple growth model; replace with reserve study values if available)
ffb_by_year = {}
for i, y in enumerate(sim_years):
    if i == 0:
        ffb_by_year[y] = ffb_start
    else:
        ffb_by_year[y] = ffb_by_year[sim_years[i-1]] * (1 + ffb_growth)

# Reserve contributions
reserve_contrib_by_year = {}
for y in sim_years:
    if reserve_contrib_mode == "Per-Home/Month":
        reserve_contrib_by_year[y] = reserve_contrib_value * homes * 12.0
    else:
        reserve_contrib_by_year[y] = reserve_contrib_value

# Special assessment receipts
sa_by_year = {y: 0.0 for y in sim_years}
if sa_value > 0 and sa_year in sa_by_year:
    if sa_mode == "Per-Home Amount":
        sa_by_year[sa_year] = sa_value * homes
    else:
        sa_by_year[sa_year] = sa_value

# Loan schedule
loan_by_year = loan_schedule(loan_amount, loan_rate, loan_term_years, loan_start, sim_years)

# Capital projects by year (sum costs, respect PhasePercent)
cap_by_year = {y: 0.0 for y in sim_years}
for _, row in cap_projects.iterrows():
    try:
        y = int(row.get("Year", sim_years[0]))
    except Exception:
        y = sim_years[0]
    cost = float(row.get("CostUSD", 0.0))
    pct = float(row.get("PhasePercent", 100.0))/100.0
    alloc = cost * pct
    if y in cap_by_year:
        cap_by_year[y] += alloc

# Build table
rows = []
reserve_balance = reserve_start
for y in sim_years:
    dues_rev = homes * dues_by_year[y] * 12.0
    op_exp = op_by_year[y]
    res_contrib = reserve_contrib_by_year[y]
    capx = cap_by_year.get(y, 0.0)

    loan_prin, loan_int, loan_ending, loan_payment_yr = loan_by_year[y]
    loan_cash_out = loan_payment_yr
    loan_draw = loan_amount if y == loan_start and loan_amount>0 else 0.0
    loan_fee_out = loan_fee if (loan_fee>0 and y == loan_start) else 0.0

    reserve_interest_earn = reserve_balance * reserve_interest

    reserve_inflows = res_contrib + sa_by_year.get(y, 0.0) + loan_draw + reserve_interest_earn
    reserve_outflows = capx + loan_cash_out + loan_fee_out
    reserve_ending = reserve_balance + reserve_inflows - reserve_outflows

    operating_margin = dues_rev - op_exp

    ffb = ffb_by_year[y]
    funding_pct = (reserve_ending / ffb) * 100.0 if ffb > 0 else 0.0

    rows.append({
        "Year": y,
        "Homes": homes,
        "Monthly Dues ($/home)": round(dues_by_year[y],2),
        "Annual Dues Revenue ($)": dues_rev,
        "Operating Expenses ($)": op_exp,
        "Operating Margin ($)": operating_margin,
        "Reserve Start ($)": reserve_balance,
        "Reserve Contributions ($)": res_contrib,
        "Special Assessment ($)": sa_by_year.get(y, 0.0),
        "Loan Draw ($)": loan_draw,
        "Loan Payments ($)": loan_cash_out,
        "Loan Interest Portion ($)": loan_int,
        "Capital Projects ($)": capx,
        "Reserve Interest Earned ($)": reserve_interest_earn,
        "Loan Fee ($)": loan_fee_out,
        "Fully Funded Balance ($)": ffb,
        "Funding %": funding_pct,
        "Reserve Ending ($)": reserve_ending
    })
    reserve_balance = reserve_ending

proj_df = pd.DataFrame(rows)

# KPIs
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("Final Year Reserve Balance", currency(proj_df["Reserve Ending ($)"].iloc[-1]))
with kpi2:
    st.metric("Final Year Funding %", f'{proj_df["Funding %"].iloc[-1]:.0f}%')
with kpi3:
    st.metric("Final Year Operating Margin", currency(proj_df["Operating Margin ($)"].iloc[-1]))
with kpi4:
    st.metric("Max Annual Capital Spend", currency(proj_df["Capital Projects ($)"].max()))
with kpi5:
    st.metric("Peak Monthly Dues / Home", currency(proj_df["Monthly Dues ($/home)"].max()))

st.markdown("---")

# ---------- Charts (matplotlib, single plot each) ----------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Reserve Balance vs Fully Funded Balance")
    fig1, ax1 = plt.subplots()
    ax1.plot(proj_df["Year"], proj_df["Reserve Ending ($)"], label="Reserve Ending")
    ax1.plot(proj_df["Year"], proj_df["Fully Funded Balance ($)"], label="Fully Funded Balance")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("USD")
    ax1.set_title("Reserves vs FFB (End of Year)")
    ax1.legend()
    st.pyplot(fig1)

with col2:
    st.subheader("Annual Cash Flows")
    fig2, ax2 = plt.subplots()
    ax2.plot(proj_df["Year"], proj_df["Annual Dues Revenue ($)"], label="Dues Revenue")
    ax2.plot(proj_df["Year"], proj_df["Operating Expenses ($)"], label="Operating Expenses")
    ax2.plot(proj_df["Year"], proj_df["Capital Projects ($)"], label="Capital Projects")
    ax2.plot(proj_df["Year"], proj_df["Loan Payments ($)"], label="Loan Payments")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("USD")
    ax2.set_title("Key Annual Cash Flows")
    ax2.legend()
    st.pyplot(fig2)

st.markdown("---")
st.subheader("Projection Table")
st.dataframe(proj_df.style.format({
    "Annual Dues Revenue ($)": "{:,.0f}",
    "Operating Expenses ($)": "{:,.0f}",
    "Operating Margin ($)": "{:,.0f}",
    "Reserve Start ($)": "{:,.0f}",
    "Reserve Contributions ($)": "{:,.0f}",
    "Special Assessment ($)": "{:,.0f}",
    "Loan Draw ($)": "{:,.0f}",
    "Loan Payments ($)": "{:,.0f}",
    "Loan Interest Portion ($)": "{:,.0f}",
    "Capital Projects ($)": "{:,.0f}",
    "Reserve Interest Earned ($)": "{:,.0f}",
    "Loan Fee ($)": "{:,.0f}",
    "Fully Funded Balance ($)": "{:,.0f}",
    "Funding %": "{:,.0f}%",
    "Reserve Ending ($)": "{:,.0f}",
    "Monthly Dues ($/home)": "{:,.2f}"
}))

# Download
st.markdown("### Download Projection")
st.markdown(download_link(proj_df, "hoa_5yr_projection.csv", "⬇️ Download CSV"), unsafe_allow_html=True)

st.markdown("---")
st.caption("Notes: FFB here is modeled as a starting value grown by an annual rate. Replace with reserve study values when available for precision.")
