
"""
config.py

Central configuration for the COMSOL Copilot.

This file contains only configuration values:
    - Gemini API key
    - COMSOL executable
    - Model paths
    - Output directories

No business logic should live here.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

# ------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY was not found. "
        "Please create a .env file containing:\n"
        "GEMINI_API_KEY=<your_api_key>"
    )

# ------------------------------------------------------------------
# Project structure
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

MODELS_DIR = PROJECT_ROOT / "models"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"

PNG_DIR = OUTPUTS_DIR / "png"

CSV_DIR = OUTPUTS_DIR / "csv"

REPORTS_DIR = OUTPUTS_DIR / "reports"

DOCUMENTS_DIR = PROJECT_ROOT / "documents"

KNOWLEDGE_DIR = DOCUMENTS_DIR / "knowledge"

USER_DOCUMENTS_DIR = DOCUMENTS_DIR / "user"

RAG_DIR = PROJECT_ROOT / "rag"

# Create folders automatically if they don't exist
for _d in (
    MODELS_DIR,
    OUTPUTS_DIR,
    PNG_DIR,
    CSV_DIR,
    REPORTS_DIR,
    DOCUMENTS_DIR,
    KNOWLEDGE_DIR,
    USER_DOCUMENTS_DIR,
    RAG_DIR,
):
    _d.mkdir(parents=True, exist_ok=True)
  

# ------------------------------------------------------------------
# COMSOL
# ------------------------------------------------------------------
COMSOLBATCH_EXE = "C:/Program Files/COMSOL/COMSOL56/Multiphysics/bin/win64/comsolbatch.exe"

MODEL_PATH = MODELS_DIR / "base_model.mph"

# Study tag inside the COMSOL model
STUDY_TAG = "std1"

# Batch Job tag inside the COMSOL model
# Replace if your model uses a different tag.
JOB_TAG = "b1"

# ------------------------------------------------------------------
# Fixed export locations used inside COMSOL
# These should match the Export to File nodes configured in your .mph
# ------------------------------------------------------------------

COMSOL_EXPORT_PNG = Path(
    r"C:\Users\User\Documents\Comsol\band_structure.png"
)

COMSOL_EXPORT_DATA = Path(
    r"C:\Users\User\Documents\Comsol\bands.txt"
)

# ------------------------------------------------------------------
# Parameter configuration
# ------------------------------------------------------------------

PARAM_ORDER = [
    "a1",
    "b",
    "rf",
]

PARAM_UNITS = {
    "a1": "nm",
    "b": "nm",
    "rf": None,
}

# ------------------------------------------------------------------
# Gemini
# ------------------------------------------------------------------

GEMINI_MODEL = "gemini-2.5-flash"
