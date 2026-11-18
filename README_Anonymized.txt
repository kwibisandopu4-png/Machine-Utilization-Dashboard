AI-ENABLED MACHINE UTILIZATION & RELIABILITY DASHBOARD
===========================================================

UPDATED PROJECT ASSUMPTIONS
----------------------------
1. Shift duration: 8 hours = 480 minutes.
2. Break: 30 minutes at the start of every shift.
3. Planned production time: 480 - 30 = 450 minutes.
4. Machines are anonymised as Machine 1 and Machine 2.
5. The bundled CSV is demonstration/synthetic data. Replace it with approved
   workplace data before presenting workplace findings as factual results.
6. The workplace VE Control Panel screenshot supplied for this project is used
   as a reference for realistic KPI ranges. Screenshot-derived values should
   not be presented as exact event-level records unless verified from the
   underlying production system.

LOCAL RUNNING
-------------
Option A:
- Double-click run_app.bat

Option B:
- Open PowerShell in this folder.
- If your virtual environment exists:
    .\venv\Scripts\python.exe -m streamlit run app.py
- Otherwise:
    python -m streamlit run app.py

Then open the local address shown by Streamlit, normally:
http://localhost:8501

SHARING WITH A LECTURER
-----------------------
A localhost URL is NOT a public URL. It only works on the computer running
the Streamlit application.

For a lecturer to open the project from their own laptop without installing
Python, deploy the app to Streamlit Community Cloud (or another approved
cloud platform). The deployment should contain:
- app.py
- requirements.txt
- sample_production_data.csv

Typical Streamlit Cloud workflow:
1. Create a GitHub repository.
2. Upload app.py, requirements.txt and sample_production_data.csv.
3. Create a Streamlit Community Cloud deployment from that repository.
4. Select app.py as the main file.
5. Streamlit provides a public HTTPS URL.
6. Submit that URL together with the project report and source-code ZIP.

Important: do not upload confidential production data, employee names,
company names, machine serial numbers, passwords or other restricted data
to a public repository. Use the anonymised demonstration CSV or an approved
anonymised dataset.

DATA COLUMNS
------------
date
shift
machine
shift_minutes
break_minutes
planned_minutes
running_minutes
downtime_minutes
target_output
actual_output
rejected_output
primary_downtime_reason

KPI DEFINITIONS
---------------
Utilization = Running minutes / Planned production minutes × 100
Downtime % = Downtime minutes / Planned production minutes × 100
Target achievement = Actual output / Target output × 100
Quality rate = (Actual output - Rejected output) / Actual output × 100

The reliability module currently reports MTBF/MTTR proxies because the
demonstration CSV is shift-level rather than event-level maintenance data.
For a formal reliability study, add validated failure and repair timestamps.
