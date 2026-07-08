"""
agents/analysis_agent.py

Reads the exported band-structure data file and reports bandgaps
between every consecutive pair of bands.

ASSUMPTIONS -- UNVERIFIED, since bands.txt doesn't exist yet (no run
has completed). Fix these once you have a real file to test against:

    - File is whitespace/comma/tab delimited (auto-detected via
      pandas sep=None, engine='python').
    - Lines starting with '%' are COMSOL metadata/header comments
      and are skipped (COMSOL's plain-text data export convention).
    - First column is the k-path parameter value (confirmed: ranges
      0 -> 2, with k=1 meaning Gamma, path M(k=0) -> Gamma(k=1) ->
      K(k=2)); every remaining column is one band's eigenfrequency,
      already in THz, ordered by increasing frequency (band 1,
      band 2, band 3, ...).
    - Gamma is located by finding the row whose k-value is closest
      to 1.0, NOT by row index/position -- this matters because the
      number of sampled k-points can vary between runs, so Gamma's
      row position isn't fixed.

Bandgap definition (confirmed): between band n and band n+1, a
COMPLETE bandgap exists only if max(band_n) across the entire k-path
is less than min(band_n+1) across the entire k-path. The gap size is
that difference.

Honesty behavior (this is the important part): if bands overlap
somewhere along the path but a local gap still exists at the Gamma
row, this is reported explicitly as "gap only at Gamma, not complete"
-- it is never reported as though it were a complete bandgap, since
that would misrepresent the model's current (known, per your note)
issue.
"""

import pandas as pd
from typing import List, Dict, Tuple


GAMMA_K_VALUE = 1.0


def load_band_data(csv_path: str) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Loads the band-structure export. Skips COMSOL '%' comment lines
    and auto-detects the delimiter.

    Returns (k_values, band_df):
        k_values -- the first column (k-path parameter, 0 to 2)
        band_df  -- remaining columns, renamed band_1, band_2, ...
    """
    df = pd.read_csv(
        csv_path,
        sep=None,
        engine="python",
        comment="%",
        header=None,
    )

    k_values = df.iloc[:, 0].copy()
    band_df = df.iloc[:, 1:].copy()
    band_df.columns = [f"band_{i+1}" for i in range(band_df.shape[1])]
    return k_values, band_df


def _gamma_row_index(k_values: pd.Series) -> int:
    """Finds the row closest to k=1.0 (Gamma), by value, not position."""
    return (k_values - GAMMA_K_VALUE).abs().idxmin()


def analyze_bandgaps(k_values: pd.Series, band_df: pd.DataFrame) -> List[Dict]:
    """
    Returns one entry per consecutive band pair:

        {
            "band_low": 1, "band_high": 2,
            "status": "complete" | "gamma_only" | "none",
            "gap_thz": <float, only meaningful if status == "complete">,
            "gamma_k_value": <float, actual k-value used as Gamma>,
            "gamma_gap_thz": <float, gap size at the Gamma row>,
        }
    """
    n_bands = band_df.shape[1]
    gamma_idx = _gamma_row_index(k_values)
    gamma_k_actual = float(k_values.loc[gamma_idx])

    results = []

    for i in range(n_bands - 1):
        low_col = band_df.iloc[:, i]
        high_col = band_df.iloc[:, i + 1]

        max_low = low_col.max()
        min_high = high_col.min()
        full_gap = min_high - max_low

        gamma_gap = float(high_col.loc[gamma_idx] - low_col.loc[gamma_idx])

        if full_gap > 0:
            status = "complete"
        elif gamma_gap > 0:
            status = "gamma_only"
        else:
            status = "none"

        results.append({
            "band_low": i + 1,
            "band_high": i + 2,
            "status": status,
            "gap_thz": float(full_gap) if status == "complete" else None,
            "gamma_k_value": gamma_k_actual,
            "gamma_gap_thz": gamma_gap,
        })

    return results


def summarize(results: List[Dict]) -> str:
    """
    Builds a plain-language summary emphasizing whether a gap exists
    at the Gamma point (k = 1) while also distinguishing between a
    complete bandgap and a Gamma-only gap.
    """
    lines = []
    any_complete = False

    lines.append(
        "Band structure analysed along the k-path M (k=0) → Γ (k=1) → K (k=2).\n"
    )

    for r in results:
        pair = f"Band {r['band_low']} - Band {r['band_high']}"

        if r["gamma_gap_thz"] > 0:
            gamma_text = (
                f"✓ Gap exists at Γ (k≈{r['gamma_k_value']:.4f}) "
                f"of {r['gamma_gap_thz']:.2f} THz."
            )
        else:
            gamma_text = (
                f"✗ No gap exists at Γ (k≈{r['gamma_k_value']:.4f})."
            )

        if r["status"] == "complete":
            any_complete = True
            lines.append(
                f"{pair}: {gamma_text} "
                f"This is a COMPLETE bandgap of {r['gap_thz']:.2f} THz "
                f"because the bands never overlap anywhere along the k-path."
            )

        elif r["status"] == "gamma_only":
            lines.append(
                f"{pair}: {gamma_text} "
                "However, this is NOT a complete bandgap because the bands "
                "overlap elsewhere along the k-path."
            )

        else:
            lines.append(
                f"{pair}: {gamma_text} "
                "The bands overlap, so there is no complete bandgap."
            )

    if not any_complete:
        lines.append(
            "\nNo complete bandgap was found. "
            "Only the presence or absence of a local gap at Γ (k=1) is reported above."
        )

    return "\n".join(lines)


def run_analysis(csv_path: str) -> Dict:
    """
    Entry point analysis_node (graph.py) will call once wired in.
    Returns {"summary": str, "bandgaps": List[Dict]} rather than
    mutating AgentState directly, so this file has no dependency on
    state.py / graph.py and can be tested standalone.
    """
    k_values, band_df = load_band_data(csv_path)
    results = analyze_bandgaps(k_values, band_df)
    summary = summarize(results)
    return {"summary": summary, "bandgaps": results}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analysis_agent.py <path_to_bands_file>")
    else:
        out = run_analysis(sys.argv[1])
        print(out["summary"])
