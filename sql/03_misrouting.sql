-- Hypothesis 1: tickets are sent to the wrong department at triage.
-- Compares misrouted and correctly routed tickets inside each category,
-- so the difference is not explained by the category itself.
SELECT
    category,
    CASE WHEN misroutes > 0 THEN 'misrouted' ELSE 'routed correctly' END AS routing,
    COUNT(*)                                AS tickets,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY category), 1) AS share_of_category_pct,
    ROUND(AVG(hours_to_resolve), 1)         AS avg_hours_to_resolve,
    ROUND(100.0 * AVG(sla_breached), 1)     AS sla_breach_pct
FROM v_ticket
GROUP BY category, routing
ORDER BY category, routing;
