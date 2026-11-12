-- Hypothesis 3: one department's queue is the bottleneck.
-- Time between assignment to the correct department and the start of work.
SELECT
    department,
    COUNT(*)                                 AS tickets,
    ROUND(AVG(hours_in_stage), 1)            AS avg_queue_hours,
    ROUND(MAX(hours_in_stage), 1)            AS max_queue_hours,
    ROUND(SUM(hours_in_stage))               AS total_queue_hours,
    ROUND(100.0 * SUM(hours_in_stage) / SUM(SUM(hours_in_stage)) OVER (), 1) AS share_of_queue_time_pct
FROM v_stage
WHERE stage = 'Assigned' AND is_misroute = 0
GROUP BY department
ORDER BY avg_queue_hours DESC;
