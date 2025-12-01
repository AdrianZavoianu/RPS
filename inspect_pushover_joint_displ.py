"""Inspect pushover joint displacements sheet structure"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Global_Resp.xlsx")

print("=" * 80)
print("PUSHOVER JOINT DISPLACEMENTS SHEET INSPECTION")
print("=" * 80)
print(f"File: {excel_file.name}")
print()

# Read Joint Displacements sheet
df = pd.read_excel(excel_file, sheet_name='Joint Displacements', header=1)
print(f"Shape: {df.shape}")
print()

print("Columns:")
for i, col in enumerate(df.columns):
    print(f"  {i}: {col}")
print()

print("First 15 rows:")
print(df.head(15))
print()

print("Unique Output Cases:")
unique_cases = df['Output Case'].dropna().unique()
print(f"  Count: {len(unique_cases)}")
for case in sorted([str(c) for c in unique_cases])[:10]:
    print(f"    - {case}")
if len(unique_cases) > 10:
    print(f"    ... and {len(unique_cases) - 10} more")
print()

print("Unique Step Types:")
print(f"  {df['Step Type'].unique()}")
print()

print("Unique Stories:")
unique_stories = df['Story'].dropna().unique()
print(f"  Count: {len(unique_stories)}")
print(f"  Stories: {sorted([str(s) for s in unique_stories])}")
print()

# Check for direction filtering pattern
print("Output case filtering:")
print(f"  X direction cases: {len([c for c in unique_cases if '_X+' in str(c) or '_X-' in str(c)])}")
print(f"  Y direction cases: {len([c for c in unique_cases if '_Y+' in str(c) or '_Y-' in str(c)])}")
print()

# Sample data for one case
sample_case = sorted([str(c) for c in unique_cases])[0]
sample = df[df['Output Case'] == sample_case].head(10)
print(f"Sample data for '{sample_case}':")
print(sample[['Story', 'Label', 'Unique Name', 'Output Case', 'Step Type', 'Ux', 'Uy', 'Uz']])
print()

print("=" * 80)
