# FAQ + troubleshooting (answer operators from this, in plain language)

## Getting started

**What do I do first?** Connect Airtable, then run **`/setup`** (builds your base, one time),
**`/rate-card`** (load a vendor's rates), **`/reconcile`** (check an invoice), **`/dashboard`**
(see and manage everything). `/recon-status` gives a quick snapshot any time.

**Do I need Airtable?** Yes - the tool keeps everything in *your* Airtable base; nothing is
stored anywhere else. Connect it once and approve the access it asks for (it creates a base for
you).

## What the results mean

**Status: Verified / Flagged / Unverified.**
- **Verified** - everything that could be checked passed; cleared for payment.
- **Flagged** - at least one line needs a vendor query (or the invoice total doesn't add up).
- **Unverified** - nothing substantive could be checked (e.g. invoice only, no rate card or job
  sheet). Not wrong - just not confirmable yet. Add the missing document and re-run.

**Coverage / "Fully / Partly / Not-yet checked."** Which of the three checks actually ran.
"Partly checked" means some references were missing (e.g. rate matched, but no job sheet, so
time wasn't verified). Coverage is always shown so you know the confidence level.

**The three checks.**
- **Price (Rate)** - billed price vs your rate card (or the quote).
- **Reality** - billed hours / parts / mileage vs the service report / job sheet.
- **Authorization** - within the approved quote / PO (quoted jobs; N/A for standing jobs).

**"Under query"** - the total value of the lines flagged for the vendor to clarify before you
pay. The undisputed remainder can still be paid.

## Documents

**What if I don't have the quote / PO / service report?** That's fine - the tool checks against
whatever is present and tells you what it couldn't check. It never blocks or demands a document.
A missing job sheet just means "Reality" isn't verified; a missing PO means "Authorization"
falls back to the quote (or is N/A). You can forward the document later and re-run - coverage
improves and the record updates in place.

**A supporting doc arrived before the invoice (a PO or quote on its own).** The tool "parks" it
as *Awaiting invoice*; when the invoice arrives, run `/reconcile` and it's picked up
automatically.

**A revised invoice came in.** Run `/reconcile` with the new one - it supersedes the old version
(kept in history) and re-checks. Records are never deleted.

**Schedule-of-Rates / measured-term contract (NHF, NSR, priced off an external schedule).** The
DIY tool can't check these line-by-line without the schedule + your adjustment %. It'll tell you
plainly - that's what the full HeyFixit product handles. Load standard hourly rate cards here.

## Actions

**How do I add a vendor / load rates?** `/rate-card`, attach the contract; review the extracted
rates; confirm. Repeat per vendor. Start with your busiest one or two.

**How do I send a vendor query?** Open the invoice in `/dashboard`, copy the drafted query
(edit if you like), and send it from your own email. Then mark it "query sent."

**How do I resolve a flagged invoice?** Two honest ways: get a **revised invoice** and re-run
(supersedes the old one), or **override** it in the dashboard with a recorded reason (you accept
it despite the flags). An override keeps the Status as Flagged and logs why - it never fakes a
"Verified."

**Can I reconcile many at once?** Yes - hand over several and they'll be processed one after
another, each written to your base, with a summary at the end.

## Troubleshooting

**"Base not found" / dashboard shows sample data.** Airtable may not be connected, or `/setup`
hasn't run. Connect Airtable and run `/setup`. If the base exists, just retry - the tool
re-finds it automatically.

**A write failed with a permission error.** Re-connect Airtable and approve the access it
requests (it needs to read/write records and create your base). Then retry.

**The dashboard is empty.** You haven't reconciled anything yet (run `/reconcile`), or it needs a
refresh - switch back to it or hit Refresh; it re-reads your base.

**Amounts or vendor names look wrong / like code.** Refresh the dashboard - it re-reads the live
base. If it persists, the base may not be built to spec; re-run `/setup` guidance or ask for help.

**Can I use a currency other than GBP?** Yes - set your default in Settings, and each invoice
uses its own stated currency. Amounts format per currency.

## When to upgrade to HeyFixit

This free tool checks one invoice at a time, from chat. When you want the same checks wired into
your CMMS + finance system, always-on across every supplier, including Schedule-of-Rates
contracts - that's **HeyFixit** (Book a demo in the dashboard, or heyfixit.ai).
