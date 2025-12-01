"""
Check t6 database - fresh import
"""
import sqlite3
from pathlib import Path
import json

# Find t6 database
db_files = list(Path("C:/SoftDev/RPS/data/projects/t6").glob("*.db"))
db_path = [f for f in db_files if f.stat().st_size > 0][0]

print(f"Using database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("T6 Project Analysis")
print("=" * 80)

# Get project and result set
cursor.execute("SELECT id, name FROM projects LIMIT 1")
project = cursor.fetchone()
print(f"\nProject: {project[1]} (ID: {project[0]})")

cursor.execute("SELECT id, name, analysis_type FROM result_sets WHERE project_id = ?", (project[0],))
result_sets = cursor.fetchall()
print(f"\nResult Sets:")
for rs in result_sets:
    print(f"  - {rs[1]} (ID: {rs[0]}, Type: {rs[2]})")

pushover_rs = [rs for rs in result_sets if rs[2] == 'Pushover']
if not pushover_rs:
    print("\nNo Pushover result sets!")
    conn.close()
    exit(0)

rs_id = pushover_rs[0][0]

# Check story_drifts counts
print("\n" + "=" * 80)
print("Story Drifts - Record Counts")
print("=" * 80)

cursor.execute("""
    SELECT
        s.name,
        sd.direction,
        COUNT(*) as count
    FROM story_drifts sd
    JOIN stories s ON sd.story_id = s.id
    GROUP BY s.name, sd.direction
    ORDER BY s.name, sd.direction
""")

for story, direction, count in cursor.fetchall():
    print(f"  {story} {direction}: {count} records")

# Check cache
print("\n" + "=" * 80)
print("Cache Entries")
print("=" * 80)

cursor.execute("""
    SELECT
        grc.id,
        grc.result_type,
        s.name AS story,
        grc.results_matrix,
        grc.story_sort_order
    FROM global_results_cache grc
    JOIN stories s ON grc.story_id = s.id
    WHERE grc.result_set_id = ?
    ORDER BY grc.result_type, grc.story_sort_order
""", (rs_id,))

cache_entries = cursor.fetchall()
print(f"\nTotal cache entries: {len(cache_entries)}")

for entry in cache_entries:
    cache_id, result_type, story, results_json, sort_order = entry
    results = json.loads(results_json)

    x_cases = [k for k in results.keys() if '_X' in k or '_VX' in k or '_UX' in k]
    y_cases = [k for k in results.keys() if '_Y' in k or '_VY' in k or '_UY' in k]

    print(f"\n{result_type} - {story} (sort: {sort_order}, id: {cache_id})")
    print(f"  Total: {len(results)} | X: {len(x_cases)} | Y: {len(y_cases)}")

    if len(results) <= 5:
        print(f"  Keys: {list(results.keys())}")
    else:
        print(f"  X sample: {x_cases[:2]}")
        print(f"  Y sample: {y_cases[:2]}")

# Check load cases
print("\n" + "=" * 80)
print("Load Cases")
print("=" * 80)

cursor.execute("SELECT id, name FROM load_cases ORDER BY name")
load_cases = cursor.fetchall()
print(f"\nTotal: {len(load_cases)}")
for lc_id, name in load_cases[:20]:
    print(f"  {lc_id:2d}: {name}")
if len(load_cases) > 20:
    print(f"  ... and {len(load_cases) - 20} more")

conn.close()
print("\n" + "=" * 80)
