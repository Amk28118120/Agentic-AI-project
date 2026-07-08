"""
tools/validator.py

Validates AgentState before planner.py decides what to run. Only
checks confirmed rules -- no invented geometric bounds beyond what
was explicitly confirmed:

    - a1, b, radius_factor (and sweep_start/end/step) must be > 0.
      No upper ceiling.
    - b must be < a1.
    - Sweep: if (sweep_end - sweep_start) isn't evenly divisible by
      sweep_step, the sweep is truncated at the last value <= end
      (never overshoots end), rather than raising a "step doesn't
      divide evenly" error.

On failure, this does NOT stop the graph or raise. It sets
state["validated"] = False and fills state["validation_errors"] /
state["error"] so planner.py can route back to the user and ask for
valid parameters again.
"""

from state import AgentState


def _check_a1_b_rf(a1, b, rf, errors: list) -> None:
    if a1 is None or a1 <= 0:
        errors.append("a1 must be a positive number (nm).")
    if b is None or b <= 0:
        errors.append("b must be a positive number (nm).")
    if rf is None or rf <= 0:
        errors.append("Radius factor must be a positive number.")
    if a1 is not None and b is not None and a1 > 0 and b > 0:
        if not (b < a1):
            errors.append("b must be smaller than a1 (b < a1).")


def _generate_sweep_values(start: float, end: float, step: float) -> list:
    """
    Generates [start, start+step, start+2*step, ...] truncated at the
    last value <= end. Never overshoots end. Uses rounding to 10
    decimal places to avoid floating point drift (e.g. 0.90 + 0.02
    repeated landing on 1.1999999999998 instead of 1.20).
    """
    values = []
    n = 0
    while True:
        value = round(start + n * step, 10)
        if value > end:
            break
        values.append(value)
        n += 1
    return values


def validate_state(state: AgentState) -> AgentState:
    errors: list = []

    task = state.get("task")

    if task == "pdf":
        # At this stage only the upload itself is checked. Once
        # pdf_parser.py / intent_parser.py extract a1 / b / radius_factor
        # (or sweep bounds) from the paper, task is reassigned to
        # "single" or "sweep" and validate_state() is called again,
        # which then runs the same numeric checks as below.
        pdf_path = state.get("pdf_path")
        if not pdf_path:
            errors.append("No PDF path found for the uploaded paper.")

    elif task == "single":
        _check_a1_b_rf(
            state.get("a1"),
            state.get("b"),
            state.get("radius_factor"),
            errors,
        )

    elif task == "sweep":
        a1 = state.get("a1")
        b = state.get("b")
        start = state.get("sweep_start")
        end = state.get("sweep_end")
        step = state.get("sweep_step")

        if a1 is None or a1 <= 0:
            errors.append("a1 must be a positive number (nm).")
        if b is None or b <= 0:
            errors.append("b must be a positive number (nm).")
        if a1 is not None and b is not None and a1 > 0 and b > 0:
            if not (b < a1):
                errors.append("b must be smaller than a1 (b < a1).")

        if start is None or start <= 0:
            errors.append("Start radius factor must be a positive number.")
        if end is None or end <= 0:
            errors.append("End radius factor must be a positive number.")
        if step is None or step <= 0:
            errors.append("Step must be a positive number.")

        if start is not None and end is not None and start > 0 and end > 0:
            if end <= start:
                errors.append("End radius factor must be greater than start.")

        if not errors:
            state["sweep_values"] = _generate_sweep_values(start, end, step)

    else:
        errors.append(f"Unknown task type: {task!r}")

    state["validation_errors"] = errors
    state["validated"] = len(errors) == 0

    if errors:
        state["error"] = (
            "Some parameters aren't valid: " + " ".join(errors) +
            " Please provide valid parameters."
        )
    else:
        state["error"] = None

    return state
