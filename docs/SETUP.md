# Setup

Build the demo in a new Box enterprise and Salesforce org. Do not copy IDs, URLs, users or credentials from another environment; every environment-bound value lives in gitignored runtime files (`config/runtime/*.json`, `.env`) or in the org itself.

The scripts generate the loan file and Doc Gen templates, create the Box folders, metadata templates and seeds, upload the documents, and deploy the portable Salesforce metadata. Administrators do the rest in a browser: licences, the credit policy Hub, Doc Gen template registration, OAuth credentials, Agentforce, and every publish, share, activate, generate or send, each with owner approval.

## 1. Prerequisites

- Python 3.11+, Node.js/npm, Mermaid CLI (`mmdc`), Box CLI, Salesforce CLI.
- A Box enterprise with Apps, AI, Hubs, Doc Gen, Sign, metadata and tasks enabled for the operator.
- A Salesforce org where you can deploy metadata, create an integration user, configure an External Client App, and use Agentforce and UI Bundles. **Salesforce Multi-Framework must be on** (Setup, React Development with Salesforce Multi-Framework) before the `UIBundle` type exists; it is per-org (MT-041).
- Box for Salesforce installed in the org: the Loan record page's Box tab uses `box:recordBoxFolder` and the deploy assigns its managed permission sets.
- Named owners for credit, compliance, security, publishing and signing.

Have administrators confirm licences; a successful CLI login proves nothing about entitlements.

## 2. Local configuration

```bash
cp .env.sample .env
cp config/runtime/demo-environment.example.json config/runtime/demo-environment.json
python3 scripts/setup_los_dev.py                                  # dependencies and runtime config
python3 scripts/setup_los_dev.py --automated --from-current-clis  # or: prefill from logged-in CLIs
```

`.env` carries the shell variables the one-time scripts read and the `VITE_*` values for a local preview; `set -a; source .env; set +a` loads it. Leave `BOX_CLIENT_SECRET` empty and export it only for the run that needs it.

In `demo-environment.json` fill `box.parentFolderId`, `box.enterpriseId`, `box.operatorLogin`, `box.reviewerLogins`, `box.hostname`, `salesforce.orgAlias`, `salesforce.orgId` (deployment refuses a mismatch), `salesforce.myDomainUrl`, and the integration username and email. Leave generated IDs and Agentforce values blank; the bootstrap writes IDs to `config/runtime/bootstrap-state.json`.

Authenticate, then check:

```bash
box login -d
sf org login web --alias <alias>
python3 scripts/demo_operator.py doctor            # expect: Doctor passed
python3 scripts/demo_operator.py doctor --platform box   # or salesforce, when admin is split
```

## 3. Bootstrap

```bash
python3 scripts/demo_operator.py bootstrap --scenario box-salesforce-los --dry-run
python3 scripts/demo_operator.py bootstrap --scenario box-salesforce-los --yes
```

`bootstrap` runs `generate-assets`, `box-foundation`, `seed-metadata`, `salesforce-deploy` and `resolve-config --allow-unresolved` in order, checkpointing after each create so a rerun skips what exists. Run the phases one at a time (each accepts `--dry-run`) when Box and Salesforce administration belong to different people.

Box phases create `LOS-2026-Harborview` (`01 - Application Intake` through `07 - Covenants and Servicing`, `08 - DocGen Templates`, `Credit Policies`), the five metadata templates, the borrower documents, the Doc Gen templates, the policy library, and sixteen metadata seeds. They publish and share nothing.

The Salesforce phase deploys the object, fields, layout, permission sets, tab, app, record page, UI Bundle and the authenticated Experience Cloud site, publishes the site, and assigns the LOS and Box permission sets to the deploying administrator. It excludes the External Client App because its scope, consumer key, callback URL and Run As user are environment-specific.

Then seed the sample records and per-loan documents from `los-salesforce-project/`:

```bash
./scripts/seed-los-sample-data.sh <alias>
sf project deploy start --target-org <alias> --source-dir force-app/main/default/staticresources
./scripts/seed-los-loan-files.sh <alias>
```

## 4. Box preview

The borrower workspace shows Box content through a short-lived token minted by `LosBoxTokenService` (`/services/apexrest/los/box-token?recordId=<sfid>`): the org first authorizes the caller against the loan and borrower account, then resolves its folder through `box__FRUP__c`, grants as the configured Box user with client credentials, returns an upload-only token and a filtered document listing. Preview requests additionally require `fileId` and receive a token scoped only to that permitted file. The browser never sees the client secret or the enterprise token; Apex never holds a credential either. Until this is configured the workspace says it could not be opened and names the reason. There is no fixture fallback.

Box renders the document on its own origin in an iframe because Experience Cloud allows only `'self'` under `script-src` and `CspTrustedSite` cannot widen it; it can grant `frame-src`, which is what the `LOS_Box_App` trusted site does.

**Box platform app (MT-037).** In the Developer Console create a Custom App with Server Authentication (Client Credentials Grant), App + Enterprise access, Generate User Access Tokens on, read and write on all files and folders (the workspace embeds the uploader; leave delete, share and admin off), and the site origin `https://<your-site>.my.site.com` under CORS Domains. A Box admin then authorizes the app under Apps, Custom Apps Manager, **in the same enterprise the Box for Salesforce package writes to**; an app authorized elsewhere fails with `invalid_grant`, and one in a different enterprise mints tokens but cannot see the package's folders (`invalid_resource`). Record the Client ID, Client Secret, and the Box user id the preview acts as (`box users:get --fields=id,login`); that user must be able to open the loan folder.

**Credential (MT-038).** Secrets go in the external credential, never a file:

```bash
read -rs BOX_CLIENT_SECRET && export BOX_CLIENT_SECRET
BOX_CLIENT_ID=<id> los-salesforce-project/scripts/configure-los-box-credential.sh <alias>
```

`LOS_Box` uses the Custom protocol: `ConnectApi.CredentialInput` accepts only `AwsSv4` or `Custom`, so a Basic principal could never be set by script. Rerunning updates the principal.

**Settings (MT-039).** On the `LOS_Box_Config__c` org default: `Box_User_Id__c` (the subject; prefer it over `Enterprise_Id__c`, whose service account would need collaborating onto every folder) and `Allowed_Folder_Ids__c` (blank allows any folder; set it to the demo workspace):

```bash
BOX_USER_ID=<id> BOX_ALLOWED_FOLDER_IDS=<id,id> los-salesforce-project/scripts/configure-los-box-settings.sh <alias>
```

The same record holds `Credit_Policy_Hub_Id__c`, `Loans_Root_Folder_Id__c` and `Commitment_Letter_Template_ID__c` (section 6).

**Site user access (MT-042).** The browser calls the endpoint as the Experience Cloud user, so the deploying admin's `LOS_Demo_Operator` does not cover it. Assign `LOS_Box_Preview_Guest` to the site guest user (it grants the Apex class, the credential principal, and **read on `UserExternalCredential`**, without which the callout throws `System.CalloutException` and the endpoint reports only `box_request_failed`). The signed-in borrower gets `LOS_Borrower_Portal` instead: exactly the projected fields, create on `LOS_Loan__c`, and no `viewAllRecords`.

**Verify.** From `los-salesforce-project/`:

```bash
sf api request rest "/services/apexrest/los/box-token?folderId=<box-folder-id>" --target-org <alias>
```

A working setup returns `accessToken`, `expiresIn`, `folderId` and `scope`. Otherwise:

| Response | Cause | Fix |
|---|---|---|
| `missing_folder_id`, `invalid_record_id` | No or bad record context | Call with `?recordId=<salesforce-id>` |
| `no_box_folder_mapping` (404) | No `box__FRUP__c` row for the loan | Provision through the workspace, or confirm the package can create folders (MT-044) |
| `invalid_folder_id` | `folderId` not numeric | The `demo-workspace` placeholder; open with `?folderId=` or rebuild with `VITE_BOX_FOLDER_ID` |
| `box_not_configured` | No CCG subject | Settings above |
| `folder_not_allowed` | Folder outside `Allowed_Folder_Ids__c` | Add it, or clear the field |
| `box_auth_failed` | Box rejected the credentials | Recheck the credential; confirm the app is authorized |
| `box_downscope_failed` | Subject cannot see the folder | Grant the Box user direct access to the folder |
| `box_request_failed` | The callout threw | Read on `UserExternalCredential`; named credential enabled |
| 200 but the list still shows | CORS | Add the site origin to the Box app |
| Preview frame empty | `frame-src` | Deploy `LOS_Box_App`; Setup, Trusted URLs lists `https://*.app.box.com` (MT-043) |
| "Box did not return a preview link" | Token lacks `item_preview` | Check `DOWNSCOPE_SCOPE` in `LosBoxTokenService` |

Production would move to per-user Box OAuth (MT-040): the committed `LOS_Box` auth provider is the scaffold, and the cost is a callback URL and a one-time consent per user.

## 5. Loan Copilot

Before publishing, set `default_agent_user` in `los-salesforce-project/force-app/main/default/aiAuthoringBundles/LOS_Loan_Copilot/` to the agent user in this org (the committed value is a placeholder) and assign `LOS_Loan_Agent` to that user, or the Extract and Apply actions are never offered. Then:

```bash
sf agent publish authoring-bundle --api-name LOS_Loan_Copilot --target-org <alias>
sf agent activate --version <n> --target-org <alias>
```

If a mis-typed agent already exists, delete it in Agent Builder first; the Metadata API refuses with "setup object in use". The Copilot is internal only; an Agentforce panel on a site would additionally need a Lightning Out 2.0 app (creatable through the Tooling API as `LightningOutApp` plus `LightningOutAppHost`, with `IsEnabled=true`) and a rebuild with `VITE_AGENTFORCE_APP_ID`.

## 5a. Connect an MCP client to the LOS server

The hosted server `LOSLoanTools` deploys with the metadata but is inert until three org-side steps run, none of which put a value in this repository.

1. **Activate the server.** Deploying `mcpServerDefinitions/` creates the definition only. Activation is a Tooling record: create `McpServerAccess` with `DeveloperName = LOSLoanTools`, `MasterLabel`, `Active = true`, and `McpServerId` set to the definition's Id. Setup → Integration → **MCP Servers** → LOS Loan Tools then shows Server Status Active and the Server URL, which for a production or Developer Edition org is `https://api.salesforce.com/platform/mcp/v1/custom/LOSLoanTools` (sandboxes and scratch orgs insert `sandbox/` after `v1/`).
2. **Deploy the External Client App.** `externalClientApps/LOS_Claude_MCP` with its OAuth settings (`MCP` and `RefreshToken` scopes), global OAuth set (callback `https://claude.ai/api/mcp/auth_callback`, PKCE required, consumer secret optional, named-user JWT tokens) and policy (admin pre-authorized users). Read the consumer key from Setup → External Client App Manager → LOS Claude MCP → Settings → OAuth; never retrieve `ExtlClntAppGlobalOauthSettings` into source, it carries the secret.
3. **Grant the user.** Assign `LOS_MCP_Client` to every presenter, and add them to the app's pre-authorized profiles or permission sets (Setup → External Client App Manager → LOS Claude MCP → Policies).

Then each presenter connects their own client by following [docs/CLIENT-SETUP.md](CLIENT-SETUP.md), written for non-developers. Before they do, add that client's callback URL to the app's global OAuth set (`https://claude.ai/api/mcp/auth_callback` for Claude, `https://oauth2.slack.com/external/auth/callback` for Slack, the URL shown in Quick's or ChatGPT's connector dialog for those), and in the Box Admin Console → Integrations → Box MCP Server enable read and write tools for Box Doc Gen and Box AI (off by default); a Box token issued before that change keeps the old grants and every Doc Gen call answers "Access denied" until the presenter reconnects.

Expect: the connector lists seven tools (`listLoans`, `getLoanPackage`, `extractLoanTerms`, `applyLoanTerms`, `classifyDocument`, `approveDocuments`, `prepareSignatureRequest`). Beat 2 uses Box MCP `query_metadata` directly.

## 5b. Amazon Quick

Amazon Quick on desktop runs the same two servers through a chat agent scoped to one skill. Nothing org-side changes beyond the callback URL in 5a. The presenter steps (connectors, skill import, agent, tool permissions, Demo Setup) are in [docs/CLIENT-SETUP.md](CLIENT-SETUP.md#amazon-quick-desktop). Maintainers keep the four Demo Setup values in `config/runtime/quick-demo-defaults.json` (gitignored; copy `quick-demo-defaults.example.json`), and give them to the presenter to paste into the skill draft before publishing. [config/quick/agent.json](../config/quick/agent.json) is the manifest of the agent configuration for review, not a Quick import file; [config/quick/instructions.md](../config/quick/instructions.md) is the agent's Instructions text. Quick has no project custom instructions, so the answer-style rules in DEMO-CLICKPATH P2 live inside the skill and the agent instructions.

| Symptom | Fix |
|---|---|
| Agent fails to publish with a "malformed wrapper ARN" error | Discard the draft and recreate the connector attachment fresh; detach and re-add does not fix it. If it recurs, create the agent fresh rather than editing the existing one. |
| The risk stage answers with `extractLoanTerms`, or letter generation asks for a separate Doc Gen guide | A stale skill import. Re-import the current file and Publish; confirm the `Skill revision` line. |
| A stage runs on the LOS connector alone and shows no previews | The skill does not reference the Box connector's tools. Edit the skill, reference both connectors, Publish. |
| `prepareSignatureRequest` or `create_docgen_batch` times out after 60 seconds | The call may have completed. The skill re-reads the loan package before any retry; do not retry by hand. |
| `applyLoanTerms` reports `Status__c` in `fieldsUpdated` | The deployed Apex differs from source, which never writes status. Redeploy `LosApplyLoanTerms` and hold signature preparation until the approval state is verified. |

## 5c. Slack (Slackbot)

Slackbot connects to remote MCP servers through a Slack app, discovers their tools, and runs them in a direct message. It loads no skills and has no custom instructions; the presenter pastes the primer from [skills/loan-origination-slack/SKILL.md](../skills/loan-origination-slack/SKILL.md) at the start of each rehearsal, and Slack shows Box links rather than document previews.

1. **Create the app.** At `api.slack.com/apps` choose Create New App → From a manifest, paste [config/slack/los-loan-tools.manifest.json](../config/slack/los-loan-tools.manifest.json) (fix the server URL for a sandbox org), and create it.
2. **Configure the server's OAuth.** Features → MCP Servers → the LOS entry: Auth Type Manual OAuth; Client ID = the consumer key; Client Secret = the consumer secret from Setup → External Client App Manager → LOS Claude MCP → Settings → OAuth; Authorization URL `https://login.salesforce.com/services/oauth2/authorize`; Token request URL `https://login.salesforce.com/services/oauth2/token`; Use PKCE on. The Slack callback `https://oauth2.slack.com/external/auth/callback` must already be on the app's global OAuth set (5a). The secret lives in Slack's app settings and the org, never in this repository.
3. **Fetch tools.** In the MCP Server Connection Details table open the entry's menu → Tools → Fetch Tools. Expect seven tools; mark the read tools read-only so Slackbot does not ask consent for them.
4. **Install and approve.** Install the app to the workspace. If the workspace requires admin approval, approve it under Integrations → Installed apps; the approval screen lists the connected MCP server with its own Allow checkbox. Re-approval is needed if the server URL's domain changes.
5. **Box.** Box for Slack must be installed in the workspace; presenters add Box in the Slackbot Apps list and complete Box OAuth themselves. Existing Box for Slack users re-authorize once at `https://account.box.com/app-api/slack-v2/install`.

Expect: in a Slackbot direct message, Apps lists `LOS Loan Tools` and `Box`; after sign-in both show under Your apps; `What tools are available from LOS Loan Tools?` lists seven. Limits: five connected apps per user, 60-second tool timeout, direct messages only.

| Symptom | Fix |
|---|---|
| App missing from the Slackbot Apps list | The `mcp:connect` scope is missing or the app is not installed or approved; reinstall after fixing the manifest. |
| "Failed to load tools" | OAuth misconfigured or the server URL is wrong; Fetch Tools again after correcting. |
| "Unexpected error" on sign-in | Callback URL mismatch: add the Slack callback to the LOS app's global OAuth set. |
| `access_token_exchange_failed` or "Not able to connect" | Token endpoint auth mismatch or a missing/incorrect client secret in the Slack app settings. |
| Tools listed but never invoked | Ask Slackbot what tools the app offers once, then repeat the prompt; confirm the tool descriptions fetched are current. |

## 6. Administrator checklist

Complete each item for every new environment. Record IDs only in the gitignored runtime files.

- Confirm the target enterprise and org; record hostname, alias and safe test scope locally.
- Store credentials only in managed connections or protected secret stores.
- Review the metadata `seed-metadata` applied; the portfolio search and the Copilot read it.
- Mark the four Word files as Doc Gen templates and record the commitment-letter template id in `LOS_Box_Config__c.Commitment_Letter_Template_ID__c`; `LosGenerateCommitmentLetter` refuses until it is set.
- Register `los-commitment-letter-salesforce-template.docx` on the Salesforce **Box Doc Gen Templates** tab against `LOS_Loan__c` and add the `box:dgRecordPage` action to the loan layout ([docs/DOCGEN-GUIDE.md](DOCGEN-GUIDE.md#salesforce-managed-package-template)); preview it against `LN-2026-0042` before presenting.
- Build the **Acme Credit Policy Library** Hub from `Credit Policies` and record its id in `Credit_Policy_Hub_Id__c`; publishing it needs owner approval.
- Record the loans root folder id in `Loans_Root_Folder_Id__c`; without it `LosPortfolioSearch` queries the whole enterprise.
- Create an API-only integration user with `LOS_Box_Automate_Integration` and nothing broader (`los-salesforce-project/scripts/configure-los-oauth.sh <alias>` with `LOS_INTEGRATION_USERNAME` and `LOS_INTEGRATION_EMAIL` set), and an External Client App with client credentials, `api` scope, admin preauthorization and that user as Run As. Keep the consumer secret in the Box-managed OAuth connection.
- Confirm the Box for Salesforce package can provision loan folders (MT-044); a failure surfaces as `box_folder_not_provisioned`.
- Give the borrower portal an authenticated user (Dana Whitfield on Harborview Logistics) with `LOS_Borrower_Portal`, site membership and a real password; `NetworkMember` must list her.
- Decide whether signed-out visitors may read loans (MT-045). `LOS_Loan__c` is Private, so a guest sees an empty list; a guest sharing rule exposes real records to anyone who can open the site.
- Select real reviewers for Credit Risk, Collateral, Compliance, Loan Documentation, Pricing, Insurance and Servicing, with Credit Administration as the triage fallback, and grant them least-privilege Box access.
- Per run: submit a labelled portal application and confirm record, folder and classification (MT-058); run Extract and confirm the write-back refuses without `confirmed = true`, then apply amount, rate and term with it (MT-057; never LTV or DSCR, which the extract reads from the policy text); confirm signature is blocked on an Underwriting loan; confirm a repeated loan ID updates the same record.
- After UI changes: capture screenshots from the real viewport and update `config/demo/screenshot-manifest.bcl` (MT-072).
- Reset: record test artifacts, restore demo state, and delete data or remove collaborators only with the owner's approval of the exact objects (MT-074).

## 7. Validate and record readiness

```bash
python3 scripts/demo_operator.py resolve-config
python3 scripts/demo_operator.py validate --scenario box-salesforce-los
python3 scripts/validate_los.py
```

Then run the preflight in `DEMO-CLICKPATH.md`. When every check passes, copy `config/runtime/validation-receipts.example.json` to `validation-receipts.json`, record secret-free references to the run, and run `python3 scripts/validate_los.py --presenter-ready`. It fails closed until both platforms have current passed receipts. The machine-readable workflow is `config/operator/operator-workflow.bcl`.

## 8. Maintenance

### Cleanup Demo Loans

Remove demo loans and their Box folders between presentations using `scripts/cleanup_demo.py`:

```bash
# Preview what would be deleted (safe dry-run)
python3 scripts/cleanup_demo.py --status Application --dry-run

# Delete all Application status loans
python3 scripts/cleanup_demo.py --status Application --yes

# Delete loans created today (useful for resetting between demos)
python3 scripts/cleanup_demo.py --today --yes

# Delete loans from the last 7 days
python3 scripts/cleanup_demo.py --last-n-days 7 --yes

# Delete specific loan by ID
python3 scripts/cleanup_demo.py --loan-id LN-2026-0042 --yes

# Delete loans for a specific borrower
python3 scripts/cleanup_demo.py --borrower "Harborview" --yes

# Interactive mode (prompts before each deletion)
python3 scripts/cleanup_demo.py --status Application --interactive
```

The script:
- Queries Salesforce for loans matching the specified criteria
- Deletes the Salesforce loan records using bulk API
- Deletes associated Box workspace folders recursively
- Requires explicit confirmation (`--yes` or `--interactive`) unless using `--dry-run`
- Handles missing folders gracefully (warns but continues)

**Safety features:**
- Always preview with `--dry-run` first
- Must specify at least one filter (won't delete all loans without criteria)
- `--interactive` mode prompts for each individual loan
- Uses Salesforce bulk delete API (safer than record-by-record)

**Common workflows:**
```bash
# Reset between demo runs (delete test loans created today)
python3 scripts/cleanup_demo.py --today --yes

# Clean up abandoned applications (borrowers who started but didn't finish)
python3 scripts/cleanup_demo.py --status Application --yes

# Remove specific borrower's test applications
python3 scripts/cleanup_demo.py --borrower "Test Company" --dry-run
python3 scripts/cleanup_demo.py --borrower "Test Company" --yes
```


### Box Sign completion

Embedded requests omit `redirect_url`: Box redirects inside the signing frame, so a full workspace return URL nests the portal. The outer workspace polls the server’s Box-backed signing status and closes the frame only after confirmed completion. `Borrower_Portal_URL__c` is no longer required for signature creation. Existing requests retain their original redirect; return with **Back to documents** and refresh if one displays the nested portal.

### Signing document classification

Keep these exact values in the `losDocument.documentType` enum and Box Extract instructions:

| Document type | Portal label | Supporting-document charts |
|---|---|---|
| Commitment Letter | Signing document | Excluded |
| Signed Commitment Letter | Signed | Excluded |
| Signing Log | Completed | Excluded |

Commitment letters are separate from term sheets. Classify actual signature evidence as a signed commitment letter; blank signature fields or a prefilled date do not prove completion. Signing logs are audit trails, not loan agreements.

The document list and history retain all three types. Metadata takes precedence; filename matching is a compatibility fallback for unclassified/Other files and never proves completion. Existing files may need reclassification; changing Extract instructions does not itself update their stored metadata.

These are display classifications, not authority to close a loan. The completion endpoint verifies `signed` with Box, retains the resulting signed files and signing log against the loan, then sets Salesforce status to **Closed**. The portal reconciles outstanding requests on workspace entry and during signing. The server sets the verified signed copies and log to their final document types, version Executed and signature status Signed before closure. It retains the request ID and exact artifact references; later visits fetch only those files and verify that they still belong to the mapped loan folder. Closed does not imply that the supporting documents were approved. Servicing is never regressed to Closed.

The storyboard source is `docs/demo-storyboard/storyboard.json`. Regenerate its Markdown and HTML with `python3 scripts/build_demo_storyboard.py` after editing steps or screenshot provenance.
