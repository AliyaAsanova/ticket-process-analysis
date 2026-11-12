"""Load the event log into SQLite, run the SQL analysis, save tables and charts.

SQLite ships with Python, so the project runs without installing a database.

Usage:
    python src/analyze.py
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR, SQL_DIR = PROJECT_DIR / "data", PROJECT_DIR / "sql"
RESULTS_DIR = PROJECT_DIR / "results"
BLUE, RED = "#4C72B0", "#C44E52"


def build_database(tickets: pd.DataFrame, events: pd.DataFrame) -> sqlite3.Connection:
    """Create an in-memory database with the two tables and the shared views."""
    conn = sqlite3.connect(":memory:")
    tickets.to_sql("tickets", conn, index=False)
    events.rename_axis("event_id").reset_index().to_sql("events", conn, index=False)
    conn.execute("CREATE INDEX idx_events_ticket ON events (ticket_id, event_time)")
    conn.executescript((SQL_DIR / "00_views.sql").read_text(encoding="utf-8"))
    return conn


def run_query(conn: sqlite3.Connection, filename: str) -> pd.DataFrame:
    return pd.read_sql(sql=(SQL_DIR / filename).read_text(encoding="utf-8"), con=conn)


def what_if(conn: sqlite3.Connection) -> pd.DataFrame:
    """Rough estimate of each fix: remove the avoidable hours from every ticket and recount SLA breaches.
    It assumes nothing else changes, so it is an upper bound, not a forecast."""
    df = pd.read_sql("""
        SELECT t.ticket_id, t.hours_to_resolve, t.sla_hours,
               COALESCE(SUM(CASE WHEN s.is_misroute = 1 THEN s.hours_in_stage END), 0) AS misroute_hours,
               COALESCE(SUM(CASE WHEN s.stage = 'Waiting for info' THEN s.hours_in_stage END), 0) AS info_hours
        FROM v_ticket t JOIN v_stage s USING (ticket_id)
        GROUP BY t.ticket_id
    """, conn)
    scenarios = {
        "Today": df["hours_to_resolve"],
        "No misrouting": df["hours_to_resolve"] - df["misroute_hours"],
        "No waiting for info": df["hours_to_resolve"] - df["info_hours"],
        "Both fixed": df["hours_to_resolve"] - df["misroute_hours"] - df["info_hours"],
    }
    return pd.DataFrame([
        {"scenario": name, "sla_breach_pct": round(100 * (hours > df["sla_hours"]).mean(), 1),
         "avg_hours_to_resolve": round(hours.mean(), 1)}
        for name, hours in scenarios.items()
    ])


def bar_chart(labels, values, title, xlabel, path, highlight=None) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 0.55 * len(labels) + 1.6))
    colors = [RED if label == highlight else BLUE for label in labels]
    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1])
    ax.bar_label(bars, fmt="%.1f", padding=3)
    ax.set(title=title, xlabel=xlabel)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    conn = build_database(pd.read_csv(DATA_DIR / "tickets.csv"), pd.read_csv(DATA_DIR / "events.csv"))
    (RESULTS_DIR / "figures").mkdir(parents=True, exist_ok=True)

    overall = pd.read_sql("""SELECT COUNT(*) AS tickets, ROUND(AVG(hours_to_resolve), 1) AS avg_hours,
                             ROUND(100.0 * AVG(sla_breached), 1) AS sla_breach_pct FROM v_ticket""", conn)
    print("OVERALL\n" + overall.to_string(index=False))

    tables = {name: run_query(conn, f"{name}.sql") for name in [
        "01_time_by_stage", "02_sla_by_category", "03_misrouting",
        "04_missing_info_by_channel", "05_queue_by_department", "06_queue_by_weekday"]}
    tables["07_what_if"] = what_if(conn)
    for name, table in tables.items():
        table.to_csv(RESULTS_DIR / f"{name}.csv", index=False)
        print(f"\n{name}\n{table.to_string(index=False)}")

    stage = tables["01_time_by_stage"]
    bar_chart(list(stage["step"]), list(stage["share_of_all_time_pct"]),
              "Where the time goes before a ticket is resolved", "Share of all hours, %",
              RESULTS_DIR / "figures" / "time_by_stage.png")
    cat = tables["02_sla_by_category"]
    bar_chart(list(cat["category"]), list(cat["sla_breach_pct"]), "SLA breaches by category",
              "Tickets resolved later than SLA, %", RESULTS_DIR / "figures" / "sla_by_category.png")
    wd = tables["06_queue_by_weekday"].query("priority_group == 'P2-P3'")
    bar_chart(list(wd["assigned_on"].str[2:]), list(wd["avg_queue_hours"]),
              "Queue time by day of assignment (P2-P3, without Field service)", "Average hours in queue",
              RESULTS_DIR / "figures" / "queue_by_weekday.png")


if __name__ == "__main__":
    main()
