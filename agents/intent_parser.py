"""
agents/intent_parser.py

Two Gemini-backed jobs (menu-driven numeric input for Workflows 1/2
is handled directly by app.py, so this file does NOT touch that path):

    parse_pdf(pdf_path)       -- Workflow 3. Uploads the paper to
                                  Gemini, extracts {a1, b, radius_factor}
                                  as JSON. Scope matches the original
                                  design doc: single a1/b/radius_factor
                                  only, no sweep-range extraction.

    clean_question(raw_text)  -- Explanation / Compare paths. Cleans
                                  up the user's free-text question
                                  before it's handed to the RAG /
                                  compare agent.

Model: gemini-2.5-flash, via the client.models.generate_content(...)
pattern (google-genai SDK). GEMINI_API_KEY is expected in .env.

NOTE on SDK surface: Google's docs currently show two coexisting
patterns -- the long-standing client.models.generate_content(...)
(shown against gemini-2.5-flash) and a newer client.interactions.create(...)
(shown against gemini-3.5-flash in more recently updated pages). This
file uses generate_content() to match the confirmed gemini-2.5-flash
model. If the rest of the project already standardized on
interactions.create() elsewhere, this should be switched to match.
"""

import os
import json
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types
from state import new_state
load_dotenv()

MODEL = "gemini-2.5-flash"

# genai.Client() automatically picks up GEMINI_API_KEY from the
# environment once load_dotenv() has populated it.
_client = genai.Client()


PDF_EXTRACTION_PROMPT = """
You are extracting parameters for a photonic crystal band structure
simulation from the attached research paper.

Find the following three values:
- a1: the lattice size (the distance the paper uses to define the
  triangular/hexagonal unit cell), in nanometers.
- b: the triangle size (the triangular nanohole edge length or
  characteristic size used in the unit cell), in nanometers.
- radius_factor: the radius factor used to compute R (often written
  as R = radius_factor * a1 / 3, or similar), a dimensionless number.

Respond with ONLY a JSON object, no other text, no markdown code
fences, in exactly this shape:

{"a1": <number>, "b": <number>, "radius_factor": <number>}

If a value truly cannot be found in the paper, use null for that
field instead of guessing.
"""


def parse_pdf(pdf_path: str) -> Dict[str, float]:
    """
    Uploads the PDF at pdf_path to Gemini and extracts a1, b, and
    radius_factor. Raises ValueError if Gemini's response isn't
    valid JSON or is missing a required key -- callers (app.py /
    tools/validator.py) are expected to catch this and re-prompt
    the user, consistent with the rest of the pipeline's "never
    silently guess" behavior.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ValueError(f"PDF not found at: {pdf_path}")

    uploaded_file = _client.files.upload(file=path)

    response = _client.models.generate_content(
        model=MODEL,
        contents=[uploaded_file, PDF_EXTRACTION_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini did not return valid JSON while parsing the PDF. "
            f"Raw response: {raw_text!r}"
        ) from e

    required_keys = ["a1", "b", "radius_factor"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(
            f"Gemini's JSON response is missing required key(s): {missing}. "
            f"Full response: {data!r}"
        )

    null_keys = [k for k in required_keys if data.get(k) is None]
    if null_keys:
        raise ValueError(
            f"Gemini could not find these value(s) in the paper: {null_keys}. "
            f"Please provide them manually."
        )

    return {
        "a1": float(data["a1"]),
        "b": float(data["b"]),
        "radius_factor": float(data["radius_factor"]),
    }


QUESTION_CLEANING_PROMPT_TEMPLATE = """
Clean up the following user question about a photonic crystal band
structure simulation. Fix typos, remove filler words, and make it a
single clear, well-formed question. Do not answer the question --
only rewrite it. Respond with ONLY the cleaned question text, no
quotation marks, no preamble.

User question: {raw_text}
"""
INTENT_PROMPT = """
You are an intent parser for a COMSOL photonic crystal copilot.

Determine the user's intent.

Supported tasks:

1. band_structure
2. R_sweep
3. explanation
4. compare
5. paper_simulation

If the request is a simulation, extract:

- a1
- b
- radius_factor

If it is a sweep, extract

- sweep_start
- sweep_end
- sweep_step

If the user asks to simulate or use the uploaded paper,
set the task to "paper_simulation".

Do not attempt to extract file paths.
The uploaded PDF is supplied separately by the application.

Return ONLY JSON.

Example

{
    "task":"paper_simulation",
    "a1":null,
    "b":null,
    "radius_factor":null,
    "sweep_start":null,
    "sweep_end":null,
    "sweep_step":null
}
"""
def clean_question(raw_text: str) -> str:
    """
    Cleans up the user's free-text question (Explanation / Compare
    paths) before it reaches the RAG / compare agent. Returns the
    original raw_text unchanged if Gemini's response is empty for
    any reason, rather than raising -- a slightly messy question is
    still usable downstream, unlike the PDF path where missing
    numeric values would break the simulation.
    """
    prompt = QUESTION_CLEANING_PROMPT_TEMPLATE.format(raw_text=raw_text)

    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    cleaned = (response.text or "").strip()
    return cleaned if cleaned else raw_text
def parse_user_request(
        user_text: str,
        uploaded_pdf: str | None = None,
    ):
    """
    Converts a natural-language user request into an AgentState.

    This function does NOT run COMSOL.
    It only determines intent and extracts parameters.
    """

    prompt = f"""
{INTENT_PROMPT}

User request:

{user_text}
"""

    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()

    raw = raw.replace("```json", "")
    raw = raw.replace("```", "")
    raw = raw.strip()

    data = json.loads(raw)

    task = data["task"]

    if task == "band_structure":

        state = new_state("single")

        state["requested_task"] = "band_structure"

        state["a1"] = data.get("a1")

        state["b"] = data.get("b")

        state["radius_factor"] = data.get("radius_factor")

    elif task == "R_sweep":

        state = new_state("sweep")

        state["requested_task"] = "R_sweep"

        state["a1"] = data.get("a1")

        state["b"] = data.get("b")

        state["sweep_start"] = data.get("sweep_start")

        state["sweep_end"] = data.get("sweep_end")

        state["sweep_step"] = data.get("sweep_step")

    elif task == "paper_simulation":

        state = new_state("pdf")

        state["requested_task"] = "band_structure"

        if uploaded_pdf is None:

            raise ValueError(
                "No PDF has been uploaded."
            )

        params = parse_pdf(uploaded_pdf)

        state["pdf_path"] = uploaded_pdf

        state["a1"] = params["a1"]

        state["b"] = params["b"]

        state["radius_factor"] = params["radius_factor"]

    elif task == "compare":

        state = new_state("single")

        state["requested_task"] = "compare"

        state["question"] = clean_question(user_text)

    else:

        state = new_state("single")

        state["requested_task"] = "explanation"

        state["question"] = clean_question(user_text)

    return state
