#!/usr/bin/env -S npx tsx
/**
 * Generate a new 12-factor agent project from the bundled TypeScript template.
 *
 * Usage:
 *   npx tsx scaffold.ts <target-dir> [--name <pkg-name>]
 *
 * Example:
 *   npx tsx scaffold.ts ./my-agent --name my-agent
 */
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const TEMPLATE = resolve(here, "../assets/template");
const PLACEHOLDER = "__PROJECT_NAME__";

const argv = process.argv.slice(2);
const target = argv.find((a) => !a.startsWith("--"));
if (!target) {
  console.error("Usage: npx tsx scaffold.ts <target-dir> [--name <pkg-name>]");
  process.exit(1);
}
const nameIdx = argv.indexOf("--name");
const dest = resolve(target);
const name = nameIdx >= 0 && argv[nameIdx + 1] ? argv[nameIdx + 1]! : basename(dest);

if (!existsSync(TEMPLATE)) {
  console.error(`Template not found at ${TEMPLATE}`);
  process.exit(1);
}
if (existsSync(dest) && readdirSync(dest).length > 0) {
  console.error(`Refusing to write: ${dest} exists and is not empty.`);
  process.exit(1);
}

mkdirSync(dest, { recursive: true });
cpSync(TEMPLATE, dest, { recursive: true });

function substitute(dir: string): void {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      substitute(full);
    } else {
      const content = readFileSync(full, "utf8");
      if (content.includes(PLACEHOLDER)) {
        writeFileSync(full, content.replaceAll(PLACEHOLDER, name));
      }
    }
  }
}
substitute(dest);

console.log(`\u2705 Scaffolded 12-factor agent "${name}" at ${dest}\n`);
console.log("Next steps:");
console.log(`  cd ${target}`);
console.log("  npm install");
console.log("  npm test       # eval harness (offline)");
console.log("  npm start      # run the example agent");
