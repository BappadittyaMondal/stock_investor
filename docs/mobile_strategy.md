# HFOS v5.0 — Mobile Strategy

## Objective
The mobile strategy pivots HFOS from a deep-research application to a "decision-only" application when viewed on form factors below 768px width.

## UI Decisions (`mobile_dashboard.py`)
- Removed all complex charts, dataframes, and scatter plots.
- Replaced with CSS grid cards optimizing thumb reachability.
- Integrated a static bottom navigation bar (Home, Scan, Port, Watch) specifically for mobile interaction.
- Information Density: Drastically reduced. The mobile app only shows the AI Summary, overall Nifty/Portfolio performance, and the top 5 `BUY`/`STRONG_BUY` signals of the day.

## Notification Aggregation
To prevent "notification fatigue", `NotificationService` aggregates signals. If the scanner finds 10 new opportunities, it bundles them into a single P3 push notification ("10 New Signals Detected") rather than buzzing the user 10 times. Critical risk alerts (P1) bypass aggregation and are dispatched immediately.
