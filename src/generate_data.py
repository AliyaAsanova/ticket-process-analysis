"""Generate a synthetic event log of technical support tickets.

The data is NOT real. It imitates how requests move through a telecom
operator's technical departments: registration -> triage -> assignment ->
work -> resolution. Several process problems are built in on purpose, so the
analysis has real bottlenecks to find.

Usage:
    python src/generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
N_TICKETS = 6_000
START, END = pd.Timestamp("2026-05-01"), pd.Timestamp("2026-10-31")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# category -> (share, responsible department, median work hours)
CATEGORIES = {
    "Network incident": (0.28, "Network operations", 5),
    "Billing system": (0.20, "Billing systems", 7),
    "Access and accounts": (0.18, "IT infrastructure", 3),
    "Equipment fault": (0.20, "Field service", 9),
    "Data request": (0.14, "Billing systems", 6),
}
DEPARTMENTS = ["Network operations", "Billing systems", "IT infrastructure", "Field service"]
SLA_HOURS = {"P1": 8, "P2": 24, "P3": 72}

# Built-in process problems:
MISSING_INFO_RATE = {"portal": 0.06, "phone": 0.12, "email": 0.45}   # free-form e-mails lack required fields
MISROUTE_RATE = {"Access and accounts": 0.38}                         # triage has no clear rule for this category
DEFAULT_MISROUTE_RATE = 0.05
QUEUE_MEDIAN_HOURS = {"Network operations": 2.5, "Billing systems": 4, "IT infrastructure": 5,
                      "Field service": 26}                            # Field service is overloaded


def lognormal_hours(rng, median: float, sigma: float = 0.6) -> pd.Timedelta:
    return pd.Timedelta(hours=float(rng.lognormal(np.log(median), sigma)))


def next_monday_9(ts: pd.Timestamp) -> pd.Timestamp:
    days = (7 - ts.day_of_week) % 7 or 7
    return (ts + pd.Timedelta(days=days)).normalize() + pd.Timedelta(hours=9)


def main() -> None:
    rng = np.random.default_rng(SEED)
    names = list(CATEGORIES)
    shares = [CATEGORIES[c][0] for c in names]
    tickets, events = [], []

    for ticket_id in range(1, N_TICKETS + 1):
        created = START + pd.Timedelta(seconds=int(rng.integers(0, int((END - START).total_seconds()))))
        created = created.normalize() + pd.Timedelta(hours=float(np.clip(rng.normal(13, 3.5), 7, 21)))
        category = str(rng.choice(names, p=shares))
        _, department, work_median = CATEGORIES[category]
        channel = str(rng.choice(["portal", "phone", "email"], p=[0.5, 0.2, 0.3]))
        priority = str(rng.choice(["P1", "P2", "P3"], p=[0.12, 0.48, 0.40]))
        tickets.append({"ticket_id": ticket_id, "created_at": created, "category": category,
                        "channel": channel, "priority": priority, "sla_hours": SLA_HOURS[priority]})

        def log(time, stage, dept=None):
            events.append({"ticket_id": ticket_id, "event_time": time, "stage": stage, "department": dept})

        t = created
        log(t, "Registered")
        t += lognormal_hours(rng, 0.7)
        log(t, "Triage", "Service desk")
        t += lognormal_hours(rng, 0.5)

        # Problem 1: the request has to go back to the author for missing details
        if rng.random() < MISSING_INFO_RATE[channel]:
            log(t, "Waiting for info", "Service desk")
            t += lognormal_hours(rng, 14)

        # Problem 2: triage sends the ticket to the wrong department first
        if rng.random() < MISROUTE_RATE.get(category, DEFAULT_MISROUTE_RATE):
            wrong = str(rng.choice([d for d in DEPARTMENTS if d != department]))
            log(t, "Assigned", wrong)
            t += lognormal_hours(rng, 18)   # sits in the wrong queue until someone notices

        log(t, "Assigned", department)
        queue = lognormal_hours(rng, QUEUE_MEDIAN_HOURS[department])
        # Problem 3: non-urgent tickets assigned late on Friday or at the weekend wait until Monday
        late_friday = t.day_of_week == 4 and t.hour >= 15
        if priority != "P1" and (late_friday or t.day_of_week >= 5):
            t = next_monday_9(t) + queue / 4
        else:
            t += queue / (3 if priority == "P1" else 1)

        log(t, "In progress", department)
        t += lognormal_hours(rng, work_median / (2 if priority == "P1" else 1))
        log(t, "Resolved", department)
        t += lognormal_hours(rng, 6)
        log(t, "Closed", "Service desk")

    DATA_DIR.mkdir(exist_ok=True)
    tickets_df, events_df = pd.DataFrame(tickets), pd.DataFrame(events)
    for df, col in ((tickets_df, "created_at"), (events_df, "event_time")):
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    tickets_df.to_csv(DATA_DIR / "tickets.csv", index=False)
    events_df.to_csv(DATA_DIR / "events.csv", index=False)
    print(f"tickets.csv: {len(tickets_df):,} rows, events.csv: {len(events_df):,} rows")


if __name__ == "__main__":
    main()
