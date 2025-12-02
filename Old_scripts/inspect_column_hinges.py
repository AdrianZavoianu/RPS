"""
Inspect pushover column hinges Excel file structure
"""
import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Column Hinges.xlsx")

print("=" * 80)
print(f"Inspecting: {excel_file.name}")
print("=" * 80)

# Check available sheets
xl = pd.ExcelFile(excel_file)
print(f"\nAvailable sheets:")
for sheet in xl.sheet_names:
    print(f"  - {sheet}")

# Read first sheet (likely the hinges data)
if xl.sheet_names:
    first_sheet = xl.sheet_names[0]
    print(f"\n" + "=" * 80)
    print(f"Inspecting: {first_sheet}")
    print("=" * 80)

    df = pd.read_excel(excel_file, sheet_name=first_sheet, header=1)
    df = df.drop(0)  # Drop units row

    print(f"\nColumns: {list(df.columns)}")
    print(f"\nShape: {df.shape}")
    print(f"\nFirst 20 rows:")
    print(df.head(20))

    print(f"\nUnique Columns (Frame): {sorted(df['Frame'].unique()) if 'Frame' in df.columns else 'N/A'}")
    print(f"\nUnique Output Cases:")
    if 'Output Case' in df.columns:
        for case in sorted(df['Output Case'].unique())[:10]:  # Show first 10
            print(f"  - {case}")

    print(f"\nUnique Stories: {sorted(df['Story'].unique()) if 'Story' in df.columns else 'N/A'}")
    print(f"\nUnique Step Types: {sorted(df['Step Type'].unique()) if 'Step Type' in df.columns else 'N/A'}")
    print(f"\nUnique Locations: {sorted(df['Location'].unique()) if 'Location' in df.columns else 'N/A'}")

    # Sample data for one column
    if 'Frame/Wall' in df.columns:
        print(f"\nUnique Columns/Frames: {sorted(df['Frame/Wall'].unique())}")
        sample_col = df['Frame/Wall'].unique()[0]
        print(f"\n" + "=" * 80)
        print(f"Sample data for Column: {sample_col}")
        print("=" * 80)

        sample = df[df['Frame/Wall'] == sample_col].head(20)
        print(sample[['Frame/Wall', 'Unique Name', 'Output Case', 'Step Type', 'R2', 'R3', 'Hinge State']])

        # Show unique names for this column
        print(f"\nUnique Names for {sample_col}: {df[df['Frame/Wall'] == sample_col]['Unique Name'].unique()}")

print("\n" + "=" * 80)
