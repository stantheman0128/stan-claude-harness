---
name: codex-security-validate
description: Validate one or more candidate security findings. Run `codex-security validate --help` for usage details.
requires_bin: codex-security
command: codex-security validate
---

# codex-security validate

Validate one or more candidate security findings.

## Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `findings...` | `string` | yes | Finding text or a file containing findings. |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--codex` | `array` |  | Override model or model_reasoning_effort with KEY=VALUE. |

> Confirm with the user before executing this destructive command.
