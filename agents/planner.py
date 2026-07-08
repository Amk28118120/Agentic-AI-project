"""
agents/planner.py

Routes the user's menu choice to the correct next node in the
LangGraph pipeline:

    task == "band_structure"  -> "run_band_structure"
    task == "R_sweep"         -> "run_sweep"
    task == "explanation"     -> "use_rag"
    task == "compare"         -> "compare_results"

Design note: state["task"] (defined in state.py) is intentionally kept
restricted to "single" / "sweep" / "pdf" -- the vocabulary
tools/validator.py already understands. The four menu options above
are a *separate* concept (which button the user pressed), so they're
carried as state["requested_task"] instead. Since AgentState is a
TypedDict, adding this extra key at runtime is harmless -- it just
isn't type-checked. This lets band_structure/R_sweep reuse
validate_state() unchanged, while explanation/compare skip geometry
validation entirely (they don't need a1/b/rf), without touching
state.py or tools/validator.py.
"""

from state import AgentState
from tools.validator import validate_state

def route(state: AgentState, requested_task: str) -> str:
    """
    requested_task: one of "band_structure", "R_sweep", "explanation", "compare"
    (this is the raw menu choice from app.py / intent_parser.py)

    Mutates state in place and returns the name of the next node for
    graph.py to route to.
    """
 #   requested_task = state.get("requested_task")

    if requested_task == "band_structure":
        state["task"] = "single"
        state = validate_state(state)
        if not state["validated"]:
            return "reprompt_user"
        return "run_band_structure"

    elif requested_task == "R_sweep":
        state["task"] = "sweep"
        state = validate_state(state)
        if not state["validated"]:
            return "reprompt_user"
        return "run_sweep"

    elif requested_task == "explanation":
        # Doesn't touch a1/b/rf at all -- needs a question instead.
        # NOTE: "question" isn't in state.py's AgentState TypedDict
        # either; same runtime-extra-key approach as requested_task.
        if not state.get("question"):
            state["error"] = "Please provide a question for me to answer."
            return "reprompt_user"
        return "use_rag"

    elif requested_task == "compare":
        # Compares band structures / data files from already-generated
        # results. Reads state["results"] (defined in state.py), which
        # holds every prior run's png_path / csv_path / rf value.
        if not state.get("results"):
            state["error"] = (
                "No previous simulation results to compare. "
                "Run a band structure or sweep first."
            )
            return "reprompt_user"
        return "compare_results"

    else:
        state["error"] = f"Unknown task: {requested_task!r}"
        return "reprompt_user"
