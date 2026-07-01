---
name: rate-card-extraction
description: Digitizes a facilities-management vendor or subcontractor contract or rate schedule into the operator's Rate Card (the Rate Lines table that the invoice reconciler checks every future invoice against). Use when onboarding a new vendor, when someone uploads a contract, rate schedule, schedule of rates (SOR), quote letter, or email stating rates and wants the rates captured, or when the user mentions setting up, importing, digitizing, or extracting a vendor's rate card. One vendor per run; nothing is saved until the human confirms.
---

# Rate-card extraction

Turn a vendor's contract into a structured **Rate Card** (the `Rate Lines` table).
Because **every future invoice is checked against these rates, accuracy and honesty
about uncertainty matter more than completeness — never invent or guess a rate.**

## The golden rule: extract, review with a human, then write

1. **You (model) extract** — read the contract, detect the pricing model, and map
   every rate into the controlled vocabulary. **No guessing.**
2. **The human confirms** — you present a **review table** and a "Needs your check"
   list. **Nothing is written until the person says go.** This is the rate card —
   a wrong rate silently corrupts every future check.
3. **`write_rates.py` validates** the confirmed lines and returns a **write-plan**.
4. **You (agent) execute** the write-plan against Airtable via MCP, verbatim.

## What you need

- The **Airtable connector** — its tools appear in your tool list with your session's
  prefix (`mcp__<server>__…`); call them by name: `list_bases`, `list_tables_for_base`,
  `list_records_for_table`, `create_records_for_table`.
- **Bash**, to run the bundled one-shot driver `build_writes.py` (which uses
  `write_rates.py` + `to_connector.py` + `schema.py`) in this skill folder.

No email tools — this is an interactive setup task with a person present.

## Find the base + dump its tables

Don't assume ids. Call **`list_bases`**, then for each candidate `list_tables_for_base`
and pick the base whose tables include **Rate Lines** and **Reconciliations**. Note its
**baseId** and **save that base's `list_tables_for_base` result to `tables.json`** (in your
working directory) — the driver reads it to resolve field ids. *(Don't use `search_bases`.)*
The Rate Lines contract
is in [reference/schema.md](reference/schema.md).

## Pricing-model detection (do this FIRST)

Before extracting, identify the model — this decides whether the tool can verify at all:

- **Rate card** (supported) — explicit labour / call-out / travel / markup / task rates → extract normally.
- **Measured-term / Schedule of Rates** (detect + **defer**) — priced off an *external* schedule (NHF, NSR, M3NHF, PSA) × an adjustment %, and/or an AOV / lump-sum with a value cap. Capture the model parameters you can (adjustment %, value cap, schedule name + version) as `Other` lines with details in `Conditions`, then **stop and tell the person plainly**: *"This contract prices off an external schedule (X) — invoices can't be checked line-by-line without that schedule and your adjustment %. That's the kind of thing HeyFixit handles in production. For this tool, load a vendor on a standard hourly rate card."* **Never fabricate hourly rates.**
- **Fixed-price / lump-sum only** — note it and flag similarly.

Full detection + mapping rules: [reference/extraction-rules.md](reference/extraction-rules.md).

## Workflow (copy this checklist and tick as you go)

```
Rate-card extraction run (ONE vendor):
- [ ] 1. Read the contract document(s)
- [ ] 2. Detect the pricing model (rate card / measured-term SoR / fixed-price)
- [ ] 3. Extract every rate into the controlled vocabulary (no guessing)
- [ ] 4. Show the REVIEW TABLE + "Needs your check" flags; ask the human to confirm
- [ ] 5. On confirmation, assemble the submission
- [ ] 6. Run build_writes.py -> writes.json (validated + field-id-ready)
- [ ] 7. Execute each call in writes.json (Vendor if new, then Rate Lines)
- [ ] 8. Report what was saved and what was skipped
```

**Step 3 — Extract.** Map every line to the controlled `Rate Type` / `Band` / `Unit`
(see [reference/extraction-rules.md](reference/extraction-rules.md)). Multipliers
("OOH = 1.5× normal") → absolute rates with the basis in `Conditions`. Inclusions
("call-out includes first hour") → `Conditions` so reconciliation won't double-count
that labour. Tiered markups → one row per tier. Copy figures **exactly** — no
rounding, no currency conversion. A rate that's referenced but not given ("on
application") → leave the rate blank and **flag it**.

**Step 4 — Review (the human gate).** Present a clean markdown table of all extracted
lines, then a **"⚠ Needs your check"** section listing every flagged/uncertain item
with a one-line reason. End with: *"This is what I read from the contract. Confirm or
correct anything and I'll save it to your rate card. Nothing is saved until you say go —
these rates are what every invoice gets checked against."* **Do not proceed without
explicit confirmation.**

**Step 5–6 — Assemble & build the writes.** Build the `submission` (schema in
`write_rates.py`'s header) from the **confirmed** lines, save it as `submission.json` in your
working directory, then run the driver by its full path (it imports its own siblings, so run it
from your writable working dir — not from inside the read-only plugin):

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/rate-card-extraction/build_writes.py submission.json tables.json <BASEID> writes.json
```

It validates the lines, prints what **will be written** and the **SKIPPED** list (rate-less
lines + flags — never written; report them to the person), and writes the ready-to-send
Airtable calls to **`writes.json`**. A line is only writable with a numeric rate **and** a
unit. `SUBMISSION ERROR` → fix the submission; `BASE/SCHEMA ERROR` → the base isn't built to
spec.

**Step 7 — Execute.** Only after the person confirmed the review table, open `writes.json`
and run each call **in order** (Vendor first if new, then Rate Lines) with
`create_records_for_table`, passing the call's `args` exactly (already keyed by fld/tbl ids
+ baseId). Do not add, drop, or alter fields. Then `list_records_for_table` on Rate Lines to
confirm.

**Step 8 — Report.** Tell the person how many lines were saved and list anything
skipped (with its reason) so they can follow up.

## Hard rules (non-negotiable)

- **Human-in-the-loop.** Never write before the person confirms the review table.
- **Never invent a rate.** Under-claim, don't over-claim. A flagged gap is success; a confident wrong rate is failure.
- **Copy figures exactly.** No rounding, no currency conversion. Rates are in the operator's currency — set `submission.currency` from the contract if stated, else the **Settings** table's `Default Currency` (read the first `Settings` row). Never hard-code a currency.
- **One vendor per run.**
- **Only execute what `build_writes.py` produced.** Never author your own Airtable writes; never map field ids by hand.
- **Detect external-schedule contracts and defer** — don't fabricate hourly rates for a measured-term / SoR contract.

## References (read as needed)

- [reference/extraction-rules.md](reference/extraction-rules.md) — pricing-model detection, the controlled vocabulary, and the full mapping rules (multipliers, inclusions, tiers, minimums).
- [reference/schema.md](reference/schema.md) — the Airtable contract: tables, fields, allowed values, the write-plan shape.
