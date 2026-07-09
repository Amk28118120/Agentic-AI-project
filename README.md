# COMSOL Copilot

An AI-assisted workflow for automating photonic crystal band structure simulations in COMSOL Multiphysics.

The project combines a Large Language Model (LLM), LangGraph agent workflow, and COMSOL Batch mode to allow users to generate, analyze, and compare photonic crystal band structures using natural language.

---

## Features

- Natural language interface
- Automatic parameter extraction
- COMSOL Batch automation
- Single simulation execution
- Radius factor parameter sweeps
- Automatic export of:
  - solved `.mph`
  - band structure image
  - band data
- Automatic bandgap analysis
- Multi-run comparison framework

---

## Project Structure

```
comsol-copilot/
│
├── agents/
│   ├── intent_parser.py
│   ├── planner.py
│   ├── analysis_agent.py
│
├── execution/
│   └── executor.py
│
├── tools/
│   ├── comsol_runner.py
│   └── validator.py
│
├── outputs/
│   ├── csv/
│   ├── png/
│   └── reports/
│
├── models/
│
├── graph.py
├── state.py
├── app.py
│
└── base_model.mph
```

---

# Workflow

```
User
   │
   ▼
Intent Parser (Gemini)
   │
   ▼
Planner
   │
   ├── Validate Parameters
   │
   ├── Single Run
   │
   └── Parameter Sweep
            │
            ▼
      COMSOL Batch
            │
            ▼
     Export PNG + Band Data
            │
            ▼
     Analysis Agent
            │
            ▼
     Final Response
```

---

# Simulation Parameters

The current implementation supports

| Parameter | Description |
|-----------|-------------|
| a1 | Lattice parameter (nm) |
| b | Geometry parameter (nm) |
| rf | Radius scaling factor |

Example prompt

```
Generate a band structure with
a1 = 420
b = 123
rf = 1.048
```

or

```
Sweep rf from 0.9 to 1.2 with step 0.02
```

---

# Requirements

- Python 3.11+
- COMSOL Multiphysics 5.6
- Google Gemini API Key
- Windows

Python packages

```
langgraph
langchain
google-genai
pandas
numpy
matplotlib
python-dotenv
```

Install

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env`

```
GOOGLE_API_KEY=YOUR_API_KEY
```

---

# COMSOL Model Requirements

The supplied COMSOL model must already contain:

- Geometry
- Materials
- Physics
- Mesh
- Study
- Solver
- Batch Job
- Export Nodes

The Python code **does not modify the COMSOL model tree.**

It only overrides global parameters using

```
-pname
-plist
```

before executing

```
-job b1
```

---

# Required COMSOL Configuration

Global parameters

```
a1
b
rf
```

Study tag

```
std1
```

Batch tag

```
b1
```

Export nodes

```
band_png
bands
```

The Batch node should contain

```
Solution
Export PNG
Export Text
```

---

# Running

```
python app.py
```

Example

```
Generate a band structure
with a1=420
b=123
rf=1.048
```

---

# Output

Each simulation generates

```
models/
    run_xxx.mph

outputs/png/
    run_xxx.png

outputs/csv/
    run_xxx.txt

outputs/reports/
    run_xxx.log
```

---

# Agent Architecture

### Intent Parser

Uses Gemini to convert natural language into structured parameters.

Example

```
Input

Generate a band structure
with a1=420
b=123
rf=1.048

↓

{
    task: "single",
    a1:420,
    b:123,
    rf:1.048
}
```

---

### Planner

Determines whether the request is

- Single simulation
- Parameter sweep
- Analysis
- Comparison

---

### Executor

Runs COMSOL using

```
comsolbatch
```

with overridden parameters.

---

### Analysis Agent

Reads exported band data

Computes

- bandgap
- frequency ranges
- summary statistics

and generates a textual report.

---

### Comparison Agent

Currently implemented as a placeholder.

Future versions will compare multiple simulation results automatically.

---

# Notes

The automation never edits the COMSOL geometry.

Instead it

1. Loads the base model
2. Overrides global parameters
3. Executes the Batch job
4. Saves a solved copy
5. Moves exported files into run-specific folders

This ensures the original COMSOL model always remains unchanged.

---

# Current Limitations

- Fixed COMSOL model structure
- Requires predefined export nodes
- Comparison agent is not fully implemented
- Supports one photonic crystal template

---

# Future Improvements

- Web interface
- Drag-and-drop PDF upload
- Automatic geometry extraction from papers
- Interactive band structure viewer
- Multi-objective optimization
- Bayesian parameter search
- Automatic report generation
- Multi-model support

---

# Acknowledgements

Built using

- COMSOL Multiphysics 5.6
- LangGraph
- Google Gemini
- Python

for AI-assisted photonic crystal simulation and analysis.
