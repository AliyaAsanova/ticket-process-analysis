-- Hypothesis 4: handoffs made before the weekend get stuck.
-- Queue time by the weekday on which the ticket reached the correct department.
-- P1 tickets are shown separately: they are handled around the clock.
SELECT
    CASE CAST(strftime('%w', s.entered_at) AS INTEGER)
        WHEN 1 THEN '1 Mon' WHEN 2 THEN '2 Tue' WHEN 3 THEN '3 Wed' WHEN 4 THEN '4 Thu'
        WHEN 5 THEN '5 Fri' WHEN 6 THEN '6 Sat' ELSE '7 Sun' END AS assigned_on,
    CASE WHEN t.priority = 'P1' THEN 'P1' ELSE 'P2-P3' END       AS priority_group,
    COUNT(*)                                                     AS tickets,
    ROUND(AVG(s.hours_in_stage), 1)                              AS avg_queue_hours
FROM v_stage s
JOIN tickets t USING (ticket_id)
WHERE s.stage = 'Assigned' AND s.is_misroute = 0
  AND s.department <> 'Field service'      -- excluded: its queue is long every day (see query 05)
GROUP BY assigned_on, priority_group
ORDER BY priority_group, assigned_on;
