import duckdb
print("Total rows:", duckdb.sql("SELECT count(*) FROM read_parquet('data/orders.parquet')").fetchone()[0])
print(duckdb.sql("SELECT * FROM read_parquet('data/orders.parquet') LIMIT 8").df().to_string(index=False))
