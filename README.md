<!--
  Repo-root README = the GitHub landing page for the HeyFixit marketplace + SEO/authority asset.
  Human-facing documentation only. The agent never loads it at runtime — plugin behavior lives in
  each plugin's skills + commands. Describe here; never put operating directives.
-->

# HeyFixit — AI for the facilities-management back office

**HeyFixit is an AI platform that runs the facilities-management back office end to end — from
help-desk request to reconciled invoice — across the systems you already use.**

What that means for your team:

- **Complete, accurate records.** Every job, cost, and approval is captured and cross-checked, so
  your decisions rest on data you can trust — not half-filled tickets and scattered email threads.
- **No more manual data entry.** The admin of gathering, chasing, formatting, and reconciling is
  automated. Your team spends its time on judgment, not keystrokes.
- **Everyone met where they already are.** Engineers, contractors, tenants, and approvers act in
  the channels they already use — WhatsApp, email, a one-tap link — so nobody has to log into a
  new tool or change how they work.
- **Silos removed.** One live picture across ticketing, CMMS/CAFM, and finance/ERP, instead of
  people copying data between disconnected systems.
- **Nothing falls through the cracks.** Every request, clock, and follow-up is tracked to
  conclusion, with a full audit trail.

The principle throughout: **judgment stays human, the admin goes to the agents.** HeyFixit never
makes the money, safety, or liability calls, and never processes payments — it does the work
around the decisions so your people can decide faster. Managed, integrated, and always-on across
your estate.

**[See the platform → heyfixit.ai](https://heyfixit.ai)** · **[Book a demo](https://tally.so/r/GxxVQe)**

---

## What this repository is

A growing set of **free, plug-and-play plugins** for facilities-management teams — our way of
giving back to the FM community.

It's a **zero-commitment way to try AI on the specific, painful, manual tasks** in your back
office: no enterprise rollout, no software to deploy, no need to adopt HeyFixit or any platform.
Install a plugin, connect **your own** Airtable, and automate one task today — on your existing
Claude subscription and a free Airtable account.

Each plugin is purpose-built for FM (it already speaks rate cards, POs, job sheets, and work
orders), and each is a small, self-serve **taste** of what the full HeyFixit platform does end to
end — genuinely useful on its own, and a way to see the value before you ever talk to us.

## How it works

1. **Add the marketplace** and **install a plugin** (in the Claude desktop app, Cowork):
   ```
   /plugin marketplace add heyfixitai/heyfixit-marketplace
   /plugin install heyfixit-cost-recon@heyfixit
   ```
2. **Connect Airtable** and approve the access it requests.
3. **Run it** — the plugin sets up what it needs and walks you through the workflow.

Free, self-contained, and backed by your own Airtable. Your data never leaves your account.

## The plugins

### Available now

**🧾 Cost Reconciliation** — verify supplier and subcontractor invoices against your contracted
rates and the work that was actually done.

Checking invoices properly is slow and error-prone because the data is scattered — rate cards,
quotes, POs, job sheets, and work orders across different tools, sites, and inboxes, passing
through many hands. This plugin pulls it together, checks **every line** (price vs your rate card,
reality vs the job sheet, authorization vs the quote/PO), flags what's off with a drafted vendor
query, and keeps a finance-ready, audit-trailed record. You **recover leakage** (rate creep,
out-of-scope work, reality gaps, arithmetic errors) *and* **win back the admin hours** of doing it
by hand.

→ **Full details, install, and setup: [`heyfixit-cost-recon/`](heyfixit-cost-recon/README.md)**

### On the roadmap

More of the FM back office, delivered the same way — free, purpose-built plugins:

- **Help-desk & work-order coordination**
- **Quotations & purchase-order management**
- **Supplier management**

*(In development — not yet available. Watch this repo or reach out to be an early tester.)*

## Free plugins vs. the HeyFixit platform

These plugins are a **free, self-serve sample** — one task at a time, run by you, on your own
Airtable.

The **[HeyFixit platform](https://heyfixit.ai)** is the full version: the same intelligence,
**managed and integrated into the systems you already run**, always-on across every supplier and
site, handling the whole lifecycle and the harder cases — with the complete, accurate, siloed-data
outcomes above delivered continuously, not one invoice at a time. The plugins give you a real
taste of the value; the platform runs it for you at scale.

**[Book a demo](https://tally.so/r/GxxVQe)** · **[heyfixit.ai](https://heyfixit.ai)**

## Who it's for

Facilities-management and integrated-facilities-management (IFM) providers, and in-house FM teams
running facilities for their own operations — anyone whose back office is drowning in manual,
cross-tool admin.

## What's in this repository

```
heyfixit-marketplace/
├── .claude-plugin/marketplace.json     # the marketplace catalog
└── heyfixit-cost-recon/                # Plugin 1 — Cost Reconciliation
    ├── README.md                       # full plugin documentation
    ├── commands/  skills/  ...
    └── LICENSE
```

## About HeyFixit

**HeyFixit** builds the AI platform for facilities-management and IFM operators — running the
back-office lifecycle so records stay complete and accurate, data entry disappears, stakeholders
are met in their own channels, and the silos between ticketing, CMMS, and finance go away. These
free plugins are a self-serve taste of that; the managed platform is the full product.

- Website: **[heyfixit.ai](https://heyfixit.ai)**
- Deep dive on invoice reconciliation for FM: *(blog post — link coming soon)*
- Contact: **contact@heyfixit.ai**

## License

Source-available under the **[PolyForm Internal Use License 1.0.0](LICENSE)** — free to use for
your company's **internal** facilities-management operations. You may **not** distribute, resell,
sublicense, or embed these plugins in a product or a hosted/managed service. This is a
source-available license, **not** an open-source (OSI) license. © HeyFixit.

*Keywords: facilities management automation, FM / IFM back-office software, AI facilities
coordinator, invoice reconciliation, subcontractor invoice verification, rate card compliance,
accounts payable automation, help desk, purchase-order management, Claude plugins for facilities
management.*
