# Demo Setup card (MCP Apps connector)

A small MCP server whose one model-visible tool, `demoSetup`, renders an interactive card inside Claude Desktop or claude.ai. The card shows the four environment bindings the LOS demo confirms once per session (Box enterprise ID, Credit Policy Hub ID, Doc Gen commitment-letter template ID, signer email), lets the operator edit them, and posts the confirmation into the chat as the operator's message. That gives the Claude Desktop demo the same clickable Demo Setup step as the Amazon Quick agent without touching the Salesforce-hosted `LOSLoanTools` server, which cannot serve MCP Apps UI resources.

It holds no credentials, calls neither Box nor Salesforce, and never offers a loan write. Loan ID and loan folder ID are not bindings; the presenter skill resolves them from the live record.

## How it works

- `demoSetup` (model-visible) returns the defaults and, if there is one, the confirmation already made in this process. Its `_meta.ui.resourceUri` points at `ui://los-demo-setup/card.html`, so an MCP Apps host renders the card.
- `confirmDemoSetup` (app-only, hidden from the model) validates the values the card submits: numeric Box IDs, a well-formed email.
- The card then calls `sendMessage` so "Demo Setup confirmed: ..." appears as the operator's chat message, which is exactly what the skill caches after a typed reply. If the host refuses chat messages it falls back to `updateModelContext`, and failing that it shows the sentence to paste.

## Defaults

Defaults come from the same gitignored file the Quick skill uses, `config/runtime/quick-demo-defaults.json` (copy the `.example.json` next to it), named through `LOS_DEMO_DEFAULTS_FILE`. Each `LOS_DEMO_*` variable overrides one key:

| Key | Variable |
|---|---|
| `boxEnterpriseId` | `LOS_DEMO_BOX_ENTERPRISE_ID` |
| `creditPolicyHubId` | `LOS_DEMO_POLICY_HUB_ID` |
| `docgenCommitmentLetterTemplateId` | `LOS_DEMO_DOCGEN_TEMPLATE_ID` |
| `signerEmail` | `LOS_DEMO_SIGNER_EMAIL` |

Anything unset shows blank on the card and must be typed before confirming.

## Build and test

```bash
cd connectors/demo-setup-card
npm ci
npm run build   # typechecks, compiles the server, bundles the card into dist/mcp-app.html
npm test        # vitest: bindings, tool metadata, resource, confirmation flow
```

`python3 scripts/validate_los.py` runs the same build and tests when `node_modules` is present.

## Run

**Remote connector (presenters).** Serve Streamable HTTP and put it behind HTTPS:

```bash
LOS_DEMO_DEFAULTS_FILE=../../config/runtime/quick-demo-defaults.json PORT=3001 npm run start:http
```

Presenters add `https://<host>/mcp` as a custom connector named `LOS Demo Setup` with no OAuth fields ([docs/CLIENT-SETUP.md](../../docs/CLIENT-SETUP.md)). The server is stateless per request; the last confirmation is remembered per process only, which is enough for one presenter and is not shared state to rely on.

**Local (maintainers).** Add a stdio entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "los-demo-setup": {
      "command": "node",
      "args": ["<repo>/connectors/demo-setup-card/dist/server/main.js", "--stdio"],
      "env": { "LOS_DEMO_DEFAULTS_FILE": "<repo>/config/runtime/quick-demo-defaults.json" }
    }
  }
}
```

Then type `Demo Setup` in a new chat.

## Governance

The card is the only decision card in the demo, and it confirms environment bindings only. The presenter skill keeps every write typed: `applyLoanTerms` runs only on a typed request containing "confirm", and generation and signature run only on a typed request. Do not add buttons that apply terms, approve documents, generate documents, or send for signature.

## Not verified here

The server, tools, resource, and confirmation flow are covered by tests over an in-memory transport. Rendering inside Claude Desktop and the `sendMessage` path depend on the host's MCP Apps support and were not exercised in the repository environment; the fallbacks exist for hosts that refuse chat messages.
