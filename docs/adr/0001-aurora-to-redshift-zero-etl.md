# Redshift reports get new orders through Aurora zero-ETL integration

Report Screens on Redshift must show the orders that Visitors place during the workshop, not only the Seeded history. We connect Aurora PostgreSQL to Redshift Serverless with a zero-ETL integration instead of letting an Engine App copy orders, because an Engine App may talk only to its own Engine; the integration is an Engine-to-Engine AWS feature, so no Engine App breaks that rule, and it teaches a real near-real-time analytics pattern.

## Consequences

- Aurora needs a custom cluster parameter group with enhanced logical replication (`rds.logical_replication`, `aurora.enhanced_logical_replication` = 1, `aurora.logical_replication_backup`, `aurora.logical_replication_globaldb` = 0). These are static parameters: changing them on a running cluster needs a writer reboot.
- The Redshift workgroup needs `enable_case_sensitive_identifier = true` and the namespace needs a resource policy that authorizes the integration.
- Redshift needs a one-time `CREATE DATABASE ... FROM INTEGRATION`; the Redshift Tutorial uses this as a step.
- Every Aurora table that must replicate needs a primary key.
