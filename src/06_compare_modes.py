"""Compare pandas vs DuckDB (1 vs all threads) vs PySpark local[1] vs local[*]."""
import time, os, duckdb, pandas as pd
PQ = "data/orders.parquet"
def timeit(f):
    f()                                  # warm-up
    s = time.perf_counter(); f(); return time.perf_counter() - s

def pandas_job():
    df = pd.read_parquet(PQ)
    df.groupby("country").agg(n=("order_id", "count"), avg_amt=("amount", "mean"))

def duck_job(th):
    def f():
        c = duckdb.connect(); c.execute(f"SET threads={th}")
        c.execute(f"SELECT country, count(*), avg(amount) FROM read_parquet('{PQ}') GROUP BY country").fetchall()
    return f

res = {"pandas": timeit(pandas_job),
       "duckdb_1_thread": timeit(duck_job(1)),
       f"duckdb_{os.cpu_count()}_threads": timeit(duck_job(os.cpu_count()))}

try:
    from pyspark.sql import SparkSession, functions as F
    for master in ["local[1]", "local[*]"]:
        spark = SparkSession.builder.master(master).appName("dq") \
                .config("spark.sql.shuffle.partitions", "8").getOrCreate()
        job = lambda: spark.read.parquet(PQ).groupBy("country") \
                .agg(F.count("*"), F.avg("amount")).collect()
        res[f"spark_{master}"] = timeit(job); spark.stop()
except Exception as e:
    print("Spark skipped:", e)

os.makedirs("results", exist_ok=True)
out = pd.DataFrame({"mode": list(res.keys()), "seconds": list(res.values())}).sort_values("seconds")
print(out.to_string(index=False)); out.to_csv("results/mode_comparison.csv", index=False)