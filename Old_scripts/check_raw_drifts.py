"""
Check story_drifts table - verify both X and Y were imported
"""
import sqlite3
from pathlib import Path

db_path = Path("C:/SoftDev/RPS/data/projects/t2/t2.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("Story Drifts Table Analysis")
print("=" * 80)

# Count by direction
cursor.execute("""
    SELECT direction, COUNT(*) as count
    FROM story_drifts
    GROUP BY direction
""")
direction_counts = cursor.fetchall()
print(f"\nRecords by direction:")
for direction, count in direction_counts:
    print(f"  {direction}: {count} records")

# Count by story
cursor.execute("""
    SELECT
        s.name AS story,
        sd.direction,
        COUNT(*) as count,
        MIN(sd.story_sort_order) as sort_order
    FROM story_drifts sd
    JOIN stories s ON sd.story_id = s.id
    GROUP BY s.name, sd.direction
    ORDER BY sort_order, sd.direction
""")

story_counts = cursor.fetchall()
print(f"\nRecords by story and direction:")
print(f"{'Story':<8} {'Direction':<10} {'Count':<10} {'Sort Order'}")
print("-" * 50)
for story, direction, count, sort_order in story_counts:
    print(f"{story:<8} {direction:<10} {count:<10} {sort_order}")

# Get sample load cases for each story/direction combo
cursor.execute("""
    SELECT
        s.name AS story,
        sd.direction,
        GROUP_CONCAT(lc.name, ', ') as load_cases
    FROM story_drifts sd
    JOIN stories s ON sd.story_id = s.id
    JOIN load_cases lc ON sd.load_case_id = lc.id
    WHERE s.name = 'L01'
    GROUP BY s.name, sd.direction
""")

l01_cases = cursor.fetchall()
print(f"\nLoad cases for L01:")
for story, direction, load_cases in l01_cases:
    cases_list = load_cases.split(', ')
    print(f"  {direction}: {len(cases_list)} cases")
    print(f"    {', '.join(cases_list[:4])}...")

conn.close()
print("\n" + "=" * 80)
