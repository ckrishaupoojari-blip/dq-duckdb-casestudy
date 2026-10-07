"""Benchmark: file format, partitioning, threads, caching; save chart + EXPLAIN plans."""
import duckdb, time, os
import matplotlib.pyplot as plt
os.makedirs("results", exist_ok=True)
Q = ("SELECT country, count(*) n, avg(amount) avg_amt, "
     "sum(CASE WHEN amount<0 THEN 1 ELSE 0 END) bad FROM {src} GROUP BY country")

def bench(label, src, threads=None, setup=None, reps=3):
    con = duckdb.connect()
    if threads: con.execute(f"SET threads={threads}")
    if setup: con.execute(setup)                       # e.g. cache into memory
    times = []
    for _ in range(reps):
        t = time.perf_counter(); con.execute(Q.format(src=src)).fetchall()
        times.append(time.perf_counter() - t)
    best = min(times); print(f"{label:35s} {best:.3f}s"); return label, best

CSV = "read_csv_auto('data/orders.csv')"
PQ  = "read_parquet('data/orders.parquet')"
PART = "read_parquet('data/orders_by_country/*/*.parquet', hive_partitioning=true)"
cpus = os.cpu_count() or 4

res = [
  bench("CSV (no cache)", CSV),
  bench("Parquet", PQ),
  bench("Parquet partitioned by country", PART),
  bench("CSV cached in memory table", "t", setup=f"CREATE TABLE t AS SELECT * FROM {CSV}"),
]
res += [bench(f"Parquet, {n} thread(s)", PQ, threads=n) for n in sorted({1, 2, 4, cpus})]

plt.figure(figsize=(10,5))
plt.barh([r[0] for r in res], [r[1] for r in res], color="#3b7ddd")
plt.xlabel("Seconds (best of 3)"); plt.title("DuckDB data-quality query: optimisation comparison")
plt.tight_layout(); plt.savefig("results/benchmark.png", dpi=150)

# Query plans (hash GROUP BY on a high-cardinality key = DuckDB's equivalent of a shuffle)
con = duckdb.connect()
with open("results/explain.txt", "w", encoding="utf-8") as f:
    for q in [Q.format(src=PQ),
              "SELECT customer_id, count(*) FROM read_parquet('data/orders.parquet') GROUP BY customer_id"]:
        f.write(q + "\n" + "\n".join(r[1] for r in con.execute("EXPLAIN ANALYZE " + q).fetchall()) + "\n\n")
print("Saved results/benchmark.png and results/explain.txt")