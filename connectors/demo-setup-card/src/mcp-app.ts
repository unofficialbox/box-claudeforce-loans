/**
 * The Demo Setup card. It receives the defaults from the `demoSetup` tool result, lets the
 * operator edit them, validates through the app-only `confirmDemoSetup` tool, and posts the
 * confirmation into the chat as the operator's message. If the host refuses chat messages it
 * falls back to model context, and if that fails too it shows the sentence to type.
 */
import { App } from "@modelcontextprotocol/ext-apps";

const KEYS = ["boxEnterpriseId", "creditPolicyHubId", "docgenCommitmentLetterTemplateId", "signerEmail"] as const;
type Key = (typeof KEYS)[number];
type Bindings = Record<Key, string>;

const LABELS: Record<Key, string> = {
  boxEnterpriseId: "Box enterprise ID",
  creditPolicyHubId: "Credit Policy Hub ID",
  docgenCommitmentLetterTemplateId: "Doc Gen commitment-letter template ID",
  signerEmail: "Signer email",
};

const form = document.getElementById("form") as HTMLFormElement;
const confirmButton = document.getElementById("confirm") as HTMLButtonElement;
const resetButton = document.getElementById("reset") as HTMLButtonElement;
const status = document.getElementById("status") as HTMLParagraphElement;
const summaryBox = document.getElementById("summary") as HTMLDivElement;

let defaults: Bindings = { boxEnterpriseId: "", creditPolicyHubId: "", docgenCommitmentLetterTemplateId: "", signerEmail: "" };

function input(key: Key): HTMLInputElement {
  return form.elements.namedItem(key) as HTMLInputElement;
}

function fill(values: Partial<Bindings>): void {
  for (const key of KEYS) input(key).value = values[key] ?? "";
}

function current(): Bindings {
  const out = { ...defaults };
  for (const key of KEYS) out[key] = input(key).value.trim();
  return out;
}

function setStatus(text: string, kind: "" | "error" | "ok" = ""): void {
  status.textContent = text;
  status.className = `status ${kind}`.trim();
}

function localErrors(values: Bindings): string[] {
  const errors: string[] = [];
  for (const key of KEYS) {
    const value = values[key];
    const field = input(key);
    const bad = !value || (key === "signerEmail" ? !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) : !/^\d{1,32}$/.test(value));
    field.classList.toggle("invalid", bad);
    if (bad) errors.push(`${LABELS[key]} ${value ? "is not valid" : "is required"}.`);
  }
  return errors;
}

function applyTheme(): void {
  const theme = app.getHostContext()?.theme;
  document.documentElement.classList.toggle("dark", theme === "dark");
}

function lock(summary: string): void {
  for (const key of KEYS) input(key).disabled = true;
  confirmButton.disabled = true;
  resetButton.disabled = true;
  summaryBox.hidden = false;
  summaryBox.textContent = summary;
}

const app = new App({ name: "LOS Demo Setup card", version: "0.1.0" });

app.ontoolresult = (result) => {
  const structured = (result.structuredContent ?? {}) as { defaults?: Partial<Bindings>; confirmed?: Partial<Bindings> | null };
  if (structured.defaults) defaults = { ...defaults, ...structured.defaults };
  fill(structured.confirmed ?? defaults);
  setStatus(structured.confirmed ? "Already confirmed this session. Change a value and confirm again if needed." : "");
};

app.onhostcontextchanged = () => applyTheme();

resetButton.addEventListener("click", () => {
  fill(defaults);
  localErrors(current());
  for (const key of KEYS) input(key).classList.remove("invalid");
  setStatus("");
});

confirmButton.addEventListener("click", async () => {
  const values = current();
  const errors = localErrors(values);
  if (errors.length) {
    setStatus(errors.join(" "), "error");
    return;
  }
  confirmButton.disabled = true;
  setStatus("Confirming…");
  try {
    const result = await app.callServerTool({ name: "confirmDemoSetup", arguments: values });
    const text = result.content?.find((c) => c.type === "text")?.text ?? "";
    if (result.isError) {
      setStatus(text || "The server rejected these values.", "error");
      confirmButton.disabled = false;
      return;
    }
    const summary = text;
    try {
      await app.sendMessage({ role: "user", content: [{ type: "text", text: summary }] });
      setStatus("Confirmed and sent to the assistant.", "ok");
    } catch {
      try {
        await app.updateModelContext({ content: [{ type: "text", text: summary }] });
        setStatus("Confirmed. The assistant will use these values from its next reply.", "ok");
      } catch {
        setStatus("Confirmed here. Paste the sentence below into the chat so the assistant caches it.", "ok");
      }
    }
    lock(summary);
  } catch (error) {
    setStatus(`Could not confirm: ${error instanceof Error ? error.message : String(error)}`, "error");
    confirmButton.disabled = false;
  }
});

void app.connect().then(applyTheme);
