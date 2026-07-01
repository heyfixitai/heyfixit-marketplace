"""
build_writes.py  -  ONE command that turns a case + a base dump into ready-to-send
                    Airtable writes. This is the whole write path in a single step,
                    so the model never hand-maps field ids (a common failure on
                    smaller models).

USAGE
-----
    python build_writes.py CASE.json TABLES.json BASEID [OUT.json]

  CASE.json   - the case you built (per-line evidence; no verdicts). See reference/edge-cases.md.
  TABLES.json - the raw result of the Airtable `list_tables_for_base` tool, saved to a file.
                (shape: {"tables":[{"id","name","fields":[{"id","name"},...]},...]})
  BASEID      - the base id (from `list_bases`), e.g. appXXXXXXXXXXXXXX.
  OUT.json    - optional; where to write the connector calls (default: writes.json beside CASE).

WHAT IT DOES
------------
  1. Builds the field-name -> field-id and table-name -> table-id maps from TABLES.json.
  2. Runs reconcile.py (the engine) on the case -> validated write-plan + disposition.
  3. Runs to_connector.py -> the write-plan becomes calls keyed by fld/tbl ids,
     with the baseId injected and consecutive same-table creates batched.
  4. Writes those calls to OUT.json and prints a human summary + the read-back target.

THEN (the model does only this):
  - For each call in OUT.json, in order, invoke  <connector-prefix><call.tool>  with call.args
    (the prefix is your Airtable MCP server prefix, e.g. mcp__<server>__).
  - Re-read the Reconciliations table for the printed Recon ID to confirm it landed.

Pure stdlib. Exits non-zero with a clear message if the case is off-contract (engine
error) or the base is missing a field/table (schema drift) - never silently drops data.
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reconcile          # noqa: E402
import to_connector       # noqa: E402


def build_maps(tables_dump):
    """From a list_tables_for_base result -> (table_map, field_map, link_fields).
    link_fields[table] = {names of multipleRecordLinks fields} so the converter can
    array-wrap + typecast them. Empty on a text-FK base (then writes are unchanged)."""
    tables = tables_dump.get("tables", tables_dump) if isinstance(tables_dump, dict) else tables_dump
    if not isinstance(tables, list):
        raise ValueError("TABLES.json is not a list of tables - save the raw "
                         "list_tables_for_base result.")
    table_map, field_map, link_fields = {}, {}, {}
    for t in tables:
        name = t.get("name")
        tid = t.get("id") or t.get("tableId")
        if not name or not tid:
            continue
        table_map[name] = tid
        fm, links = {}, set()
        for f in (t.get("fields") or []):
            fn = f.get("name")
            fid = f.get("id") or f.get("fieldId")
            if fn and fid:
                fm[fn] = fid
            if fn and f.get("type") == "multipleRecordLinks":
                links.add(fn)
        field_map[name] = fm
        if links:
            link_fields[name] = links
    return table_map, field_map, link_fields


def build_writes(case, tables_dump, base_id):
    """Return (disposition_dict, calls_list). Raises on engine / schema errors."""
    table_map, field_map, link_fields = build_maps(tables_dump)
    result = reconcile.reconcile(case)                       # may raise -> bad case
    calls = to_connector.to_connector_payload(result["write_plan"], field_map, table_map, link_fields)
    to_connector.with_base_id(calls, base_id)
    rec = result.get("reconciliation", {})
    disposition = {
        "action": result.get("action"),
        "status": result.get("status"),
        "coverage": result.get("coverage"),
        "exceptions": result.get("exceptions"),
        "value_queried": result.get("value_queried"),
        "currency": (case.get("job", {}) or {}).get("currency"),
        "recon_id": rec.get("Recon ID"),
        "version": rec.get("Version"),
        "verification_summary": result.get("verification_summary"),
        "reconciliations_table": table_map.get("Reconciliations"),
    }
    return disposition, calls


def _main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    case_path, tables_path, base_id = argv[1], argv[2], argv[3]
    out_path = argv[4] if len(argv) > 4 else os.path.join(os.path.dirname(os.path.abspath(case_path)), "writes.json")

    try:
        case = json.load(open(case_path))
        tables_dump = json.load(open(tables_path))
    except Exception as e:
        print("INPUT ERROR: couldn't read the case or tables file:", e)
        return 2

    try:
        disposition, calls = build_writes(case, tables_dump, base_id)
    except KeyError as e:
        print("BASE/SCHEMA ERROR:", e)
        print("-> the base is missing a field or table the engine expects. "
              "The base is not built to spec - re-run /setup (cost-recon-setup).")
        return 3
    except Exception as e:
        print("CASE ERROR:", e)
        print("-> the case is off-contract. Fix the case (see reference/edge-cases.md) and re-run. "
              "Do NOT hand-write Airtable records.")
        return 4

    json.dump(calls, open(out_path, "w"), indent=1)

    d = disposition
    print("=== DISPOSITION (engine decided this - do not change it) ===")
    print("  action          :", d["action"])
    print("  Recon ID        :", d["recon_id"], "v" + str(d["version"]))
    print("  Status          :", d["status"])
    print("  coverage        :", ", ".join(d["coverage"] or []) or "-")
    print("  exceptions      :", d["exceptions"], "| value under query:",
          d["currency"], d["value_queried"])
    print("  summary         :", (d["verification_summary"] or "")[:160])
    print()
    print("=== WRITES (%d connector calls) -> %s ===" % (len(calls), out_path))
    for i, c in enumerate(calls):
        print("  %2d. %-26s %-18s records=%d" % (
            i + 1, c["tool"], c["table"], len(c["args"]["records"])))
    print()
    print("NEXT:")
    print("  1. For each call in %s, in order, invoke  <your-airtable-prefix><tool>" % out_path)
    print("     with that call's 'args' (tool = create_records_for_table or")
    print("     update_records_for_table; args already use fld/tbl ids + baseId).")
    print("  2. Read back the Reconciliations table (%s) for Recon ID %s to confirm it landed."
          % (d["reconciliations_table"], d["recon_id"]))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
