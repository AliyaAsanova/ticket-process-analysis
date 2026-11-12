-- Where does the time go? Total and typical hours per process step until resolution.
-- "Assigned" is split into waiting in the correct queue and waiting in a wrong department.
WITH steps AS (
    SELECT
        CASE WHEN stage = 'Assigned' AND is_misroute = 1 THEN 'Assigned (wrong department)'
             WHEN stage = 'Assigned'                     THEN 'Assigned (queue)'
             ELSE stage END AS step,
        ticket_id,
        hours_in_stage
    FROM v_stage
    WHERE stage NOT IN ('Resolved', 'Closed')
)
SELECT
    step,
    COUNT(DISTINCT ticket_id)                                        AS tickets,
    ROUND(AVG(hours_in_stage), 1)                                    AS avg_hours_when_it_happens,
    ROUND(SUM(hours_in_stage))                                       AS total_hours,
    ROUND(100.0 * SUM(hours_in_stage) / SUM(SUM(hours_in_stage)) OVER (), 1) AS share_of_all_time_pct
FROM steps
GROUP BY step
ORDER BY total_hours DESC;
