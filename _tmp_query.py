import sqlite3, json
conn = sqlite3.connect('data/projects/t2/t2.db')
c = conn.cursor()
row = c.execute('SELECT results_matrix FROM element_results_cache WHERE result_type="QuadRotations" LIMIT 1').fetchone()
print('Quad rotation sample:')
if row:
    data = json.loads(row[0])
    for k,v in list(data.items())[:5]:
        print(k, v)
conn.close()
