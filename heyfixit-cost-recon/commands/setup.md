---
description: One-time setup - build your Cost Reconciliation Airtable base and settings
---
Run the **cost-recon-setup** skill. First check whether a relational Cost Reconciliation base
already exists (Reconciliations + Line Items tables, with Line Items.Reconciliation a
multipleRecordLinks field) - if so, don't rebuild, just confirm they're set up. Otherwise build
the base from the verbatim recipe (create_base + the 4 link fields), ask me for my settings
(who signs vendor queries, default currency, company) and write the Settings row, confirm, then
point me to `/rate-card` next. If Airtable isn't connected yet, tell me to connect it first.
