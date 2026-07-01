"""
build_writes.py (rate-card)  -  ONE command that turns a confirmed submission + a base
                                dump into ready-to-send Airtable writes, so the model
                                never hand-maps field ids.

USAGE
-----
    python build_writes.py SUBMISSION.json TABLES.json BASEID [OUT.json]

  SUBMISSION.json - the human-CONFIRMED rate-card submission (see write_rates.py header).
  TABLES.json     - the raw result of the Airtable `list_tables_for_base` tool, saved to a file.
  BASEID          - the base id (from `list_bases`), e.g. appXXXXXXXXXXXXXX.
  OUT.json        - optional; default writes.json beside SUBMISSION.

WHAT IT DOES
  1. Runs write_rates.py (validates the confirmed lines) -> write-plan + a skipped list.
  2. Builds field/table id maps from TABLES.json and runs to_connector.py -> id-keyed calls.
  3. Writes the calls to OUT.json; prints what will be written and what was skipped.

THEN the model: only after the human has confirmed the review table, execute each call in
OUT.json (Vendor first if new, then Rate Lines) via <connector-prefix><tool>, then read back.

Pure stdlib. Exits non-zero with a clear message on a bad submission or a base missing a field.
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import write_rates       # noqa: E402
import to_connector      # noqa: E402


def build_maps(tables_dump):
    tables = tables_dump.get("tables", tables_dump) if isinstance(tables_dump, dict) else tables_dump
    if not isinstance(tables, list):
        raise ValueError("TABLES.json is not a list of tables - save the raw list_tables_for_base result.")
    table_map, field_map, link_fields = {}, {}, {}
    for t in tables:
        name, tid = t.get("name"), (t.get("id") or t.get("tableId"))
        if not name or not tid:
            continue
        table_map[name] = tid
        field_map[name] = {f.get("name"): (f.get("id") or f.get("fieldId"))
                           for f in (t.get("fields") or []) if f.get("name")}
        links = {f.get("name") for f in (t.get("fields") or [])
                 if f.get("name") and f.get("type") == "multipleRecordLinks"}
        if links:
            link_fields[name] = links
    return table_map, field_map, link_fields


def build_writes(submission, tables_dump, base_id):
    table_map, field_map, link_fields = build_maps(tables_dump)
    result = write_rates.write_rates(submission)
    calls = to_connector.to_connector_payload(result["write_plan"], field_map, table_map, link_fields)
    to_connector.with_base_id(calls, base_id)
    summary = {
        "vendor": result.get("vendor"),
        "pricing_model": result.get("pricing_model"),
        "written_count": result.get("written_count"),
        "skipped": result.get("skipped"),
        "rate_lines_table": table_map.get("Rate Lines"),
    }
    return summary, calls


def _main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    sub_path, tables_path, base_id = argv[1], argv[2], argv[3]
    out_path = argv[4] if len(argv) > 4 else os.path.join(os.path.dirname(os.path.abspath(sub_path)), "writes.json")
    try:
        submission = json.load(open(sub_path))
        tables_dump = json.load(open(tables_path))
    except Exception as e:
        print("INPUT ERROR: couldn't read the submission or tables file:", e)
        return 2
    try:
        summary, calls = build_writes(submission, tables_dump, base_id)
    except KeyError as e:
        print("BASE/SCHEMA ERROR:", e)
        print("-> the base is missing a field/table. Re-run /setup (cost-recon-setup) to build the base to spec.")
        return 3
    except Exception as e:
        print("SUBMISSION ERROR:", e)
        print("-> the submission is off-contract. Fix it (see write_rates.py header) and re-run.")
        return 4

    json.dump(calls, open(out_path, "w"), indent=1)
    print("=== RATE CARD: %s (%s) ===" % (summary["vendor"], summary["pricing_model"]))
    print("  will write   :", summary["written_count"], "rate line(s)")
    if summary["skipped"]:
        print("  SKIPPED (report to the person, do not guess):")
        for s in summary["skipped"]:
            print("    -", s.get("description", ""), "::", s.get("reason", ""))
    print("\n=== WRITES (%d connector calls) -> %s ===" % (len(calls), out_path))
    for i, c in enumerate(calls):
        print("  %2d. %-26s %-12s records=%d" % (i + 1, c["tool"], c["table"], len(c["args"]["records"])))
    print("\nNEXT (only after the human confirmed the review table):")
    print("  1. Execute each call in %s, in order, via <your-airtable-prefix><tool> with its args." % out_path)
    print("  2. Read back Rate Lines (%s) for this vendor to confirm." % summary["rate_lines_table"])
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
