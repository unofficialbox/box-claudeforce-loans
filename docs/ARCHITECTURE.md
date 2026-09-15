# Architecture

Two platforms, one set of governed actions between them. Box stores the loan file (application package, borrower documents, appraisal, term sheets, credit memos, commitment letters, executed agreements, metadata, versions, audit trail). Salesforce `LOS_Loan__c` stores structured credit truth. Loan-file bytes never flow into Salesforce, and term write-back requires explicit confirmation, and signature preparation enforces the loan state; draft generation requires a human request: AI drafts, compares, extracts and recommends; people approve credit decisions, exceptions, accepted terms and signatures.

Diagrams: [LOS architecture](diagrams/los-architecture.svg) ([source](diagrams/los-architecture.mmd)) and the [Box + Salesforce flow](diagrams/box-salesforce-los-flow.svg) ([source](diagrams/box-salesforce-los-flow.mmd)).

```text
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                     Salesforce - governed Apex actions (6 tools)                     │
│                                                                                      │
│  Salesforce only:                                                                   │
│  ┌──────────┐  ┌──────────┐                                                        │
│  │ List     │  │ Apply    │                                                        │
│  │ loans    │  │ terms    │                                                        │
│  │ (SOQL)   │  │(confirmed│                                                        │
│  └──────────┘  └──────────┘                                                        │
│                                                                                      │
│  Box for Salesforce:                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐                     │
│  │ Loan     │  │ Extract  │  │ Classify │  │ Prepare       │                     │
│  │ package  │  │ terms    │  │ document │  │ signature     │                     │
│  │          │  │ (Box AI) │  │ (Box AI) │  │ (state-gated) │                     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘                     │
│  ┌────┴──────────────┴──────────────┴──────────────┴─────────────────────────┐   │
│  │       Client Credentials Grant - the Box token never leaves Apex           │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
        ▲                                                      ▲
        │ MCP / Agentforce (internal)     downscoped token (borrower portal)

Additional Box operations now use Box MCP directly (not via Salesforce):
- Metadata search: Box MCP query_metadata (enterprise-wide, faster)
- Box AI QA: Box MCP box_ai_ask (direct API)
- Doc Gen: Box MCP create_document_from_template (direct API)
```

Two surfaces share the governed assets. The internal surface is the `LOSLoanTools` hosted MCP server (Claude Desktop, ChatGPT, Slack) or the `LOS_Loan_Copilot` Employee Agent inside Agentforce, running as the signed-in employee over the whole portfolio. The external surface is the Acme Borrower Portal, a React UI Bundle on an authenticated Experience Cloud site, running as the community user and bounded by a sharing set, field permissions and server-authorized document listings, upload-only folder tokens and per-file preview tokens. The portal carries no agent: a Service Agent runs as its own user and takes the loan from the conversation, so it could not be scoped to the borrower. An optional third connector, `connectors/demo-setup-card` (an MCP Apps server), renders the Demo Setup card in Claude Desktop so the four session bindings are confirmed on a clickable card as in Amazon Quick; it holds no credentials and writes nothing to Box or Salesforce.

## Box

| Object | Purpose |
|---|---|
| `01 - Application Intake` | Packages entering by the alternate `losLoan` metadata trigger |
| `02 - Borrower Documents` | The borrower's package: application, financials, tax returns, bank statements, appraisal, insurance |
| `03 - Underwriting`, `04 - Credit Approval`, `05 - Closing` | Internal memos, committee packets and closing sets by stage |
| `06 - Executed Loan Documents` | Signed agreements and commitment letters with retention and maturity metadata |
| `07 - Covenants and Servicing` | Covenant tests, insurance renewals, maturity notices |
| `Credit Policies` folder and the **Acme Credit Policy Library** Hub | The eight governed policy Markdown files (`sample-data/policies/`); the Copilot's policy check reads this Hub and no other |

Metadata templates (`config/box/metadata-templates.bcl`): `losLoan` on the workspace folder (loanId, borrower, loanType, status, amount, term, rate, ltv, dscr, owner, riskRating, dates); `losDocument` on files (documentType, versionStatus `Draft | Internal | Approved | Executed`, policyRisk `Low | Medium | High | Critical`, aiSummaryStatus, approvalStatus, signatureStatus); `losCovenant`; `losPolicy`; `losUnderwritingReview` (specified, not live). `losDocument` is the index: the portfolio search, the Copilot and the borrower's checklist all read it, and `versionStatus = Internal` is what withholds a file from the borrower. Metadata search is enterprise-wide, so every query is bounded by `ancestor_folder_id` from `Loans_Root_Folder_Id__c`.

## Salesforce loan record

`LOS_Loan__c` (label "Loan") is a dedicated custom object, not the standard `Contract`. It links to Account and Opportunity for relationship context; the Opportunity is the Box-mapped object. Sharing is Private internally and externally; the borrower portal reaches records through the `LOS_Borrower_Access` sharing set on `Borrower_Account__c`, which is the anchor (the `Borrower__c` text can hold both "Harborview Logistics" and "Harborview Logistics Holdings LLC").

| Group | Fields |
|---|---|
| Identity | `Name`, `Loan_ID__c` (external ID, `LN-<yyyy>-<NNNN>`), `Record_Source__c` (`Box Automate`, `Manual`, `API`, `Borrower Portal`) |
| Intake | `Applicant_Name__c`, `Applicant_Email__c`, `Borrower__c`, `Borrower_Account__c`, `Borrower_Entity__c`, `Opportunity__c`, `Loan_Type__c`, `Loan_Amount__c`, `Term_Months__c`, `Purpose__c`, `Region__c`, `Collateral_Type__c`, `Target_Closing_Date__c` |
| Credit terms | `Interest_Rate__c`, `LTV__c`, `DSCR__c`, `Collateral_Value__c`, `Maturity_Date__c`; with amount and term, the allow-list `LosApplyLoanTerms` may write |
| Assessment | `Risk_Rating__c`, `Underwriting_Notes__c`; never projected to the borrower |
| Ownership | `OwnerId`, `Loan_Officer__c` (active User only; otherwise `Loan_Officer_Name__c` keeps the name) |
| Lifecycle | `Status__c`: `Application`, `Underwriting`, `Credit Review`, `Approved`, `Commitment`, `Closed`, `Servicing` |
| Box | `Box_Workspace_Folder_ID__c` |

Only `Name`, `Loan_Amount__c` and `Target_Closing_Date__c` are required on the layout. The mapping is `config/salesforce/los-loan-record.bcl`; the metadata is `los-salesforce-project/force-app/main/default/objects/LOS_Loan__c/`.

**Borrower projection.** `LosLoanListService.LoanSummary` serves exactly `recordId, loanId, name, borrower, borrowerEntity, loanType, status, loanAmount, termMonths, maturityDate, boxFolderId` (plus `purpose` on create). The assessment fields are absent from the projection, not merely from the permission set, because Apex does not enforce field-level security in SOQL for authenticated users. `LOS_Box_Preview_Guest` and `LOS_Borrower_Portal` grant read on exactly those fields; `validate_los.py` checks the agreement offline.

## Governed actions

| Class | Surface | Does | Refuses |
|---|---|---|---|
| `LosLoanList` | MCP | Lists loans by status and borrower | Never offered to the borrower site |
| `LosLoanPackage` | MCP, agent | Resolves a loan by ID, name or record ID; lists its Box documents | A loan with no folder is reported, not provisioned |
| `LosBoxAskDocument` | Agent only | Asks Box AI about one document or the policy Hub; used by Copilot | A file outside the named loan's folder |
| `LosExtractLoanTerms` | MCP, agent | Box AI Extract of amount, rate, term, collateral value, LTV, DSCR, maturity; validation against record and policy | Writes nothing, ever |
| `LosApplyLoanTerms` | MCP, agent | Writes human-accepted terms to the seven allow-listed fields | `confirmed != true`; a Closed or Servicing loan; any other field |
| `LosClassifyDocument` | MCP, agent, portal | Box AI structured extraction of `losDocument.documentType` for one upload | A file outside the loan's folder; a type outside the enum |
| `LosSendForSignature` | MCP | Prepares a Box Sign request and returns the prepare URL | Any status but Approved or Commitment; it never sends |
| ~~`LosPortfolioSearch`~~ | Removed | Use Box MCP `query_metadata` directly (faster, enterprise-wide) | |
| ~~`LosGenerateCommitmentLetter`~~ | Removed | Use Box MCP `create_document_from_template` directly | |
| `LosBorrowerLoans` | Borrower portal | The signed-in borrower's loans via Contact, Account | Any other borrower's loan |
| `LosCreateApplication` | Borrower portal, `POST /los/applications` | One `LOS_Loan__c` in Application status for the caller's own Account, numbered after the last that year, user-mode DML | Guests (401); no Contact or Account (403); invalid type, amount, term or purpose (400); any account id in the body; rate, LTV, DSCR, risk or officer, ever |
| `LosBoxFolderService` | Borrower portal, `POST /los/box-folder` | Provisions the loan's Box folder through the Box for Salesforce package and grants the CCG user direct access | Runs as a second request: Apex cannot call out after DML, so create and provision are never one call |
| `LosBoxTokenService` | Borrower portal, `GET /los/box-token` | Resolves the record's folder, grants as the configured Box user, downscopes to that folder | A folder outside `Allowed_Folder_Ids__c` |

All Box calls go through `LosBoxAuth` with the `LOS_Box` external credential, so no MCP client, agent or browser holds an enterprise token. Configuration is the `LOS_Box_Config__c` custom setting: CCG subject, folder allowlist, policy Hub, loans root, commitment-letter template.

## Intake

The demo's intake is the borrower's own: sign in, submit the form (`LosCreateApplication`), provision the folder (`LosBoxFolderService`), upload the documents the checklist for that loan type asks for (`config/los/required-documents.bcl`, mirrored by `src/lib/requiredDocuments.ts`), and let Box AI classify each one (`LosClassifyDocument`). The loan officer sees the result in the **New applications** list view.

The alternate path is email or Box Automate. `EmailIntakeHandler` captures a borrower's email onto the Opportunity's timeline and uploads the attachment into that Opportunity's Box folder; it creates no loan. Applying `losLoan` metadata in `01 - Application Intake` starts the Automate workflow specified in `config/box/automate-workflows.bcl` (Extract, Box AI review, human approval task, then an HTTPS connector to Salesforce standard REST). The connector as captured (`config/box/https-connectors.bcl`, `salesforceLoanCreate`) is a plain POST and is not idempotent; the duplicate-safe design is a `PATCH` upsert by `Loan_ID__c` followed by a `GET` on the same external-ID resource. Neither has run live for loans; the CLM predecessor proved the POST.

## Deployment shape

`python3 scripts/demo_operator.py salesforce-deploy` deploys the Digital Experiences settings, object, fields, layout, permission sets, tab, app, record page with its Box tab, the UI Bundle and the site, publishes the site, and assigns the LOS and Box permission sets to the deploying admin. It excludes the External Client App and the OAuth metadata because those are environment-specific. Apex tests run only in an org (`sf apex run test --test-level RunLocalTests`); every Box callout is mocked by dispatching on the endpoint. The React bundle (`los-salesforce-project/force-app/main/default/uiBundles/losreactapp`) contains no tenant values; `VITE_*` variables supply them at build time, and without a real downscoped token the workspace names the refusal rather than showing fixtures.

## Data

`scripts/generate_sample_loan_assets.py` and `scripts/generate_docgen_templates.py` produce the twelve synthetic loan-file PDFs, two JSON fixtures and the Doc Gen Word templates under `output/` (the assistant-filled commitment letter, the Box for Salesforce managed-package commitment letter whose tags resolve against `sample-data/docgen/LOS_Loan__c_DocGen.json`, and the editable term sheet); `validate_los.py` regenerates them and fails on drift. `los-salesforce-project/sample-data/` seeds two Accounts (Harborview Logistics, Pinecrest Dental Group), their Contacts and Opportunities, and four loans: `LN-2023-0311` and `LN-2025-0148` (Harborview, Closed, 70% LTV and 1.30x DSCR in Schedule 1 of each executed agreement), `LN-2026-0042` (Harborview, Underwriting, $4,800,000 at 85% and 1.12x, risk High, with the borrower's term-sheet markup), and `LN-2026-0088` (Pinecrest, Application). The seed is idempotent by `Loan_ID__c`, and each loan's document is uploaded into its Opportunity's Box folder. All of it is deterministic fixture evidence, not proof of a deployed integration.
