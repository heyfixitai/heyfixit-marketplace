---
description: Load a vendor's rate card into Airtable (so invoices can be checked)
argument-hint: attach the contract / rate schedule for one vendor
---
Run the **rate-card-extraction** skill on the contract / rate schedule I've attached, for ONE
vendor. Detect the pricing model, extract the rates into the controlled vocabulary, and show me
a review table plus anything uncertain. Only after I confirm, write the rates to Airtable via
`build_writes.py`. Never invent a rate - flag gaps instead.
