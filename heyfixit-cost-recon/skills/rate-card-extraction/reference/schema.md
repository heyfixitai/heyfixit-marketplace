# Reconciliation data contract (Airtable)

The authoritative description of the Airtable base this skill reads and writes.
It mirrors `schema.py` (the machine-checked version). If the two ever disagree,
`schema.py` wins. Self-contained: everything needed is on this page.

## Contents

- 1. Tables at a glance
- 2. Field reference (every table, every field)
- 3. Controlled values (the allowed-value vocabularies)
- 4. Required-on-create fields
- 5. Immutable fields & append-only rules
- 6. Stage state machine (legal workflow transitions)
- 7. Status vs Stage vs Verdict (don't confuse them)
- 8. The write-plan shape

---

## 1. Tables at a glance

| Table | Role | Written by the agent? |
|---|---|---|
| **Vendors** | One row per supplier/subcontractor. | Find-or-create only. |
| **Rate Lines** | The contracted rates per vendor (the rate card). | Only by the rate-card extractor, with human review. |
| **Reconciliations** | One row per invoice verified (or per parked stub). | Yes — create + limited updates. |
| **Line Items** | One row per invoice line, with its three checks. | Yes — create. |
| **Events** | Append-only audit log. | Yes — create only (never updated). |
| **Settings** | One-row operator config: default currency, operator name, company. | Set at onboarding; read by the skills + dashboard. |

`Reconciliations` is the parent; `Line Items` and `Events` link to it.

> **Links are real `multipleRecordLinks`** (Reconciliations->Vendors, Rate Lines->Vendors, Line Items->Reconciliations, Events->Reconciliations). The engine emits the linked record's **primary value** (a `Recon ID` / `Vendor Name`); `build_writes.py` wraps it as an array and writes with **`typecast:true`**, so Airtable resolves it to the real record. Always write the parent before its children (Vendors -> Reconciliations -> Line Items/Events) or typecast creates an empty stub. `build_writes.py` auto-detects link fields from the base, so the same command works on a relational base or a legacy text-FK base.

---

## 2. Field reference

### Vendors
| Field | Type | Notes |
|---|---|---|
| Vendor Name | text | The match key. Find before create to avoid duplicates. |

### Rate Lines (read-only during reconciliation)
| Field | Type | Notes |
|---|---|---|
| Vendor | link/text | Which vendor this rate belongs to. |
| Rate Type | single-select | See §3. |
| Description / Trade | text | e.g. "Electrician", "Call-out (out of hours)". |
| Band | text | Optional skill/time band, e.g. "Standard", "OOH". |
| Unit | text | e.g. hour, call-out, visit, day, each, mile. |
| Rate | number | The contracted unit price. |
| Min Units | number | Minimum billable units (e.g. 1-hour minimum call-out). |
| Conditions | text | Free-text rules, e.g. "call-out includes first hour". |
| Effective From | date | Rate validity start. Use the latest rate effective on/before the invoice date. |

### Reconciliations
| Field | Type | Notes |
|---|---|---|
| Recon ID | text | Stable ID, e.g. `REC-0001`. **Immutable.** |
| Stage | single-select | Workflow state. See §3 / §6. |
| Version | number | 1, 2, 3 … within a Job Key. **Immutable.** |
| Job Key | text | `"{vendor}|{wo ref}|{invoice no}"`, lowercased. Dedup key. **Immutable.** |
| Job / WO Ref | text | The work-order / job reference. |
| Vendor | link/text | The supplier. |
| Job Type | single-select | `Quoted` or `Standing`. See §3. |
| Invoice No | text | Supplier invoice number. |
| Invoice Date | date | |
| Invoice Total | number | Header total billed. |
| Currency | single select | ISO code of the invoice (e.g. `GBP`, `EUR`, `USD`). The invoice's stated currency, falling back to the Settings default. Built as a single select of the 12 supported ISO codes (see Controlled values). |
| Docs Present | text | Which documents were available, e.g. "Invoice, Service report". |
| Coverage | multi-select | Which checks actually ran. See §3. |
| PO Total | number | If a PO was present. |
| Quote Total | number | If a quote was present. |
| Reality Hours | number | Hours evidenced by the reality doc. |
| Reality Materials | number | Materials/parts evidenced by the reality doc. |
| Status | single-select | Verification result. See §3 / §7. |
| Exceptions | number | Count of queried lines. |
| Value Queried | number | Currency sum of the queried lines. |
| Verification Summary | text | One short paragraph of what was checked and found. |
| Vendor Query Draft | text | A ready-to-send query naming flagged lines + evidence. |
| Attachments | attachment | Source documents, named `v{version}-{filename}`. |

### Line Items
| Field | Type | Notes |
|---|---|---|
| Reconciliation | link | Parent reconciliation. |
| Description | text | The invoice line text. |
| Qty / Hours | number | Quantity or hours billed. |
| Unit Price | number | Billed unit price. |
| Amount | number | Line total billed. |
| Expected Rate | number | The contracted rate matched from the rate card (blank if none). |
| Rate Check | single-select | See §3. |
| Reality Check | single-select | See §3. |
| Authorization Check | single-select | See §3. |
| Verdict | single-select | Per-line roll-up. See §3. |
| Flag Reason | text | One short sentence if Verdict = Query. |

### Events (append-only)
| Field | Type | Notes |
|---|---|---|
| Event | text | Short label, e.g. "Verification Flagged". |
| Recon Ref | link/text | The reconciliation this event belongs to. |
| Type | single-select | See §3. |
| Detail | text | What happened. |
| Actor | text | Who/what acted. **Use the actor convention** (below) so actions are attributable. |
| At | datetime | ISO timestamp. |

**Actor convention** (every Event must set one of these so actions are attributable):
- **`Managed agent`** — the autonomous server-side agent (scheduled deployment / email path).
- **`Cowork agent`** — Claude running a skill in the operator's Cowork/chat (manual path).
- **the operator's name** (from `Settings.Operator Name`, else `Operator`) — a human action taken in the dashboard (archive, edit, mark sent/queried/resolved).

### Settings (one row, operator config)
| Field | Type | Notes |
|---|---|---|
| Default Currency | single select | ISO code used when an invoice doesn't state one, and for display (e.g. `GBP`, `EUR`). One of the 12 supported ISO codes. |
| Operator Name | text | Who signs vendor queries. |
| Company | text | The operator's company name. |

Read this row for the default currency and the query signatory; the reconcile and
rate-card skills never need more than the single Settings row.

---

## 3. Controlled values

These are the only allowed values for each controlled field. Anything else is
refused by `schema.py`.

- **Reconciliations.Status** — `Verified`, `Flagged`, `Unverified`
- **Reconciliations.Stage** — `Awaiting invoice`, `New`, `Queried`, `Re-run complete`, `Sent to finance`, `Resolved`, `Superseded`, `Archived` (`Archived` = user-hidden from the dashboard; kept for audit)
- **Reconciliations.Coverage** (multi-select) — `Price`, `Reality`, `Authorization`, `Internal`
- **Reconciliations.Job Type** — `Quoted`, `Standing`
- **Line Items.Rate Check / Reality Check / Authorization Check** — `Pass`, `Flag`, `N/A`, `Unverified`
  - `Pass` = checked and consistent · `Flag` = checked, discrepancy found · `N/A` = check doesn't apply · `Unverified` = couldn't run (reference doc absent)
- **Line Items.Verdict** — `Pass`, `Query`, `Unverified`
  - `Pass` = a substantive check passed and nothing flagged · `Query` = at least one check flagged · `Unverified` = no substantive check could run (thin coverage)
- **Events.Type** — `Created`, `Document added`, `Re-run`, `Superseded`, `Promoted`, `Parked`, `Queried`, `Sent to finance`, `Resolved`, `Re-opened`, `Archived`, `Restored`
- **Rate Lines.Rate Type** — `Labour`, `Call-out`, `Travel`, `Materials markup`, `Specialist markup`, `Plant hire`, `SOR task`, `Minimum charge`, `Other` (`Other` is the escape hatch — extraction never invents a category)
- **Rate Lines.Band** — `Normal`, `OOH`, `Saturday`, `Sunday / Bank Hol`, `Emergency` (blank for non-time-based lines)
- **Rate Lines.Unit** — *suggested* values (not strictly enforced): `per hour`, `per visit`, `per day`, `per mile`, `per item`, `%`, `fixed`
- **Reconciliations.Currency** / **Settings.Default Currency** — a **single select** of the 12 supported ISO codes: `GBP`, `EUR`, `USD`, `AUD`, `CAD`, `INR`, `JPY`, `CHF`, `AED`, `ZAR`, `SGD`, `NZD`. `schema.py` does not enum-validate the value and a novel code is auto-added on write (typecast), so any currency works — but the base ships with these 12.

---

## 4. Required-on-create fields

A create is refused if any of these are missing/empty:

- **Vendors** — Vendor Name
- **Rate Lines** — Vendor, Rate Type, Unit, Rate
- **Reconciliations** — Recon ID, Stage, Version, Job Key, Status
- **Line Items** — Reconciliation, Verdict
- **Events** — Recon Ref, Type, At
- **Settings** — Default Currency

---

## 5. Immutable fields & append-only rules

The single writer (the script's write-plan) never touches these:

- **Reconciliations** — `Recon ID`, `Version`, `Job Key` may never be updated.
- A **Superseded** reconciliation is **frozen entirely** — no field may be
  updated. To change history, create a new `Version` instead.
- **Events** are **append-only** — rows are only ever created, never updated or
  deleted. This is the tamper-evident audit trail.
- **Vendors** — `Vendor Name` is the match key and is not updated.

Airtable cannot lock fields itself, so this is enforced in `schema.py` and the
agent is forbidden (in `SKILL.md`) from authoring its own writes. A determined
human editing the base by hand can still change a record — the guardrail
protects against the agent, not a person in the base.

---

## 6. Stage state machine

Legal agent transitions (anything else is refused):

| From | May move to |
|---|---|
| Awaiting invoice | New, Superseded, Archived |
| New | Queried, Sent to finance, Superseded, Archived |
| Queried | Re-run complete, Superseded, Archived |
| Re-run complete | Queried, Sent to finance, Superseded, Archived |
| Sent to finance | Resolved, Queried, Superseded, Archived |
| Resolved | Archived |
| Superseded | *(terminal — frozen)* |
| Archived | New (restore / unarchive) |

Re-opening a `Resolved` record is a deliberate human action in the dashboard,
not an agent transition.

---

## 7. Status vs Stage vs Verdict

Three different axes — never substitute one for another:

- **Status** = the verification *result* (what we found): `Verified` / `Flagged` / `Unverified`.
- **Stage** = the workflow *position* (where it is in the lifecycle): `New` → … → `Resolved`.
- **Verdict** = a single line's roll-up: `Verified` / `Query` / `Unverified`.

Record-level Status rolls up the line Verdicts: any `Query` line → `Flagged`;
otherwise, if at least one substantive external check (Price / Reality /
Authorization) ran and passed → `Verified`; if only internal consistency was
possible → `Unverified`.

---

## 8. The write-plan shape

The engine emits a list of ops; the agent executes them verbatim via MCP.

```json
[
  {"op": "create", "table": "Vendors", "record": {"Vendor Name": "Acme"}},
  {"op": "create", "table": "Reconciliations",
   "record": {"Recon ID": "REC-0001", "Stage": "New", "Version": 1,
              "Job Key": "acme|wo-1|inv-1", "Status": "Flagged",
              "Coverage": ["Price", "Reality"]}},
  {"op": "update", "table": "Reconciliations", "record_id": "rec...",
   "record": {"Stage": "Superseded"}, "current_stage": "New"}
]
```

- `create` ops list only allowed fields with allowed values and all required fields.
- `update` ops carry a `record_id`, only mutable fields, and (for a Stage change)
  the `current_stage` so the transition can be checked.
- `validate_write_plan()` refuses the whole plan on the first violation, so an
  invalid plan can never reach Airtable.
