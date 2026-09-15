# Loan Origination Demo

Commercial loan origination demo showcasing Box + Salesforce integration with AI-powered workflows.

## What It Does

A borrower applies through the Acme Borrower Portal. Documents uploaded to Box are automatically classified by Box AI. A loan officer's AI assistant:

- Extracts loan terms from marked-up documents
- Validates terms against credit policy (stored in Box Hubs)
- Reviews borrower's loan history
- Generates commitment letters via Box Doc Gen
- Enforces governance (status checks, confirmation requirements)

**Key features:**
- Governed loan files in Box, structured records in Salesforce
- Box-confirmed signature completion closes the loan; signed letters and signing logs remain available in the borrower workspace
- Box AI for document classification and term extraction
- Credit policy validation via Box Hubs
- Headless AI integration (works with Claude Desktop, Amazon Quick, ChatGPT, Slack, Agentforce)
- Multi-connector strategy: Box MCP for Box operations, LOS tools for Salesforce governance

## Quick Start

### Prerequisites

- Box enterprise with AI, Hubs, Doc Gen, Sign, and metadata enabled
- Salesforce org with Agentforce and UI Bundles (Hyperforce required)
- Box for Salesforce package installed
- Python 3.11+, Node.js, Box CLI, Salesforce CLI

### Setup

1. **Configure:**
   ```bash
   cp .env.sample .env
   cp config/runtime/demo-environment.example.json config/runtime/demo-environment.json
   python3 scripts/setup_los_dev.py
   ```

2. **Deploy:**
   ```bash
   python3 scripts/demo_operator.py bootstrap --scenario box-salesforce-los --yes
   ./scripts/seed-los-sample-data.sh <alias>
   ./scripts/seed-los-loan-files.sh <alias>
   ```

3. **Configure Box preview, Loan Copilot, and MCP connectors**  
   Optional for Claude Desktop: run the [Demo Setup card](connectors/demo-setup-card/README.md), a third connector that confirms the session bindings on a clickable card.  
   See [docs/SETUP.md](docs/SETUP.md) for the admin steps. Presenters connect their own AI client with [docs/CLIENT-SETUP.md](docs/CLIENT-SETUP.md) (no code).

### Cleanup

Remove demo loans and their Box folders between presentations:

```bash
# Preview what would be deleted
python3 scripts/cleanup_demo.py --status Application --dry-run

# Delete all Application status loans
python3 scripts/cleanup_demo.py --status Application --yes

# Delete loans created today
python3 scripts/cleanup_demo.py --today --yes

# Delete specific loan
python3 scripts/cleanup_demo.py --loan-id LN-2026-0042 --yes

# Interactive mode (prompts for each)
python3 scripts/cleanup_demo.py --status Application --interactive
```

### Demo

**[Open the public demo guide](https://unofficialbox.github.io/box-claudeforce-loans/)** · [Download portable HTML](https://unofficialbox.github.io/box-claudeforce-loans/docs/demo-storyboard/standalone.html)

[Open the borrower portal login](https://agentforce-box.my.site.com/loansvforcesite/login)

Run the demo beats with Claude Desktop (or any AI harness):
- **Demo guide:** [Setup](docs/demo-storyboard/index.html#setup) · [Storyboard](docs/demo-storyboard/index.html#storyboard) · [Resources and sample files](docs/demo-storyboard/index.html#resources)
- **Standalone HTML:** [Portable edition](docs/demo-storyboard/standalone.html) — embedded images/fonts; resource links open GitHub. Rebuild with `python3 scripts/build_standalone_storyboard.py`.
- **Markdown storyboard:** [Tell / Show / Tell with screenshots](docs/demo-storyboard/storyboard.md)
- **Amazon Quick edition:** [demo guide](docs/demo-storyboard/index-quick.html) · [portable HTML](docs/demo-storyboard/standalone-quick.html) · [Markdown](docs/demo-storyboard/storyboard-quick.md) — same beats with Amazon Quick as the officer harness and the [Quick platform trio](docs/demo-storyboard/platform-trio-quick.svg). Rebuild everything with `python3 scripts/build_demo_trio.py --png && python3 scripts/build_demo_storyboard.py && python3 scripts/build_standalone_storyboard.py`.
- **Prompts & walkthrough:** [DEMO-CLICKPATH.md](DEMO-CLICKPATH.md)
- **Presenter skill:** [skills/loan-origination/SKILL.md](skills/loan-origination/SKILL.md) — [package for Claude](docs/DOCGEN-GUIDE.md#distributing-the-claude-skill)
- **Amazon Quick:** [skills/loan-origination-quick/SKILL.md](skills/loan-origination-quick/SKILL.md) plus the agent manifest in [config/quick/](config/quick/agent.json) — setup in [docs/SETUP.md §5b](docs/SETUP.md#5b-amazon-quick)
- **Slack (Slackbot):** [skills/loan-origination-slack/SKILL.md](skills/loan-origination-slack/SKILL.md) — a paste-in primer, since Slackbot loads no skills; app manifest in [config/slack/](config/slack/los-loan-tools.manifest.json) — setup in [docs/SETUP.md §5c](docs/SETUP.md#5c-slack-slackbot)
- **Connect your client (all harnesses):** [docs/CLIENT-SETUP.md](docs/CLIENT-SETUP.md)
- **Presenter guide:** [docs/PRESENTING.md](docs/PRESENTING.md)

## Documentation

- **[docs/SETUP.md](docs/SETUP.md)** - Complete deployment guide
- **[docs/CLIENT-SETUP.md](docs/CLIENT-SETUP.md)** - Connect Claude, Amazon Quick, Slack, or ChatGPT to the demo (for presenters)
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and governance
- **[CLAUDE.md](CLAUDE.md)** - AI connector strategy (metadata-first, Box MCP vs LOS tools)
- **[docs/SECURITY.md](docs/SECURITY.md)** - Borrower authorization and token scoping
- **[docs/paved-path.md](docs/paved-path.md)** - MCP deployment guidance

## Repository Structure

- `config/` - Box metadata templates and runtime configuration
- `scripts/` - Deployment automation and helpers
- `los-salesforce-project/` - Salesforce metadata and UI components
- `sample-data/` - Credit policy library and demo documents
- `docs/` - Setup guides and architecture documentation
