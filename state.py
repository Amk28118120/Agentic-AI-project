"""
state.py

Defines AgentState, the single state object passed between every
LangGraph node (intent_parser -> validator -> planner -> comsol_runner
-> analysis_agent). Written as a TypedDict, which is LangGraph's
standard state schema convention for StateGraph.

Three workflows share this same state shape:
    1. Single Simulation      -> radius_factor is a single float
    2. Radius Factor Sweep    -> sweep_start/end/step are set,
                                  sweep_values is the expanded list
    3. Upload Paper           -> pdf_path is set; intent_parser fills
                                  a1 / b / radius_factor from the PDF,
                                  after which it's treated identically
                                  to Workflow 1 or 2

This file does NOT validate anything (that's validator.py) and does
NOT call COMSOL (that's tools/comsol_runner.py). It only defines the
shape of the data those files read and write.
"""

from typing import TypedDict, Optional, List, Literal


TaskType = Literal["single", "sweep", "pdf"]


class RunOutput(TypedDict):
    """
    Result of a single comsol_runner.run_comsol() call, stored in
    AgentState["results"]. One entry for Workflow 1 (single run),
    one entry per rf value for Workflow 2 (sweep).
    """
    rf: float                      # radius factor used for this run
    run_id: str                    # matches comsol_runner's run_id
    success: bool
    mph_path: Optional[str]
    png_path: Optional[str]
    csv_path: Optional[str]
    log_path: Optional[str]
    error: Optional[str]


class AgentState(TypedDict):
    # --- which workflow this request is ---
    task: TaskType

    # --- core geometry parameters (all three workflows converge here) ---
    a1: Optional[float]             # lattice size, nm
    b: Optional[float]              # triangle size, nm

    # --- Workflow 1: Single Simulation ---
    radius_factor: Optional[float]

    # --- Workflow 2: Radius Factor Sweep ---
    sweep_start: Optional[float]
    sweep_end: Optional[float]
    sweep_step: Optional[float]
    sweep_values: Optional[List[float]]   # expanded rf values to run

    # --- Workflow 3: Upload Paper ---
    pdf_path: Optional[str]

    # --- validator.py output ---
    validated: bool
    validation_errors: List[str]

    # --- comsol_runner.py output (one item for single, many for sweep) ---
    results: List[RunOutput]

    # --- analysis_agent.py output (filled later) ---
    analysis_summary: Optional[str]
    bandgap_ev: Optional[float]
    requested_task: Optional[str]
    question: Optional[str]
    user_query: Optional[str]
    uploaded_pdf: Optional[str]
    # --- pipeline-level error, distinct from per-run errors above ---
    error: Optional[str]


def new_state(task: TaskType) -> AgentState:
    """
    Returns a freshly initialized AgentState with sensible empty
    defaults, so app.py / intent_parser.py don't need to remember
    every key up front.
    """
    return AgentState(
        task=task,
        a1=None,
        b=None,
        radius_factor=None,
        sweep_start=None,
        sweep_end=None,
        sweep_step=None,
        sweep_values=None,
        pdf_path=None,
        validated=False,
        validation_errors=[],
        results=[],
        analysis_summary=None,
        bandgap_ev=None,
        user_query=None,
        uploaded_pdf=None,
        error=None,
        requested_task=None,
        question=None,
    )
