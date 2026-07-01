---
description: Quick read-only status of your reconciliations
---
Give me a quick **read-only** snapshot from my Cost Reconciliation base - do NOT change
anything. Find the base (`list_bases` + the relational fingerprint: Reconciliations + Line
Items tables), read the **Reconciliations** table, and report:
- counts by Status (Verified / Flagged / Unverified), excluding Superseded + Archived;
- total value **under query**, grouped by currency;
- how many are **awaiting docs / invoice**;
- the few oldest **Flagged** ones that need attention (WO ref, vendor, amount under query).
Then remind me I can open `/dashboard` to act on them.
