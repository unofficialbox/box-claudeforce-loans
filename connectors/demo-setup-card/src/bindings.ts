/**
 * The four confirm-once environment bindings the LOS demo needs before its first stage.
 * They mirror config/runtime/quick-demo-defaults.json, so one gitignored file feeds both
 * the Amazon Quick skill and this card. Loan ID and loan folder ID are never bindings; the
 * presenter skill resolves them from the live record every session.
 */
import fs from "node:fs";

export const BINDING_KEYS = [
  "boxEnterpriseId",
  "creditPolicyHubId",
  "docgenCommitmentLetterTemplateId",
  "signerEmail",
] as const;

export type BindingKey = (typeof BINDING_KEYS)[number];
export type Bindings = Record<BindingKey, string>;

export const BINDING_LABELS: Record<BindingKey, string> = {
  boxEnterpriseId: "Box enterprise ID",
  creditPolicyHubId: "Credit Policy Hub ID",
  docgenCommitmentLetterTemplateId: "Doc Gen commitment-letter template ID",
  signerEmail: "Signer email",
};

export const ENV_VARS: Record<BindingKey, string> = {
  boxEnterpriseId: "LOS_DEMO_BOX_ENTERPRISE_ID",
  creditPolicyHubId: "LOS_DEMO_POLICY_HUB_ID",
  docgenCommitmentLetterTemplateId: "LOS_DEMO_DOCGEN_TEMPLATE_ID",
  signerEmail: "LOS_DEMO_SIGNER_EMAIL",
};

export const DEFAULTS_FILE_ENV = "LOS_DEMO_DEFAULTS_FILE";

const NUMERIC_ID = /^\d{1,32}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function emptyBindings(): Bindings {
  return {
    boxEnterpriseId: "",
    creditPolicyHubId: "",
    docgenCommitmentLetterTemplateId: "",
    signerEmail: "",
  };
}

/**
 * Defaults come from a JSON file (the same shape as quick-demo-defaults.json) named by
 * LOS_DEMO_DEFAULTS_FILE or passed explicitly, and each LOS_DEMO_* variable overrides its
 * key. Anything unset stays blank and the card asks the operator for it.
 */
export function loadDefaults(
  env: NodeJS.ProcessEnv = process.env,
  filePath: string | undefined = env[DEFAULTS_FILE_ENV],
): Bindings {
  const defaults = emptyBindings();
  if (filePath && fs.existsSync(filePath)) {
    const parsed = JSON.parse(fs.readFileSync(filePath, "utf8")) as Record<string, unknown>;
    for (const key of BINDING_KEYS) {
      const value = parsed[key];
      if (typeof value === "string") defaults[key] = value.trim();
    }
  }
  for (const key of BINDING_KEYS) {
    const value = env[ENV_VARS[key]];
    if (typeof value === "string" && value.trim()) defaults[key] = value.trim();
  }
  return defaults;
}

export type Validation = { ok: true; bindings: Bindings } | { ok: false; errors: string[] };

export function validateBindings(input: Partial<Record<BindingKey, unknown>>): Validation {
  const bindings = emptyBindings();
  const errors: string[] = [];
  for (const key of BINDING_KEYS) {
    const raw = input[key];
    const value = typeof raw === "string" ? raw.trim() : "";
    if (!value) {
      errors.push(`${BINDING_LABELS[key]} is required.`);
      continue;
    }
    if (key === "signerEmail" ? !EMAIL.test(value) : !NUMERIC_ID.test(value)) {
      errors.push(
        key === "signerEmail"
          ? `${BINDING_LABELS[key]} must be an email address.`
          : `${BINDING_LABELS[key]} must be a numeric Box ID.`,
      );
      continue;
    }
    bindings[key] = value;
  }
  return errors.length ? { ok: false, errors } : { ok: true, bindings };
}

/** The sentence the card sends into the chat once the operator confirms. */
export function summarizeBindings(bindings: Bindings): string {
  const parts = BINDING_KEYS.map((key) => `${BINDING_LABELS[key]} ${bindings[key]}`);
  return `Demo Setup confirmed: ${parts.join("; ")}. Use these bindings for the rest of this session and resolve the loan and folder from the live record.`;
}

export function bindingsTable(bindings: Bindings): string {
  const rows = BINDING_KEYS.map((key) => `| ${BINDING_LABELS[key]} | ${bindings[key] || "(not set)"} |`);
  return ["| Binding | Value |", "|---|---|", ...rows].join("\n");
}
