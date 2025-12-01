"""
Inspect pushover wall rotations Excel file structure
"""
import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Walls.xlsx")

print("=" * 80)
print(f"Inspecting: {excel_file.name}")
print("=" * 80)

# Read Quad Strain Gauge - Rotation sheet
df = pd.read_excel(excel_file, sheet_name='Quad Strain Gauge - Rotation', header=1)
df = df.drop(0)  # Drop units row

print(f"\n" + "=" * 80)
print("Quad Strain Gauge - Rotation Sheet Structure")
print("=" * 80)

print(f"\nColumns: {list(df.columns)}")
print(f"\nShape: {df.shape}")
print(f"\nFirst 20 rows:")
print(df.head(20))

print(f"\nUnique Elements (Name): {sorted(df['Name'].unique())}")
print(f"\nUnique Property Names: {sorted(df['PropertyName'].unique())}")
print(f"\nUnique Output Cases:")
for case in sorted(df['Output Case'].unique()):
    print(f"  - {case}")

print(f"\nUnique Stories: {sorted(df['Story'].unique())}")
print(f"\nUnique Step Types: {sorted(df['StepType'].unique())}")
print(f"\nUnique Directions: {sorted(df['Direction'].unique())}")

# Sample data for one element
sample_elem = df['Name'].unique()[0]
print(f"\n" + "=" * 80)
print(f"Sample data for Element: {sample_elem}")
print("=" * 80)

sample = df[df['Name'] == sample_elem].head(20)
print(sample[['Name', 'PropertyName', 'Story', 'Output Case', 'StepType', 'Direction', 'Rotation']])

print("\n" + "=" * 80)
