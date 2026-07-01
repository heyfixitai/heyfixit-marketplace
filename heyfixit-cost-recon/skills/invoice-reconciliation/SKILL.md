---
name: invoice-reconciliation
description: Verifies a facilities-management supplier or subcontractor invoice against the operator's contracted rates and the work actually done, then writes a finance-ready reconciliation (status, per-line checks, coverage, a drafted vendor query, audit events) to Airtable. Use when an invoice PDF or image arrives or is uploaded for checking, when reconciling supplier/subcontractor bills, when matching an invoice to a rate card / quote / PO / service report, or when the user mentions invoice reconciliation, cost checking, overbilling, or verifying a vendor bill before payment.
---

# Invoice reconciliation

Verify a supplier/subcontractor invoice for a facilities-management (FM) operator and
leave a clean, evidenced reconciliation in Airtable. You **assemble facts and flag
discrepancies; you never approve payment or make the commercial call.** There is no
payment tool — do not attempt to move money.

## Golden rule: perceive → run the scripts → execute the writes

The work is split so results are deterministic and the same on any model:

1. **You (model) perceive.** Read the documents and build a strict, factual `case`
   (per-line evidence — *no verdicts, no arithmetic*). This is your only judgement step.
2. **The bundled scripts decide + prepare the writes.** `build_writes.py` runs the
   engine (`reconcile.py`) and the field-id translator (`to_connector.py`) and hands
   you ready-to-send Airtable calls. **You never compute a verdict or map a field id.**
3. **You execute those calls verbatim**, then read back to confirm.

Never author your own Airtable writes, never change the plan, never invent a rate or a
verdict. If a script errors, fix the `case` and re-run — do not work around it.

## What you need

- The **Airtable connector** (the user authorises it once). You'll use these tools —
  they appear in your tool list with your session's connector prefix
  (`mcp__<server>__…`); call them by name: `list_bases`, `list_tables_for_base`,
  `list_records_for_table`, `create_records_for_table`, `update_records_for_table`.
  **There is no delete tool — by design.** You supersede, never delete.
- **Bash**, to run the two bundled scripts in this skill folder
  (`${CLAUDE_PLUGIN_ROOT}/skills/invoice-reconciliation/`): `build_writes.py` (the
  one you run) which uses `reconcile.py` + `to_connector.py` + `schema.py`.

> **v1 is manual mode** — one invoice (plus any supporting docs) handed to you in chat.
> Autonomous email intake (AgentMail) is a Tier-2 / heyfixit upsell and is not part of
> this skill; ignore email steps unless an AgentMail connector is actually present.

## The pipeline

```
- [ ] 1. Gather the documents (the upload)
- [ ] 2. Find the base + save its table dump (tables.json)
- [ ] 3. Read references: the rate card + any existing record for this WO
- [ ] 4. Build the case.json (per-line evidence; NO verdicts)
- [ ] 5. Run build_writes.py  ->  writes.json (+ the engine's disposition)
- [ ] 6. Execute each call in writes.json, in order
- [ ] 7. Read back to confirm it landed
```

### Step 1 — Gather
Use the uploaded invoice and any quote / PO / service report / work-order export. If one
upload holds **multiple invoices or jobs**, process each as its own reconciliation.

### Step 2 — Find the base + dump its tables
Don't assume ids. Call **`list_bases`**, then for each candidate call
`list_tables_for_base` and pick the base whose tables include **Reconciliations** and
**Line Items** (the others are Vendors, Rate Lines, Events, Settings). Note its
**baseId**. **Save that base's `list_tables_for_base` result to a file** — e.g. write it
to `tables.json` in your working directory. `build_writes.py` reads it to resolve field ids.
*(Do not use `search_bases` — its parameter differs and it's unreliable here.)*

### Step 3 — Read references
Read the vendor's **Rate Lines** (`list_records_for_table` on Rate Lines) so you can map
each invoice line to a contracted rate. For the WO, fetch any **existing**
Reconciliations (`list_records_for_table` on Reconciliations, match the WO ref) so the
engine can route (new / revised / promote / augment). Pass each existing one into the
case `existing` list with: `record_id`, `recon_id`, `job_key`, `stage`, `version`,
`invoice_no`. Read **Settings** (first row) for `Default Currency` and `Operator Name`.

### Step 4 — Build the `case` (your only judgement step)
Write `case.json`. Fill **what the documents say**, never verdicts or maths. If you can't
confidently map a line to a rate, set `expected_rate: null` — the engine flags it. Never
guess a rate. Set the job flags honestly. Schema + full rules:
[reference/edge-cases.md](reference/edge-cases.md) §5.

```jsonc
{
  "recon_id": "REC-0007",            // next free REC-#### (or omit and pass recon_seq)
  "vendor_exists": true,             // false only for a brand-new vendor (adds a Vendors row)
  "actor": "Jane Smith, Accounts Payable",   // Settings.Operator Name (signs the query)
  "now": "2026-06-21T09:00:00Z",
  "job": {
    "vendor": "Apex Mechanical Services Ltd",
    "job_wo_ref": "WO-4471", "job_type": "Quoted",   // Quoted | Standing
    "currency": "GBP",                                // invoice's currency; else Settings default
    "invoice_no": "INV-20431", "invoice_date": "2026-06-12", "invoice_total": 330,
    "documents_present": ["INV","SR"],                // INV, SR, QT, PO, WO
    "has_price_reference": true,                      // is there a rate card / quote to price against?
    "has_reality": true,                              // is there a service report / WO export?
    "has_authorization_reference": false,             // is there a PO / quote scope? (Standing -> false)
    "po_total": null, "quote_total": null,
    "reality_hours": 3, "reality_materials": null
  },
  "lines": [
    { "description": "Labour - HVAC Engineer", "qty": 3, "unit_price": 80, "amount": 240,
      "rate":          { "applicable": true, "expected_rate": 60, "basis": "rate_card" },
      "reality":       { "evidenced_qty": 3, "on_report": true },
      "authorization": { "in_scope": true, "authorized_amount": null } },
    { "description": "Standard call-out", "qty": 1, "unit_price": 90, "amount": 90,
      "rate":          { "applicable": true, "expected_rate": 90, "basis": "rate_card" },
      "reality":       { "evidenced_qty": null, "on_report": true },
      "authorization": { "in_scope": true, "authorized_amount": null } }
  ],
  "existing": []
}
```
*(The `//` notes above are annotations only — a real `case.json` is plain JSON with no
comments and no trailing commas.)*

Per line: `rate.applicable`=false for parts with no rate; `expected_rate`=null if not on the
card; `reality.evidenced_qty`=hours/qty the job sheet evidences (or `on_report`: true/false
/ null); `authorization.in_scope`=true/false vs the quote/PO (with `authorized_amount` if
capped). Engine maths and verdicts come from these — you only report what the docs show.

### Step 5 — Run the one-shot driver
Run this from a **writable working directory** (your session's working dir) — not from inside
the installed plugin, which may be read-only. Invoke the script by its full path; it imports its
own siblings, so it works from any directory:
```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/invoice-reconciliation/build_writes.py case.json tables.json <BASEID> writes.json
```
It prints the engine's **disposition** (action, Status, coverage, value under query) and
writes the ready-to-send Airtable calls to **`writes.json`**. If it prints `CASE ERROR`,
your case is off-contract — fix it and re-run. If it prints `BASE/SCHEMA ERROR`, the base
is missing a field — it isn't built to spec (run `cost-recon-setup`).

### Step 6 — Execute the writes
Open `writes.json`. It's a list of calls, **in order**. For each one, call the named tool
(`create_records_for_table` or `update_records_for_table`) with that call's `args` exactly
— the args already contain `baseId`, `tableId`, and field-id-keyed `records`. **Do not add,
drop, or rename any field.** (Line Items and Events reference their reconciliation by the
**Recon ID text** — no record-id linking needed.) Send creates in batches of ≤10 (the
driver already batches).

### Step 7 — Read back
`list_records_for_table` on Reconciliations for the printed Recon ID (and a couple of its
Line Items) to confirm it landed. If a write failed, retry that one call; if it still
fails, write one Events row noting the failure and continue — don't crash the run.

## Hard rules (non-negotiable)
- **Only execute what `build_writes.py` produced.** Never construct your own Airtable
  writes; never change a field or value the engine produced.
- **Never invent a rate or a verdict.** Unmatched line → `expected_rate: null` → the engine
  flags it. A flagged gap is success; a confident wrong rate is failure.
- **Never delete.** Corrections happen by supersede (a new Version) or augment in place.
- **Never approve payment or move money.** You present facts; the human decides.
- **Always leave the audit trail.** Every run writes Events; never edit or delete an Event.
- **Report coverage honestly.** Never mark something Verified off thin coverage — the engine
  handles this; don't override it.

## References (read as needed)
- [reference/schema.md](reference/schema.md) — the Airtable contract: tables, fields,
  allowed values, immutability, the Stage state machine, the write-plan shape.
- [reference/edge-cases.md](reference/edge-cases.md) — the disposition contract: the four
  checks and fallbacks, roll-up rules, the exact `case`, routing, and the 24-row edge table.
