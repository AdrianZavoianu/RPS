"""
Debug script to investigate Y direction drift extraction
"""
import pandas as pd
from pathlib import Path

# Use the global response file (contains Story Drifts, Story Forces, etc.)
excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Global_Resp.xlsx")

print("=" * 80)
print("Debugging Y Direction Drift Extraction")
print("=" * 80)

# Read Story Drifts sheet
df = pd.read_excel(excel_file, sheet_name='Story Drifts', header=1)
df = df.drop(0)  # Drop units row

print(f"\n1. Total rows after reading: {len(df)}")
print(f"   Columns: {list(df.columns)}")
print(f"\n   Unique stories: {sorted(df['Story'].unique())}")
print(f"   Unique output cases: {sorted(df['Output Case'].unique())}")
print(f"   Unique directions: {sorted(df['Direction'].unique())}")

# Filter columns
df = df[['Story', 'Output Case', 'Step Type', 'Direction', 'Drift']]

# Filter by Y pushover direction in Output Case name
direction = 'Y'
pattern = f'[_/]{direction}[+-]'
df_filtered_cases = df[df['Output Case'].str.contains(pattern, na=False, regex=True)]

print(f"\n2. After filtering to Y pushover cases (pattern '{pattern}'):")
print(f"   Rows: {len(df_filtered_cases)}")
print(f"   Unique stories: {sorted(df_filtered_cases['Story'].unique())}")
print(f"   Unique output cases: {sorted(df_filtered_cases['Output Case'].unique())}")
print(f"   Unique directions: {sorted(df_filtered_cases['Direction'].unique())}")

# Filter to Y drift component
df_final = df_filtered_cases[df_filtered_cases['Direction'] == direction]

print(f"\n3. After filtering to Y drift component (Direction == '{direction}'):")
print(f"   Rows: {len(df_final)}")
print(f"   Unique stories: {sorted(df_final['Story'].unique())}")
print(f"   Unique output cases: {sorted(df_final['Output Case'].unique())}")

# Show sample data for each story
print(f"\n4. Sample data per story:")
for story in sorted(df_final['Story'].unique()):
    story_data = df_final[df_final['Story'] == story]
    print(f"\n   {story}: {len(story_data)} rows")
    print(f"      Output cases: {sorted(story_data['Output Case'].unique())}")
    print(f"      Drift range: {story_data['Drift'].min():.4f} to {story_data['Drift'].max():.4f}")

# Groupby to see max drifts
print(f"\n5. After groupby max operation:")
story_order = df_final['Story'].unique().tolist()
max_drifts = df_final.groupby(['Story', 'Output Case'], sort=False)['Drift'].apply(
    lambda x: x.max()
).unstack().reset_index()

print(f"   Resulting DataFrame shape: {max_drifts.shape}")
print(f"   Stories: {list(max_drifts.iloc[:, 0])}")
print(f"   Load case columns: {list(max_drifts.columns[1:])}")
print("\n   Data preview:")
print(max_drifts)

print("\n" + "=" * 80)
