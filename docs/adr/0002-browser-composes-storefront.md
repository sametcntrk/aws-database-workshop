# The browser composes Storefront pages and orchestrates checkout

A product page shows data from DocumentDB, Neptune, Keyspaces and DynamoDB, and checkout touches Aurora, DynamoDB, ElastiCache, Keyspaces and InfluxDB. We let the browser call each Engine App's API and show every call as its own row in the Behind-the-Scenes Panel, instead of a backend that calls several Engines or an event bus (EventBridge/SQS), because an Engine App must talk only to its own Engine and because the workshop's goal is to make each Engine call visible.

## Considered Options

- **Backend aggregator or saga service**: hides the per-Engine calls and breaks the one-Engine-per-app rule.
- **Event-driven checkout (EventBridge or SQS)**: closest to production, but adds infrastructure and cost; the Behind-the-Scenes Panel states that real systems use events here.

## Consequences

- Checkout is not atomic across Engines. If a later step fails, the Panel shows which steps succeeded; this is a teaching point, not a defect.
