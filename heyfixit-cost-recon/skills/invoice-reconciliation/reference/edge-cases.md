# Reconciliation disposition contract (edge cases)

The complete behaviour `reconcile.py` implements: every input has a defined
disposition, the agent never dead-ends, never demands a missing document, and
never "verifies" off thin coverage. Self-contained — everything needed is here.

## Contents

- 1. Principles
- 2. Document types
- 3. The four checks (and their fallbacks)
- 4. Status, Verdict, Coverage (the roll-up rules)
- 5. The `case` the model must produce (input contract)
- 6. Disposition for every scenario
- 7. Routing: new / revised / promote / augment / park
- 8. Full edge-case table (24 rows)
- 9. The model/code line

---

## 1. Principles

1. **Verify against whatever is present.** The rate card is one reference among several — quote, PO, service report, WO export are *also* references. Run every check whose inputs exist; skip the rest and say so.
2. **Never block, never demand.** A missing document never stops the run. Verify what you can; report the gap.
3. **Always report coverage.** Every record states what was checked, what couldn't be, and why. Never call something `Verified` off thin coverage.
4. **Judgment stays human; the workflow is deterministic.** The model reads + classifies documents; `reconcile.py` applies the rules and writes the records. No improvised workflow, no "I don't know" errors.
5. **Documents arrive over time, in any order.** A record is assembled incrementally — a PO today, the invoice tomorrow, the service report next week. Coverage only improves; nothing is lost or reprocessed from scratch.

---

## 2. Document types

| Code | Document | Role |
|---|---|---|
| INV | Invoice | The bill being verified — the anchor. |
| QT | Quote | Agreed price. A **price** and **authorization** reference. |
| PO | Purchase Order | Operator authorization. An **authorization** reference. |
| SR | Service Report | Vendor's report of work — time, parts. A **reality** reference. |
| WO | Work-Order export / Job Report | CMMS download. A **reality** reference (if both SR and WO, cross-check). |
| RC | Rate Card *(in Airtable, not per-job)* | Contracted rates. The preferred **price** reference. |

---

## 3. The four checks (and their fallbacks)

Each runs only if its inputs are present; otherwise it is recorded (not failed).

| Check | Compares | Reference priority | Result values |
|---|---|---|---|
| **Price** (Rate Check) | invoice rates | Rate Card → fallback Quote → else none | Pass / Flag / N/A / Unverified |
| **Reality** (Reality Check) | invoice hours/parts/mileage | Service Report → or WO export | Pass / Flag / Unverified |
| **Authorization** | invoice lines vs authorised | PO → fallback Quote (note "PO not provided"); Standing job → N/A | Pass / Flag / N/A / Unverified |
| **Internal consistency** | the invoice alone | — (always runs) | issues list (lines sum to total; qty×rate = amount; no negatives) |

Key fallback behaviours: quoted job with PO missing but a quote present → Authorization falls back to the quote ("PO not provided"). New vendor with no rate card but a quote present → Price falls back to the quote. No service report → Reality is `Unverified` (a gap, not a fail).

---

## 4. Status, Verdict, Coverage (the roll-up rules)

`reconcile.py` computes these deterministically:

**Per-line Verdict** — `Query` if any of its three checks is `Flag`; else `Pass` if at least one check was substantive (`Pass`/`Flag`); else `Unverified` (nothing could be checked).

**Record Status** — `Flagged` if any line is `Query` or any internal-consistency issue exists; else `Verified` if at least one substantive external check (Price/Reality/Authorization) ran and passed; else `Unverified` (only internal consistency was possible).

**Coverage** (multi-select) — `Price` if any line's Rate Check ran (Pass/Flag); `Reality` likewise; `Authorization` likewise; `Internal` always. Recorded so the human sees the confidence honestly.

**Value Queried** — per `Query` line, the **largest single disputed amount** across its flagged checks (never the sum — the same overage appears under more than one check), capped at the line amount. Summed across queried lines.

---

## 5. The `case` the model must produce (input contract)

The model's only job is to read the documents and emit this structure faithfully
— classify, map, and quantify, but assign **no verdicts**. `reconcile.py` does
the rest. (Full annotated schema is in `reconcile.py`'s header.)

```jsonc
{
  "job": {
    "vendor": "...", "job_wo_ref": "...", "job_type": "Quoted|Standing",
    "currency": "GBP", "invoice_no": "...", "invoice_date": "YYYY-MM-DD",
    "invoice_total": 0, "documents_present": ["INV","QT","PO","SR","WO","RC"],
    "has_price_reference": true, "has_reality": true,
    "has_authorization_reference": true, "authorization_basis": "po|quote|null",
    "po_total": 0, "quote_total": 0, "reality_hours": 0, "reality_materials": "..."
  },
  "lines": [
    {
      "description": "...", "qty": 0, "unit_price": 0, "amount": 0,
      "rate":          { "applicable": true, "expected_rate": 0, "basis": "rate_card|quote|null" },
      "reality":       { "evidenced_qty": 0, "on_report": true },
      "authorization": { "in_scope": true, "authorized_amount": 0 }
    }
  ],
  "existing": [ /* records the agent pre-fetched for this WO ref */ ],
  "vendor_exists": true, "recon_seq": 1, "actor": "...", "now": "ISO-8601"
}
```

How to set the per-line evidence (this is the only place judgment enters, and it
is bounded classification, not verdicts):

- `rate.applicable` — `false` for cost-plus materials (no contracted rate expected); `true` for labour/call-out/travel that should be on the rate card.
- `rate.expected_rate` — the matched contracted/quoted rate, or `null` if the line is **not** on any price reference (→ the engine flags it; never invent a rate).
- `reality.evidenced_qty` — for quantitative lines (hours, mileage), the quantity the reality doc evidences; `null` if not quantitative or no reality doc.
- `reality.on_report` — for discrete items (a part), `true`/`false` whether it appears on the reality doc; `null` if no reality doc.
- `authorization.in_scope` — `true`/`false` whether the line is within the quote/PO scope; `null` if neither present.
- `authorization.authorized_amount` — the amount the quote/PO authorises for this line, if itemised; `null` otherwise.

If a line can't be confidently mapped to a price reference, set `expected_rate: null` — the engine flags that line. Never guess.

---

## 6. Disposition for every scenario

**Single document alone** — Invoice only → reconcile degraded (internal + Price if a rate card exists); Status `Verified` only if a substantive check ran and passed, else `Unverified`. Quote / PO / Service Report / WO alone → **park** as an `Awaiting invoice` stub keyed by WO ref; matched when the invoice arrives.

**Combinations (2+ docs)** — run all checks whose inputs are present (see §3) and write the coverage note. E.g. INV+QT → Price + Authorization(vs quote, "PO not provided") + Internal. INV+SR → Reality + Price(if RC) + Internal. INV+QT+PO+SR → all four.

**Multiple jobs / multiple invoices in one upload** — group documents by job key (WO/PO/quote/invoice no, fallback vendor+site+date); each group with an invoice → its own reconciliation; groups without an invoice → park; a doc whose references don't match its group's invoice → exclude + flag; a doc that links to no job → flag "couldn't link — please confirm".

**New vendor / no rate card** — never demand onboarding first. Price falls back to the quote; Reality runs vs the service report; Authorization vs PO/quote. Verify everything possible and *suggest* (not require) adding the rate card for rate-level checks.

**Incremental assembly (late / out-of-order docs)** — on **every** incoming document the agent first looks up Airtable by job reference, then routes (§7). A record's coverage builds up over time; a Flagged/Unverified record becomes Verified automatically when the missing PO/quote/SR is forwarded later, with a clean audit trail.

---

## 7. Routing: new / revised / promote / augment / park

`reconcile.py`'s `_decide_action()` chooses one, from the WO's pre-fetched `existing` records:

| Situation | Action | What the write-plan does |
|---|---|---|
| Invoice, no matching record | **new** | Create reconciliation v1 (Stage `New`) + line items + Event `Created`. |
| Invoice, an active record with the **same invoice no** exists | **revised_invoice** | Supersede the prior (Stage `Superseded` + Event `Superseded`), create a new **Version** + Event `Re-run`. |
| Invoice, an **`Awaiting invoice` stub** exists for this WO | **promote** | Create the real reconciliation (carrying the stub's docs), supersede the stub, Event `Promoted`. |
| Supporting doc only, an active reconciliation exists | **augment** | Update it **in place** (mutable fields + Event `Document added`) — **not** a new version — then re-run with the full document set to recompute checks. |
| Supporting doc only, no record | **park** | Create an `Awaiting invoice` stub keyed by WO ref + Event `Parked`. |

**Rule of thumb:** a *revised invoice* makes a new version; a *late supporting doc* augments in place. Promotion creates the real record and retires the stub (Job Key is immutable, so the stub is superseded rather than mutated).

---

## 8. Full edge-case table

| # | Edge case | Disposition |
|---|---|---|
| 1 | Invoice only (no QT/PO/SR/WO) | Reconcile degraded; Status `Unverified` unless a rate-card price check ran; note gaps. |
| 2 | Quote / PO / SR / WO uploaded alone | Park as a stub keyed by WO ref; match on invoice arrival. |
| 3 | Quoted job, PO missing, INV + QT | Authorization falls back to quote; note "PO not provided"; not blocked. |
| 4 | No service report, INV + QT (+PO) | Reality = `Unverified`; verify Price/Authorization; note gap. |
| 5 | New vendor / no rate card, INV + QT/SR | Price → quote; Reality → SR; verify; *suggest* rate card. |
| 6 | Supporting doc references a different job | Exclude + flag. |
| 7 | Multiple invoices in one upload | Split → one reconciliation each. |
| 8 | Multiple jobs, mixed docs | Group by ref; reconcile groups with an invoice; park the rest; flag orphans. |
| 9 | Non-rate-card contract (external SoR / AOV) | Defer — verification limited; don't fabricate rates. |
| 10 | Same invoice again (re-run / revised) | Supersede prior version; new Version. |
| 11 | Not an invoice / illegible scan | Reject + notify "couldn't read this". |
| 12 | Invoice line can't be matched to a price reference | Flag that line (`expected_rate: null`); never guess. |
| 13 | Missing invoice no / total | Flag for human; don't infer. |
| 14 | Uplift (invoice > authorised quote/PO) | Flag unauthorised uplift. |
| 15 | Email with no / wrong attachment | Notify, no record. |
| 16 | Currency ≠ reference currency | Flag mismatch (`currency_mismatch: true`). |
| 17 | Staged billing (several invoices, one WO) | Each its own reconciliation (Job Key includes invoice no). |
| 18 | Both SR and WO export present | Cross-check; use the stronger; flag if they disagree. |
| 19 | Duplicate supporting doc (two quotes) | Use the latest/highest version; note. |
| 20 | Quote present but superseded/expired | Note staleness (`quote_expired: true`); verify but flag if expired. |
| 21 | Supporting doc arrives after the invoice was reconciled | Augment in place, re-run now-possible checks, update Status/coverage, Event `Document added`. |
| 22 | Parked doc(s) completed by a later invoice | Promote the stub → full reconciliation. |
| 23 | Missing PO/quote/SR forwarded days later | Augments incrementally; Unverified/Flagged → Verified if it now reconciles. |
| 24 | Late doc contradicts the invoice (e.g. PO authorises less) | Re-verify downgrades: new Flag + query, logged. |

---

## 9. The model/code line

- **Model (perception, bounded):** read/classify each document; group by job; detect multiple/illegible invoices; detect non-rate-card contracts; map each invoice line to a price reference and fill the per-line evidence in §5. No verdicts, no arithmetic.
- **Code (`reconcile.py`, deterministic):** reference fallbacks, all check arithmetic, verdicts, coverage, Status, Job Key, dedup/version/park/promote/augment routing, and the validated write-plan.
- **Agent:** executes the validated write-plan via MCP verbatim; re-reads to verify; never authors its own writes; has no payment tool.
