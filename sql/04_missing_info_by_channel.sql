-- Hypothesis 2: requests arrive without the details needed to start work.
-- How often does each intake channel lead to "Waiting for info", and what does it cost?
SELECT
    t.channel,
    COUNT(*)                                             AS tickets,
    ROUND(100.0 * AVG(t.waited_for_info), 1)             AS waited_for_info_pct,
    ROUND(AVG(w.hours_in_stage), 1)                      AS avg_wait_hours_when_it_happens,
    ROUND(SUM(COALESCE(w.hours_in_stage, 0)))            AS total_hours_lost,
    ROUND(100.0 * AVG(t.sla_breached), 1)                AS sla_breach_pct
FROM v_ticket t
LEFT JOIN v_stage w ON w.ticket_id = t.ticket_id AND w.stage = 'Waiting for info'
GROUP BY t.channel
ORDER BY waited_for_info_pct DESC;
