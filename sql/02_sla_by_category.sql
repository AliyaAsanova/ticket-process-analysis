-- SLA breaches by category: the symptom that started the investigation.
SELECT
    category,
    COUNT(*)                                   AS tickets,
    ROUND(AVG(hours_to_resolve), 1)            AS avg_hours_to_resolve,
    ROUND(100.0 * AVG(sla_breached), 1)        AS sla_breach_pct,
    ROUND(100.0 * AVG(misroutes > 0), 1)       AS misrouted_pct,
    ROUND(100.0 * AVG(waited_for_info), 1)     AS waited_for_info_pct,
    RANK() OVER (ORDER BY AVG(sla_breached) DESC) AS breach_rank
FROM v_ticket
GROUP BY category
ORDER BY sla_breach_pct DESC;
