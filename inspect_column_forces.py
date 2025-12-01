"""Inspect the Element Forces - Columns sheet structure."""

from pathlib import Path
import pandas as pd

excel_file = Path(r"Typical Pushover Results\711Vic_Push_DES_All.xlsx")

print(f"Inspecting: Element Forces - Columns")
print("=" * 80)

# Read with header=1 (row 2) to skip table name row
df = pd.read_excel(excel_file, sheet_name='Element Forces - Columns', header=1)

print(f"\nSheet shape: {df.shape[0]} rows x {df.shape[1]} columns")

print("\nFirst 3 data columns:")
print("-" * 80)
for col in df.columns[:15]:
    print(f"  {col}")

print("\nFirst 10 data rows:")
print("-" * 80)
# Select key columns
key_cols = [col for col in df.columns if col in ['Column', 'OutputCase', 'Output Case', 'CaseType', 'Case Type', 'StepType', 'Step Type', 'P', 'V2', 'V3', 'T', 'M2', 'M3']]
if key_cols:
    print(df[key_cols].head(10).to_string())
else:
    print(df.iloc[:10, :10].to_string())

print("\n" + "=" * 80)
print("Unique values in key columns:")
print("-" * 80)

# Check for Output Case column (various naming)
output_case_col = None
for col in df.columns:
    if 'output' in str(col).lower() and 'case' in str(col).lower():
        output_case_col = col
        break

if output_case_col:
    print(f"\n{output_case_col}:")
    unique_cases = df[output_case_col].dropna().unique()
    for case in sorted(unique_cases)[:10]:
        print(f"  - {case}")
    if len(unique_cases) > 10:
        print(f"  ... and {len(unique_cases) - 10} more")

# Check for Step Type
step_type_col = None
for col in df.columns:
    if 'step' in str(col).lower() and 'type' in str(col).lower():
        step_type_col = col
        break

if step_type_col:
    print(f"\n{step_type_col}:")
    unique_steps = df[step_type_col].dropna().unique()
    for step in unique_steps:
        print(f"  - {step}")

# Check for Column column
column_col = None
for col in df.columns:
    if str(col).lower() == 'column':
        column_col = col
        break

if column_col:
    print(f"\n{column_col}:")
    unique_columns = df[column_col].dropna().unique()
    print(f"  Total columns: {len(unique_columns)}")
    print(f"  Sample: {', '.join(str(c) for c in sorted(unique_columns)[:10])}...")
