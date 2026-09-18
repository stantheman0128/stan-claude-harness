#!/usr/bin/env -S npx tsx
/**
 * 12-factor agents compliance scanner.
 *
 * Heuristic, text-based signals — NOT verdicts. A WARN is a question to answer
 * by reading the cited files, not proof of a violation.
 *
 * Usage:
 *   npx tsx audit.ts <path>           # human-readable report
 *   npx tsx audit.ts <path> --json    # machine-readable
 *   node audit.ts <path>              # Node 23.6+ (native TS)
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, extname, relative, resolve } from "node:path";

type Severity = "PASS" | "WARN" | "INFO";

interface Hit {
  file: string;
  line: number;
  text: string;
}

interface SignalSpec {
  id: string;
  pattern: RegExp;
}

const CODE_EXT = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"]);
const SKIP_DIR = new Set(["node_modules", ".git", "dist", "build", ".next", "coverage", "venv", ".venv", "__pycache__"]);

// Named signals we look for across the codebase.
const SIGNALS: SignalSpec[] = [
  { id: "llm_call", pattern: /\b(openai|anthropic|generateText|generateObject|chat\.completions|messages\.create|createChatCompletion|ollama|@ai-sdk)\b/i },
  { id: "framework", pattern: /\b(langchain|langgraph|@langchain|crewai|crew_ai|llama[-_]?index|llamaindex|autogen|semantic[-_]kernel|haystack|griptape|smolagents)\b/i },
  { id: "own_prompt", pattern: /\b(PROMPT|systemPrompt|system_prompt|promptVersion|prompt_v\d|buildPrompt|renderPrompt)\b/ },
  { id: "context_curation", pattern: /\b(compact|compaction|summariz|truncat|trimContext|renderContext|contextWindow|buildContext)\b/i },
  { id: "schema_validation", pattern: /\b(zod|valibot|ajv|\.parse\(|safeParse|JSONSchema|z\.object|pydantic|BaseModel)\b/ },
  { id: "discriminated_union", pattern: /\bintent\b\s*[:=]|discriminatedUnion|switch\s*\(.*intent/i },
  { id: "state_serialize", pattern: /\b(JSON\.stringify|serialize|deserialize|toJSON|fromJSON|model_dump|\.dict\(\))\b/ },
  { id: "reducer", pattern: /\b(reduce|reducer)\b|\(\s*state\s*[,:]/ },
  { id: "pause_resume", pattern: /\b(resume|pause|checkpoint|snapshot|persistState|loadState|saveState)\b/i },
  { id: "human_in_loop", pattern: /\b(request_human|requestHuman|human[-_]?in[-_]?the[-_]?loop|approval|approve|escalat)\b/i },
  { id: "loop", pattern: /while\s*\(\s*true\s*\)|while\s+True\s*:|for\s*\([^)]*\b(turn|step|iteration|iter|attempt)s?\b/i },
  { id: "retry_cap", pattern: /\b(maxRetries|max_retries|maxSteps|max_steps|maxTurns|max_turns|maxAttempts|max_iterations|maxIterations|attempts\s*<|retries\s*<)\b/i },
  { id: "error_compaction", pattern: /catch\s*\(|except\s+\w/ },
  { id: "trigger", pattern: /\b(express|fastify|hono|@slack|slack_bolt|webhook|cron|schedule|lambda|cloudfunction|nextjs|app\.(get|post)|@app\.route)\b/i },
  { id: "tool_def", pattern: /\b(intent|name)\b\s*:\s*["'`]/ },
];

const args = process.argv.slice(2);
const jsonOut = args.includes("--json");
const root = resolve(args.find((a) => !a.startsWith("--")) ?? ".");

const hits = new Map<string, Hit[]>();
for (const s of SIGNALS) hits.set(s.id, []);
let filesScanned = 0;
let maxToolDefsInFile = 0;
let largestFileLines = 0;
let largestFile = "";

function walk(dir: string): void {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return;
  }
  for (const name of entries) {
    if (SKIP_DIR.has(name)) continue;
    const full = join(dir, name);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) walk(full);
    else if (CODE_EXT.has(extname(name))) scanFile(full);
  }
}

function scanFile(file: string): void {
  let content: string;
  try {
    content = readFileSync(file, "utf8");
  } catch {
    return;
  }
  filesScanned++;
  const rel = relative(root, file) || file;
  const lines = content.split("\n");
  if (lines.length > largestFileLines) {
    largestFileLines = lines.length;
    largestFile = rel;
  }
  let toolDefsHere = 0;
  lines.forEach((line, i) => {
    for (const s of SIGNALS) {
      if (s.pattern.test(line)) {
        if (s.id === "tool_def") toolDefsHere++;
        const arr = hits.get(s.id)!;
        if (arr.length < 5) arr.push({ file: rel, line: i + 1, text: line.trim().slice(0, 120) });
      }
    }
  });
  if (toolDefsHere > maxToolDefsInFile) maxToolDefsInFile = toolDefsHere;
}

walk(root);

const has = (id: string): boolean => (hits.get(id)?.length ?? 0) > 0;
const isAgent = has("llm_call") || has("framework") || has("tool_def");

interface FactorResult {
  factor: number;
  title: string;
  status: Severity;
  note: string;
  evidence: Hit[];
}

function evidence(...ids: string[]): Hit[] {
  return ids.flatMap((id) => hits.get(id) ?? []).slice(0, 3);
}

const results: FactorResult[] = [
  {
    factor: 1,
    title: "Natural language to tool calls",
    ...(isAgent
      ? { status: "PASS" as Severity, note: "LLM/tool-call usage detected." }
      : { status: "INFO" as Severity, note: "No LLM or tool-call usage detected — is this an agent?" }),
    evidence: evidence("llm_call", "tool_def"),
  },
  {
    factor: 2,
    title: "Own your prompts",
    ...(has("framework") && !has("own_prompt")
      ? { status: "WARN" as Severity, note: "Framework detected but no owned-prompt signal — prompts may be hidden in the framework." }
      : has("own_prompt")
        ? { status: "PASS" as Severity, note: "Owned prompt constants/builders found." }
        : { status: "INFO" as Severity, note: "No explicit prompt ownership detected." }),
    evidence: evidence("own_prompt", "framework"),
  },
  {
    factor: 3,
    title: "Own your context window",
    ...(has("context_curation")
      ? { status: "PASS" as Severity, note: "Context curation/compaction signals found." }
      : { status: "INFO" as Severity, note: "No context-curation signals (compact/summarize/render). Verify the context isn't a raw message dump." }),
    evidence: evidence("context_curation"),
  },
  {
    factor: 4,
    title: "Tools are structured outputs",
    ...(has("schema_validation")
      ? { status: "PASS" as Severity, note: "Output schema/validation found." }
      : isAgent
        ? { status: "WARN" as Severity, note: "No schema validation (zod/pydantic/parse) — LLM outputs may be trusted unvalidated." }
        : { status: "INFO" as Severity, note: "No schema validation found." }),
    evidence: evidence("schema_validation", "discriminated_union"),
  },
  {
    factor: 5,
    title: "Unify execution & business state",
    ...(has("state_serialize")
      ? { status: "PASS" as Severity, note: "State serialization present (single representable state)." }
      : { status: "INFO" as Severity, note: "No serialization signal — confirm there aren't two parallel state stores." }),
    evidence: evidence("state_serialize"),
  },
  {
    factor: 6,
    title: "Launch / pause / resume",
    ...(has("pause_resume")
      ? { status: "PASS" as Severity, note: "Pause/resume/checkpoint signals found." }
      : { status: "INFO" as Severity, note: "No pause/resume signals — long-running or human steps may block." }),
    evidence: evidence("pause_resume"),
  },
  {
    factor: 7,
    title: "Contact humans with tool calls",
    ...(has("human_in_loop")
      ? { status: "PASS" as Severity, note: "Human-in-the-loop signals found." }
      : { status: "INFO" as Severity, note: "No human-in-the-loop path detected — fine if never needed." }),
    evidence: evidence("human_in_loop"),
  },
  {
    factor: 8,
    title: "Own your control flow",
    ...(has("framework") && !has("loop")
      ? { status: "WARN" as Severity, note: "Framework present without an explicit loop — control flow may be ceded to the framework." }
      : has("loop")
        ? { status: "PASS" as Severity, note: "Explicit agent loop found." }
        : { status: "INFO" as Severity, note: "No explicit loop detected." }),
    evidence: evidence("loop", "framework"),
  },
  {
    factor: 9,
    title: "Compact errors into context",
    ...(has("loop") && !has("retry_cap")
      ? { status: "WARN" as Severity, note: "Loop present but no retry/step cap — risk of an unbounded failure loop." }
      : has("retry_cap")
        ? { status: "PASS" as Severity, note: "Retry/step cap found." }
        : { status: "INFO" as Severity, note: "No retry cap detected." }),
    evidence: evidence("retry_cap", "error_compaction"),
  },
  {
    factor: 10,
    title: "Small, focused agents",
    ...(maxToolDefsInFile > 15
      ? { status: "WARN" as Severity, note: `A single file declares ~${maxToolDefsInFile} tools — likely a mega-agent. Consider decomposing.` }
      : largestFileLines > 600
        ? { status: "WARN" as Severity, note: `Largest file ${largestFile} is ${largestFileLines} lines — check for an over-scoped agent.` }
        : { status: "PASS" as Severity, note: "No mega-agent signal." }),
    evidence: [],
  },
  {
    factor: 11,
    title: "Trigger from anywhere",
    ...(has("trigger")
      ? { status: "PASS" as Severity, note: "Trigger/entry-point signals found." }
      : { status: "INFO" as Severity, note: "No trigger surface detected — agent may be coupled to one entry point." }),
    evidence: evidence("trigger"),
  },
  {
    factor: 12,
    title: "Stateless reducer",
    ...(has("reducer") && has("state_serialize")
      ? { status: "PASS" as Severity, note: "Reducer-style signature + serialization found." }
      : { status: "INFO" as Severity, note: "No clear (state,event)->state reducer with serializable state." }),
    evidence: evidence("reducer", "state_serialize"),
  },
];

if (jsonOut) {
  console.log(JSON.stringify({ root, filesScanned, isAgent, results }, null, 2));
} else {
  const icon: Record<Severity, string> = { PASS: "\u2705", WARN: "\u26a0\ufe0f ", INFO: "\u2139\ufe0f " };
  const counts = { PASS: 0, WARN: 0, INFO: 0 };
  console.log(`\n12-factor audit  \u00b7  root: ${root}  \u00b7  ${filesScanned} files scanned\n`);
  for (const r of results) {
    counts[r.status]++;
    console.log(`${icon[r.status]} Factor ${r.factor}: ${r.title}`);
    console.log(`     ${r.note}`);
    for (const e of r.evidence) console.log(`     \u2192 ${e.file}:${e.line}  ${e.text}`);
  }
  console.log(`\nSummary: ${counts.PASS} PASS \u00b7 ${counts.WARN} WARN \u00b7 ${counts.INFO} INFO`);
  console.log("Signals are heuristic. Confirm each WARN by reading the cited files.\n");
  if (!isAgent) console.log("Note: no agent signals detected — point this at your agent's source directory.\n");
}
