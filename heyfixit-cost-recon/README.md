# HeyFixit — Cost Reconciliation

**Verify every supplier and subcontractor invoice against your contracted rates and the work
that was actually done — and stop losing time and money to manual checking.**

Part of the **[HeyFixit marketplace](https://github.com/heyfixitai/heyfixit-marketplace)** — free,
purpose-built automation plugins for facilities-management back-office teams. This is the first
plugin. Up and running in about fifteen minutes; no spreadsheets, no code.

---

## The problem: checking invoices is slow, scattered, and easy to get wrong

It's not that you *can't* check supplier and subcontractor invoices — it's that checking them
**properly is hard and time-consuming**. To verify a single invoice you have to pull together the
**rate card, the quote, the purchase order, the job sheet / service report, and the work order** —
and that data lives in different tools, spreadsheets, inboxes, and sites. It passes through several
hands with back-and-forth before anyone signs it off.

So in practice invoices get approved with a light touch — and two costs pile up:

- **Money leaks out.** Rate creep (labour, call-out, and out-of-hours rates that don't match the
  contract), out-of-scope work billed above the approved quote/PO, reality gaps (hours, parts, or
  mileage beyond what was actually done), and arithmetic or duplicate errors.
- **Admin time burns.** Hours every month spent gathering and cross-checking data across work
  orders, rate cards, POs, and job sheets — the checking itself is expensive, even when nothing's
  wrong.

This plugin attacks both: it makes the checking **easy and fast**, and it **surfaces the things
that would otherwise slip through**.

## What this plugin does

It reads an invoice (plus whatever supporting documents you have), **checks every line three
ways**, and keeps a finance-ready, audit-trailed record in your own Airtable — with a drafted
vendor query for anything that doesn't add up.

### The three checks

| Check | The question it answers | Checked against |
|---|---|---|
| **Price / Rate** | Is each line billed at the rate you actually agreed? | your loaded **rate card** (or the quote) |
| **Reality** | Were the billed hours, parts, and mileage actually done? | the **service report / job sheet** |
| **Authorization** | Is the work within what was approved? | the **quote / purchase order** (quoted jobs) |

On top of the three, it runs an **internal-consistency** check (do the line items sum to the
invoice total?) and reports **honest coverage** — it tells you exactly which checks it *could*
run and which it couldn't, so a "verified" is never a false comfort.

### What it never does

- **Never guesses a rate or a verdict.** A line that isn't on the rate card gets flagged, not
  invented.
- **Never approves payment or moves money.** There is no payment tool — it surfaces the facts; a
  human decides.
- **Never deletes.** Corrections happen by superseding with a new version; the audit trail is
  append-only.

### What you get for each invoice

- A **status** — Verified, Flagged, or Unverified (with the reason).
- The **value under query** — the disputed total, so you can pay the undisputed remainder now.
- A **drafted vendor query** — ready to copy, edit, and send.
- A **finance-ready pack** — the verified summary your finance team can act on.
- A **live dashboard** — the queue, KPIs (value under query, value verified, time saved),
  per-line drill-in, and the full audit trail.

## The value: money recovered *and* time saved

- **Recover leakage** you're paying today — rate creep, out-of-scope work, reality gaps, and
  arithmetic/duplicate errors, surfaced *before* you pay.
- **Save the admin hours** of doing it by hand — no more pulling and comparing data across work
  orders, rate cards, POs, and job sheets for every invoice. The plugin assembles and checks it
  for you, and flags what needs a human's attention.

## How it works (and why you can trust it)

Your judgement — or the model's — isn't what decides a verdict. **A bundled, deterministic engine
does.** When you reconcile: Claude reads the documents and records the facts (per-line evidence,
no maths); a tested engine applies every check and rule and produces the verdict, coverage, and
value under query; Claude writes that result to your Airtable. Same inputs, same result, every
time — so it's consistent and **runs reliably even on lighter AI models**.

Your **Airtable base is the source of truth**, not the chat — each result is written there as it's
produced. Hand over a stack of invoices and it works through them; nothing is lost if a session is
interrupted (it re-reads the base and continues). Ask it *"how does this work?"* or *"what does
flagged mean?"* any time — there's a built-in operating guide and FAQ.

## Before and after

| Today (manual) | With this plugin |
|---|---|
| Data scattered across tools, sites, and inboxes | Assembled and checked in one place |
| Invoices approved with a light touch | **Every line** checked: rate + reality + authorization |
| Rates buried in a contract PDF | Rate card loaded once, applied automatically |
| Hours pulling and cross-checking by hand | The checking is automated; you review what's flagged |
| "Looks about right" | A deterministic verdict **plus** honest coverage of what was checked |
| No record after payment | Status, line breakdown, finance pack, and audit trail per invoice |

## Get started (about fifteen minutes)

**You'll need:** the **Claude desktop app with Cowork**, and an **Airtable** account (free tier
is fine).

1. **Install** (in Claude):
   ```
   /plugin marketplace add heyfixitai/heyfixit-marketplace
   /plugin install heyfixit-cost-recon@heyfixit
   ```
2. **Connect Airtable** in Cowork and approve the access it requests. `/setup` **creates a base,
   tables, and fields** for you, so the connector needs permission to build a base — not just edit
   records. Your data stays in *your* Airtable; nothing is stored anywhere else.
3. **`/setup`** — builds your reconciliation base and asks three quick questions (who signs vendor
   queries, default currency, company name). One time.
4. **`/rate-card`** — attach a vendor's contract or rate schedule; it extracts the rates, shows a
   review table, and (once you confirm) saves them. Repeat per vendor.
5. **`/reconcile`** — attach an invoice (plus any quote, PO, or service report). It checks every
   line and writes the result to your base with a drafted query for anything flagged.
6. **`/dashboard`** — review, mark sent-to-finance / resolved, archive, edit queries, open the
   finance pack.

`/recon-status` gives a quick read-only snapshot any time.

## Your data, your control

- **Everything lives in your Airtable base** — reads and writes only your base, through your own
  connector. Nothing is sent to HeyFixit.
- **No secrets, no bundled credentials.** Airtable is authorized by you in Cowork.
- **Append-only audit.** Every change logs an attributable event; verification is immutable (an
  accepted-despite-flags override is recorded as an override, never re-labelled "verified").

## This plugin vs. the HeyFixit platform

This plugin is a **free, self-serve sample** of what HeyFixit does — one invoice at a time, in
chat, run by you, backed by your Airtable.

| This free plugin | **[HeyFixit](https://heyfixit.ai)** (managed platform) |
|---|---|
| One invoice at a time, in chat | **Always-on**, across every supplier and site, automatically |
| You run each step | An autonomous agent wired into your **CMMS + finance system** |
| Standard hourly rate cards | Also **Schedule-of-Rates / measured-term** contracts (NHF/NSR + adjustment %) |
| A review-and-manage surface | Integrated, scaled, and monitored end to end |

It's a taste of the platform, not a replacement for it. **[Book a demo](https://tally.so/r/GxxVQe)**
or visit **[heyfixit.ai](https://heyfixit.ai)**.

## License & support

Source-available under the **PolyForm Internal Use License 1.0.0** — free for your company's
**internal** facilities-management operations; you may not distribute, resell, sublicense, or
embed it in a product or hosted service. See [`LICENSE`](LICENSE). Not an open-source license.

Questions or feedback: **contact@heyfixit.ai** · **https://heyfixit.ai**
