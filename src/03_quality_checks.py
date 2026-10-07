"""Run data-quality rules with DuckDB, clean data, quarantine bad rows, store history."""
import duckdb, os, datetime
os.makedirs("results", exist_ok=True)
con = duckdb.connect("data/dq.duckdb")
if os.getenv("DUCK_THREADS"):                       # used in the Kubernetes bonus
    con.execute(f"SET threads={os.getenv('DUCK_THREADS')}")
print("Threads in use:", con.execute("SELECT current_setting('threads')").fetchone()[0])

# ---- LOAD (CSV -> DuckDB table; reading is parallelised across threads) ----
con.execute("CREATE OR REPLACE TABLE orders AS SELECT * FROM read_csv_auto('data/orders.csv')")
con.execute("CREATE TABLE IF NOT EXISTS dq_results (run_ts TIMESTAMP, dataset VARCHAR, "
            "check_name VARCHAR, dimension VARCHAR, failed BIGINT, total BIGINT, pass_pct DOUBLE)")

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$"
CHECKS = [  # (name, dimension, SQL that returns number of FAILING rows)
 ("email_not_null",   "Completeness", "SELECT count(*) FROM TABLE WHERE email IS NULL"),
 ("customer_not_null","Completeness", "SELECT count(*) FROM TABLE WHERE customer_id IS NULL"),
 ("order_id_unique",  "Uniqueness",   "SELECT count(*) - count(DISTINCT order_id) FROM TABLE"),
 ("email_format",     "Validity",     f"SELECT count(*) FROM TABLE WHERE email IS NOT NULL AND NOT regexp_matches(email, '{EMAIL_RE}')"),
 ("age_in_18_100",    "Validity",     "SELECT count(*) FROM TABLE WHERE age NOT BETWEEN 18 AND 100"),
 ("amount_non_neg",   "Validity",     "SELECT count(*) FROM TABLE WHERE amount < 0"),
 ("country_allowed",  "Consistency",  "SELECT count(*) FROM TABLE WHERE country NOT IN ('IN','US','UK','DE','FR')"),
 ("status_allowed",   "Consistency",  "SELECT count(*) FROM TABLE WHERE status NOT IN ('PAID','PENDING','CANCELLED')"),
 ("date_in_range",    "Timeliness",   "SELECT count(*) FROM TABLE WHERE order_date NOT BETWEEN DATE '2024-01-01' AND DATE '2025-12-31'"),
]

def run_checks(table, label):
    ts = datetime.datetime.now()                      # one timestamp for the whole run
    total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    for name, dim, sql in CHECKS:
        failed = con.execute(sql.replace("TABLE", table)).fetchone()[0]
        pct = 100.0 * (1 - failed / total)
        con.execute("INSERT INTO dq_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [ts, label, name, dim, failed, total, pct])
    print(f"\n=== {label} ({total:,} rows) ===")
    print(con.execute("SELECT check_name, dimension, failed, round(pass_pct,2) AS pass_pct "
                      "FROM dq_results WHERE dataset=? AND run_ts=?",
                      [label, ts]).df().to_string(index=False))

run_checks("orders", "raw")                                     # ACTION: scan + aggregate

# ---- TRANSFORMATIONS: dedupe, filter, standardise ----
con.execute(f"""
CREATE OR REPLACE TABLE orders_clean AS
SELECT DISTINCT ON (order_id) order_id, customer_id, lower(email) AS email, age, amount,
       country, order_date, status
FROM orders
WHERE email IS NOT NULL AND regexp_matches(email, '{EMAIL_RE}')
  AND customer_id IS NOT NULL AND age BETWEEN 18 AND 100 AND amount >= 0
  AND country IN ('IN','US','UK','DE','FR') AND status IN ('PAID','PENDING','CANCELLED')
  AND order_date BETWEEN DATE '2024-01-01' AND DATE '2025-12-31'
""")
con.execute("CREATE OR REPLACE TABLE orders_quarantine AS "
            "SELECT o.* FROM orders o ANTI JOIN orders_clean c ON o.order_id = c.order_id")

run_checks("orders_clean", "clean")                             # should be ~100%

# ---- ACTIONS: export results ----
con.execute("COPY orders_clean TO 'results/orders_clean.parquet' (FORMAT PARQUET)")
con.execute("COPY orders_quarantine TO 'results/orders_quarantine.csv' (HEADER)")
con.execute("COPY (SELECT * FROM dq_results ORDER BY run_ts DESC) TO 'results/dq_report.csv' (HEADER)")
print("\nClean rows:", con.execute("SELECT count(*) FROM orders_clean").fetchone()[0],
      "| Quarantined:", con.execute("SELECT count(*) FROM orders_quarantine").fetchone()[0])