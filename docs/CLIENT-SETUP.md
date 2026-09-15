# Connect your AI client to the demo

For presenters and demo operators. No code, no terminal. Budget ten minutes per client the first time.

The demo needs two connections in whichever AI client you present from: **LOS Loan Tools** (the Salesforce side) and **Box**. Every client below ends in the same place, so check the same three things at the end of each section.

## Before you start: get three things from your admins

Ask your **Salesforce admin** for:

1. **The LOS server URL.** It looks like `https://api.salesforce.com/platform/mcp/v1/custom/LOSLoanTools` (sandboxes and scratch orgs have `sandbox/` after `v1/`).
2. **The consumer key** of the LOS Claude MCP app. You paste it wherever a client asks for an OAuth Client ID. There is no secret to paste unless the client's section below says so.

Tell the Salesforce admin which client you will use. Each client has its own callback URL that must be on the LOS app before you connect ([admin section](#for-admins)).

Ask your **Box admin** to confirm the Box MCP Server is enabled for you with the **Box AI** and **Doc Gen** tools turned on. They are off by default, and if you connected Box before they were turned on, you will need to disconnect and reconnect.

## What "connected" looks like, in every client

1. Both connections are listed and signed in.
2. LOS shows seven tools: list loans, get loan package, extract loan terms, apply loan terms, classify document, approve documents, prepare signature request.
3. This prompt returns the latest Harborview loan and shows (or links) the marked-up term sheet:

```
What's the latest loan for Harborview Logistics? Which documents in that loan are flagged critical policy risk?
```

If step 3 answers with a filename but no document, say `show me the document` once.

---

## Claude Desktop or claude.ai

**Connect LOS**

1. Open **Settings**, then **Connectors**, then **Add custom connector** (the **+** button).
2. Name: `LOS Loan Tools`. URL: the LOS server URL.
3. Open **Advanced settings**. OAuth Client ID: the consumer key. Leave the secret blank.
4. Click **Connect** and sign in to Salesforce when the browser opens.
5. Back in Connectors, open **LOS Loan Tools**, choose **Configure**, and turn all seven tools on.

**Connect Box**

1. In **Connectors**, find **Box** in the directory and click **Connect**. Sign in to Box.
2. If Box was connected before your admin turned on the Doc Gen and Box AI tools, click **Disconnect**, then **Connect** again.

**Load the presenter skill**

1. Create a Project for the demo and paste the custom instructions from DEMO-CLICKPATH check P2 into the project's instructions.
2. Add the skill: upload `skills/loan-origination/SKILL.md` (or the `.skill` archive your maintainer sends you) under **Customize**, **Skills**.
3. Start every rehearsal in a new chat inside that project with both connectors enabled under the **+** menu.

**Optional: the Demo Setup card**

The Demo Setup card is a small third connector that shows the four session bindings (Box enterprise ID, Credit Policy Hub ID, Doc Gen template ID, signer email) as a clickable card, the way Amazon Quick does, instead of a typed reply. Your maintainer runs it ([connectors/demo-setup-card](../connectors/demo-setup-card/README.md)); you only connect to it.

1. Ask your maintainer for the card URL. It ends in `/mcp`.
2. In **Connectors**, **Add custom connector**. Name: `LOS Demo Setup`. URL: the card URL. Leave the OAuth fields blank and click **Connect**.
3. In a new chat with all three connectors enabled, type `Demo Setup`. The card appears with the defaults. Change any value, then click **Use these for this session**. The confirmation shows up in the chat as your message and the skill caches it.

Without this connector, `Demo Setup` still works: the assistant shows the same four values as a table and you reply "use these defaults" or type replacements.

**If it fails**

- The LOS connector lists fewer than seven tools: it was connected before the newer tools existed. **Disconnect**, then **Connect** again with the same URL.
- Doc Gen answers "Access denied": the Box tools were turned on after you connected. Disconnect and reconnect Box.

---

## Amazon Quick (desktop)

**Connect LOS**

1. Open **Customize**, then **Connectors**, then **Create**, then **Cloud connector**, then **MCP server**.
2. Name: `Salesforce Loan Origination` (the skill expects this exact name). URL: the LOS server URL.
3. Authentication: **User authentication (OAuth)**. Client ID: the consumer key. Tick **Public OAuth client** so no secret is required.
4. Save, then click **Sign in** on the new connector and sign in to Salesforce.

**Connect Box**

1. In **Connectors**, click **Browse all**, find **Box**, click **Install**, and sign in to Box. The installed name should be `Box Agent`; if it is different, tell your maintainer so the skill's tool prefixes can be updated.

**Load the presenter skill**

1. Open **Customize**, then **Skills**, then **Create**, then **From file**. Choose `skills/loan-origination-quick/SKILL.md` or the `.skill` archive your maintainer sends you.
2. In the editor, reference the tools of **both** connectors. Without this, Quick runs the demo on one connector and never loads the other.
3. Fill the four placeholders in the **Demo Setup** table (Box enterprise ID, Credit Policy Hub ID, Doc Gen template ID, signer email). Your maintainer has them in the environment's runtime defaults file.
4. Click **Publish**. Open the skill panel and confirm the first line reads the current `Skill revision`.

**Create the agent**

1. Open **Customize**, then **Agents**, then **Create**. Paste `config/quick/instructions.md` into **Instructions**.
2. On **Capabilities**: attach both connectors, limit **Skills** to `Loan Origination (Amazon Quick)`, turn **Web search** off. Click **Publish**.
3. On **Connectors**, open **Manage permissions** for each connector and leave `applyLoanTerms`, `approveDocuments`, `prepareSignatureRequest`, and `create_docgen_batch` at **Ask Each Time**.

**Before each show**

1. Start a new chat with the agent and send `Demo Setup`. Confirm the four bindings.

**If it fails**

- The agent will not publish and mentions a malformed wrapper ARN: discard the draft and attach the connector again from scratch. Detaching and re-adding does not fix it. If it happens twice, create a new agent.
- The first prompt answers with extracted terms and no document preview: the old skill is still loaded. Re-import the file and Publish.
- A stage stops after 60 seconds: the call may still have finished. Do not repeat it; the skill re-checks before any retry.

---

## Slack (Slackbot)

Slackbot has no skills and no custom instructions, so the presenter pastes a short primer at the start of each rehearsal. Tools run in a direct message with Slackbot only, not in channels, and Slack does not show Box document previews; the demo cites documents with Box links instead.

**One-time, by your Slack admin:** the `LOS Loan Tools` Slack app must be installed and approved for the workspace ([admin section](#for-admins)). Box for Slack must be installed.

**Connect LOS**

1. Open a direct message with **Slackbot**.
2. Click the **Apps** button in the message toolbar.
3. Click **+** next to **LOS Loan Tools** and sign in to Salesforce when the browser opens.

**Connect Box**

1. If you used Box for Slack before, open `https://account.box.com/app-api/slack-v2/install` once to re-authorize it with the MCP permissions.
2. In the same Slackbot direct message, click **Apps**, click **+** next to **Box**, and sign in to Box.
3. Both apps now appear under **Your apps** in the **Integrations** tab.

**Load the presenter primer**

1. Open `skills/loan-origination-slack/SKILL.md` and copy the block under **Primer**.
2. Paste it as the first message of the Slackbot direct message.
3. When Slackbot asks to allow a tool: choose **Always allow** for reads (list loans, get loan package, extract, search, Box AI, preview), and **Allow once** each time for apply, approve, Doc Gen, and signature.

**If it fails**

- `LOS Loan Tools` is not in the Apps list: the app is not installed or not approved in this workspace. Ask the Slack admin.
- "Not able to connect" or "Unexpected error" on sign-in: the LOS app is missing the Slack callback URL or the client secret. Ask the Salesforce admin.
- Slackbot lists the tools but never calls them: ask `What tools are available from LOS Loan Tools?` once, then repeat the prompt.
- You already have five apps connected: Slackbot allows five at a time. Remove one under **Your apps**.

---

## ChatGPT (not yet rehearsed)

The connection works the same way as in Claude, but nobody on this project has run the full demo from ChatGPT. Treat these steps as a starting point.

1. Open **Settings**, then **Connectors**, then **Advanced settings**, and turn on **Developer mode** (a workspace admin may have to do this).
2. In **Connectors**, click **Create**. Name: `LOS Loan Tools`. MCP Server URL: the LOS server URL. Authentication: **OAuth**, Client ID: the consumer key. Sign in to Salesforce.
3. Add **Box** from the connector directory, or create a second custom connector with URL `https://mcp.box.com` if Box is not listed. Sign in to Box.
4. In a new chat, open the **+** menu, choose **Developer mode**, and select both connectors before the first prompt.
5. Paste the primer from `skills/loan-origination-slack/SKILL.md` as the first message; it is written for clients without skills.

---

## For admins

**Salesforce admin.** In Setup, open **External Client App Manager**, then **LOS Claude MCP**, then **Settings**, then **OAuth**. Add the callback URL for each client presenters will use, one per line:

| Client | Callback URL |
|---|---|
| Claude Desktop / claude.ai | `https://claude.ai/api/mcp/auth_callback` |
| Slack (Slackbot) | `https://oauth2.slack.com/external/auth/callback` |
| Amazon Quick | The redirect URL shown in Quick's **Create connector** dialog |
| ChatGPT | The redirect URL shown in ChatGPT's **Create connector** dialog |

Then give each presenter the LOS server URL and the consumer key, assign them the `LOS_MCP_Client` permission set, and add them to the app's pre-authorized users. Full org-side steps are in [SETUP.md §5a](SETUP.md#5a-connect-an-mcp-client-to-the-los-server).

**Slack admin.** Create the `LOS Loan Tools` Slack app from [config/slack/los-loan-tools.manifest.json](../config/slack/los-loan-tools.manifest.json) at `api.slack.com/apps` (**Create New App**, **From a manifest**). Under **Features**, **MCP Servers**, open the LOS server entry and set **Auth Type** to **Manual OAuth** with: Client ID = the consumer key, Client Secret = the consumer secret from the same Salesforce OAuth page, Authorization URL = `https://login.salesforce.com/services/oauth2/authorize`, Token request URL = `https://login.salesforce.com/services/oauth2/token`, **Use PKCE** on. Open the entry's menu, choose **Tools**, then **Fetch Tools**, and confirm seven tools. Install the app to the workspace and approve it under **Integrations**, **Installed apps**. Full steps in [SETUP.md §5c](SETUP.md#5c-slack-slackbot).

**Box admin.** In the Admin Console, open **Integrations**, filter by the **MCP** category, and enable the Box MCP Server for presenters with the Box AI and Doc Gen tools on. Presenters who connected earlier must disconnect and reconnect.
