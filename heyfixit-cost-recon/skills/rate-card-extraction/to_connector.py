"""
to_connector.py  -  translate the engine's validated write-plan into Airtable
                    connector calls keyed by table/field IDs.

WHY THIS EXISTS
---------------
The Airtable MCP connector is FIELD-ID based: a write must address the table by
its `tbl...` id and every field by its `fld...` id. `reconcile.py` (and
`write_rates.py`) deliberately emit the write-plan in human field *names* so the
engine stays base-agnostic - every lead's base has different random ids. This
module is the deterministic bridge: name-keyed plan  ->  id-keyed connector calls.

Pure stdlib. No Airtable calls here - the agent/skill fetches the id maps once via
`list_tables_for_base` and passes them in, then sends each returned call with the
connector's create_records_for_table / update_records_for_table.

CONTRACT
--------
to_connector_payload(write_plan, field_map, table_map, batch=True) -> [call, ...]

  write_plan : list of ops from reconcile.reconcile(...)["write_plan"], each:
                 {"op":"create","table":<name>,"record":{<fieldName>:value,...}}
                 {"op":"update","table":<name>,"record_id":<recId>,
                  "record":{...}, "current_stage":<ignored here>}
  field_map  : {<tableName>: {<fieldName>: "fld..."}}   (from list_tables_for_base)
  table_map  : {<tableName>: "tbl..."}                  (from list_tables_for_base)

  returns a list of calls, in plan order, each:
    {"op":"create","table":<name>,"tableId":"tbl...","tool":"create_records_for_table",
     "args":{"baseId":<set by caller>,"tableId":"tbl...","records":[{"fields":{fld:val}}]}}
    {"op":"update", ... "tool":"update_records_for_table",
     "args":{..., "records":[{"id":"rec...","fields":{fld:val}}]}}

  - Consecutive create ops on the SAME table are merged into one call (records[]),
    preserving order, so 5 line items = 1 connector call.
  - Values pass through verbatim: the engine already emits connector-valid values
    (single-select = option name string, multi-select = list of names, numbers as
    numbers, links-as-text as strings). None values are skipped.
  - Unknown table or field raises KeyError (fail loud on schema drift) - never
    silently drop data.

The caller injects "baseId" into each call's args (one base per run).
"""


def _map_fields(table, record, field_map, link_fields=None):
    fmap = field_map.get(table)
    if fmap is None:
        raise KeyError("No field map for table %r (have: %s)"
                       % (table, ", ".join(sorted(field_map)) or "none"))
    links = (link_fields or {}).get(table) or set()
    out = {}
    for name, value in record.items():
        if value is None:
            continue
        fid = fmap.get(name)
        if not fid:
            raise KeyError("No field id for %r.%r - is the base built to spec?"
                           % (table, name))
        # On a RELATIONAL base, a link field wants an array of the linked record's
        # primary value(s); with typecast:true Airtable resolves it to the real
        # record. The engine emits the primary value as a plain string, so wrap it.
        if name in links and not isinstance(value, list):
            value = [value]
        out[fid] = value
    return out


def to_connector_payload(write_plan, field_map, table_map, link_fields=None, batch=True):
    """`link_fields` = {tableName: {linkFieldName, ...}} (from the base's field types).
    When a table has link fields, its values are wrapped as arrays and the call is
    marked typecast:true. Omit link_fields (or pass empty) for a text-FK base -
    behaviour is then identical to before (backward compatible)."""
    calls = []
    for op in write_plan:
        kind = op.get("op")
        table = op.get("table")
        tid = table_map.get(table)
        if not tid:
            raise KeyError("No table id for %r - is the base built to spec?" % (table,))
        fields = _map_fields(table, op.get("record", {}), field_map, link_fields)
        has_links = bool(link_fields and link_fields.get(table))

        if kind == "create":
            if (batch and calls and calls[-1]["op"] == "create"
                    and calls[-1]["tableId"] == tid):
                calls[-1]["args"]["records"].append({"fields": fields})
                continue
            args = {"tableId": tid, "records": [{"fields": fields}]}
            if has_links:
                args["typecast"] = True
            calls.append({"op": "create", "table": table, "tableId": tid,
                          "tool": "create_records_for_table", "args": args})
        elif kind == "update":
            rid = op.get("record_id")
            if not rid:
                raise ValueError("update op for %r has no record_id" % (table,))
            args = {"tableId": tid, "records": [{"id": rid, "fields": fields}]}
            if has_links:
                args["typecast"] = True
            calls.append({"op": "update", "table": table, "tableId": tid,
                          "tool": "update_records_for_table", "args": args})
        else:
            raise ValueError("Unknown op %r" % (kind,))
    return calls


def with_base_id(calls, base_id):
    """Inject baseId into every call's args (one base per run). Returns calls."""
    for c in calls:
        c["args"]["baseId"] = base_id
    return calls


# ---------------------------------------------------------------------------
#  Self-test:  python to_connector.py   (reproduces REC-0001's plan, maps it)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    try:
        import reconcile as R
    except ModuleNotFoundError:
        print("self-test skipped: reconcile.py is not a sibling in this skill folder "
              "(it lives in invoice-reconciliation; the rate-card copy shares this "
              "converter but not the engine). The runtime path is unaffected.")
        raise SystemExit(0)

    # A small real plan to map (offline, no Airtable).
    case = {
        "job": {"vendor": "Apex", "job_wo_ref": "WO-1", "job_type": "Quoted",
                "currency": "GBP", "invoice_no": "INV-1", "invoice_date": "2026-06-12",
                "invoice_total": 100, "documents_present": ["INV", "QT", "PO"],
                "has_price_reference": True, "has_reality": False,
                "has_authorization_reference": True, "authorization_basis": "po",
                "po_total": 100, "quote_total": 100},
        "lines": [
            {"description": "Labour", "qty": 1, "unit_price": 100, "amount": 100,
             "rate": {"applicable": True, "expected_rate": 100, "basis": "rate_card"},
             "reality": {"evidenced_qty": None, "on_report": None},
             "authorization": {"in_scope": True, "authorized_amount": None}},
        ],
        "existing": [], "vendor_exists": True, "recon_seq": 1,
        "actor": "Reconciliation agent", "now": "2026-06-12T10:00:00Z",
    }
    plan = R.reconcile(case)["write_plan"]

    # Fake maps: assign synthetic fld/tbl ids per distinct name seen in the plan.
    table_map, field_map = {}, {}
    for op in plan:
        t = op["table"]
        table_map.setdefault(t, "tbl" + str(abs(hash(t)) % 10**14).rjust(14, "0"))
        fm = field_map.setdefault(t, {})
        for name in op["record"]:
            fm.setdefault(name, "fld" + str(abs(hash((t, name))) % 10**14).rjust(14, "0"))

    calls = to_connector_payload(plan, field_map, table_map)
    with_base_id(calls, "appTESTTESTTEST01")

    assert all(k["args"]["tableId"].startswith("tbl") for k in calls)
    for k in calls:
        for rec in k["args"]["records"]:
            assert all(f.startswith("fld") for f in rec["fields"]), rec
            assert "baseId" in k["args"]
    # batching: the single Reconciliations create + 1 line create + 1 event create
    print("plan ops:", len(plan), "-> connector calls:", len(calls))
    print(json.dumps(calls, indent=1)[:900])

    # fail-loud checks
    try:
        to_connector_payload([{"op": "create", "table": "Nope", "record": {}}],
                             field_map, table_map)
        raise SystemExit("FAIL: unknown table did not raise")
    except KeyError:
        pass
    try:
        bad = [{"op": "create", "table": plan[0]["table"], "record": {"Ghost Field": 1}}]
        to_connector_payload(bad, field_map, table_map)
        raise SystemExit("FAIL: unknown field did not raise")
    except KeyError:
        pass
    print("to_connector self-test OK")
