"""Poll a live API, validate with DuckDB, append DQ metrics to a history table.
Usage: python src/05_realtime_api.py <iterations> <interval_seconds>"""
import duckdb, requests, time, sys, os, datetime
os.makedirs("data", exist_ok=True)
URL = ("https://api.open-meteo.com/v1/forecast?latitude=19.07&longitude=72.87"
       "&hourly=temperature_2m,relative_humidity_2m&past_days=1&forecast_days=1&timezone=UTC")
con = duckdb.connect("data/dq.duckdb")
con.execute("CREATE TABLE IF NOT EXISTS api_dq_history (run_ts TIMESTAMP, rows_total BIGINT, "
            "null_temp BIGINT, temp_out_of_range BIGINT, humidity_out_of_range BIGINT, pass_pct DOUBLE)")

def run_once():
    r = requests.get(URL, timeout=30); r.raise_for_status()
    h = r.json()["hourly"]
    con.execute("CREATE OR REPLACE TABLE api_weather (ts VARCHAR, temp DOUBLE, humidity DOUBLE)")
    con.executemany("INSERT INTO api_weather VALUES (?,?,?)",
                    list(zip(h["time"], h["temperature_2m"], h["relative_humidity_2m"])))
    total, nt, to, ho = con.execute("""
        SELECT count(*), count(*) FILTER (WHERE temp IS NULL),
               count(*) FILTER (WHERE temp NOT BETWEEN -50 AND 60),
               count(*) FILTER (WHERE humidity NOT BETWEEN 0 AND 100) FROM api_weather""").fetchone()
    pct = 100 * (1 - (nt + to + ho) / (total * 3))
    con.execute("INSERT INTO api_dq_history VALUES (?, ?, ?, ?, ?, ?)",
                [datetime.datetime.now(), total, nt, to, ho, pct])
    print(f"rows={total} null_temp={nt} temp_bad={to} hum_bad={ho} pass={pct:.2f}%")

n, gap = int(sys.argv[1]) if len(sys.argv) > 1 else 3, int(sys.argv[2]) if len(sys.argv) > 2 else 30
for i in range(n):
    run_once()
    if i < n - 1: time.sleep(gap)
print(con.execute("SELECT * FROM api_dq_history ORDER BY run_ts").df().to_string(index=False))