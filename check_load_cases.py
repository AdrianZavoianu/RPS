"""
Check load cases and cache building
"""
import sqlite3
from pathlib import Path
import json

db_path = Path("C:/SoftDev/RPS/data/projects/t2/t2.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("Load Cases and Cache Analysis")
print("=" * 80)

# Get all load cases
cursor.execute("SELECT id, name, case_type FROM load_cases ORDER BY name")
load_cases = cursor.fetchall()
print(f"\nTotal load cases: {len(load_cases)}")
print("\nLoad cases:")
for lc in load_cases:
    print(f"  {lc[0]:2d}: {lc[1]:<25} ({lc[2]})")

# Get all cache entries
cursor.execute("""
    SELECT
        grc.id,
        grc.result_type,
        s.name AS story,
        grc.results_matrix,
        grc.story_sort_order
    FROM global_results_cache grc
    JOIN stories s ON grc.story_id = s.id
    WHERE grc.result_set_id = 1
    ORDER BY grc.result_type, grc.story_sort_order
""")

cache_entries = cursor.fetchall()
print(f"\n" + "=" * 80)
print(f"Cache Entries: {len(cache_entries)}")
print("=" * 80)

for entry in cache_entries:
    cache_id, result_type, story, results_json, sort_order = entry
    results = json.loads(results_json)

    print(f"\n{result_type} - {story} (sort_order: {sort_order}, cache_id: {cache_id})")
    print(f"  Load cases in cache: {len(results)}")

    # Group by direction suffix
    x_cases = [k for k in results.keys() if k.endswith('_X') or k.endswith('_VX') or k.endswith('_UX')]
    y_cases = [k for k in results.keys() if k.endswith('_Y') or k.endswith('_VY') or k.endswith('_UY')]
    other = [k for k in results.keys() if k not in x_cases and k not in y_cases]

    print(f"  X direction: {len(x_cases)}")
    if x_cases:
        print(f"    {x_cases[:3]}")
    print(f"  Y direction: {len(y_cases)}")
    if y_cases:
        print(f"    {y_cases[:3]}")
    if other:
        print(f"  Other: {other}")

conn.close()
print("\n" + "=" * 80)
