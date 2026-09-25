# Template Design Specification — RET-C3-008 (Cat 3)

## Position in AgentCore Architecture

- **Agent Class**: `Graph` (`src/graph/graph.py`) — the graph IS the agent
- **L1 Base**: `AutonomousBaseGraph` (Cat 3 — autonomous think → act → observe loop)
- **Three-Layer Separation**: State (`class State(AutonomousState)`, agent-specific fields
  `NotRequired[...]`) / Node (framework think/act + custom initialize/finalize) / Graph
  (autonomous loop, `add_edges()` NOT overridden).

## Architecture Overview (Cat 3)

```
START → initialize(InputValidate S-1/S-2) → think ⇄ act → finalize(ReportFinalize) → END
                                              │  ToolActNode: dispatch_ticket / send_alert /
                                              │  hvac_setpoint_write (HITL D6 confirm) / verify
                                              ▼
Loop termination: resolved (in-band ≥2 cycles) | max_iterations=12 | budget_usd=$0.10 | HITL escalation
```

### Node / slot configuration

| Slot | Class | Responsibility | Trust |
|------|-------|---------------|-------|
| initialize | `InputValidateInitializeNode` (`src/nodes/`) | S-1 trust gate + S-2 deterministic scan (token/credential/PII); seed `action_trace`; flag `input_rejected` | INTERNAL |
| think | `GuardedThinkNode` (`src/graph/`) | framework ThinkNode + S-2 rejection short-circuit (halts loop ERROR before the LLM when `input_rejected`) | (framework) |
| act | `ToolActNode` (framework) | executes tool calls; enforces `hitl.tool_policies` (D6 interrupt for `hvac_setpoint_write`) | (framework) |
| finalize | `ReportFinalizeNode` (`src/graph/`) | runs `assemble_output()` → surfaces `final_output` (action_trace + reports) | (framework) |

Tools (`src/tools/energy_tools.py`, deterministic): `observe_telemetry`, `detect_anomaly`
(mean ± 3σ per equipment × time-of-day × day-of-week × season), `dispatch_maintenance_ticket`,
`send_staff_alert`, `hvac_setpoint_write` (approval-gated, degraded fallback = ticket-only),
`verify_return_to_baseline`.

### State Definition (extends AutonomousState)

| Field | Type | Purpose |
|-------|------|---------|
| store_id | `NotRequired[str]` | target store |
| telemetry | `NotRequired[dict]` | normalized cycle frame |
| baseline_config | `NotRequired[dict]` | per-store baseline (deployment-time artifact) |
| anomalies | `NotRequired[list[dict]]` | detected anomalies |
| action_trace | `NotRequired[list[dict]]` | append-only audit: `{cycle_idx, observation, reason, action_type, action_params, approval_state, verification, timestamp}` |

AutonomousState already provides `plan`, `thoughts`, `tool_calls`, `tool_results`,
`working_memory`, `final_output`, `cost_usd`, `iterations`.

## Framework Utilization

- **S-1**: `required_trust_level: INTERNAL` on the initialize node (BMS write reachable);
  agent default INTERNAL. HVAC write tool gated `confirm`.
- **S-2**: framework `@final` PII scan + deterministic token/credential/PII scan in
  `InputValidateInitializeNode`; enforced via `GuardedThinkNode` short-circuit.
- **S-3**: framework `@final` credential scan on outputs; reports carry no raw BMS secrets.
- **S-3 secrets**: `LLM_API_KEY` / `BMS_API_KEY` in `agent.yaml requires.secrets`. Never
  `os.environ`, never in state.
- **S-4**: `emit_trace_event()` in the initialize node + the guarded think node; framework
  emits lifecycle events for think/act.
- **HITL (D6)**: `hitl.enabled: true` + `memory_enabled: true` (mandatory checkpointer);
  `hitl.tool_policies['hvac_setpoint_write'] = confirm` → `interrupt()` before the BMS write.

### Cat 3 mandatory config (`config/agent.yaml`)

`budget_usd: 0.10` (hard cost ceiling — absent raises ConfigError), `max_iterations: 12`,
`llm` (injected at deploy), `memory_enabled: true`, `hitl` block.

## Import Isolation

- No Level 0 (`agenticstar`) imports; imports limited to `framework/`, `shared/`, `src/`.

## Design Decision Record

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| L1 base | AutonomousBaseGraph | autonomous self-directed loop (Cat 3) |
| S-2 rejection halt | GuardedThinkNode | backbone routes initialize→think unconditionally; a think-stage guard is the only reliable halt point |
| GuardedThinkNode/ReportFinalizeNode in `src/graph/` | constructor-arg override, not a domain node | Both classes override framework-slot nodes and require constructor args (`self`/agent reference, LLM client) at graph-assembly time; `src/nodes/` holds no-arg domain nodes instantiated directly by PB-6, so these two live alongside `graph.py` where they are wired |
| HVAC write gated | HITL D6 confirm | physical-equipment mutation requires human approval |
| Degraded fallback | ticket-only | safe behaviour when approval withheld / BMS absent |
