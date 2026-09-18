---
name: codex-security-scan
description: Run a Codex Security scan. Run `codex-security scan --help` for usage details.
requires_bin: codex-security
command: codex-security scan
---

# codex-security scan

Run a Codex Security scan.

## Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `repository` | `string` | no | Repository root to scan (default: current directory). |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--auth` | `string` | `auto` | Select automatic, ChatGPT, or API-key authentication. |
| `--path` | `array` |  | Scan only PATH; repeat for multiple paths. |
| `--knowledgeBase` | `array` |  | Read security docs; repeat for multiple paths. |
| `--diff` | `string` |  | Scan Git changes from BASE to --head. |
| `--workingTree` | `boolean` | `false` | Scan staged and unstaged changes. |
| `--head` | `string` |  | Git head ref for --diff. |
| `--base` | `string` |  | Git base ref for --working-tree. |
| `--mode` | `string` | `standard` | Scan mode. |
| `--model` | `string` |  | Model to use for the scan. |
| `--outputDir` | `string` |  | Write scan artifacts to DIR. |
| `--archiveExisting` | `boolean` | `false` | Archive existing results before scanning. |
| `--pluginPath` | `string` |  | Use a Codex Security plugin directory or ZIP. |
| `--python` | `string` |  | Python interpreter for the bundled plugin runtime. |
| `--codex` | `array` |  | Override isolated Codex config with KEY=VALUE; repeat as needed. |
| `--failOnSeverity` | `string` |  | Exit 1 for findings at or above LEVEL. |
| `--maxCost` | `number` |  | Stop the scan if estimated USD cost exceeds AMOUNT. |
| `--dryRun` | `boolean` | `false` | Validate local scan inputs without starting a scan. |

## Output

Type: `object`

## Examples

```sh
codex-security scan .

codex-security scan . --model gpt-5.6-terra

codex-security scan . --path src,tests

codex-security scan . --diff origin/main
```

> Confirm with the user before executing this destructive command.
