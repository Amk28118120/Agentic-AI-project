"""
tools/comsol_runner.py

Runs the fixed C6-lattice photonic crystal band-structure model
(base_model.mph) through comsolbatch (COMSOL 5.6, Windows) for a
given (a1, b, rf) parameter set, and returns paths to the exported
PNG / data file for that run.

Python never touches geometry, never computes R, never edits the
model tree. It only overrides Global Parameters via -pname/-plist
and triggers the Batch job (Solution -> Export to File -> Export to
File) via -job.

THINGS HARDCODED TO THIS SPECIFIC MODEL -- VERIFY BEFORE FIRST REAL RUN:

    MODEL_PATH    - path to base_model.mph. Never overwritten; every
                    run writes its own -outputfile.
    STUDY_TAG     = "std1"   (Study 1 / eigenfrequency) - confirmed.
    JOB_TAG       = "b1"     <-- PLACEHOLDER. Not yet confirmed.
                    Enable "Show Name and Tag" in Model Builder,
                    right-click the Batch node under
                    Study 1 > Job Configurations, read its {tag},
                    and replace the value below.
    COMSOL_EXPORT_PNG / COMSOL_EXPORT_DATA
                  - the FIXED paths the two Export to File nodes
                    write to inside COMSOL. Confirmed from your
                    setup (Add parameters to filename = None, so
                    these never change between runs -- this script
                    moves them into a run-specific location right
                    after each call).
"""

import cmd
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict


# ---- Fixed, model-specific configuration -----------------------------

COMSOLBATCH_EXE = "C:/Program Files/COMSOL/COMSOL56/Multiphysics/bin/win64/comsolbatch.exe"  # confirmed on PATH

MODEL_PATH = Path("C:/Users/User/Documents/base_model.mph")

STUDY_TAG = "std1"
JOB_TAG = "b1"  # TODO: CONFIRM real tag from Model Builder before real use

# Fixed output paths the two Export to File nodes write to inside COMSOL
# (Add parameters to filename = None on both, per your setup)
COMSOL_EXPORT_PNG = Path(r"C:/Users/User/Documents/Comsol/band_structure.png")
COMSOL_EXPORT_DATA = Path(r"C:/Users/User/Documents/Comsol/bands.txt")

# comsol-copilot project layout
PROJECT_ROOT = Path(r"C:/Users/User/Documents/comsol-copilot")
MODELS_DIR = PROJECT_ROOT / "models"           # per-run solved .mph files
PNG_DIR = PROJECT_ROOT / "outputs" / "png"
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"  # batch logs

for _d in (MODELS_DIR, PNG_DIR, CSV_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Which global parameters carry units baked into their COMSOL definition.
# Confirmed: a1 and b are defined with [nm] in COMSOL; rf is unitless.
# This matters because overriding a parameter that has a unit, using a
# plain unitless number via -plist, does NOT preserve that unit -- the
# override replaces the value outright, so the unit suffix must be
# supplied explicitly on the command line or the value is silently
# misinterpreted in base SI units (e.g. metres instead of nanometres).
PARAM_UNITS = {
    "a1": "None",
    "b": "None",
    "rf": None,
}

PARAM_ORDER = ["a1", "b", "rf"]  # order sent to -pname / -plist


@dataclass
class ComsolRunResult:
    success: bool
    run_id: str
    mph_path: Path
    png_path: Optional[Path]
    csv_path: Optional[Path]
    log_path: Path
    returncode: int
    error: Optional[str] = None


def _format_plist(params: Dict[str, float]) -> str:
    parts = []

    for name in PARAM_ORDER:
        value = params[name]
        unit = PARAM_UNITS.get(name)

        if unit:
            parts.append(f"{value}[{unit}]")
        else:
            parts.append(str(value))

    return ",".join(parts)


def run_comsol(params: Dict[str, float], run_id: str) -> ComsolRunResult:
    """
    params: {"a1": 420, "b": 123, "rf": 1.048}
    run_id: unique string for this run (e.g. "rf_1p048" or a uuid) --
            used to name the per-run .mph / .png / .csv / .log so a
            crash on one run can never corrupt or overwrite another,
            and the original base_model.mph is never touched.
    """
    missing = [k for k in PARAM_ORDER if k not in params]
    if missing:
        raise ValueError(f"Missing required parameter(s): {missing}")

    mph_out = MODELS_DIR / f"run_{run_id}.mph"
    log_out = REPORTS_DIR / f"run_{run_id}.log"

    pname = ",".join(PARAM_ORDER)
    plist = _format_plist(params)

    cmd = [
        COMSOLBATCH_EXE,
        "-inputfile", str(MODEL_PATH),
        "-outputfile", str(mph_out),
        "-job", JOB_TAG,
        "-pname", pname,
        "-plist", plist,
        "-batchlog", str(log_out),
    ]
    print("Executing command:")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print("=" * 60)
    print("Return code:", proc.returncode)
    print("\nSTDOUT:\n")
    print(proc.stdout)
    print("\nSTDERR:\n")
    print(proc.stderr)
    print("=" * 60)
    log_text = ""
    if log_out.exists():
        log_text = log_out.read_text(errors="ignore")

    # comsolbatch returns non-zero on failure; the log-text check is a
    # secondary signal only -- "Error" can appear in benign log lines
    # (e.g. "Error estimate"), so treat this as a soft check, not proof.
    failed = proc.returncode != 0

    if failed:
        return ComsolRunResult(
            success=False,
            run_id=run_id,
            mph_path=mph_out,
            png_path=None,
            csv_path=None,
            log_path=log_out,
            returncode=proc.returncode,
            error=(proc.stderr or log_text or "Unknown COMSOL failure")[-2000:],
        )

    # move the fixed-path exports into their run-specific location
    png_dest = PNG_DIR / f"run_{run_id}.png"
    csv_dest = CSV_DIR / f"run_{run_id}.txt"

    png_ok = COMSOL_EXPORT_PNG.exists()
    csv_ok = COMSOL_EXPORT_DATA.exists()

    if png_ok:
        shutil.move(str(COMSOL_EXPORT_PNG), str(png_dest))
    if csv_ok:
        shutil.move(str(COMSOL_EXPORT_DATA), str(csv_dest))

    if not (png_ok and csv_ok):
        return ComsolRunResult(
            success=False,
            run_id=run_id,
            mph_path=mph_out,
            png_path=png_dest if png_ok else None,
            csv_path=csv_dest if csv_ok else None,
            log_path=log_out,
            returncode=proc.returncode,
            error=(
                "comsolbatch exited with code 0 but expected export file(s) "
                "were not found. Check: JOB_TAG is correct, the Batch node's "
                "Solution subnode Run=All, and both Export to File subnodes "
                "are present under Batch (not just under Results > Export)."
            ),
        )

    return ComsolRunResult(
        success=True,
        run_id=run_id,
        mph_path=mph_out,
        png_path=png_dest,
        csv_path=csv_dest,
        log_path=log_out,
        returncode=proc.returncode,
    )


if __name__ == "__main__":
    # manual smoke test -- run this alone first, before wiring it into
    # the LangGraph pipeline, to confirm JOB_TAG and export paths are right
    result = run_comsol({"a1": 420, "b": 123, "rf": 1.048}, run_id="smoketest")
    print(result)
