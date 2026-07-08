"""
app.py

Backend interface for the COMSOL Copilot.

This file is intended to be called from a GUI
(Streamlit / Gradio / React / Qt).

No menus.
No input().
No print().

Everything enters through process_request().
"""

from graph import build_graph
from state import new_state

# ------------------------------------------------------------------
# Build graph once
# ------------------------------------------------------------------

graph = build_graph()

# ------------------------------------------------------------------
# Session state
# ------------------------------------------------------------------

# Stores all successful simulations from the current session.
previous_results = []


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def process_request(
    user_query: str,
    uploaded_pdf: str | None = None,
):
    """
    Process one user request.

    Parameters
    ----------
    user_query
        Natural language request from the UI.

    uploaded_pdf
        Path to the uploaded PDF (None if no paper uploaded).

    Returns
    -------
    AgentState
        Final state returned by LangGraph.
    """

    global previous_results

    state = new_state("single")

    state["user_query"] = user_query

    state["uploaded_pdf"] = uploaded_pdf

    # Make previous simulations available
    state["results"] = previous_results

    result = graph.invoke(state)

    # Preserve simulation history
    if result.get("results"):
        previous_results.extend(result["results"])

    return result


# ------------------------------------------------------------------
# Utilities for the future UI
# ------------------------------------------------------------------

def get_history():
    """
    Returns every simulation performed
    in this session.
    """
    return previous_results


def clear_history():
    """
    Clears simulation history.
    """

    global previous_results

    previous_results = []


# ------------------------------------------------------------------
# Optional terminal testing
# ------------------------------------------------------------------

if __name__ == "__main__":

    print("=" * 50)
    print("COMSOL Copilot Backend")
    print("=" * 50)
    print("Type 'exit' to quit.\n")

    uploaded_pdf = None

    while True:

        query = input("> ").strip()

        if query.lower() == "exit":
            break

        if query.lower().startswith("paper:"):

            uploaded_pdf = query.split(":", 1)[1].strip()

            print(f"Current paper set to:\n{uploaded_pdf}")

            continue

        result = process_request(
            user_query=query,
            uploaded_pdf=uploaded_pdf,
        )

        print("\n==============================")

        if result.get("error"):
            print("ERROR:")
            print(result["error"])

        if result.get("analysis_summary"):
            print(result["analysis_summary"])

        if result.get("results"):

            print("\nSimulation Runs")

            for run in result["results"]:

                print("-" * 40)

                print("Run:", run["run_id"])

                print("Success:", run["success"])

                if run["success"]:

                    print("PNG :", run["png_path"])

                    print("CSV :", run["csv_path"])

                else:

                    print(run["error"])
