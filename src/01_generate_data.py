"""Generate a 2M-row 'orders' dataset with injected data-quality problems."""
import duckdb, os
os.makedirs("data", exist_ok=True)
con = duckdb.connect()
N = 2_000_000

con.execute(f"""
CREATE TABLE raw AS
SELECT
  i AS order_id,
  CASE WHEN random() < 0.03 THEN NULL
       ELSE 1000 + CAST(floor(random()*50000) AS INTEGER) END AS customer_id,
  CASE WHEN random() < 0.05 THEN NULL
       WHEN random() < 0.05 THEN 'bad_email_' || i
       ELSE 'user' || i || '@example.com' END AS email,
  CASE WHEN random() < 0.02 THEN -5
       WHEN random() < 0.02 THEN 250
       ELSE 18 + CAST(floor(random()*60) AS INTEGER) END AS age,
  CASE WHEN random() < 0.02 THEN -round(random()*100, 2)
       ELSE round(random()*500, 2) END AS amount,
  CASE WHEN random() < 0.02 THEN 'XX'
       ELSE (['IN','US','UK','DE','FR'])[1 + CAST(floor(random()*5) AS INTEGER)] END AS country,
  CASE WHEN random() < 0.01 THEN DATE '2030-01-01'
       ELSE DATE '2024-01-01' + CAST(floor(random()*700) AS INTEGER) END AS order_date,
  CASE WHEN random() < 0.02 THEN 'UNKNOWN'
       ELSE (['PAID','PENDING','CANCELLED'])[1 + CAST(floor(random()*3) AS INTEGER)] END AS status
FROM range(1, {N}+1) t(i)
""")
# inject ~1% duplicate rows
con.execute("INSERT INTO raw SELECT * FROM raw WHERE order_id % 100 = 0")

con.execute("COPY raw TO 'data/orders.csv' (HEADER, DELIMITER ',')")
con.execute("COPY raw TO 'data/orders.parquet' (FORMAT PARQUET)")
con.execute("COPY raw TO 'data/orders_by_country' (FORMAT PARQUET, PARTITION_BY (country), OVERWRITE_OR_IGNORE true)")
con.execute("COPY (SELECT * FROM raw LIMIT 1000) TO 'data/orders_sample.json' (FORMAT JSON, ARRAY true)")
print("Rows:", con.execute("SELECT count(*) FROM raw").fetchone()[0])