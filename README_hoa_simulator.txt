HOA 5-Year Budget Scenario Simulator (Streamlit)
===============================================

What this is
------------
A lightweight, interactive simulator to model a 5-year HOA budget for a 420-home community 
(with golf course, pools, courts, and common areas). It handles operating expenses, reserve 
funding, capital projects, dues strategies, special assessments, loans, and reserve interest.

Files
-----
- hoa_budget_simulator.py  : The Streamlit app
- sample_operating_budget.csv : Editable baseline operating categories
- (Optional) You can upload your own CSVs in the app to replace the sample data.

How to run (locally)
--------------------
1) Ensure you have Python 3.9+ installed.
2) Install required packages:
   pip install streamlit pandas numpy matplotlib
3) From a terminal/shell, run:
   streamlit run hoa_budget_simulator.py
4) Your browser will open at a local URL (shown in the terminal).

Data assumptions you can change in the app
------------------------------------------
- Number of homes (default 420)
- Starting monthly dues and step increases by year
- Operating expense inflation rate
- Reserve starting balance and annual contribution method
- Capital project list, timing, costs, and phasing
- Special assessment amount (per-home or total) and timing
- HOA loan (amount, rate, term, start year, fee)
- Reserve interest/earnings rate

Tips
----
- Start with the "Base Case" then try "Catch-Up" or "High Inflation" preset toggles.
- Use the charts and KPIs to communicate options to the board and homeowners.
- Export scenario tables using Streamlit's download widgets.