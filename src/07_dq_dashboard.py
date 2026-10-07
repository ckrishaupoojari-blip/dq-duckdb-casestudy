"""Build a monitoring dashboard from the DuckDB history tables."""
import duckdb, os
import matplotlib.pyplot as plt

con = duckdb.connect("data/dq.duckdb", read_only=True)

latest = con.execute("""
    SELECT d.check_name, d.dataset, d.pass_pct FROM dq_results d
    WHERE d.run_ts = (SELECT max(run_ts) FROM dq_results WHERE dataset = d.dataset)
""").df().pivot(index="check_name", columns="dataset", values="pass_pct").sort_values("raw")

trend = con.execute("""
    SELECT run_ts, dataset, avg(pass_pct) AS p FROM dq_results
    GROUP BY run_ts, dataset ORDER BY run_ts""").df()

try:
    api = con.execute("SELECT run_ts, pass_pct FROM api_dq_history ORDER BY run_ts").df()
except Exception:
    api = None

fig, ax = plt.subplots(1, 3, figsize=(18, 5.5))

# Panel 1: raw vs clean pass rate per rule
y = range(len(latest))
ax[0].barh([i - 0.2 for i in y], latest["raw"], height=0.4, label="Raw", color="#d9534f")
ax[0].barh([i + 0.2 for i in y], latest["clean"], height=0.4, label="Clean", color="#5cb85c")
ax[0].set_yticks(list(y)); ax[0].set_yticklabels(latest.index)
ax[0].set_xlim(90, 100.5); ax[0].set_xlabel("Pass rate (%)")
ax[0].set_title("Latest run: pass rate per rule"); ax[0].legend()

# Panel 2: average pass rate for every pipeline run
for ds, color in [("raw", "#d9534f"), ("clean", "#5cb85c")]:
    t = trend[trend.dataset == ds]
    ax[1].plot(range(1, len(t) + 1), t["p"], marker="o", label=ds, color=color)
ax[1].set_xlabel("Pipeline run #"); ax[1].set_ylabel("Avg pass rate (%)")
ax[1].set_title("Quality over time (each run is logged)"); ax[1].legend()

# Panel 3: live API monitoring history
if api is not None and len(api):
    ax[2].plot(range(1, len(api) + 1), api["pass_pct"], marker="o", color="#3b7ddd")
    ax[2].set_ylim(0, 105)
ax[2].set_xlabel("API poll #"); ax[2].set_ylabel("Pass rate (%)")
ax[2].set_title("Live API monitoring (Open-Meteo)")

plt.suptitle("Data Quality Monitoring Dashboard (DuckDB)", fontsize=15)
plt.tight_layout()
os.makedirs("results", exist_ok=True)
plt.savefig("results/dq_dashboard.png", dpi=150)
print("Saved results/dq_dashboard.png")
try:
    os.startfile("results\\dq_dashboard.png")
except Exception:
    pass