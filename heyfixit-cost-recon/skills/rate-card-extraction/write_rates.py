"""write_rates.py - validate human-approved extracted rate lines -> write-plan.

Pure Python standard library only (no network, no third-party imports). Imports
the contract from schema.py. This is the deterministic half of the rate-card
extractor:

    MODEL  -> reads the contract, classifies the pricing model, maps every rate
              into the controlled vocabulary, and presents a REVIEW TABLE.
    HUMAN  -> confirms or corrects the review table (the human-in-the-loop gate).
    CODE   -> this file: validates the confirmed rate lines and builds a
              VALIDATED write-plan.
    AGENT  -> executes the write-plan against Airtable via MCP, verbatim.

Nothing is written until the human confirms. The rate card is the backbone of
every future invoice check, so a line is only written when it has a numeric rate
AND a unit; anything else is reported back, never guessed.

------------------------------------------------------------------------------
INPUT: the `submission` dict (the human-approved extraction)
------------------------------------------------------------------------------
submission = {
  "vendor_name": str,
  "currency": "GBP" | "USD" | ...,
  "effective_date": "YYYY-MM-DD" | None,        # contract-level default
  "pricing_model": "rate_card" | "measured_term" | "fixed_price",
  "rate_lines": [
    { "rate_type": str, "description": str, "band": str, "unit": str,
      "rate": number | None, "min_units": number | None,
      "conditions": str, "effective_from": "YYYY-MM-DD" | None }, ...
  ],
  "flags": [ { "item": str, "issue": str }, ... ],   # things the human should check
  "vendor_exists": bool,                              # is the vendor already a Vendors row?
  "actor": str, "now": "ISO-8601"
}

------------------------------------------------------------------------------
OUTPUT: write_rates(submission) -> dict
------------------------------------------------------------------------------
{
  "vendor": str, "pricing_model": str,
  "written_count": int, "written": [ {Rate Lines record}, ... ],
  "skipped": [ {"description": str, "reason": str}, ... ],   # rate-less lines + flags
  "write_plan": [ ops ]   # validated by schema.validate_write_plan
}
"""

from __future__ import annotations

import schema


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _norm_rate_type(rt):
    """Map to a controlled Rate Type; unknown -> 'Other' (never invent a category)."""
    rt = (rt or "").strip()
    return rt if rt in schema.RATE_TYPE else "Other"


def _norm_band(b):
    """Keep a controlled Band; blank or unknown -> '' (non-time-based line)."""
    b = (b or "").strip()
    return b if b in schema.BAND else ""


def build_rate_line(raw, submission):
    rate = _num(raw.get("rate"))
    rt_in = (raw.get("rate_type") or "").strip()
    rt = _norm_rate_type(rt_in)
    conditions = (raw.get("conditions") or "").strip()
    # if we had to coerce an unrecognised rate type, preserve the original
    if rt == "Other" and rt_in and rt_in != "Other":
        conditions = (conditions + f" [original rate_type: {rt_in}]").strip()
    rec = {
        "Vendor": submission.get("vendor_name", ""),
        "Rate Type": rt,
        "Description / Trade": (raw.get("description") or "").strip(),
        "Band": _norm_band(raw.get("band")),
        "Unit": (raw.get("unit") or "").strip(),
        "Rate": rate,
        "Min Units": _num(raw.get("min_units")),
        "Conditions": conditions,
        "Effective From": raw.get("effective_from") or submission.get("effective_date"),
    }
    # Airtable: omit blank/None fields rather than writing empties
    return {k: v for k, v in rec.items() if v not in (None, "")}


def write_rates(submission):
    vendor = (submission.get("vendor_name") or "").strip()
    writable, skipped = [], []

    for raw in submission.get("rate_lines", []):
        rate = _num(raw.get("rate"))
        unit = (raw.get("unit") or "").strip()
        if rate is None:
            skipped.append({"description": raw.get("description", ""),
                            "reason": "no numeric rate - confirm the figure before it can be saved"})
            continue
        if not unit:
            skipped.append({"description": raw.get("description", ""),
                            "reason": "no unit - confirm the unit (per hour / per visit / %, etc.)"})
            continue
        writable.append(build_rate_line(raw, submission))

    # carry the model's own flags through to the human, too
    for f in submission.get("flags", []):
        skipped.append({"description": f.get("item", ""), "reason": f.get("issue", "")})

    plan = []
    if not submission.get("vendor_exists", False) and vendor:
        plan.append({"op": "create", "table": schema.VENDORS,
                     "record": {"Vendor Name": vendor}})
    for rec in writable:
        plan.append({"op": "create", "table": schema.RATE_LINES, "record": rec})

    schema.validate_write_plan(plan)

    return {
        "vendor": vendor,
        "pricing_model": submission.get("pricing_model", "rate_card"),
        "written_count": len(writable),
        "written": writable,
        "skipped": skipped,
        "write_plan": plan,
    }


# ---------------------------------------------------------------------------
# CLI + self-test
# ---------------------------------------------------------------------------
#   python write_rates.py submission.json  -> read confirmed submission, print result JSON
#   python write_rates.py                  -> run the Apex sample self-test
# ---------------------------------------------------------------------------

def _selftest():
    submission = {
        "vendor_name": "Apex Mechanical Services Ltd", "currency": "GBP",
        "effective_date": "2026-01-01", "pricing_model": "rate_card",
        "rate_lines": [
            {"rate_type": "Labour", "description": "HVAC / Mechanical Engineer",
             "band": "Normal", "unit": "per hour", "rate": 68, "min_units": 1,
             "conditions": "Min 1 hr; 15-min increments after", "effective_from": "2026-01-01"},
            {"rate_type": "Call-out", "description": "Standard-hours call-out",
             "band": "Normal", "unit": "per visit", "rate": 85, "min_units": None,
             "conditions": "Includes first 30 min on site", "effective_from": None},
            {"rate_type": "Materials markup", "description": "Parts markup (tier 1)",
             "band": "", "unit": "%", "rate": 15, "min_units": None,
             "conditions": "Net cost up to GBP 500", "effective_from": None},
            {"rate_type": "SOR task", "description": "Replace tap washer set",
             "band": "", "unit": "fixed", "rate": 24, "min_units": None,
             "conditions": "", "effective_from": None},
            # a weird rate type -> coerced to Other, original preserved in conditions
            {"rate_type": "Mobilisation fee", "description": "One-off mobilisation",
             "band": "", "unit": "fixed", "rate": 50, "min_units": None,
             "conditions": "", "effective_from": None},
            # flagged: no rate -> skipped, reported to human
            {"rate_type": "Specialist markup", "description": "Specialist subcontractor",
             "band": "", "unit": "%", "rate": None, "min_units": None,
             "conditions": "Rate on application", "effective_from": None},
        ],
        "flags": [
            {"item": "Specialist subcontractor rate", "issue": "Contract says 'on application' - no figure given."}
        ],
        "vendor_exists": False, "actor": "Setup agent", "now": "2026-06-24T10:00:00Z",
    }

    out = write_rates(submission)
    print("vendor        :", out["vendor"])
    print("pricing_model :", out["pricing_model"])
    print("written_count :", out["written_count"])
    print("skipped       :", [s["description"] for s in out["skipped"]])
    print("write_plan ops:", len(out["write_plan"]))

    assert out["written_count"] == 5, out["written_count"]
    # 1 vendor create + 5 rate-line creates
    assert len(out["write_plan"]) == 6, len(out["write_plan"])
    # the rate-less specialist line is skipped (plus the model flag)
    descs = [s["description"] for s in out["skipped"]]
    assert "Specialist subcontractor" in descs
    # the coerced rate type
    mob = [r for r in out["written"] if r["Description / Trade"] == "One-off mobilisation"][0]
    assert mob["Rate Type"] == "Other", mob["Rate Type"]
    assert "Mobilisation fee" in mob["Conditions"]
    # the call-out inclusion is preserved (so reconciliation won't double-count labour)
    co = [r for r in out["written"] if r["Rate Type"] == "Call-out"][0]
    assert "Includes first 30 min" in co["Conditions"]
    # plan is contract-valid
    assert schema.validate_write_plan(out["write_plan"]) is True
    print("\nApex sample reproduced. Write-plan valid (", len(out["write_plan"]), "ops ).")


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1 and sys.argv[1] not in ("--selftest", "-t"):
        with open(sys.argv[1]) as _fh:
            _result = write_rates(json.load(_fh))
        print(json.dumps(_result, indent=2, default=str))
    else:
        _selftest()
