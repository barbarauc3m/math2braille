import sqlite3
conn = sqlite3.connect("service/backend/data/db/math2pix_test.sqlite")
scores = [row[0] for row in conn.execute("SELECT confidence_score FROM formula")]

import statistics
print(f"Total: {len(scores)}")
print(f"Media: {statistics.mean(scores):.3f}, mediana: {statistics.median(scores):.3f}")
for umbral in [0.25, 0.3, 0.4, 0.5, 0.6, 0.7]:
    por_encima = sum(1 for s in scores if s >= umbral)
    print(f"  >= {umbral}: {por_encima} ({100*por_encima/len(scores):.1f}%)")