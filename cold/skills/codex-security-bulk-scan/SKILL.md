---
name: codex-security-bulk-scan
description: Discover repositories and run resumable bulk security scans. Run `codex-security bulk-scan --help` for usage details.
requires_bin: codex-security
command: codex-security bulk-scan
---

# codex-security bulk-scan

Discover repositories and run resumable bulk security scans.

## Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `input` | `string` | no | CSV repository list; omit to discover repositories. |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--outputDir` | `string` |  | Directory for scan artifacts and resumable results. |
| `--workers` | `number` | `4` |  |
| `--mode` | `string` | `standard` |  |
| `--model` | `string` |  | Model to use for each repository. |
| `--maxAttempts` | `number` | `1` | Maximum scan attempts per repository. |
| `--pluginPath` | `string` |  |  |
| `--python` | `string` |  |  |
| `--codex` | `array` |  |  |

## Output

Type: `object`

> Confirm with the user before executing this destructive command.
