# Explore the data model in ERD Studio

Install `liamwynne.erd-studio` from the VS Code Marketplace. Open the repository folder, run **Developer: Reload Window**, and click the ERD Studio activity-bar icon.

Open **Synthetic evaluation / workload_evaluation** or **Runtime telemetry / execution_telemetry** in the Logical stage. The supplied domains are already configured; no setup wizard or database is needed.

The root `dbt_project.yml` is only the extension activation marker documented for non-dbt projects. This does not convert the application to dbt. Physical comparison is unavailable for these Python/CSV/JSONL models.

## What the diagrams describe

- `workload_events`: all fields of `WorkloadEvent` in `src/workloads/schema.py`.
- `counterfactual_outcomes`: the CSV output of `build_counterfactual_dataset` in `src/simulation/counterfactuals.py`. Its composite grain is event_id + tool within one generation, not across seeds.
- `simulated_tools`: logical lookup of the simulator's TOOLS list, not a physical table.
- `telemetry_events`: all fields of `TelemetryEvent` in `src/telemetry/schema.py`.
- `routing_strategies`: logical lookup of the runtime STRATEGIES list, not a physical table.

The runtime workload_id is caller-supplied; it is not proven to equal a synthetic event_id, so these domains deliberately have no cross-domain join. Telemetry has no unique event key. Its success field currently reflects verifier status, and latency/token fields describe the final executor rather than the entire cascade. These diagrams document current behavior, not proposed fixes.

## Editing and sharing

Model definitions live in `.erd-studio/logical-models/*.yml` (JSON syntax, valid YAML). Relationships and canvas positions live in the domain JSON files. Commit these files and this guide alongside code. GitHub displays the source files; the interactive canvas opens in VS Code.

Changes to Python schemas are not automatically synchronized by this extension. Update model definitions with code changes. No application code, live API settings, telemetry data, or model calls are changed by this setup.
