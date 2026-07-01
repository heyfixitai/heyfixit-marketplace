"""schema.py - the reconciliation data contract (single source of truth).

Pure Python standard library only: no third-party imports, no network, no file
or environment access. This lets it run unchanged in any skill runtime (the
managed-agent API surface has no network and no runtime pip installs). It is
imported by reconcile.py and write_rates.py.

What it defines:
  - the exact Airtable table and field names (never rename these),
  - the allowed values for every controlled field,
  - which fields are required on create,
  - which fields are immutable (and that Events are append-only),
  - the Stage state machine (legal workflow transitions),
  - verbose validators that REFUSE off-contract data with an explicit message,
  - validate_write_plan(): validates a whole write-plan so an invalid plan can
    never reach Airtable.

Design rule: the script decides and validates; the agent only executes the
validated write-plan via MCP. Nothing here performs I/O.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Tables & fields  (exact Airtable names - do not rename)
# ---------------------------------------------------------------------------

VENDORS = "Vendors"
RATE_LINES = "Rate Lines"
RECONCILIATIONS = "Reconciliations"
LINE_ITEMS = "Line Items"
EVENTS = "Events"
SETTINGS = "Settings"

FIELDS = {
    VENDORS: [
        "Vendor Name",
    ],
    RATE_LINES: [
        "Vendor", "Rate Type", "Description / Trade", "Band", "Unit",
        "Rate", "Min Units", "Conditions", "Effective From",
    ],
    RECONCILIATIONS: [
        "Recon ID", "Stage", "Version", "Job Key", "Job / WO Ref", "Vendor",
        "Job Type", "Invoice No", "Invoice Date", "Invoice Total", "Currency",
        "Docs Present", "Coverage", "PO Total", "Quote Total", "Reality Hours",
        "Reality Materials", "Status", "Exceptions", "Value Queried",
        "Verification Summary", "Vendor Query Draft", "Attachments",
    ],
    LINE_ITEMS: [
        "Reconciliation", "Description", "Qty / Hours", "Unit Price", "Amount",
        "Expected Rate", "Rate Check", "Reality Check", "Authorization Check",
        "Verdict", "Flag Reason",
    ],
    EVENTS: [
        "Event", "Recon Ref", "Type", "Detail", "Actor", "At",
    ],
    SETTINGS: [
        "Default Currency", "Operator Name", "Company",
    ],
}

# ---------------------------------------------------------------------------
# 2. Controlled vocabularies (allowed values)
# ---------------------------------------------------------------------------

# Reconciliations.Status - the VERIFICATION result (what we found).
STATUS = ["Verified", "Flagged", "Unverified"]

# Reconciliations.Stage - the WORKFLOW state (where it is in the lifecycle).
STAGE = [
    "Awaiting invoice",   # parked stub: a supporting doc arrived before its invoice
    "New",                # freshly reconciled, awaiting human action
    "Queried",            # a vendor query has been raised
    "Re-run complete",    # re-verified after a vendor response / new doc
    "Sent to finance",    # pushed to finance for payment
    "Resolved",           # closed out
    "Superseded",         # replaced by a newer version (frozen)
    "Archived",           # user-hidden (e.g. a mistaken record); kept for audit, hidden in views
]

# Reconciliations.Coverage - which checks actually ran (multi-select).
COVERAGE = ["Price", "Reality", "Authorization", "Internal"]

# Reconciliations.Job Type.
JOB_TYPE = ["Quoted", "Standing"]

# Line Items - the three per-line checks share this vocabulary.
#   Pass       = checked and consistent
#   Flag       = checked and a discrepancy was found (a human should look)
#   N/A        = the check does not apply to this line/job
#   Unverified = the check could not run (the reference document was absent)
CHECK = ["Pass", "Flag", "N/A", "Unverified"]

# Line Items.Verdict - the per-line roll-up of its checks.
#   Pass       = at least one substantive check passed and nothing flagged
#   Query      = at least one check flagged (a human should look)
#   Unverified = no substantive check could run for this line (thin coverage)
VERDICT = ["Pass", "Query", "Unverified"]

# Events.Type - the audit vocabulary (append-only log).
EVENT_TYPE = [
    "Created", "Document added", "Re-run", "Superseded", "Promoted", "Parked",
    "Queried", "Sent to finance", "Resolved", "Re-opened", "Archived", "Restored",
]

# Rate Lines.Rate Type - used when writing extracted rate cards. "Other" is the
# deliberate escape hatch so extraction never has to invent a category.
RATE_TYPE = ["Labour", "Call-out", "Travel", "Materials markup", "Specialist markup",
             "Plant hire", "SOR task", "Minimum charge", "Other"]

# Rate Lines.Band - time band for time-based lines (blank for non-time lines).
BAND = ["Normal", "OOH", "Saturday", "Sunday / Bank Hol", "Emergency"]

# Rate Lines.Unit - SUGGESTED values (the extractor maps to these). Not strictly
# enforced (human reference data); documented for the rate-card extractor.
UNIT_SUGGESTED = ["per hour", "per visit", "per day", "per mile", "per item", "%", "fixed"]

# Map of (table, field) -> allowed values for every CONTROLLED field.
# Fields not listed here are free text / numbers and are not value-checked.
ALLOWED = {
    (RECONCILIATIONS, "Status"): STATUS,
    (RECONCILIATIONS, "Stage"): STAGE,
    (RECONCILIATIONS, "Coverage"): COVERAGE,
    (RECONCILIATIONS, "Job Type"): JOB_TYPE,
    (LINE_ITEMS, "Rate Check"): CHECK,
    (LINE_ITEMS, "Reality Check"): CHECK,
    (LINE_ITEMS, "Authorization Check"): CHECK,
    (LINE_ITEMS, "Verdict"): VERDICT,
    (EVENTS, "Type"): EVENT_TYPE,
    (RATE_LINES, "Rate Type"): RATE_TYPE,
    (RATE_LINES, "Band"): BAND,
}

# Fields that hold a LIST of allowed values rather than a single one.
MULTI_SELECT = {
    (RECONCILIATIONS, "Coverage"),
}

# ---------------------------------------------------------------------------
# 3. Required-on-create fields
# ---------------------------------------------------------------------------

REQUIRED_ON_CREATE = {
    VENDORS: ["Vendor Name"],
    RATE_LINES: ["Vendor", "Rate Type", "Unit", "Rate"],
    RECONCILIATIONS: ["Recon ID", "Stage", "Version", "Job Key", "Status"],
    LINE_ITEMS: ["Reconciliation", "Verdict"],
    EVENTS: ["Recon Ref", "Type", "At"],
    SETTINGS: ["Default Currency"],
}

# ---------------------------------------------------------------------------
# 4. Immutability rules
# ---------------------------------------------------------------------------

# Fields that may NEVER appear in an update. "ALL" means the whole table is
# append-only (no field may ever be updated). Beyond this, a Reconciliation
# whose Stage == "Superseded" is frozen entirely (see assert_updatable()).
IMMUTABLE = {
    VENDORS: ["Vendor Name"],
    RATE_LINES: [],
    RECONCILIATIONS: ["Recon ID", "Version", "Job Key"],
    LINE_ITEMS: [],
    EVENTS: "ALL",
    SETTINGS: [],
}

# ---------------------------------------------------------------------------
# 5. Stage state machine (legal agent transitions)
# ---------------------------------------------------------------------------

# A transition not listed here is illegal for the agent. Re-opening a Resolved
# record is a deliberate human action performed in the dashboard, not an agent
# transition, so Resolved is terminal here.
STAGE_TRANSITIONS = {
    "Awaiting invoice": ["New", "Superseded", "Archived"],
    "New": ["Queried", "Sent to finance", "Superseded", "Archived"],
    "Queried": ["Re-run complete", "Superseded", "Archived"],
    "Re-run complete": ["Queried", "Sent to finance", "Superseded", "Archived"],
    "Sent to finance": ["Resolved", "Queried", "Superseded", "Archived"],
    "Resolved": ["Archived"],
    "Superseded": [],
    "Archived": ["New"],   # restore / unarchive back to active
}

# ---------------------------------------------------------------------------
# 6. Validators (verbose: every failure names the field and the allowed set)
# ---------------------------------------------------------------------------

VALID_OPS = ["create", "update"]


class SchemaError(ValueError):
    """Raised when data violates the contract. The message names the offending
    field and lists the allowed values so the caller can fix it precisely."""


def _fmt(values):
    return ", ".join(str(v) for v in values)


def validate_value(table, field, value):
    """Refuse an out-of-vocabulary value for a controlled field.

    No-op for free-text / numeric fields and for empty values (emptiness is a
    'required' concern, handled in validate_record)."""
    key = (table, field)
    if key not in ALLOWED:
        return True
    allowed = ALLOWED[key]
    if key in MULTI_SELECT:
        if not isinstance(value, (list, tuple)):
            raise SchemaError(
                f"{table}.{field} must be a list of values; got "
                f"{type(value).__name__} ({value!r}). Allowed: {_fmt(allowed)}.")
        bad = [v for v in value if v not in allowed]
        if bad:
            raise SchemaError(
                f"{table}.{field} contains invalid value(s) {bad}; "
                f"allowed: {_fmt(allowed)}.")
        return True
    if value is None or value == "":
        return True
    if value not in allowed:
        raise SchemaError(
            f"{table}.{field} value {value!r} is invalid; "
            f"allowed: {_fmt(allowed)}.")
    return True


def validate_fields_exist(table, record):
    """Refuse unknown table or unknown field names."""
    if table not in FIELDS:
        raise SchemaError(
            f"Unknown table {table!r}. Known tables: {_fmt(FIELDS.keys())}.")
    unknown = [f for f in record if f not in FIELDS[table]]
    if unknown:
        raise SchemaError(
            f"Unknown field(s) for {table}: {unknown}. "
            f"Valid fields: {_fmt(FIELDS[table])}.")
    return True


def assert_no_immutable(table, fields):
    """Refuse an update that touches any immutable field."""
    imm = IMMUTABLE.get(table, [])
    if imm == "ALL":
        raise SchemaError(
            f"{table} is append-only and can never be updated "
            f"(attempted fields: {fields}).")
    hit = [f for f in fields if f in imm]
    if hit:
        raise SchemaError(
            f"Cannot update immutable field(s) on {table}: {hit}. "
            f"Immutable on {table}: {_fmt(imm) if imm else '(none)'}.")
    return True


def assert_updatable(table, current_stage=None):
    """Refuse any update to a Superseded reconciliation (the whole record is
    frozen; create a new version instead)."""
    if table == RECONCILIATIONS and current_stage == "Superseded":
        raise SchemaError(
            "This reconciliation is Superseded and is frozen. Create a new "
            "version (Version + 1) instead of updating it.")
    return True


def validate_transition(old_stage, new_stage):
    """Refuse an illegal Stage transition; a same-stage no-op is allowed."""
    if old_stage not in STAGE_TRANSITIONS:
        raise SchemaError(
            f"Unknown current Stage {old_stage!r}. Known stages: {_fmt(STAGE)}.")
    if new_stage not in STAGE:
        raise SchemaError(
            f"Unknown target Stage {new_stage!r}. Known stages: {_fmt(STAGE)}.")
    if new_stage == old_stage:
        return True
    allowed = STAGE_TRANSITIONS[old_stage]
    if new_stage not in allowed:
        raise SchemaError(
            f"Illegal Stage transition {old_stage!r} -> {new_stage!r}. "
            f"From {old_stage!r} the only legal moves are: "
            f"{_fmt(allowed) if allowed else '(terminal - no transitions)'}.")
    return True


def validate_record(table, record, mode="create"):
    """Validate one record dict {field: value}.

    mode='create': check field names, controlled values, required fields.
    mode='update': check field names, controlled values, immutability."""
    if not isinstance(record, dict):
        raise SchemaError(
            f"{table} record must be a dict of field->value; got "
            f"{type(record).__name__}.")
    validate_fields_exist(table, record)
    for field, value in record.items():
        validate_value(table, field, value)
    if mode == "create":
        for req in REQUIRED_ON_CREATE.get(table, []):
            v = record.get(req)
            if v is None or v == "" or v == []:
                raise SchemaError(
                    f"{table} create is missing required field {req!r}. "
                    f"Required on create: "
                    f"{_fmt(REQUIRED_ON_CREATE.get(table, []))}.")
    elif mode == "update":
        assert_no_immutable(table, list(record.keys()))
    else:
        raise SchemaError(f"mode must be 'create' or 'update'; got {mode!r}.")
    return True


def validate_write_plan(plan):
    """Validate a whole write-plan (list of ops) against the contract.

    Each op is a dict:
      {"op": "create", "table": <table>, "record": {field: value, ...}}
      {"op": "update", "table": <table>, "record_id": <id>,
       "record": {field: value, ...}, "current_stage": <stage or None>}

    Raises SchemaError on the FIRST violation, so an invalid plan can never be
    executed. Returns True when the entire plan is contract-clean."""
    if not isinstance(plan, list):
        raise SchemaError(
            f"Write-plan must be a list of ops; got {type(plan).__name__}.")
    for i, op in enumerate(plan):
        at = f"write-plan op #{i}"
        if not isinstance(op, dict) or "op" not in op or "table" not in op:
            raise SchemaError(
                f"{at}: each op needs at least 'op' and 'table'; got {op!r}.")
        action, table = op["op"], op["table"]
        if action not in VALID_OPS:
            raise SchemaError(
                f"{at}: unknown op {action!r}; allowed: {_fmt(VALID_OPS)}.")
        record = op.get("record", {})
        if action == "create":
            try:
                validate_record(table, record, mode="create")
            except SchemaError as e:
                raise SchemaError(f"{at}: {e}")
        else:  # update
            if not op.get("record_id"):
                raise SchemaError(
                    f"{at}: an update on {table} requires 'record_id'.")
            try:
                assert_updatable(table, op.get("current_stage"))
                validate_record(table, record, mode="update")
                if "Stage" in record and op.get("current_stage") is not None:
                    validate_transition(op["current_stage"], record["Stage"])
            except SchemaError as e:
                raise SchemaError(f"{at}: {e}")
    return True


# ---------------------------------------------------------------------------
# 7. Self-test (run `python schema.py` to sanity-check the contract)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ok = 0

    def expect_ok(fn, label):
        global ok
        fn()
        ok += 1
        print(f"  ok: {label}")

    def expect_fail(fn, label):
        global ok
        try:
            fn()
        except SchemaError:
            ok += 1
            print(f"  ok (refused): {label}")
        else:
            raise AssertionError(f"expected SchemaError but passed: {label}")

    print("schema.py self-test")

    expect_ok(lambda: validate_record(RECONCILIATIONS, {
        "Recon ID": "REC-0001", "Stage": "New", "Version": 1,
        "Job Key": "acme|wo-1|inv-1", "Status": "Flagged",
        "Coverage": ["Price", "Reality"]}, "create"),
        "valid Reconciliation create")

    expect_fail(lambda: validate_record(RECONCILIATIONS, {
        "Recon ID": "REC-0002", "Stage": "Newish", "Version": 1,
        "Job Key": "k", "Status": "Flagged"}, "create"),
        "bad Stage value")

    expect_fail(lambda: validate_record(RECONCILIATIONS, {
        "Recon ID": "REC-0003", "Stage": "New", "Version": 1,
        "Job Key": "k", "Status": "Flagged",
        "Coverage": "Price"}, "create"),
        "Coverage not a list")

    expect_fail(lambda: validate_record(RECONCILIATIONS,
        {"Version": 2}, "update"),
        "update touches immutable Version")

    expect_fail(lambda: validate_record(EVENTS,
        {"Detail": "x"}, "update"),
        "Events are append-only")

    expect_ok(lambda: validate_transition("New", "Queried"),
        "legal transition New -> Queried")
    expect_fail(lambda: validate_transition("Resolved", "New"),
        "illegal transition out of Resolved")
    expect_fail(lambda: assert_updatable(RECONCILIATIONS, "Superseded"),
        "Superseded record is frozen")

    expect_ok(lambda: validate_write_plan([
        {"op": "create", "table": VENDORS, "record": {"Vendor Name": "Acme"}},
        {"op": "create", "table": RECONCILIATIONS, "record": {
            "Recon ID": "REC-0001", "Stage": "New", "Version": 1,
            "Job Key": "acme|wo-1|inv-1", "Status": "Verified",
            "Coverage": ["Price"]}},
        {"op": "update", "table": RECONCILIATIONS, "record_id": "rec123",
         "record": {"Stage": "Superseded"}, "current_stage": "New"},
    ]), "valid mixed write-plan")

    print(f"\nAll {ok} checks passed.")
