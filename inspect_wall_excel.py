"""
Inspect pushover walls Excel file structure
"""
import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Walls.xlsx")

print("=" * 80)
print(f"Inspecting: {excel_file.name}")
print("=" * 80)

# Check available sheets
xl = pd.ExcelFile(excel_file)
print(f"\nAvailable sheets:")
for sheet in xl.sheet_names:
    print(f"  - {sheet}")

# Read Pier Forces sheet
df = pd.read_excel(excel_file, sheet_name='Pier Forces', header=1)
df = df.drop(0)  # Drop units row

print(f"\n" + "=" * 80)
print("Pier Forces Sheet Structure")
print("=" * 80)

print(f"\nColumns: {list(df.columns)}")
print(f"\nShape: {df.shape}")
print(f"\nFirst 10 rows:")
print(df.head(10))

print(f"\nUnique Piers: {sorted(df['Pier'].unique())}")
print(f"\nUnique Output Cases:")
for case in sorted(df['Output Case'].unique()):
    print(f"  - {case}")

print(f"\nUnique Stories: {sorted(df['Story'].unique())}")
print(f"\nUnique Step Types: {sorted(df['Step Type'].unique())}")
print(f"\nUnique Locations: {sorted(df['Location'].unique())}")

# Sample data for one pier
sample_pier = df['Pier'].unique()[0]
print(f"\n" + "=" * 80)
print(f"Sample data for Pier: {sample_pier}")
print("=" * 80)

sample = df[df['Pier'] == sample_pier].head(20)
print(sample[['Pier', 'Story', 'Output Case', 'Step Type', 'Location', 'P', 'V2', 'V3', 'M2', 'M3']])

print("\n" + "=" * 80)
