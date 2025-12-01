"""
Inspect pushover column hinge stories
"""
import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Column Hinges.xlsx")

df = pd.read_excel(excel_file, sheet_name='Fiber Hinge States', header=1)
df = df.drop(0)  # Drop units row

print("=" * 80)
print(f"Hinge Locations by Column and Story")
print("=" * 80)

# For each column, show unique names and their stories
for column in sorted(df['Frame/Wall'].unique()):
    col_df = df[df['Frame/Wall'] == column]
    unique_names = col_df['Unique Name'].unique()

    print(f"\nColumn: {column}")
    print(f"  Unique Names ({len(unique_names)}): {sorted(unique_names)}")

    for un in sorted(unique_names):
        stories = col_df[col_df['Unique Name'] == un]['Story'].unique()
        print(f"    {un}: Story = {stories[0] if len(stories) == 1 else stories}")

print("\n" + "=" * 80)
