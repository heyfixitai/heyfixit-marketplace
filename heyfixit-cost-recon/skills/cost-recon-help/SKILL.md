---
name: cost-recon-help
description: Operating guide + FAQ for the HeyFixit Cost Reconciliation tool - how state is kept, how to run a batch of invoices, how to resume after an interruption, how Airtable authorization works, and answers to common operator questions. Use when the user asks how the tool works, how to do something, what a term means (Flagged, coverage, under query, override), when something isn't working (base not found, permission error, missing documents), when reconciling MANY invoices at once, or when continuing a job from earlier.
---

# Cost Reconciliation - operating guide + help

How to run the tool reliably across long sessions, batches, and interruptions - and how to
answer the operator's questions. Read this whenever you're driving the tool, not just when
asked a question.

## How state is kept (read this first)

**The Airtable base is the single source of truth - not this conversation.** Every
reconciliation, its line items, its Stage, and its audit Events live in Airtable. The chat is
disposable. This has three consequences you must operate by:

1. **Never store or recall a base ID, table ID, or field ID from memory.** They are not stable
   across sessions and must never be guessed. **Always re-discover** at the start of any
   operation: `list_bases` -> for each candidate `list_tables_for_base` -> use the base whose
   tables include **Reconciliations + Line Items** with **Line Items.Reconciliation** as a
   `multipleRecordLinks` field (the relational base). Resolve field IDs from
   `list_tables_for_base` every run. `build_writes.py` does this for you when writing.
2. **Compaction / a new session loses nothing.** If your context is trimmed, re-discover the
   base and read it - the work is all there. Do not apologise for "losing track"; just re-read.
3. **Writing to Airtable IS the checkpoint.** As soon as a reconciliation is written, it's
   durable. You don't need a separate progress store.

## Reconciling a batch (proactive - don't wait to be nudged)

When the operator hands you several invoices ("reconcile these", a folder, multiple attachments):

1. **Make a task list** (one task per invoice/job) so progress is visible and survives compaction.
2. For **each** invoice, run the full `invoice-reconciliation` workflow end to end - build the
   case, run `build_writes.py`, **write the result to Airtable**, mark the task done - then move
   to the next **without waiting for the operator to say "next" or "now save it."** Completing
   the write is part of the job, not a separate step to ask permission for.
3. **Group correctly first:** if one upload contains multiple invoices/jobs, split by job
   reference and reconcile each separately (see invoice-reconciliation + edge-cases reference).
4. **At the end, summarise:** how many verified / flagged / unverified, total under query, and
   what needs the operator (queries to send, missing docs). Point them to `/dashboard`.

**Idempotent + safe to re-run:** the engine routes each invoice (new / revised->supersede /
promote a parked stub / augment in place) by Job Key, so re-processing updates in place rather
than duplicating. If you're unsure whether one was already done, it's safe to run it - or check
`/recon-status` first.

## Resuming after an interruption or compaction

Don't start over. **Re-discover the base, then read what's already there** (run the
`recon-status` summary, or list Reconciliations). Compare against the invoices in hand, and
**continue only the ones not yet done.** The audit Events show what happened and when.

## Retries + partial failures

- A single bad invoice never stops a batch: reconcile the rest, and leave a note/Event on the
  one that failed.
- If an Airtable write errors, retry that one call; if it still fails after a couple of tries,
  record an Events note describing the failure and continue - don't crash the run.
- Writes are batched (<=10 records/call) to stay within Airtable rate limits; the driver does this.

## Airtable authorization (what to do when writes fail with a permission error)

The tool works entirely through the operator's **Airtable connector**, which they authorize
once in Cowork. It needs permission to **read/write records AND create a base + fields**
(`/setup` builds the base). If a call fails with an authorization/permission error:
- Tell the operator plainly to **re-connect Airtable and approve the access it requests**
  (including creating a base), then retry. Do **not** loop retries or ask for tokens/keys.
- If `create_base` needs a workspace, use `list_workspaces` and pick one the operator can create
  bases in; if none, ask them to create/enable a workspace.

## Answering operator questions

For "how do I…", "what does X mean", "why is this flagged/under query", "it's not working",
read **[reference/faq.md](reference/faq.md)** and answer from it in plain language. For anything
about the checks/verdicts themselves, the source of truth is the invoice-reconciliation skill's
`reference/edge-cases.md`.

## Hard rules
- **Airtable is the state; re-discover, never remember IDs.**
- **Finish the write** - don't stop at "here's the verdict" and wait; persist it.
- **Never invent** a base, a rate, or a verdict; never move money; never delete (supersede/archive).

## Reference
- [reference/faq.md](reference/faq.md) - operator FAQ + troubleshooting.
