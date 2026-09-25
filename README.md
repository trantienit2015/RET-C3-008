# RET-C3-008 — Retail Autonomous Store Energy Anomaly Detection & Cost Reduction Agent

> **Category**: Cat 3 (autonomous think → act → observe loop with self-directed execution)
> **Industry**: RET

## Overview

An autonomous think → act → observe loop for store energy management. A language model decides
which tool to call next; the tools are deterministic Python functions: `observe_telemetry`
summarises a telemetry window per piece of equipment (mean, sample count, last reading);
`detect_anomaly` flags equipment whose last reading lies three standard deviations or more from
a per-store baseline and classifies it (equipment fault, schedule gap, behaviour);
`dispatch_maintenance_ticket` and `send_staff_alert` record a ticket or alert;
`hvac_setpoint_write` records an HVAC setpoint change; `verify_return_to_baseline` checks that the
last two readings are within 5% of the baseline. There is no connection to real meters, a
building-management system or a ticketing tool: every action returns a record only. The loop
stops when the model returns no tool call, or at the iteration ceiling (12) or cost ceiling
(USD 0.10) set in `config/config.yaml`.

`hvac_setpoint_write` is behind a confirmation policy: calling it pauses the run for a human
decision (`awaiting_human`), and it is refused when the caller does not allow human interaction.
The entry node requires an internal caller and rejects input containing tokens, credential-shaped
JSON or 12-digit identifiers before any model call.

Current limitation: the think prompt is built from the `store_id` and `telemetry` state fields,
not from the request text, and the bundled HTTP entry point only forwards the request text.
Through that entry point the model therefore sees no telemetry. The per-store baseline service
(`src/services/baseline_service.py`) is not wired into the graph either, so the model has to
pass a baseline to `detect_anomaly` itself.

The bundled HTTP entry point uses an Anthropic client when `ANTHROPIC_API_KEY` is available.
Without a key it starts only when `STG_MOCK_MODE=true` or `RET_C3_008_ALLOW_OFFLINE_LLM=1` is set,
using a scripted offline stand-in (`src/services/offline_llm.py`) that observes and checks one
telemetry frame and then stops, never writing a setpoint; otherwise start-up fails.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the anomaly rules and equipment integrations in `src/tools/energy_tools.py`, and provision your own per-store baselines.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
