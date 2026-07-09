"""
agents/analysis_agent.py

Reads the exported band-structure data file and reports bandgaps
between every consecutive pair of bands.

FILE FORMAT (confirmed against a real bands.txt export -- this is
COMSOL's "Global Point Evaluation" text export, NOT a delimited
table):

    % Data (real(freq)/1[THz] (1) @ 1: Eigenfrequency=285.21 THz, p=0)
    285.2095642909698
    % Data (real(freq)/1[THz] (1) @ 2: Eigenfrequency=310.11 THz, p=0)
    310.1082786724921
    ...

Each data point is a '%'-comment header line giving the sweep
parameter (labeled "p" in the export -- this is the same thing
confirmed earlier as "k", ranging 0 -> 2 with k=1 = Gamma, path
M(k=0) -> Gamma(k=1) -> K(k=2)), followed by ONE line containing the
plain real-part frequency value in THz. The comment line's
"Eigenfrequency=X+Yi THz" expression is NOT parsed -- the line right
below it is already real(freq) alone, which is exactly what's needed.

Rows are grouped by consecutive p-value: all lines sharing the same p
are one k-point's set of bands, in increasing-frequency order as
COMSOL wrote them (band_1, band_2, ...). If different p-values end up
with different numbers of bands (e.g. a k-point where the solver
found fewer eigenmodes), this is NOT silently truncated -- it's
raised as an error, since that would typically indicate a solver
convergence problem worth knowing about, not something to paper over.

Bandgap definition (confirmed): between band n and band n+1, a
COMPLETE bandgap exists only if max(band_n) across the entire k-path
is less than min(band_n+1) across the entire k-path. The gap size is
that difference.

Honesty behavior: if bands overlap somewhere along the path but a
local gap still exists at the Gamma row (p=1), this is reported
explicitly as "gap only at Gamma, not complete" -- never reported as
though it were a complete bandgap.
"""

import re
import pandas as pd
from typing import List, Dict, Tuple


GAMMA_K_VALUE = 1.0

_DATA_LINE_RE = re.compile(r"^%\s*Data.*?p\s*=\s*([-\d.eE]+)\s*\)\s*$")


def load_band_data(csv_path: str) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Parses COMSOL's Global Point Evaluation text export.

    Returns (k_values, band_df):
        k_values -- one row per distinct p (k-path parameter, 0 to 2),
                    in the order first encountered in the file
        band_df  -- one column per band (band_1, band_2, ...), values
                    already real(freq) in THz
    """
    with open(csv_path, "r") as f:
        lines = f.readlines()

    p_to_freqs: Dict[float, List[float]] = {}
    order: List[float] = []

    i = 0
    n_lines = len(lines)
    while i < n_lines:
        match = _DATA_LINE_RE.match(lines[i].strip())
        if match:
            p_val = float(match.group(1))
            i += 1
            if i >= n_lines:
                raise ValueError(
                    f"File ended right after a '% Data' header line "
                    f"(p={p_val}) with no frequency value following it."
                )
            freq = float(lines[i].strip())
            if p_val not in p_to_freqs:
                p_to_freqs[p_val] = []
                order.append(p_val)
            p_to_freqs[p_val].append(freq)
        i += 1

    if not order:
        raise ValueError(
            "No '% Data ... p=...)' lines found -- this file doesn't "
            "match the expected COMSOL Global Point Evaluation export "
            "format at all."
        )

    band_counts = {p: len(freqs) for p, freqs in p_to_freqs.items()}
    distinct_counts = set(band_counts.values())
    if len(distinct_counts) > 1:
        raise ValueError(
            f"Inconsistent number of bands across k-points: {band_counts}. "
            f"This usually means the solver found a different number of "
            f"eigenmodes at some k-point(s) -- check convergence before "
            f"trusting the bandgap analysis, rather than truncating "
            f"silently."
        )

    n_bands = distinct_counts.pop()

    k_values = pd.Series(order, name="k")
    band_data = {
        f"band_{b + 1}": [p_to_freqs[p][b] for p in order]
        for b in range(n_bands)
    }
    band_df = pd.DataFrame(band_data)

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
    Builds a plain-language summary that never overstates a
    Gamma-only gap as a complete bandgap.
    """
    lines = []
    any_complete = False

    for r in results:
        pair = f"band {r['band_low']}-{r['band_high']}"
        if r["status"] == "complete":
            any_complete = True
            lines.append(
                f"{pair}: complete bandgap of {r['gap_thz']:.2f} THz "
                f"(bands do not overlap anywhere along the k-path)."
            )
        elif r["status"] == "gamma_only":
            lines.append(
                f"{pair}: NOT a complete bandgap -- bands overlap "
                f"somewhere along the k-path, though a local gap of "
                f"{r['gamma_gap_thz']:.2f} THz exists at Gamma "
                f"(k={r['gamma_k_value']:.4f}). "
                f"This likely reflects an unresolved modeling issue "
                f"rather than a genuine full bandgap."
            )
        else:
            lines.append(f"{pair}: no gap found (bands overlap throughout).")

    if not any_complete:
        lines.append(
            "\nNo complete bandgap was found between any band pair. "
            "If a complete gap (e.g. near 318 THz) is expected, check "
            "geometry/mesh convergence rather than treating a Gamma-only "
            "gap as the real result."
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
