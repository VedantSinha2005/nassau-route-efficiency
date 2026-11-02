# Executive Summary | Nassau Candy Shipping Intelligence Case Study
**For government and public-sector stakeholders**  
**12 October 2026 | Evidence status: UNVERIFIED case-study dataset**

## Decision in one sentence
**Do not use the supplied shipment dates for regulatory, procurement, or operational performance claims until independently reconciled.** The project still offers a transparent framework for future verified lane monitoring.

## What the dataset actually contains
- **10,194 line items**, collapsed into **8,549 dispatch records**, mapped to 5 assumption-based factories and 196 factory-state combinations.
- **8,389 US** and **160 Canadian** dispatch records.
- Order dates from 2024-2025 but shipping dates from 2026-2030. **Every raw order-to-ship interval exceeds 365 days**; 8,245 dates are later than 12 October 2026.
- The official Nassau Candy website documents wholesale distribution and real distribution centers. The assignment's five factory names are not verified corporate origins.

## Why the apparent results cannot be used as actual service KPIs
The recorded dates show three 365-day-spaced bands (904, 1,269 and 1,634 days). Subtracting these offsets produces an **illustrative adjusted average of 4.29 days**, with **24.6% >5 days**. This is an exploratory inference only. The dataset also lacks final delivery timestamps and shipping costs. Order-to-ship time is not delivery time.

## What the exploratory comparison suggests (subject to verification)

| Shipping tier | Adjusted scenario mean |
|---|---:|
| Same Day | 0.38 days |
| First Class | 2.55 days |
| Second Class | 3.54 days |
| Standard Class | 5.32 days |


The dashboard can identify relative-volume candidates, show a US state heatmap, retain Canadian records in separate tables, and drill into order dates. It cannot validate congestion, on-time delivery, or cost-speed tradeoffs without new source data.

## Recommended phased actions
**0-30 days | Validate source:** Request original shipment events, lineage, date-format documentation, true origin facility identifiers, promised delivery dates, and carrier scans. Reconcile a statistical sample of orders and confirm/reject the three offset hypotheses.

**30-60 days | Build trusted operational measures:** Add actual delivery date, freight cost, lane miles, customer state and state/province normalization, mode, weather/holiday and carrier exception labels. Implement data-quality checks that flag future dates, negative intervals and unrecognized origins.

**60-90 days | Pilot monitoring:** Publish a version-controlled dashboard reporting actual fulfillment interval separately from transit interval, delivery reliability and cost per shipment. Investigate high-volume states only after controlling for service-mode mix, geography and seasonality.

## Safeguards relevant to public decision-making
- Clearly distinguish **scenario analytics** from **validated operational evidence**.
- Maintain US and Canada as distinct jurisdictions on maps and service policy.
- Avoid procurement or performance ratings based on artificial date shifts.
- Keep an audit trail for source validation, route definitions, KPI thresholds and changes.

**Bottom line:** The project is a working decision-support prototype and a documented data-governance warning, not an independently verified assessment of Nassau Candy performance.

**Sources:** User-supplied assignment & CSV; https://www.nassaucandy.com/ ; https://www.nassaucandy.com/delivery-information ; https://www.nassaucandy.com/contact/ (accessed 12 October 2026).
