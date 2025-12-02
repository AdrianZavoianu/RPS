"""
Check what's actually in the database for Y direction drifts
"""
import sqlite3
from pathlib import Path

# Find a project database
db_path = Path("C:/SoftDev/RPS/data/projects/t2/t2.db")

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("Database Drift Analysis - Y Direction")
print("=" * 80)

# Get project info
cursor.execute("SELECT id, name FROM projects LIMIT 1")
project = cursor.fetchone()
print(f"\nProject: {project[1]} (ID: {project[0]})")

# Get result sets
cursor.execute("SELECT id, name, analysis_type FROM result_sets WHERE project_id = ?", (project[0],))
result_sets = cursor.fetchall()
print(f"\nResult Sets:")
for rs in result_sets:
    print(f"  - {rs[1]} (ID: {rs[0]}, Type: {rs[2]})")

# Focus on Pushover result set
pushover_rs = [rs for rs in result_sets if rs[2] == 'Pushover']
if not pushover_rs:
    print("\nNo Pushover result sets found!")
    conn.close()
    exit(0)

rs_id = pushover_rs[0][0]
print(f"\nAnalyzing Pushover Result Set: {pushover_rs[0][1]} (ID: {rs_id})")

# Check story_drifts table
print("\n" + "=" * 80)
print("Story Drifts Table - Y Direction")
print("=" * 80)

cursor.execute("""
    SELECT
        sd.id,
        s.name AS story,
        lc.name AS load_case,
        sd.direction,
        sd.drift,
        sd.story_sort_order
    FROM story_drifts sd
    JOIN stories s ON sd.story_id = s.id
    JOIN load_cases lc ON sd.load_case_id = lc.id
    WHERE sd.direction = 'Y'
    ORDER BY sd.story_sort_order, lc.name
""")

rows = cursor.fetchall()
print(f"\nTotal Y drift records: {len(rows)}")

if rows:
    print(f"\nFirst 20 records:")
    print(f"{'Story':<8} {'Load Case':<20} {'Drift':<10} {'Sort Order':<10}")
    print("-" * 50)
    for row in rows[:20]:
        print(f"{row[1]:<8} {row[2]:<20} {row[4]:<10.6f} {row[5]}")

    # Group by story
    print(f"\nRecords per story:")
    cursor.execute("""
        SELECT
            s.name AS story,
            COUNT(*) as count,
            MIN(sd.story_sort_order) as sort_order
        FROM story_drifts sd
        JOIN stories s ON sd.story_id = s.id
        WHERE sd.direction = 'Y'
        GROUP BY s.name
        ORDER BY sort_order
    """)
    story_counts = cursor.fetchall()
    for story, count, sort_order in story_counts:
        print(f"  {story}: {count} records (sort_order: {sort_order})")
else:
    print("\nNo Y drift records found!")

# Check cache
print("\n" + "=" * 80)
print("Global Results Cache - Drifts")
print("=" * 80)

cursor.execute("""
    SELECT
        grc.id,
        s.name AS story,
        grc.result_type,
        grc.results_matrix,
        grc.story_sort_order
    FROM global_results_cache grc
    JOIN stories s ON grc.story_id = s.id
    WHERE grc.result_set_id = ? AND grc.result_type = 'Drifts'
    ORDER BY grc.story_sort_order
""", (rs_id,))

cache_rows = cursor.fetchall()
print(f"\nCache entries: {len(cache_rows)}")

if cache_rows:
    print(f"\nCache contents:")
    for row in cache_rows:
        story = row[1]
        sort_order = row[4]
        # Parse JSON to see load cases
        import json
        results = json.loads(row[3])
        load_cases = list(results.keys())
        # Filter to Y direction load cases
        y_cases = [lc for lc in load_cases if '_Y' in lc or '_UY' in lc]
        print(f"\n  {story} (sort_order: {sort_order}):")
        print(f"    Total load cases in cache: {len(load_cases)}")
        print(f"    Y direction cases: {len(y_cases)}")
        if y_cases:
            print(f"    Y cases: {y_cases[:3]}..." if len(y_cases) > 3 else f"    Y cases: {y_cases}")
            # Show sample values
            for lc in y_cases[:2]:
                print(f"      {lc}: {results[lc]:.6f}")
else:
    print("\nNo cache entries found!")

conn.close()
print("\n" + "=" * 80)
