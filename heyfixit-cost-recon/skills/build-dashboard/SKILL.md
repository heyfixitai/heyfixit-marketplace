---
name: build-dashboard
description: Builds or refreshes the live Cost Reconciliation dashboard - a visual, interactive view of the reconciliation queue, KPIs (value under query, value verified, time saved), per-line checks, coverage, drafted vendor queries, a finance-pack, and Settings - reading and managing the user's Airtable via the connector. Use when the user says "build my dashboard", "show my reconciliation dashboard", "open the cost dashboard", "refresh the dashboard", or asks to see the reconciliation queue / KPIs / what's under query as a visual.
---

# Build the reconciliation dashboard

Load the live dashboard as a Cowork **artifact** that reads the user's Airtable base and
lets them manage it. The dashboard is a **read + manage** surface: it shows the queue and
KPIs, and it writes safe workflow changes back to Airtable (mark sent to finance / queried /
resolved, archive/restore, edit the drafted vendor query, edit Settings) — each write logs
an Actor-attributed **Events** row. It **never** reconciles by itself and **never** rewrites
a verdict: reconciling happens in chat via the `invoice-reconciliation` skill; the "+ Reconcile
an invoice" button just shows the user the message to paste there.

## Prerequisite

The **Airtable connector** is connected (you authorize Airtable once in Cowork). The base is the one built
by `cost-recon-setup` — tables **Vendors, Rate Lines, Reconciliations, Line Items, Events,
Settings**, with the cross-table refs as real **`multipleRecordLinks`**.

## Build it (Cowork — the live artifact)

1. **Read the bundled page** `${CLAUDE_PLUGIN_ROOT}/skills/build-dashboard/dashboard-v2.html`.
   It is self-contained and pure-ASCII: it finds the base, reads it on load, refreshes on
   focus + on the Refresh button, and writes safe changes back — all through the connector.

2. **Fill the connector prefix.** The page has one placeholder, `__AIRTABLE_PREFIX__`. Replace
   **every** occurrence with **your own** Airtable MCP tool prefix — i.e. the part of your
   Airtable tools' fully-qualified names up to and including the final `__` before the tool
   name. Read it off your actual tool list: if your Airtable tool is named
   `mcp__<your-airtable-server-id>__list_bases`, then the prefix is
   `mcp__<your-airtable-server-id>__` (the `<your-airtable-server-id>` part is unique to your
   session — never hardcode one from an example; use the one you actually see). Write the filled
   HTML to a file (e.g. `dashboard.filled.html` in your working dir). Do **not** change anything
   else in the page.

3. **(Optional) probe once.** If unsure the base is built to spec, call the connector's
   `list_bases` then `list_tables_for_base` and confirm the tables + fields exist. The page
   already handles the field-ID reads, the `{id,name}` select/link shapes, and the relational
   base-finder — no code edits needed for a to-spec base.

4. **Create the artifact.** Call `create_artifact` with `html_path` = the filled file and
   `mcp_tools` = the five connector tools it uses, **fully-qualified with your prefix**:
   `list_bases`, `list_tables_for_base`, `list_records_for_table`,
   `create_records_for_table`, `update_records_for_table`.

5. Tell the user it's in their **Live artifacts** tab, reads their base each time they open it
   (and re-pulls when they switch back to it), and that reconciling new invoices happens in
   chat via `/reconcile`.

## What the dashboard does

- **KPIs:** value under query, value verified, invoices processed (verified/flagged/unverified),
  time saved; a strip with exceptions, % flagged, flagged-reasons %, awaiting docs.
- **Queue:** each reconciliation's Status chip + Stage badge, Vendor, WO, Invoice, coverage
  (Fully/Partly/Not-yet), total, value under query. Filters + "show archived" + bulk actions.
- **Drill-in:** verdict box (Ready / Hold / Not-verified / Resolved-by-override), per-line
  Rate/Reality/Auth + Verdict + reason, coverage in words, summary, an **editable** vendor
  query (Save/Copy), a **finance pack** (renders in-artifact; Print / Save-as-PDF / Download),
  versions + audit trail.
- **Actions (write back):** mark sent-to-finance / query-sent / resolved (a flagged invoice
  requires a re-run OR a recorded **override** — Status stays Flagged), archive/restore, edit
  query, edit Settings. Every write logs an Actor-attributed Event.
- **Settings tab:** default currency (dropdown), operator name (signs queries), company, the
  Vendors + Rate-card tables.
- **Floating upsell:** the HeyFixit "production version" card → Book-a-demo (Tally).

## Rules

- **Emit `dashboard-v2.html` verbatim** — only substitute `__AIRTABLE_PREFIX__`. Don't rewrite
  the layout or logic inline; if the dashboard itself needs changing, edit the bundled file.
- **No keys in the page.** All access is through the user's connector — never embed a token.
- **Never invent field IDs or verdicts.** The page resolves field IDs live and only writes the
  safe workflow fields; verdicts/amounts are the engine's and are never edited here.
