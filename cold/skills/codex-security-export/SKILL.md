---
name: codex-security-export
description: Export findings from a completed scan as CSV, JSON, or SARIF. Run `codex-security export --help` for usage details.
requires_bin: codex-security
command: codex-security export
---

# codex-security export

Export findings from a completed scan as CSV, JSON, or SARIF.

## Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `scanDir` | `string` | yes | Completed Codex Security scan directory. |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--exportFormat` | `string` | `sarif` | Export format (default: sarif). |
| `--output` | `string` |  | Write the selected format to FILE or stdout with '-'. |
| `--sourceRoot` | `string` |  | Repository checkout used for SARIF source-line fingerprints. |
| `--python` | `string` |  | Python interpreter for the bundled plugin exporter. |

> Confirm with the user before executing this destructive command.
