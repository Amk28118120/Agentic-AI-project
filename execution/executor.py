

"""
execution/executor.py

Actually invokes tools/comsol_runner.py for the two workflows that
need COMSOL runs:

    execute_single(state)  -- Workflow 1, one comsolbatch call
    execute_sweep(state)   -- Workflow 2, one comsolbatch call per
                              rf value in state["sweep_values"]

Kept separate from planner.py (routing only, no COMSOL calls) and
tools/comsol_runner.py (wraps exactly one comsolbatch call, knows
nothing about single-vs-sweep). graph.py wires:

    "run_band_structure" -> execute_single
    "run_sweep"          -> execute_sweep

Sweep behavior: if one rf value's comsolbatch call fails, the loop
continues with the remaining values rather than aborting the whole
sweep -- a bad run is recorded with success=False in state["results"]
but doesn't take down the other runs, consistent with each run writing
its own isolated .mph file.
"""

from state import AgentState, RunOutput
from tools.comsol_runner import run_comsol, ComsolRunResult


def _to_run_output(result: ComsolRunResult, rf: float) -> RunOutput:
    """Converts a comsol_runner.ComsolRunResult into the RunOutput
    shape state.py expects (plain strings, not Path objects, and
    carries the rf value since ComsolRunResult itself doesn't store it)."""
    return RunOutput(
        rf=rf,
        run_id=result.run_id,
        success=result.success,
        mph_path=str(result.mph_path) if result.mph_path else None,
        png_path=str(result.png_path) if result.png_path else None,
        csv_path=str(result.csv_path) if result.csv_path else None,
        log_path=str(result.log_path) if result.log_path else None,
        error=result.error,
    )


def execute_single(state: AgentState) -> AgentState:
    a1 = state["a1"]
    b = state["b"]
    rf = state["radius_factor"]

    run_id = f"single_a1{a1}_b{b}_rf{rf}"
    params = {"a1": a1, "b": b, "rf": rf}

    result = run_comsol(params, run_id)
    state["results"] = [_to_run_output(result, rf)]

    state["error"] = result.error if not result.success else None
    return state


def execute_sweep(state: AgentState) -> AgentState:
    a1 = state["a1"]
    b = state["b"]
    sweep_values = state["sweep_values"]

    results = []
    for rf in sweep_values:
        run_id = f"sweep_a1{a1}_b{b}_rf{rf}"
        params = {"a1": a1, "b": b, "rf": rf}

        result = run_comsol(params, run_id)
        results.append(_to_run_output(result, rf))
        # deliberately no break/return here on failure -- see module
        # docstring: one bad rf value shouldn't kill the rest of the sweep

    state["results"] = results

    failed = [r for r in results if not r["success"]]
    if failed:
        state["error"] = (
            f"{len(failed)} of {len(results)} sweep runs failed. "
            f"Check state['results'] for per-run error details."
        )
    else:
        state["error"] = None

    return state
