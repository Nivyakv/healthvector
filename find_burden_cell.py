"""
Fix the burden_trend calculation in Section 3 of analysis.ipynb.
Use the 'visits' column (authoritative count) instead of counting
unique date_of_test entries (which can be fewer if data is missing).
"""
import nbformat as nbf, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('analysis.ipynb', 'r', encoding='utf-8') as f:
    nb = nbf.read(f, as_version=4)

# Find the burden trend cell (Section 3)
for i, cell in enumerate(nb['cells']):
    src = cell.get('source', '')
    if 'burden_trend_records' in src and cell['cell_type'] == 'code':
        print(f"Found burden_trend cell at index {i}")
        print("Current source:")
        print(src[:300])
        print("---")
        break
