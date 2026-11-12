-- Views shared by all analysis queries.

-- One row per stage visit: how long the ticket stayed there.
-- LEAD() takes the time of the NEXT event of the same ticket, so no self-join is needed.
DROP VIEW IF EXISTS v_stage;
CREATE VIEW v_stage AS
SELECT
    ticket_id,
    stage,
    department,
    event_time AS entered_at,
    LEAD(event_time) OVER (PARTITION BY ticket_id ORDER BY event_time, event_id) AS left_at,
    (julianday(LEAD(event_time) OVER (PARTITION BY ticket_id ORDER BY event_time, event_id))
     - julianday(event_time)) * 24.0 AS hours_in_stage,
    -- an "Assigned" stage followed by another "Assigned" means the first department was wrong
    CASE WHEN stage = 'Assigned'
          AND LEAD(stage) OVER (PARTITION BY ticket_id ORDER BY event_time, event_id) = 'Assigned'
         THEN 1 ELSE 0 END AS is_misroute
FROM events;

-- One row per ticket with its key timestamps and SLA result.
DROP VIEW IF EXISTS v_ticket;
CREATE VIEW v_ticket AS
SELECT
    t.*,
    r.resolved_at,
    (julianday(r.resolved_at) - julianday(t.created_at)) * 24.0 AS hours_to_resolve,
    CASE WHEN (julianday(r.resolved_at) - julianday(t.created_at)) * 24.0 > t.sla_hours
         THEN 1 ELSE 0 END AS sla_breached,
    COALESCE(s.misroutes, 0)        AS misroutes,
    COALESCE(s.waited_for_info, 0)  AS waited_for_info
FROM tickets t
JOIN (SELECT ticket_id, MIN(event_time) AS resolved_at
      FROM events WHERE stage = 'Resolved' GROUP BY ticket_id) r USING (ticket_id)
LEFT JOIN (SELECT ticket_id,
                  SUM(is_misroute) AS misroutes,
                  MAX(stage = 'Waiting for info') AS waited_for_info
           FROM v_stage GROUP BY ticket_id) s USING (ticket_id);
