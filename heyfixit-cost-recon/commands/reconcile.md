---
description: Reconcile a supplier/subcontractor invoice against the rate card + job docs
argument-hint: attach the invoice (+ any quote, PO, service report)
---
Run the **invoice-reconciliation** skill on the invoice I've attached (plus any quote, PO, or
service report / job sheet). Build the case from the documents, run the engine and
`build_writes.py`, write the result to my Airtable base, then tell me the verdict, what's under
query, and the drafted vendor query. You never approve payment - you flag; I decide. If I
haven't attached anything, ask me to attach the invoice.
