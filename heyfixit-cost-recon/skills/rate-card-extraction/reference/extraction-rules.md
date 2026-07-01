# Rate-card extraction rules

The complete methodology for digitizing a vendor contract into the `Rate Lines`
table. Self-contained — everything needed is here. The guiding principle: the rate
card is checked against every future invoice, so **never invent or guess a rate**;
under-claim rather than over-claim, and flag uncertainty loudly.

## Contents

- 1. Input
- 2. Pricing-model detection (do this first)
- 3. The Rate Lines fields + controlled vocabulary
- 4. Mapping rules
- 5. The review table (the human gate)
- 6. The `submission` to hand to write_rates.py
- 7. Worked example

---

## 1. Input

One or more documents for a **single vendor**: a contract, rate schedule, schedule
of rates (SOR), quote letter, or an email stating rates. They may be messy, scanned,
multi-file, or have rates spread across sections and appendices. Ignore payment terms,
SLAs, and legal clauses — they aren't tracked here.

---

## 2. Pricing-model detection (do this first)

Identify the model before extracting — it decides whether line-by-line verification
is even possible:

- **Rate card** (supported) — explicit labour / call-out / travel / markup / task
  rates. Extract normally.
- **Measured-term / Schedule of Rates** (detect + **defer**) — priced off an
  *external* schedule (NHF, NSR, M3NHF, PSA) × an adjustment %, and/or an AOV /
  lump-sum with a value cap. Capture the parameters you can (adjustment %, value cap,
  schedule name + version, AOV) as `Other` lines with details in `Conditions`, then
  **stop and tell the person plainly** that invoices can't be checked line-by-line
  without that external schedule and their adjustment % — that is HeyFixit-production
  territory; for this tool, load a vendor on a standard hourly rate card. **Never
  fabricate hourly rates.**
- **Fixed-price / lump-sum only** — note it and flag similarly.

---

## 3. The Rate Lines fields + controlled vocabulary

Produce one Rate Line per rate, with these fields (exact Airtable names):

| Field | Allowed values / format |
|---|---|
| Vendor | the vendor name (one vendor per run) |
| Rate Type | `Labour` · `Call-out` · `Travel` · `Materials markup` · `Specialist markup` · `Plant hire` · `SOR task` · `Minimum charge` · `Other` |
| Description / Trade | the service / trade / task — e.g. "HVAC Engineer", "Standard-hours call-out", "Replace tap washer set" |
| Band | `Normal` · `OOH` · `Saturday` · `Sunday / Bank Hol` · `Emergency` (blank for non-time-based lines) |
| Unit | `per hour` · `per visit` · `per day` · `per mile` · `per item` · `%` · `fixed` |
| Rate | the number only, no currency symbol. **Copy exactly; never round.** |
| Min Units | minimum charge units if stated (e.g. 1 for "minimum 1 hour"); else blank |
| Conditions | inclusions / tiers / thresholds / caveats — e.g. "Includes first 1 hr labour", "Net cost up to 500", "OOH = 1.5x normal" |
| Effective From | rate effective/review date if stated (YYYY-MM-DD); else blank |

Also capture contract-level facts: `vendor_name`, `currency`, `effective_date`.

`write_rates.py` coerces an unrecognised Rate Type to `Other` (and preserves the
original in `Conditions`), and drops an unrecognised Band to blank — so map as
cleanly as you can, but these are safety nets, not licences to be sloppy.

---

## 4. Mapping rules

1. **Controlled vocabulary only.** Map every line to an allowed `Rate Type` / `Band` / `Unit`. If something truly doesn't fit, use `Rate Type: Other`, explain in `Conditions`, and **flag it**.
2. **Multipliers → absolute rates.** "OOH = 1.5× normal" → compute the absolute rate **and** record the basis in `Conditions`. If the base rate to multiply is unclear, **flag it** instead of guessing.
3. **Inclusions → `Min Units` + `Conditions`.** "Call-out includes first hour" → the call-out line gets `Conditions: "includes first 1 hr labour"`. This is critical — it stops the reconciliation engine double-counting that labour.
4. **Tiered markups → one row per tier**, threshold in `Conditions` ("up to 500", "500–2000", "above 2000").
5. **Minimum charges / increments → `Min Units` + `Conditions`** ("min 1 hr; 15-min increments after").
6. **Never invent.** A rate referenced but not given ("specialist rates on application") → create the line with `Rate` blank and **flag it**. (write_rates.py will skip a rate-less line and report it back, not save it.)
7. **Copy figures exactly** — no rounding, no currency conversion.

---

## 5. The review table (the human gate)

Always show this **before** saving anything:

1. A clean markdown table of all extracted Rate Lines.
2. A **"⚠ Needs your check"** section listing every flagged/uncertain item with a one-line reason.
3. Close with: *"This is what I read from the contract. Confirm or correct anything and I'll save it to your rate card. Nothing is saved until you say go — these rates are what every invoice gets checked against."*

Do not assemble the submission or run write_rates.py until the person confirms.

---

## 6. The `submission` to hand to write_rates.py

After confirmation, build this (the validator's input — full schema in
`write_rates.py`'s header):

```jsonc
{
  "vendor_name": "Apex Mechanical Services Ltd",
  "currency": "GBP",
  "effective_date": "2026-01-01",
  "pricing_model": "rate_card",
  "rate_lines": [
    {"rate_type":"Labour","description":"HVAC / Mechanical Engineer","band":"Normal",
     "unit":"per hour","rate":68,"min_units":1,
     "conditions":"Min 1 hr; 15-min increments after","effective_from":"2026-01-01"}
  ],
  "flags": [
    {"item":"Specialist subcontractor rate","issue":"Contract says 'on application' - no figure given."}
  ],
  "vendor_exists": false,
  "actor": "Setup agent",
  "now": "ISO-8601"
}
```

`write_rates.py` writes only lines with a numeric rate **and** a unit; everything
else (rate-less lines + your flags) comes back in `skipped` for the person to follow
up. It returns a validated `write_plan` for you to execute via MCP.

---

## 7. Worked example

Running against a fully-specified hourly contract for "Apex Mechanical Services Ltd"
should produce: banded labour rows (Normal/OOH/Saturday/Sunday), the two call-outs
with their inclusions in `Conditions`, included-then-per-mile travel, the three
markup tiers (one row each), specialist + plant markups, and the SOR tasks — with
**no flags**, since that contract is fully specified. A line such as "specialist
rate on application" would instead appear under "Needs your check" with a blank rate,
and would be skipped (not saved) until a figure is confirmed.
