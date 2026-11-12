"""Check the SQL views on a tiny hand-made event log where every answer is known: `pytest`."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyze import build_database  # noqa: E402

TICKETS = pd.DataFrame([
    {"ticket_id": 1, "created_at": "2026-05-04 09:00:00", "category": "A", "channel": "portal",
     "priority": "P1", "sla_hours": 8},
    {"ticket_id": 2, "created_at": "2026-05-04 09:00:00", "category": "A", "channel": "email",
     "priority": "P1", "sla_hours": 8},
])
EVENTS = pd.DataFrame([
    # ticket 1: straight through, resolved in 5 hours
    (1, "2026-05-04 09:00:00", "Registered", None),
    (1, "2026-05-04 10:00:00", "Assigned", "Dept X"),
    (1, "2026-05-04 12:00:00", "In progress", "Dept X"),
    (1, "2026-05-04 14:00:00", "Resolved", "Dept X"),
    # ticket 2: waits for info 3 h, is misrouted for 4 h, resolved in 12 hours
    (2, "2026-05-04 09:00:00", "Registered", None),
    (2, "2026-05-04 10:00:00", "Waiting for info", "Service desk"),
    (2, "2026-05-04 13:00:00", "Assigned", "Dept Y"),
    (2, "2026-05-04 17:00:00", "Assigned", "Dept X"),
    (2, "2026-05-04 19:00:00", "In progress", "Dept X"),
    (2, "2026-05-04 21:00:00", "Resolved", "Dept X"),
], columns=["ticket_id", "event_time", "stage", "department"])


def test_stage_durations_and_misroute_flag():
    conn = build_database(TICKETS, EVENTS)
    stages = pd.read_sql("SELECT * FROM v_stage WHERE ticket_id = 2 ORDER BY entered_at", conn)
    hours = dict(zip(stages["stage"] + "/" + stages["department"].fillna(""), stages["hours_in_stage"].round(2)))
    assert hours["Waiting for info/Service desk"] == 3.0
    assert hours["Assigned/Dept Y"] == 4.0
    assert stages.loc[stages["department"] == "Dept Y", "is_misroute"].item() == 1
    assert stages.loc[(stages["stage"] == "Assigned") & (stages["department"] == "Dept X"), "is_misroute"].item() == 0


def test_ticket_view_sla_and_flags():
    conn = build_database(TICKETS, EVENTS)
    t = pd.read_sql("SELECT * FROM v_ticket ORDER BY ticket_id", conn).set_index("ticket_id")
    assert round(t.loc[1, "hours_to_resolve"], 2) == 5.0 and t.loc[1, "sla_breached"] == 0
    assert round(t.loc[2, "hours_to_resolve"], 2) == 12.0 and t.loc[2, "sla_breached"] == 1
    assert t.loc[1, "misroutes"] == 0 and t.loc[2, "misroutes"] == 1
    assert t.loc[1, "waited_for_info"] == 0 and t.loc[2, "waited_for_info"] == 1
