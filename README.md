# COMSOL Copilot

An **Agentic AI framework** for automating photonic crystal band structure simulations using **COMSOL Multiphysics**, **LangGraph**, **Google Gemini**, and **Retrieval-Augmented Generation (RAG)**.

The system enables users to interact with COMSOL using natural language, automatically extract simulation parameters from research papers, execute simulations through COMSOL Batch Mode, perform parameter sweeps, analyze generated results, and answer domain-specific theory questions using a custom RAG pipeline.

---

# Features

## Natural Language Simulation

Generate photonic crystal band structures using natural language.

Example

```
Generate a band structure with
a1 = 420 nm
b = 123 nm
rf = 1.048
```

The AI automatically

- Understands the request
- Extracts simulation parameters
- Validates inputs
- Executes COMSOL
- Returns generated outputs

---

## Research Paper Assisted Simulation

Upload a research paper and automatically reproduce the reported simulation.

The AI extracts

- Lattice parameter (a1)
- Geometry parameter (b)
- Radius factor (rf)

from the uploaded paper using Google Gemini before launching the COMSOL simulation.

Example

```
Upload this paper and reproduce the reported band structure.
```

---

## Radius Factor Sweep

Perform automated parameter sweeps without manually editing the COMSOL model.

Example

```
Sweep radius factor from
0.90
to
1.20
with step
0.02
```

The system

- Generates multiple COMSOL runs
- Stores each solved model
- Saves generated plots
- Saves numerical band data

---

## Theory Assistant (RAG)

The project includes a Retrieval-Augmented Generation (RAG) pipeline built using uploaded research papers and documentation.

Instead of relying only on the LLM's internal knowledge, answers are grounded in the uploaded literature.

Example questions

```
What is Floquet periodicity?

Explain Bloch boundary conditions.

Why are PMLs used?

What is the irreducible Brillouin zone?

What are TE and TM modes?

How are photonic bandgaps formed?

What is the Γ-K-M-Γ path?

How does the Eigenfrequency solver work?

What is the Plane Wave Expansion method?

Why do flat bands occur?
```

---

## Automatic Simulation Analysis

After each successful COMSOL simulation, the analysis agent processes the exported numerical data and generates a concise summary of the simulation.

The analysis currently includes

- Reading exported band data
- Detecting bandgaps
- Frequency range estimation
- Automatic summary generation

---

## Simulation Comparison

The project maintains the history of simulations performed during the current session.

Users can compare previously generated simulation runs through natural language queries.

Example

```
Compare the first and latest simulation.

Which radius factor produced the larger bandgap?

Compare the sweep results.
```

---

# Agent Architecture

The system consists of multiple specialized AI agents working together.

---

## Intent Parser Agent

Uses Google Gemini to convert natural language into structured simulation requests.

Responsibilities

- Intent recognition
- Parameter extraction
- Paper understanding
- Question preprocessing

---

## Planner Agent

Determines which workflow should be executed.

Supported workflows

- Single simulation
- Radius sweep
- Paper-based simulation
- Theory question (RAG)
- Simulation comparison

---

## Validation Agent

Ensures that

- Simulation parameters are valid
- Sweep ranges are valid
- Required inputs are present

before COMSOL execution begins.

---

## COMSOL Execution Agent

Responsible for running COMSOL Batch Mode.

Functions

- Overrides global parameters
- Executes Batch Job
- Saves solved model
- Exports band diagram
- Exports numerical data
- Stores execution logs

---

## Analysis Agent

Processes COMSOL output files and generates simulation summaries.

Current functionality

- Reads exported band data
- Computes bandgap information
- Produces natural-language summaries

---

## RAG Agent

Answers theory questions using uploaded research papers and documentation.

Pipeline

```
User Question

↓

Retrieve Relevant Chunks

↓

Gemini

↓

Grounded Response
```

---

## Comparison Agent

Compares simulation runs generated during the current application session and produces a summary highlighting differences between the results.

---

# Overall Workflow

```
                    User
                      │
                      ▼
             Intent Parser Agent
                      │
                      ▼
                Planner Agent
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
  COMSOL Run       RAG Query     Comparison
        │             │             │
        ▼             ▼             ▼
COMSOL Batch     FAISS Retrieval   Previous Runs
        │             │             │
        ▼             ▼             ▼
 Export Results     Gemini        Summary
        │
        ▼
 Analysis Agent
        │
        ▼
 Final Response
```

---

# Project Structure

```
comsol-copilot/

├── agents/
│   ├── analysis_agent.py
│   ├── intent_parser.py
│   └── planner.py
│
├── execution/
│   └── executor.py
│
├── rag/
│   ├── embed.py
│   ├── retrieve.py
│   ├── index.faiss
│   └── chunks.pkl
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
├── papers/
│
├── graph.py
├── state.py
├── app.py
└── base_model.mph
```

---

# COMSOL Requirements

The supplied COMSOL model should already contain

- Geometry
- Materials
- Physics
- Mesh
- Eigenfrequency Study
- Batch Job
- Export Nodes

The AI **does not modify the COMSOL model tree.**

Instead, it overrides the global parameters using

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

Global Parameters

```
a1
b
rf
```

Study Tag

```
std1
```

Batch Tag

```
b1
```

Required Export Nodes

```
band_png
bands
```

---

# Running

```
python app.py
```

Example

```
Generate a band structure
with a1 = 420
b = 123
rf = 1.048
```

---

# Outputs

Each simulation produces

```
models/
    solved_model.mph

outputs/png/
    band_structure.png

outputs/csv/
    bands.txt

outputs/reports/
    execution.log
```

---

# Technology Stack

- Python
- COMSOL Multiphysics 5.6
- LangGraph
- Google Gemini
- FAISS
- Sentence Transformers
- Pandas
- NumPy
- Matplotlib
- Retrieval-Augmented Generation (RAG)

---

# Current Limitations

- Supports a predefined COMSOL model
- Requires configured Batch Job and Export Nodes
- Comparison is limited to simulations generated during the current session
- Currently designed for C6 photonic crystal band structure simulations

---

# Future Improvements

- Web-based graphical interface
- Drag-and-drop result analysis
- Analysis of uploaded COMSOL outputs
- Interactive band diagram visualization
- Automatic report generation
- Bayesian optimization
- Multi-objective optimization
- Support for multiple COMSOL models

---

# Acknowledgements

Built using

- COMSOL Multiphysics 5.6
- Google Gemini
- LangGraph
- FAISS
- Sentence Transformers

to provide an Agentic AI assistant for photonic crystal simulation, analysis, and scientific question answering.
