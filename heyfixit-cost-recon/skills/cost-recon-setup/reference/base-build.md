# Base build recipe (verbatim payloads)

The `cost-recon-setup` skill builds the relational base by executing these EXACT
payloads. Do not improvise the schema - copy them. (This is the recipe validated live
when the reference base was built.)

**Contents:** Step 1 - `create_base` (6 tables, all non-link fields) . Step 2 - add the 4 `multipleRecordLinks` fields . Step 3 - write the one Settings row . Step 4 - confirm.

## Step 1 - create the base (6 tables, all non-link fields)

Get `<WORKSPACE_ID>` from `list_workspaces`, then call **`create_base`** with:

```json
{
  "workspaceId": "<WORKSPACE_ID from list_workspaces>",
  "name": "Cost Reconciliation",
  "tables": [
    {
      "name": "Vendors",
      "fields": [
        {
          "name": "Vendor Name",
          "type": "singleLineText"
        }
      ]
    },
    {
      "name": "Rate Lines",
      "fields": [
        {
          "name": "Description / Trade",
          "type": "singleLineText"
        },
        {
          "name": "Rate Type",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Labour"
              },
              {
                "name": "Call-out"
              },
              {
                "name": "Travel"
              },
              {
                "name": "Materials markup"
              },
              {
                "name": "Specialist markup"
              },
              {
                "name": "Plant hire"
              },
              {
                "name": "SOR task"
              },
              {
                "name": "Minimum charge"
              },
              {
                "name": "Other"
              }
            ]
          }
        },
        {
          "name": "Band",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Normal"
              },
              {
                "name": "OOH"
              },
              {
                "name": "Saturday"
              },
              {
                "name": "Sunday / Bank Hol"
              },
              {
                "name": "Emergency"
              }
            ]
          }
        },
        {
          "name": "Unit",
          "type": "singleLineText"
        },
        {
          "name": "Rate",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Min Units",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Conditions",
          "type": "multilineText"
        },
        {
          "name": "Effective From",
          "type": "date",
          "options": {
            "dateFormat": {
              "name": "iso"
            }
          }
        }
      ]
    },
    {
      "name": "Reconciliations",
      "fields": [
        {
          "name": "Recon ID",
          "type": "singleLineText"
        },
        {
          "name": "Stage",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Awaiting invoice"
              },
              {
                "name": "New"
              },
              {
                "name": "Queried"
              },
              {
                "name": "Re-run complete"
              },
              {
                "name": "Sent to finance"
              },
              {
                "name": "Resolved"
              },
              {
                "name": "Superseded"
              },
              {
                "name": "Archived"
              }
            ]
          }
        },
        {
          "name": "Version",
          "type": "number",
          "options": {
            "precision": 0
          }
        },
        {
          "name": "Job Key",
          "type": "singleLineText"
        },
        {
          "name": "Job / WO Ref",
          "type": "singleLineText"
        },
        {
          "name": "Job Type",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Quoted"
              },
              {
                "name": "Standing"
              }
            ]
          }
        },
        {
          "name": "Invoice No",
          "type": "singleLineText"
        },
        {
          "name": "Invoice Date",
          "type": "date",
          "options": {
            "dateFormat": {
              "name": "iso"
            }
          }
        },
        {
          "name": "Invoice Total",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Currency",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "GBP"
              },
              {
                "name": "EUR"
              },
              {
                "name": "USD"
              },
              {
                "name": "AUD"
              },
              {
                "name": "CAD"
              },
              {
                "name": "INR"
              },
              {
                "name": "JPY"
              },
              {
                "name": "CHF"
              },
              {
                "name": "AED"
              },
              {
                "name": "ZAR"
              },
              {
                "name": "SGD"
              },
              {
                "name": "NZD"
              }
            ]
          }
        },
        {
          "name": "Docs Present",
          "type": "singleLineText"
        },
        {
          "name": "Coverage",
          "type": "multipleSelects",
          "options": {
            "choices": [
              {
                "name": "Price"
              },
              {
                "name": "Reality"
              },
              {
                "name": "Authorization"
              },
              {
                "name": "Internal"
              }
            ]
          }
        },
        {
          "name": "PO Total",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Quote Total",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Reality Hours",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Reality Materials",
          "type": "singleLineText"
        },
        {
          "name": "Status",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Verified"
              },
              {
                "name": "Flagged"
              },
              {
                "name": "Unverified"
              }
            ]
          }
        },
        {
          "name": "Exceptions",
          "type": "number",
          "options": {
            "precision": 0
          }
        },
        {
          "name": "Value Queried",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Verification Summary",
          "type": "multilineText"
        },
        {
          "name": "Vendor Query Draft",
          "type": "multilineText"
        },
        {
          "name": "Attachments",
          "type": "multipleAttachments"
        }
      ]
    },
    {
      "name": "Line Items",
      "fields": [
        {
          "name": "Description",
          "type": "singleLineText"
        },
        {
          "name": "Qty / Hours",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Unit Price",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Amount",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Expected Rate",
          "type": "number",
          "options": {
            "precision": 2
          }
        },
        {
          "name": "Rate Check",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Pass"
              },
              {
                "name": "Flag"
              },
              {
                "name": "N/A"
              },
              {
                "name": "Unverified"
              }
            ]
          }
        },
        {
          "name": "Reality Check",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Pass"
              },
              {
                "name": "Flag"
              },
              {
                "name": "N/A"
              },
              {
                "name": "Unverified"
              }
            ]
          }
        },
        {
          "name": "Authorization Check",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Pass"
              },
              {
                "name": "Flag"
              },
              {
                "name": "N/A"
              },
              {
                "name": "Unverified"
              }
            ]
          }
        },
        {
          "name": "Verdict",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Pass"
              },
              {
                "name": "Query"
              },
              {
                "name": "Unverified"
              }
            ]
          }
        },
        {
          "name": "Flag Reason",
          "type": "singleLineText"
        }
      ]
    },
    {
      "name": "Events",
      "fields": [
        {
          "name": "Event",
          "type": "singleLineText"
        },
        {
          "name": "Type",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "Created"
              },
              {
                "name": "Document added"
              },
              {
                "name": "Re-run"
              },
              {
                "name": "Superseded"
              },
              {
                "name": "Promoted"
              },
              {
                "name": "Parked"
              },
              {
                "name": "Queried"
              },
              {
                "name": "Sent to finance"
              },
              {
                "name": "Resolved"
              },
              {
                "name": "Re-opened"
              },
              {
                "name": "Archived"
              },
              {
                "name": "Restored"
              }
            ]
          }
        },
        {
          "name": "Detail",
          "type": "multilineText"
        },
        {
          "name": "Actor",
          "type": "singleLineText"
        },
        {
          "name": "At",
          "type": "dateTime",
          "options": {
            "dateFormat": {
              "name": "iso"
            },
            "timeFormat": {
              "name": "24hour"
            },
            "timeZone": "Europe/London"
          }
        }
      ]
    },
    {
      "name": "Settings",
      "fields": [
        {
          "name": "Operator Name",
          "type": "singleLineText"
        },
        {
          "name": "Default Currency",
          "type": "singleSelect",
          "options": {
            "choices": [
              {
                "name": "GBP"
              },
              {
                "name": "EUR"
              },
              {
                "name": "USD"
              },
              {
                "name": "AUD"
              },
              {
                "name": "CAD"
              },
              {
                "name": "INR"
              },
              {
                "name": "JPY"
              },
              {
                "name": "CHF"
              },
              {
                "name": "AED"
              },
              {
                "name": "ZAR"
              },
              {
                "name": "SGD"
              },
              {
                "name": "NZD"
              }
            ]
          }
        },
        {
          "name": "Company",
          "type": "singleLineText"
        }
      ]
    }
  ]
}
```

The first field of each table is its primary field (all primary-eligible types). Link fields are added in step 2 (they need the target table's id, which doesn't exist yet).

## Step 2 - add the 4 real link fields (`multipleRecordLinks`)

Call `list_tables_for_base` on the new base to get the **table ids**, then call **`create_field`** four times - fill each `linkedTableId` from that list:

- on **Reconciliations** (`baseId`=new base, `tableId`=the **Reconciliations** table id):

```json
{
  "name": "Vendor",
  "type": "multipleRecordLinks",
  "options": {
    "linkedTableId": "<Vendors table id>"
  }
}
```

- on **Rate Lines** (`baseId`=new base, `tableId`=the **Rate Lines** table id):

```json
{
  "name": "Vendor",
  "type": "multipleRecordLinks",
  "options": {
    "linkedTableId": "<Vendors table id>"
  }
}
```

- on **Line Items** (`baseId`=new base, `tableId`=the **Line Items** table id):

```json
{
  "name": "Reconciliation",
  "type": "multipleRecordLinks",
  "options": {
    "linkedTableId": "<Reconciliations table id>"
  }
}
```

- on **Events** (`baseId`=new base, `tableId`=the **Events** table id):

```json
{
  "name": "Recon Ref",
  "type": "multipleRecordLinks",
  "options": {
    "linkedTableId": "<Reconciliations table id>"
  }
}
```

`linkedTableId` targets: Reconciliations.Vendor + Rate Lines.Vendor -> the **Vendors** table id; Line Items.Reconciliation + Events.Recon Ref -> the **Reconciliations** table id. (Airtable auto-creates the reverse link fields - ignore them.)

## Step 3 - one Settings row

`create_records_for_table` on **Settings** with the operator's answers:

```json
{
  "records": [
    {
      "fields": {
        "Operator Name": "<who signs vendor queries, e.g. Jane Smith, Accounts Payable>",
        "Default Currency": "<GBP|EUR|USD|...>",
        "Company": "<company name>"
      }
    }
  ]
}
```

(Use field-ID keys - resolve names->ids from step-2's `list_tables_for_base`, exactly like the reconcile/rate-card skills do. Default Currency + the option must be one of the 12 ISO codes.)

## Step 4 - confirm

`list_tables_for_base` again; verify all 6 tables exist and Line Items.Reconciliation + the 3 other refs are type `multipleRecordLinks`. The base is now ready for `/rate-card`, `/reconcile`, and `/dashboard`.
