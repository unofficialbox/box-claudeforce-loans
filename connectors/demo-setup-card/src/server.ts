/**
 * MCP Apps server for the LOS demo's Demo Setup decision card.
 *
 * One model-visible tool, `demoSetup`, renders the card with the four environment bindings
 * and their defaults. One app-only tool, `confirmDemoSetup`, validates what the operator
 * confirmed and records it for the process. The card then posts the confirmation into the
 * chat as the operator's message, so the presenter skill caches the bindings exactly as it
 * would after a typed reply. The card never offers a loan write; those stay typed.
 */
import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/server";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import {
  BINDING_KEYS,
  type Bindings,
  bindingsTable,
  loadDefaults,
  summarizeBindings,
  validateBindings,
} from "./bindings.js";

export const RESOURCE_URI = "ui://los-demo-setup/card.html";
export const SERVER_NAME = "LOS Demo Setup";
export const SERVER_VERSION = "0.1.0";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILT_CARD = path.resolve(HERE, "..", "mcp-app.html");

export interface ServerOptions {
  defaults?: Bindings;
  readCardHtml?: () => Promise<string>;
  store?: ConfirmationStore;
}

/** Process-wide memory of the last confirmation, shared across stateless HTTP requests. */
export class ConfirmationStore {
  private confirmed: Bindings | undefined;
  get(): Bindings | undefined {
    return this.confirmed;
  }
  set(bindings: Bindings): void {
    this.confirmed = bindings;
  }
  clear(): void {
    this.confirmed = undefined;
  }
}

export const defaultStore = new ConfirmationStore();

async function readBuiltCard(): Promise<string> {
  return fs.readFile(BUILT_CARD, "utf8");
}

const bindingsSchema = z.object({
  boxEnterpriseId: z.string().describe("Box enterprise ID"),
  creditPolicyHubId: z.string().describe("Credit Policy Hub ID"),
  docgenCommitmentLetterTemplateId: z.string().describe("Doc Gen commitment-letter template ID"),
  signerEmail: z.string().describe("Signer email"),
});

export function createServer(options: ServerOptions = {}): McpServer {
  const defaults = options.defaults ?? loadDefaults();
  const readCardHtml = options.readCardHtml ?? readBuiltCard;
  const store = options.store ?? defaultStore;

  const server = new McpServer({ name: SERVER_NAME, version: SERVER_VERSION });

  registerAppTool(
    server,
    "demoSetup",
    {
      title: "Demo Setup",
      description:
        "Shows the Demo Setup card with the four environment bindings the LOS demo needs " +
        "(Box enterprise ID, Credit Policy Hub ID, Doc Gen commitment-letter template ID, signer email) " +
        "and their defaults. The operator confirms or overrides them once per session. " +
        "Call it when the operator asks for Demo Setup or before the first stage. It writes nothing to Box or Salesforce.",
      inputSchema: z.object({}),
      annotations: { readOnlyHint: true, openWorldHint: false },
      _meta: { ui: { resourceUri: RESOURCE_URI, visibility: ["model", "app"] } },
    },
    async () => {
      const confirmed = store.get();
      const text = confirmed
        ? `Demo Setup already confirmed this session.\n\n${bindingsTable(confirmed)}\n\nThe card lets the operator change any value.`
        : `Demo Setup defaults for this environment.\n\n${bindingsTable(defaults)}\n\n` +
          "The operator confirms or overrides them on the card. If the card is not shown, ask the operator " +
          "to reply \"use these defaults\" or give replacement values, then cache the result for the session. " +
          "Loan ID and loan folder ID are resolved from the live record, not here.";
      return {
        content: [{ type: "text", text }],
        structuredContent: { defaults, confirmed: confirmed ?? null },
      };
    },
  );

  registerAppTool(
    server,
    "confirmDemoSetup",
    {
      title: "Confirm Demo Setup",
      description: "Records the bindings the operator confirmed on the Demo Setup card for this session.",
      inputSchema: bindingsSchema,
      annotations: { readOnlyHint: true, openWorldHint: false },
      _meta: { ui: { resourceUri: RESOURCE_URI, visibility: ["app"] } },
    },
    async (args) => {
      const result = validateBindings(args);
      if (!result.ok) {
        return {
          isError: true,
          content: [{ type: "text", text: `Demo Setup not confirmed: ${result.errors.join(" ")}` }],
          structuredContent: { errors: result.errors },
        };
      }
      store.set(result.bindings);
      return {
        content: [{ type: "text", text: summarizeBindings(result.bindings) }],
        structuredContent: { bindings: result.bindings, summary: summarizeBindings(result.bindings) },
      };
    },
  );

  registerAppResource(
    server,
    "Demo Setup card",
    RESOURCE_URI,
    { mimeType: RESOURCE_MIME_TYPE, _meta: { ui: { prefersBorder: true } } },
    async () => ({
      contents: [{ uri: RESOURCE_URI, mimeType: RESOURCE_MIME_TYPE, text: await readCardHtml() }],
    }),
  );

  return server;
}

export { BINDING_KEYS };
