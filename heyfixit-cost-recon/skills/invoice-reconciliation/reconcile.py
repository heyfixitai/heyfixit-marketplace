"""reconcile.py - the deterministic reconciliation engine.

Pure Python standard library only (no network, no third-party imports). Imports
the contract from schema.py. This is the deterministic half of the design:

    MODEL  -> reads the documents and emits a strict, factual `case` (below).
    CODE   -> this file: applies the checks, verdicts, roll-ups, and routing,
              and emits a VALIDATED write-plan.
    AGENT  -> executes the write-plan against Airtable via MCP, verbatim.

The engine never reads documents, never guesses a rate, and never invents a
verdict. It only does arithmetic and rule application on the facts the model
gives it, so the same inputs always produce the same records.

------------------------------------------------------------------------------
INPUT: the `case` dict (what the model produces, then the agent passes in)
------------------------------------------------------------------------------
case = {
  "job": {
    "vendor": str,
    "job_wo_ref": str,
    "job_type": "Quoted" | "Standing",
    "currency": "GBP" | "USD" | "EUR" | ...,
    "invoice_no": str | "",          # "" means no invoice in this batch (supporting doc only)
    "invoice_date": "YYYY-MM-DD" | None,
    "invoice_total": number | None,
    "documents_present": [ "INV","QT","PO","SR","WO","RC" ],   # codes actually present
    "has_price_reference": bool,         # a rate card OR a quote is available
    "has_reality": bool,                 # a service report OR WO export is available
    "has_authorization_reference": bool, # a PO OR a quote is available
    "authorization_basis": "po" | "quote" | None,
    "po_total": number | None,
    "quote_total": number | None,
    "reality_hours": number | None,
    "reality_materials": str | None,
    "quote_expired": bool | None,        # edge 20 (optional)
    "currency_mismatch": bool | None     # edge 16 (optional)
  },
  "lines": [                              # the invoice lines (empty if supporting doc only)
    {
      "description": str, "qty": number, "unit_price": number, "amount": number,
      "rate":          {"applicable": bool, "expected_rate": number|None, "basis": "rate_card"|"quote"|None},
      "reality":       {"evidenced_qty": number|None, "on_report": bool|None},
      "authorization": {"in_scope": bool|None, "authorized_amount": number|None}
    }, ...
  ],
  "existing": [                           # records the agent pre-fetched for this WO ref
    {"record_id": str, "recon_id": str, "job_key": str, "stage": str,
     "version": number, "invoice_no": str}
  ],
  "vendor_exists": bool,                   # is the vendor already a row in Vendors?
  "recon_seq": int,                        # next sequence number (existing count + 1) for REC-id
  "actor": str,                            # who/what is acting (operator name or "Reconciliation agent")
  "now": "YYYY-MM-DDTHH:MM:SSZ"            # ISO timestamp
}

------------------------------------------------------------------------------
OUTPUT: reconcile(case) -> dict
------------------------------------------------------------------------------
{
  "action": "new" | "revised_invoice" | "promote" | "augment" | "park",
  "reconciliation": {field: value, ...},  # the computed record fields
  "lines": [ {field: value, ...}, ... ],  # the computed line-item fields
  "status": ..., "coverage": [...], "exceptions": int, "value_queried": number,
  "verification_summary": str, "vendor_query_draft": str,
  "write_plan": [ ops ]                    # validated by schema.validate_write_plan
}
"""

from __future__ import annotations

import schema

EPS = 0.005  # money/quantity comparison tolerance for float noise only (not a leniency dial)

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

_CCY = {"GBP": "£", "USD": "$", "EUR": "€", "AUD": "A$", "CAD": "C$",
        "NZD": "NZ$", "INR": "₹", "JPY": "¥", "CNY": "¥", "CHF": "CHF ",
        "ZAR": "R", "SGD": "S$", "HKD": "HK$", "AED": "AED ", "SAR": "SAR "}

_DOC_LABEL = {
    "INV": "Invoice", "QT": "Quote", "PO": "PO",
    "SR": "Service report", "WO": "WO export", "RC": "Rate card",
}


def _num(v, default=0.0):
    if v is None or v == "":
        return float(default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _approx(a, b):
    return abs(_num(a) - _num(b)) <= EPS


def _trim(n):
    """Format a number without a trailing .0 (3.5 -> '3.5', 5.0 -> '5')."""
    n = _num(n)
    return str(int(n)) if abs(n - round(n)) < 1e-9 else f"{n:g}"


def _money(n, ccy="GBP"):
    sym = _CCY.get(ccy, ccy + " ")
    n = round(_num(n), 2)
    return f"{sym}{int(n)}" if abs(n - round(n)) < 1e-9 else f"{sym}{n:.2f}"


def make_job_key(job):
    """Stable grouping key for a real (invoiced) reconciliation."""
    return "|".join([
        str(job.get("vendor", "")).strip().lower(),
        str(job.get("job_wo_ref", "")).strip().lower(),
        str(job.get("invoice_no", "")).strip().lower(),
    ])


def make_stub_key(job):
    """Stub key (no invoice yet) - keyed by vendor + WO ref only."""
    return "|".join([
        str(job.get("vendor", "")).strip().lower(),
        str(job.get("job_wo_ref", "")).strip().lower(),
        "",
    ])


# ---------------------------------------------------------------------------
# The three checks (+ internal consistency). Each returns (check, disputed, reason).
# ---------------------------------------------------------------------------

def check_rate(line, job):
    r = line.get("rate", {}) or {}
    if not r.get("applicable", True):
        return ("N/A", 0.0, "")
    if not job.get("has_price_reference", False):
        return ("Unverified", 0.0, "No rate card or quote to check the rate against")
    expected = r.get("expected_rate")
    unit = _num(line.get("unit_price"))
    qty = _num(line.get("qty"))
    amount = _num(line.get("amount"), unit * qty)
    ccy = job.get("currency", "GBP")
    if expected is None:
        return ("Flag", amount, "Not on the rate card or quote")
    if _approx(unit, expected):
        return ("Pass", 0.0, "")
    disputed = abs(unit - _num(expected)) * qty
    direction = "over" if unit > _num(expected) else "under"
    return ("Flag", disputed,
            f"Billed {_money(unit, ccy)} vs contracted {_money(expected, ccy)} ({direction})")


def check_reality(line, job):
    if not job.get("has_reality", False):
        return ("Unverified", 0.0, "No service report or work-order export to verify against")
    rl = line.get("reality", {}) or {}
    qty = _num(line.get("qty"))
    unit = _num(line.get("unit_price"))
    ccy = job.get("currency", "GBP")
    evid = rl.get("evidenced_qty")
    if evid is not None:
        if qty <= _num(evid) + EPS:
            return ("Pass", 0.0, "")
        over_units = qty - _num(evid)
        disputed = over_units * unit
        return ("Flag", disputed,
                f"Billed {_trim(qty)} vs {_trim(evid)} evidenced; "
                f"{_trim(over_units)} over ({_money(disputed, ccy)})")
    on_report = rl.get("on_report")
    if on_report is True:
        return ("Pass", 0.0, "")
    if on_report is False:
        return ("Flag", _num(line.get("amount"), unit * qty),
                "Not evidenced on the service report / work-order export")
    return ("N/A", 0.0, "")


def check_authorization(line, job):
    if job.get("job_type") == "Standing":
        return ("N/A", 0.0, "")
    if not job.get("has_authorization_reference", False):
        return ("N/A", 0.0, "No PO or quote provided")
    a = line.get("authorization", {}) or {}
    in_scope = a.get("in_scope")
    unit = _num(line.get("unit_price"))
    qty = _num(line.get("qty"))
    amount = _num(line.get("amount"), unit * qty)
    ccy = job.get("currency", "GBP")
    if in_scope is False:
        return ("Flag", amount, "Not in the approved quote / PO")
    if in_scope is True:
        auth_amt = a.get("authorized_amount")
        if auth_amt is not None and amount > _num(auth_amt) + EPS:
            return ("Flag", amount - _num(auth_amt),
                    f"Billed {_money(amount, ccy)} exceeds authorised {_money(auth_amt, ccy)}")
        return ("Pass", 0.0, "")
    return ("Unverified", 0.0, "Couldn't confirm this line against the quote / PO")


def internal_consistency(job, lines):
    """Always runs (the invoice alone). Returns a list of issue strings."""
    issues = []
    ccy = job.get("currency", "GBP")
    total_lines = 0.0
    for ln in lines:
        q = _num(ln.get("qty"))
        u = _num(ln.get("unit_price"))
        a = _num(ln.get("amount"), q * u)
        total_lines += a
        desc = ln.get("description", "line")
        if not _approx(q * u, a):
            issues.append(f"{desc}: {_trim(q)} x {_money(u, ccy)} = {_money(q * u, ccy)} "
                          f"but billed {_money(a, ccy)}")
        if q < 0 or u < 0 or a < 0:
            issues.append(f"{desc}: contains a negative value")
    inv_total = job.get("invoice_total")
    if inv_total is not None and lines and not _approx(total_lines, inv_total):
        issues.append(f"Lines sum to {_money(total_lines, ccy)} but the invoice total is "
                      f"{_money(inv_total, ccy)}")
    if job.get("currency_mismatch") is True:
        issues.append("Invoice currency differs from the reference currency")
    if job.get("quote_expired") is True:
        issues.append("The quote used as a reference appears expired")
    return issues


# ---------------------------------------------------------------------------
# Per-line evaluation + roll-up
# ---------------------------------------------------------------------------

def evaluate_line(line, job):
    rate_c, rate_d, rate_r = check_rate(line, job)
    real_c, real_d, real_r = check_reality(line, job)
    auth_c, auth_d, auth_r = check_authorization(line, job)

    checks = (rate_c, real_c, auth_c)
    flagged = [c == "Flag" for c in checks]
    substantive = any(c in ("Pass", "Flag") for c in checks)

    if any(flagged):
        verdict = "Query"
    elif substantive:
        verdict = "Pass"
    else:
        verdict = "Unverified"

    # The queried amount is the LARGEST single disputed amount across the flagged
    # checks (never the sum - the same overage shows up under more than one check),
    # capped at the line amount.
    amount = _num(line.get("amount"), _num(line.get("unit_price")) * _num(line.get("qty")))
    queried = 0.0
    if verdict == "Query":
        queried = min(amount, max(rate_d, real_d, auth_d))

    reasons = [r for c, r in
               ((rate_c, rate_r), (real_c, real_r), (auth_c, auth_r))
               if c == "Flag" and r]
    flag_reason = "; ".join(reasons)[:140] if reasons else ""

    return {
        "Description": line.get("description", ""),
        "Qty / Hours": _num(line.get("qty")),
        "Unit Price": _num(line.get("unit_price")),
        "Amount": round(amount, 2),
        "Expected Rate": (None if (line.get("rate") or {}).get("expected_rate") is None
                          else _num((line.get("rate") or {}).get("expected_rate"))),
        "Rate Check": rate_c,
        "Reality Check": real_c,
        "Authorization Check": auth_c,
        "Verdict": verdict,
        "Flag Reason": flag_reason,
        "_queried": round(queried, 2),
    }


def compute_coverage(evaluated):
    cov = []
    if any(e["Rate Check"] in ("Pass", "Flag") for e in evaluated):
        cov.append("Price")
    if any(e["Reality Check"] in ("Pass", "Flag") for e in evaluated):
        cov.append("Reality")
    if any(e["Authorization Check"] in ("Pass", "Flag") for e in evaluated):
        cov.append("Authorization")
    cov.append("Internal")  # internal consistency always runs
    return cov


def rollup_status(evaluated, internal_issues):
    has_query = any(e["Verdict"] == "Query" for e in evaluated)
    substantive_ran = any(
        e["Rate Check"] in ("Pass", "Flag")
        or e["Reality Check"] in ("Pass", "Flag")
        or e["Authorization Check"] in ("Pass", "Flag")
        for e in evaluated
    )
    if has_query or internal_issues:
        return "Flagged"
    if substantive_ran:
        return "Verified"
    return "Unverified"


def coverage_note(job, evaluated, internal_issues):
    cov = compute_coverage(evaluated)
    checked, not_checked = [], []

    def basis_price():
        bases = {(e.get("Expected Rate") is not None) for e in evaluated}
        return "rate card" if job.get("documents_present") and "RC" in job["documents_present"] else \
               ("quote" if "QT" in (job.get("documents_present") or []) else "reference")

    if "Price" in cov:
        checked.append(f"Price (vs {basis_price()})")
    else:
        not_checked.append("Price (no rate card or quote)")
    if "Reality" in cov:
        checked.append("Reality (vs service report / WO export)")
    else:
        not_checked.append("Reality (no service report or WO export)")
    if "Authorization" in cov:
        ab = job.get("authorization_basis")
        label = "PO + quote" if ab == "po" and "QT" in (job.get("documents_present") or []) else \
                ("PO" if ab == "po" else ("quote - PO not provided" if ab == "quote" else "quote/PO"))
        checked.append(f"Authorization (vs {label})")
    elif job.get("job_type") == "Standing":
        not_checked.append("Authorization (standing job - N/A)")
    else:
        not_checked.append("Authorization (no PO or quote)")
    checked.append("Internal consistency")

    note = "Checked: " + ", ".join(checked) + "."
    if not_checked:
        note += " Not checked: " + ", ".join(not_checked) + "."
    if internal_issues:
        note += " Internal consistency issues: " + "; ".join(internal_issues) + "."
    return note


def vendor_query_draft(job, evaluated, value_queried, actor):
    """A clean, paste-ready email: subject, greeting, numbered queries, remainder, sign-off."""
    ccy = job.get("currency", "GBP")
    flagged = [e for e in evaluated if e["Verdict"] == "Query"]
    if not flagged:
        return ""
    inv = job.get("invoice_no", "") or "(no number)"
    wo = job.get("job_wo_ref", "")
    vendor = job.get("vendor", "") or "team"
    total = _num(job.get("invoice_total"))
    undisputed = max(0.0, total - _num(value_queried))
    signer = actor if actor and actor not in (
        "Reconciliation agent", "Managed agent", "Cowork agent") else "Accounts Payable"
    n = len(flagged)
    items = "\n".join(
        f"  {i + 1}. {e['Description']} - {e['Flag Reason'] or 'please confirm'}"
        for i, e in enumerate(flagged))
    return (
        f"Subject: Query on invoice {inv} ({wo})\n\n"
        f"Hi {vendor},\n\n"
        f"Thank you for invoice {inv} for {wo}. Before we can process payment, "
        f"please could you clarify the following {n} line{'s' if n != 1 else ''}, "
        f"{_money(value_queried, ccy)} under query:\n\n"
        f"{items}\n\n"
        f"We're happy to settle the undisputed remainder "
        f"({_money(undisputed, ccy)}) in the meantime. Please send a revised "
        f"invoice or supporting evidence for the items above.\n\n"
        f"Kind regards,\n{signer}"
    )


# ---------------------------------------------------------------------------
# Routing + write-plan
# ---------------------------------------------------------------------------

def _docs_present_label(job):
    return ", ".join(_DOC_LABEL.get(c, c) for c in (job.get("documents_present") or []))


def _event(recon_id, etype, detail, actor, now):
    return {"op": "create", "table": schema.EVENTS, "record": {
        "Event": f"{etype}",
        "Recon Ref": recon_id,
        "Type": etype,
        "Detail": detail,
        "Actor": actor,
        "At": now,
    }}


def _decide_action(job, existing, has_invoice):
    active = [e for e in (existing or []) if e.get("stage") != "Superseded"]
    stubs = [e for e in active if e.get("stage") == "Awaiting invoice"]
    same_invoice = [e for e in active
                    if e.get("stage") != "Awaiting invoice"
                    and str(e.get("invoice_no", "")).strip().lower()
                    == str(job.get("invoice_no", "")).strip().lower()
                    and job.get("invoice_no")]
    real_records = [e for e in active if e.get("stage") != "Awaiting invoice"]
    if has_invoice:
        if same_invoice:
            return "revised_invoice", same_invoice, stubs
        if stubs:
            return "promote", same_invoice, stubs
        return "new", same_invoice, stubs
    # supporting doc only
    if real_records:
        return "augment", real_records, stubs
    if stubs:
        return "augment_stub", real_records, stubs
    return "park", real_records, stubs


def reconcile(case):
    job = case.get("job", {})
    lines = case.get("lines", []) or []
    actor = case.get("actor") or "Reconciliation agent"
    now = case.get("now") or "1970-01-01T00:00:00Z"
    has_invoice = bool(str(job.get("invoice_no", "")).strip()) and bool(lines)

    action, targets, stubs = _decide_action(job, case.get("existing", []), has_invoice)

    # ---- Park (supporting doc only, no existing record) -------------------
    if action == "park":
        recon_id = case.get("recon_id") or f"REC-{int(case.get('recon_seq', 1)):04d}"
        rec = {
            "Recon ID": recon_id, "Stage": "Awaiting invoice", "Version": 1,
            "Job Key": make_stub_key(job), "Job / WO Ref": job.get("job_wo_ref", ""),
            "Vendor": job.get("vendor", ""), "Status": "Unverified",
            "Docs Present": _docs_present_label(job),
            "Verification Summary": "Parked: supporting document received before its "
                                    "invoice. Will reconcile automatically when the invoice arrives.",
        }
        plan = []
        if not case.get("vendor_exists", False):
            plan.append({"op": "create", "table": schema.VENDORS,
                         "record": {"Vendor Name": job.get("vendor", "")}})
        plan.append({"op": "create", "table": schema.RECONCILIATIONS, "record": rec})
        plan.append(_event(recon_id, "Parked",
                           f"Parked {_docs_present_label(job)} awaiting invoice", actor, now))
        schema.validate_write_plan(plan)
        return {"action": action, "reconciliation": rec, "lines": [],
                "status": "Unverified", "coverage": [], "exceptions": 0,
                "value_queried": 0.0,
                "verification_summary": rec["Verification Summary"],
                "vendor_query_draft": "", "write_plan": plan}

    # ---- Augment in place (late supporting doc onto an existing record) ----
    if action in ("augment", "augment_stub"):
        target = sorted(targets, key=lambda e: _num(e.get("version"), 1))[-1]
        schema.assert_updatable(schema.RECONCILIATIONS, target.get("stage"))
        upd = {"Docs Present": _docs_present_label(job)}
        detail = f"Document(s) added: {_docs_present_label(job)} - re-verify now-possible checks"
        plan = [
            {"op": "update", "table": schema.RECONCILIATIONS,
             "record_id": target.get("record_id"), "record": upd,
             "current_stage": target.get("stage")},
            _event(target.get("recon_id", ""), "Document added", detail, actor, now),
        ]
        schema.validate_write_plan(plan)
        return {"action": action, "reconciliation": upd, "lines": [],
                "status": None, "coverage": [], "exceptions": 0, "value_queried": 0.0,
                "verification_summary": detail, "vendor_query_draft": "",
                "write_plan": plan,
                "note": "Augment is a metadata update; after attaching the doc the agent "
                        "re-runs reconcile() with the full document set to recompute checks."}

    # ---- Evaluate the invoice (new / revised / promote) -------------------
    evaluated = [evaluate_line(ln, job) for ln in lines]
    internal_issues = internal_consistency(job, lines)
    status = rollup_status(evaluated, internal_issues)
    coverage = compute_coverage(evaluated)
    exceptions = sum(1 for e in evaluated if e["Verdict"] == "Query")
    value_queried = round(sum(e["_queried"] for e in evaluated), 2)
    summary = coverage_note(job, evaluated, internal_issues)
    query_draft = vendor_query_draft(job, evaluated, value_queried, actor)

    # version + recon id
    if action == "revised_invoice":
        version = int(max(_num(e.get("version"), 1) for e in targets)) + 1
        recon_id = case.get("recon_id") or f"REC-{int(case.get('recon_seq', 1)):04d}"
    else:
        version = 1
        recon_id = case.get("recon_id") or f"REC-{int(case.get('recon_seq', 1)):04d}"

    rec = {
        "Recon ID": recon_id, "Stage": "New", "Version": version,
        "Job Key": make_job_key(job), "Job / WO Ref": job.get("job_wo_ref", ""),
        "Vendor": job.get("vendor", ""), "Job Type": job.get("job_type", "Quoted"),
        "Invoice No": job.get("invoice_no", ""), "Invoice Date": job.get("invoice_date"),
        "Invoice Total": (None if job.get("invoice_total") is None else _num(job.get("invoice_total"))),
        "Currency": job.get("currency"),
        "Docs Present": _docs_present_label(job), "Coverage": coverage,
        "PO Total": (None if job.get("po_total") is None else _num(job.get("po_total"))),
        "Quote Total": (None if job.get("quote_total") is None else _num(job.get("quote_total"))),
        "Reality Hours": (None if job.get("reality_hours") is None else _num(job.get("reality_hours"))),
        "Reality Materials": job.get("reality_materials"),
        "Status": status, "Exceptions": exceptions, "Value Queried": value_queried,
        "Verification Summary": summary, "Vendor Query Draft": query_draft,
    }
    rec = {k: v for k, v in rec.items() if v is not None}

    # build the line-item records (linked to the recon by Recon ID)
    line_ops = []
    for e in evaluated:
        rec_line = {k: v for k, v in e.items() if k != "_queried"}
        if rec_line.get("Expected Rate") is None:
            rec_line.pop("Expected Rate", None)
        if not rec_line.get("Flag Reason"):
            rec_line.pop("Flag Reason", None)
        rec_line["Reconciliation"] = recon_id
        line_ops.append({"op": "create", "table": schema.LINE_ITEMS, "record": rec_line})

    plan = []
    if not case.get("vendor_exists", False):
        plan.append({"op": "create", "table": schema.VENDORS,
                     "record": {"Vendor Name": job.get("vendor", "")}})

    created_detail = f"Verification {status}; {_money(value_queried, job.get('currency', 'GBP'))} under query"

    if action == "revised_invoice":
        for t in targets:
            plan.append({"op": "update", "table": schema.RECONCILIATIONS,
                         "record_id": t.get("record_id"),
                         "record": {"Stage": "Superseded"},
                         "current_stage": t.get("stage")})
            plan.append(_event(t.get("recon_id", ""), "Superseded",
                               f"Superseded by {recon_id} (revised invoice)", actor, now))
        plan.append({"op": "create", "table": schema.RECONCILIATIONS, "record": rec})
        plan.extend(line_ops)
        plan.append(_event(recon_id, "Re-run",
                           created_detail + f" (v{version}, revised invoice)", actor, now))
    elif action == "promote":
        for s in stubs:
            plan.append({"op": "update", "table": schema.RECONCILIATIONS,
                         "record_id": s.get("record_id"),
                         "record": {"Stage": "Superseded"},
                         "current_stage": s.get("stage")})
            plan.append(_event(s.get("recon_id", ""), "Superseded",
                               f"Promoted into {recon_id} (invoice arrived)", actor, now))
        plan.append({"op": "create", "table": schema.RECONCILIATIONS, "record": rec})
        plan.extend(line_ops)
        plan.append(_event(recon_id, "Promoted",
                           created_detail + "; promoted from awaiting-invoice stub", actor, now))
    else:  # new
        plan.append({"op": "create", "table": schema.RECONCILIATIONS, "record": rec})
        plan.extend(line_ops)
        plan.append(_event(recon_id, "Created", created_detail, actor, now))

    schema.validate_write_plan(plan)

    return {
        "action": action, "reconciliation": rec,
        "lines": [{k: v for k, v in e.items() if k != "_queried"} for e in evaluated],
        "status": status, "coverage": coverage, "exceptions": exceptions,
        "value_queried": value_queried, "verification_summary": summary,
        "vendor_query_draft": query_draft, "write_plan": plan,
    }


# ---------------------------------------------------------------------------
# CLI + self-test
# ---------------------------------------------------------------------------
#   python reconcile.py case.json   -> read the case, print the result JSON
#                                      (the field records + the validated write-plan)
#   python reconcile.py             -> run the REC-0001 self-test
# ---------------------------------------------------------------------------

def _selftest():
    case = {
        "job": {
            "vendor": "Apex Mechanical Services Ltd", "job_wo_ref": "WO-4471",
            "job_type": "Quoted", "currency": "GBP", "invoice_no": "INV-20431",
            "invoice_date": "2026-06-12", "invoice_total": 965,
            "documents_present": ["INV", "SR", "QT", "PO"],
            "has_price_reference": True, "has_reality": True,
            "has_authorization_reference": True, "authorization_basis": "po",
            "po_total": 723, "quote_total": 723, "reality_hours": 3.5,
            "reality_materials": "1x compressor capacitor; refrigerant recharge",
        },
        "lines": [
            {"description": "Labour - HVAC Engineer", "qty": 5, "unit_price": 68, "amount": 340,
             "rate": {"applicable": True, "expected_rate": 68, "basis": "rate_card"},
             "reality": {"evidenced_qty": 3.5, "on_report": None},
             "authorization": {"in_scope": True, "authorized_amount": 238}},
            {"description": "Compressor capacitor", "qty": 1, "unit_price": 220, "amount": 220,
             "rate": {"applicable": False, "expected_rate": None, "basis": None},
             "reality": {"evidenced_qty": None, "on_report": True},
             "authorization": {"in_scope": True, "authorized_amount": None}},
            {"description": "Refrigerant recharge", "qty": 1, "unit_price": 180, "amount": 180,
             "rate": {"applicable": False, "expected_rate": None, "basis": None},
             "reality": {"evidenced_qty": None, "on_report": True},
             "authorization": {"in_scope": True, "authorized_amount": None}},
            {"description": "Standard call-out", "qty": 1, "unit_price": 85, "amount": 85,
             "rate": {"applicable": True, "expected_rate": 85, "basis": "rate_card"},
             "reality": {"evidenced_qty": None, "on_report": True},
             "authorization": {"in_scope": True, "authorized_amount": None}},
            {"description": "Additional sundries", "qty": 1, "unit_price": 140, "amount": 140,
             "rate": {"applicable": True, "expected_rate": None, "basis": None},
             "reality": {"evidenced_qty": None, "on_report": False},
             "authorization": {"in_scope": False, "authorized_amount": None}},
        ],
        "existing": [], "vendor_exists": True, "recon_seq": 1,
        "actor": "Reconciliation agent", "now": "2026-06-12T10:00:00Z",
    }

    out = reconcile(case)
    print("action          :", out["action"])
    print("status          :", out["status"])
    print("exceptions      :", out["exceptions"])
    print("value_queried   :", out["value_queried"])
    print("coverage        :", out["coverage"])
    print("recon id        :", out["reconciliation"]["Recon ID"],
          "v" + str(out["reconciliation"]["Version"]),
          "| job key:", out["reconciliation"]["Job Key"])
    print("\nline checks (rate / reality / auth -> verdict):")
    for ln in out["lines"]:
        print(f"  {ln['Description']:<24} "
              f"{ln['Rate Check']:<5} {ln['Reality Check']:<5} "
              f"{ln['Authorization Check']:<5} -> {ln['Verdict']}")

    assert out["status"] == "Flagged", out["status"]
    assert out["exceptions"] == 2, out["exceptions"]
    assert out["value_queried"] == 242, out["value_queried"]
    assert out["coverage"] == ["Price", "Reality", "Authorization", "Internal"], out["coverage"]
    v = {ln["Description"]: ln for ln in out["lines"]}
    assert v["Labour - HVAC Engineer"]["Reality Check"] == "Flag"
    assert v["Labour - HVAC Engineer"]["Authorization Check"] == "Flag"
    assert v["Labour - HVAC Engineer"]["Verdict"] == "Query"
    assert v["Compressor capacitor"]["Verdict"] == "Pass"
    assert v["Additional sundries"]["Rate Check"] == "Flag"
    assert v["Additional sundries"]["Verdict"] == "Query"
    assert len(out["write_plan"]) == 1 + 5 + 1  # recon + 5 lines + 1 event
    print("\nREC-0001 reproduced. Write-plan valid (", len(out["write_plan"]), "ops ).")


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1 and sys.argv[1] not in ("--selftest", "-t"):
        with open(sys.argv[1]) as _fh:
            _result = reconcile(json.load(_fh))
        print(json.dumps(_result, indent=2, default=str))
    else:
        _selftest()
