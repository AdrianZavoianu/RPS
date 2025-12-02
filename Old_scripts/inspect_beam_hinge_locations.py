"""
Inspect beam hinge locations
"""
import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Beam Hinges.xlsx")

df = pd.read_excel(excel_file, sheet_name='Hinge States', header=1)
df = df.drop(0)  # Drop units row

print("=" * 80)
print(f"Hinge Locations by Beam")
print("=" * 80)

# For each beam, show unique names and their stories
for beam in sorted(df['Frame/Wall'].unique())[:5]:  # Show first 5 beams
    beam_df = df[df['Frame/Wall'] == beam]
    unique_names = beam_df['Unique Name'].unique()

    print(f"\nBeam: {beam}")
    print(f"  Unique Names ({len(unique_names)}): {sorted(unique_names)}")

    for un in sorted(unique_names):
        stories = beam_df[beam_df['Unique Name'] == un]['Story'].unique()
        print(f"    {un}: Story = {stories[0] if len(stories) == 1 else stories}")

print("\n" + "=" * 80)
print("Summary")
print("=" * 80)

total_beams = len(df['Frame/Wall'].unique())
total_unique_names = len(df['Unique Name'].unique())
print(f"Total beams: {total_beams}")
print(f"Total unique hinge locations: {total_unique_names}")
print(f"Average hinges per beam: {total_unique_names / total_beams:.1f}")
