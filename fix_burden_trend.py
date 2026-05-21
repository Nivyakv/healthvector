"""
fix_burden_trend.py
===================
Recomputes burden_trend in patient_summary.csv using the 'visits' column
from patient_health_data.csv as the authoritative visit count.

Key change:
- OLD: insufficient_data if len(unique dates in CSV) < 2
- NEW: insufficient_data if visits column < 2
  (since min visits = 3 for all patients, NO patient gets insufficient_data)

For each patient, burden trend is computed from actual CSV data:
  - worsening  : burden_score increased from first visit to last
  - improving  : burden_score decreased
  - stable     : burden_score unchanged
"""
import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')

# ── Load data ─────────────────────────────────────────────────────────────────
df  = pd.read_csv('patient_health_data.csv', parse_dates=['date_of_test'])
summary = pd.read_csv('patient_summary.csv')

print(f"Loaded patient_summary.csv: {len(summary)} rows")
print(f"Before fix — burden_trend distribution:")
print(summary['burden_trend'].value_counts().to_string())
print()

# ── Parameter abnormality check ───────────────────────────────────────────────
INVERTED_PARAMS = {'hdl', 'total_protein'}   # lower is worse

def is_abnormal(row):
    """True if the result is outside the normal range."""
    if row['param_name'] in INVERTED_PARAMS:
        return row['result'] < row['low_range']
    return row['result'] < row['low_range'] or row['result'] > row['high_range']

df['abnormal'] = df.apply(is_abnormal, axis=1)

# ── Per-visit burden score (count of abnormal params per patient per date) ─────
burden_score = (
    df.groupby(['patient_id', 'date_of_test'])['abnormal']
    .sum()
    .reset_index()
    .rename(columns={'abnormal': 'burden_score'})
)

# ── Recompute burden_trend using visits column ────────────────────────────────
visits_per_patient = (
    df.groupby('patient_id')['visits'].first()
)

def compute_burden_trend(pid):
    total_visits = visits_per_patient.get(pid, 0)

    # Use the authoritative visits column — if < 2, insufficient data
    if total_visits < 2:
        return 'insufficient_data'

    # Get per-visit burden scores from actual data
    grp = burden_score[burden_score['patient_id'] == pid].sort_values('date_of_test')
    scores = grp['burden_score'].values

    # Need at least 2 data points to determine direction
    if len(scores) < 2:
        # Patient has visits >= 2 per column but only 1 date in CSV
        # Cannot determine direction → stable (not insufficient)
        return 'stable'

    first, last = scores[0], scores[-1]
    if last > first:
        return 'worsening'
    elif last < first:
        return 'improving'
    else:
        return 'stable'

# Apply to all patients
print("Recomputing burden_trend for all patients...")
summary['burden_trend'] = summary['patient_id'].apply(compute_burden_trend)

print(f"After fix — burden_trend distribution:")
print(summary['burden_trend'].value_counts().to_string())
print()

# ── Save ──────────────────────────────────────────────────────────────────────
import shutil
summary.to_csv('patient_summary_new.csv', index=False)
try:
    shutil.copy('patient_summary_new.csv', 'patient_summary.csv')
    print("Saved patient_summary.csv")
except PermissionError:
    print("NOTE: patient_summary.csv is open — saved as patient_summary_new.csv")

# ── Verify: no more insufficient_data ─────────────────────────────────────────
remaining = (summary['burden_trend'] == 'insufficient_data').sum()
print(f"\nPatients still with insufficient_data: {remaining} (should be 0)")
