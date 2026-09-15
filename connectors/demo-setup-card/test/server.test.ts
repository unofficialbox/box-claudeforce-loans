import { Client, InMemoryTransport } from "@modelcontextprotocol/client";
import { describe, expect, it } from "vitest";
import {
  BINDING_KEYS,
  bindingsTable,
  loadDefaults,
  summarizeBindings,
  validateBindings,
} from "../src/bindings.js";
import { ConfirmationStore, RESOURCE_URI, createServer } from "../src/server.js";

const DEFAULTS = {
  boxEnterpriseId: "123456",
  creditPolicyHubId: "987654321",
  docgenCommitmentLetterTemplateId: "246822413",
  signerEmail: "dana.whitfield@example.com",
};
const CARD_HTML = "<!DOCTYPE html><html><body><h1>Demo Setup</h1></body></html>";

async function connect(store = new ConfirmationStore()) {
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const server = createServer({ defaults: DEFAULTS, readCardHtml: async () => CARD_HTML, store });
  await server.connect(serverTransport);
  const client = new Client({ name: "test", version: "0.0.0" });
  await client.connect(clientTransport);
  return { client, server, store };
}

function text(result: { content?: Array<{ type: string; text?: string }> }): string {
  return result.content?.find((c) => c.type === "text")?.text ?? "";
}

describe("bindings", () => {
  it("loads file defaults and lets environment variables override them", () => {
    const tmp = `${process.env.TMPDIR ?? "/tmp"}/los-demo-defaults-${process.pid}.json`;
    const fs = require("node:fs") as typeof import("node:fs");
    fs.writeFileSync(tmp, JSON.stringify({ ...DEFAULTS, _comment: "ignored" }));
    const loaded = loadDefaults({ LOS_DEMO_SIGNER_EMAIL: "override@example.com" }, tmp);
    fs.unlinkSync(tmp);
    expect(loaded).toEqual({ ...DEFAULTS, signerEmail: "override@example.com" });
    expect(loadDefaults({}, undefined)).toEqual({
      boxEnterpriseId: "",
      creditPolicyHubId: "",
      docgenCommitmentLetterTemplateId: "",
      signerEmail: "",
    });
  });

  it("validates numeric Box IDs and the signer email", () => {
    expect(validateBindings(DEFAULTS)).toEqual({ ok: true, bindings: DEFAULTS });
    const bad = validateBindings({ ...DEFAULTS, creditPolicyHubId: "hub-1", signerEmail: "dana" });
    expect(bad.ok).toBe(false);
    if (!bad.ok) expect(bad.errors).toEqual([
      "Credit Policy Hub ID must be a numeric Box ID.",
      "Signer email must be an email address.",
    ]);
    const missing = validateBindings({});
    expect(missing.ok).toBe(false);
    if (!missing.ok) expect(missing.errors).toHaveLength(BINDING_KEYS.length);
  });

  it("summarizes every binding and never mentions a loan write", () => {
    const summary = summarizeBindings(DEFAULTS);
    for (const value of Object.values(DEFAULTS)) expect(summary).toContain(value);
    expect(summary).not.toMatch(/\b(apply|approve|generate|sign)\b/i);
    expect(bindingsTable({ ...DEFAULTS, signerEmail: "" })).toContain("| Signer email | (not set) |");
  });
});

describe("Demo Setup MCP App server", () => {
  it("exposes demoSetup to the model with the card resource and keeps confirmDemoSetup app-only", async () => {
    const { client } = await connect();
    const { tools } = await client.listTools();
    const byName = Object.fromEntries(tools.map((t) => [t.name, t]));
    expect(Object.keys(byName).sort()).toEqual(["confirmDemoSetup", "demoSetup"]);
    const ui = (name: string) => (byName[name]._meta as { ui: { resourceUri: string; visibility?: string[] } }).ui;
    expect(ui("demoSetup").resourceUri).toBe(RESOURCE_URI);
    expect(ui("demoSetup").visibility).toEqual(["model", "app"]);
    expect(ui("confirmDemoSetup").visibility).toEqual(["app"]);
    expect(byName.demoSetup.annotations?.readOnlyHint).toBe(true);
  });

  it("serves the card as an MCP Apps HTML resource", async () => {
    const { client } = await connect();
    const { resources } = await client.listResources();
    expect(resources.map((r) => r.uri)).toEqual([RESOURCE_URI]);
    const read = await client.readResource({ uri: RESOURCE_URI });
    expect(read.contents[0].mimeType).toBe("text/html;profile=mcp-app");
    expect((read.contents[0] as { text: string }).text).toContain("Demo Setup");
  });

  it("returns the defaults, then the confirmation once the card confirms", async () => {
    const { client, store } = await connect();
    const before = await client.callTool({ name: "demoSetup", arguments: {} });
    expect(before.structuredContent).toEqual({ defaults: DEFAULTS, confirmed: null });
    expect(text(before)).toContain("| Signer email | dana.whitfield@example.com |");

    const rejected = await client.callTool({ name: "confirmDemoSetup", arguments: { ...DEFAULTS, boxEnterpriseId: "" } });
    expect(rejected.isError).toBe(true);
    expect(store.get()).toBeUndefined();

    const overrides = { ...DEFAULTS, signerEmail: "priya.shah@example.com" };
    const confirmed = await client.callTool({ name: "confirmDemoSetup", arguments: overrides });
    expect(confirmed.isError).toBeFalsy();
    expect(text(confirmed)).toBe(summarizeBindings(overrides));
    expect(store.get()).toEqual(overrides);

    const after = await client.callTool({ name: "demoSetup", arguments: {} });
    expect(after.structuredContent).toEqual({ defaults: DEFAULTS, confirmed: overrides });
    expect(text(after)).toContain("already confirmed");
  });
});
