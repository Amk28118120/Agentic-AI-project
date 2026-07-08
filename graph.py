"""
graph.py

Wires everything built so far into a LangGraph StateGraph:

    START -> planner -> (conditional) -> run_band_structure -> analysis -> END
                                       -> run_sweep          -> analysis -> END
                                       -> use_rag             (STUB)     -> END
                                       -> compare_results     (STUB)     -> END
                                       -> reprompt_user                 -> END

app.py is responsible for:
    - collecting menu input (a1/b/radius_factor or sweep bounds) directly
    - for the PDF workflow: calling agents/intent_parser.py's parse_pdf()
      itself and filling state BEFORE invoking this graph
    - for explanation/compare: calling clean_question() itself and
      setting state["question"] BEFORE invoking this graph
    - setting state["requested_task"] to one of "band_structure",
      "R_sweep", "explanation", "compare"
    - then calling graph.invoke(state)

This graph does NOT call intent_parser itself -- by the time state
reaches "planner", all needed fields (a1/b/radius_factor, or
sweep_start/end/step, or question) are assumed to already be filled in.

STUBS (marked below) exist so the graph compiles and the
band_structure / sweep paths are fully testable right now, even
though rag/retrieve.py and analysis_agent.py don't exist yet.
"""

from langgraph.graph import StateGraph, START, END

from state import AgentState, new_state
from agents import planner
from execution.executor import execute_single, execute_sweep
from agents.analysis_agent import run_analysis
from rag.retrieve import answer_question
from agents.intent_parser import parse_user_request

# ---------------------------------------------------------------------
# planner wrapper node
# ---------------------------------------------------------------------

# def planner_node(state: AgentState) -> AgentState:
#     """
#     Wraps planner.route(state, requested_task) -- which takes two
#     arguments -- into the single-state-argument shape LangGraph nodes
#     expect. Stores the routing decision in state["_next_node"] (a
#     runtime-only key, not part of the formal AgentState TypedDict)
#     for route_after_planner() to read.
#     """
#     next_node = planner.route(
#         state,
#         state["requested_task"],
#     )
#     state["_next_node"] = next_node
#     return state
def planner_node(state: AgentState) -> AgentState:
    return state
def intent_parser_node(state: AgentState) -> AgentState:
    """
    Parses the user's natural-language request into a populated
    AgentState. Existing state values (e.g. previous results) are
    copied over so later nodes can still access them.
    """

    parsed_state = parse_user_request(
        state["user_query"],
        uploaded_pdf=state.get("uploaded_pdf"),
)

    # Preserve anything that should survive parsing
    parsed_state["results"] = state.get("results", [])


    parsed_state["uploaded_pdf"] = state.get("uploaded_pdf")
    parsed_state["user_query"] = state.get("user_query")
    print(parsed_state)
    return parsed_state

# def route_after_planner(state: AgentState) -> str:
#     return state["_next_node"]
def route_after_planner(state: AgentState) -> str:
    return planner.route(
        state,
        state["requested_task"],
    )

# ---------------------------------------------------------------------
# STUB nodes -- replace once analysis_agent.py / rag/retrieve.py exist
# ---------------------------------------------------------------------

def analysis_node(state: AgentState) -> AgentState:
    """
    Runs analysis on the COMSOL output files.

    For a single simulation:
        analyse the one CSV.

    For a sweep:
        analyse every successful CSV and combine the summaries.
    """

    summaries = []

    bandgap = None

    for run in state["results"]:

        if not run["success"]:
            continue

        csv_path = run["csv_path"]

        analysis = run_analysis(csv_path)

        summaries.append(
            f"Run {run['run_id']}:\n"
            f"{analysis['summary']}"
        )

        # Store first detected bandgap if available
        if analysis["bandgaps"]:

            for gap in analysis["bandgaps"]:

                if gap["status"] == "complete":

                    bandgap = gap["gap_thz"]

                    break

    if summaries:

        state["analysis_summary"] = "\n\n".join(summaries)

    else:

        state["analysis_summary"] = (
            "No successful simulations were available for analysis."
        )

    state["bandgap_ev"] = bandgap

    return state


def use_rag_node(state: AgentState) -> AgentState:
    """
    Answers the user's question using the RAG pipeline.
    """

    question = state.get("question")

    if not question:
        state["analysis_summary"] = "No question was provided."
        return state

    try:
        answer = answer_question(question)
        state["analysis_summary"] = answer
        state["error"] = None

    except Exception as e:
        state["analysis_summary"] = None
        state["error"] = f"RAG failed: {e}"

    return state


def compare_results_node(state: AgentState) -> AgentState:
    """
    TODO: replace with a real comparison agent.
    Should read state["results"] (all prior runs' png_path/csv_path)
    and state.get("question") and produce a comparison summary.
    """
    state["analysis_summary"] = (
        f"STUB: compare_results not yet implemented. "
        f"{len(state.get('results', []))} run(s) available to compare."
    )
    return state


def reprompt_user_node(state: AgentState) -> AgentState:
    """
    Terminal node for invalid input / missing prerequisites (set by
    planner.py or tools/validator.py via state["error"]). Does not
    retry automatically -- app.py is expected to read state["error"]
    and state["validation_errors"], show them to the user, and start
    a fresh graph.invoke() once the user provides valid input.
    """
    return state


# ---------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------

def build_graph():
    # builder = StateGraph(AgentState)

    # builder.add_node("planner", planner_node)
    # builder.add_node("run_band_structure", execute_single)
    # builder.add_node("run_sweep", execute_sweep)

    builder = StateGraph(AgentState)

    builder.add_node("intent_parser", intent_parser_node)

    builder.add_node("planner", planner_node)

    builder.add_node("run_band_structure", execute_single)

    builder.add_node("run_sweep", execute_sweep)
    builder.add_node("analysis", analysis_node)
    builder.add_node("use_rag", use_rag_node)
    builder.add_node("compare_results", compare_results_node)
    builder.add_node("reprompt_user", reprompt_user_node)


    builder.add_edge(START, "intent_parser")

    builder.add_edge("intent_parser", "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "run_band_structure": "run_band_structure",
            "run_sweep": "run_sweep",
            "use_rag": "use_rag",
            "compare_results": "compare_results",
            "reprompt_user": "reprompt_user",
        },
    )

    builder.add_edge("run_band_structure", "analysis")
    builder.add_edge("run_sweep", "analysis")
    builder.add_edge("analysis", END)
    builder.add_edge("use_rag", END)
    builder.add_edge("compare_results", END)
    builder.add_edge("reprompt_user", END)

    return builder.compile()


if __name__ == "__main__":
    # manual smoke test -- Workflow 1 (single band structure), bypassing
    # app.py's menu prompts by filling state directly
    graph = build_graph()

    test_state = new_state(task="single")

    test_state["user_query"] = (
        "Run a band structure with "
        "a1=420 nm, b=123 nm, "
        "radius factor 1.048"
)

    result = graph.invoke(test_state)
    print(result)
