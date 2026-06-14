# Turing Engine: Project Flow and Architecture Details

## Overview
**Turing Engine** is an advanced AI pipeline designed for **Autonomous Causal Discovery & Cross-Domain Abstraction**. The primary goal of the system is to ingest raw datasets or text, map their underlying causal topology, strip away domain-specific semantics, and then search external domains (like biology, physics, or supply chains) for isomorphic structural solutions. Finally, it validates proposed interventions through dynamic simulations.

## Project Structure
The repository is structured as a full-stack application with two main components:
1. **Frontend (`src/`)**: A modern web application built with **Next.js**, **React**, and **Tailwind CSS**. It serves as the user interface for launching discovery pipelines, uploading datasets, and viewing real-time pipeline status.
2. **Backend (`python-engine/`)**: A robust API built with **FastAPI** in Python. It handles the heavy lifting, including data parsing, graph mathematics, LLM integration, and causal simulations.

---

## The Workflow / Pipeline

### 1. Initialization (User Input)
- The user interacts with the Next.js Frontend landing page (`src/app/page.tsx`).
- They upload a dataset (e.g., CSV, JSON, XLSX) or a text document (PDF, MD, TXT).
- They provide a **Research Hypothesis / Objective** as a text prompt.
- The frontend calls the backend to initialize a `Run` via the `/api/runs` router and uploads the dataset. The user is then redirected to a live dashboard for that specific run.

### 2. Processing Layers (Backend Architecture)
The Python engine is divided into four distinct processing layers, each managed by its own router and dedicated services:

#### **Layer 1: Data Ingestion (`/api/layer1`)**
- Receives the uploaded files.
- Uses tools like `pandas`, `openpyxl`, and `pdfplumber` to extract structured data from CSVs/Excel or unstructured text from PDFs/Markdown.
- Normalizes the input into a unified format ready for causal analysis.

#### **Layer 2: Agent Simulation & Causal Discovery (`/api/layer2`)**
- This is the core mathematical and simulation engine.
- Uses libraries like `causal-learn` and `scikit-learn` to perform causal discovery (e.g., using the PC Algorithm) to map the causal graph of the ingested data.
- Employs **Do-Calculus interventions** to simulate what happens if certain variables in the system are altered.
- Features an agent simulation loop to test hypotheses against the causal model.

#### **Layer 3: Cross-Domain Search (`/api/layer3`)**
- Once the causal graph is built, this layer uses `networkx` to represent the system as a mathematical graph.
- It strips away the specific "domain semantics" (e.g., turning "revenue drops when inventory is low" into a pure graph structure).
- It then uses LLMs (`litellm`) and search tools (`httpx`) to look for **isomorphic structures** (similar graph topologies) in completely different domains (e.g., how a biological cell handles resource starvation) to propose novel solutions.

#### **Layer 4: Report Generation (`/api/layer4`)**
- Synthesizes the findings from the causal discovery, the cross-domain isomorphic matches, and the simulation results.
- Generates a final, comprehensive report explaining the bottleneck, the proposed intervention, and the cross-domain analogy used to solve it.

### 3. Output and Dashboard
- Throughout the process, the backend updates the state of the "Run".
- The frontend dashboard polls or listens to these updates to show the user real-time progress across all four layers.
- Once complete, the user can review the discovered causal graph, the simulated interventions, and the final generative report.

### The AI Agents (Layer 2 Simulation)
During the Layer 2 simulation phase, the backend employs a Bayesian Optimization cycle managed by an **Orchestrator**. The orchestrator utilizes three specialized AI "ReAct" agents to propose different interventions on the causal graph, simulating how to maximize a specific target outcome:

1. **Explorer Agent (`agent_explorer.py`)**: Focuses on boundary testing. It takes the current best values and pushes each variable to the farthest extreme of its search space. Its goal is to find where performance degrades or to discover hidden "cliffs" in the system.
2. **Exploiter Agent (`agent_exploiter.py`)**: Focuses on maximizing the target yield based on historical data and current trends, making safe, optimizing adjustments.
3. **Contrarian Agent (`agent_contrarian.py`)**: Challenges the consensus by proposing counter-intuitive values.

In each iteration, these three agents submit their proposed interventions to a `DoCalculusSimulator`. The orchestrator evaluates which agent's proposal yields the highest ambiguity reduction or the best predicted outcome, and selects that intervention for the next round.

## Technology Stack Summary
- **Frontend**: Next.js (App Router), React, Tailwind CSS, TypeScript.
- **Backend API**: FastAPI, Uvicorn, Pydantic.
- **Data & Math**: Pandas, Scikit-Learn, Numpy, NetworkX.
- **Causal Analysis**: Causal-Learn (PC Algorithm), Do-Calculus principles.
- **LLM Integration**: LiteLLM (supports swapping between Claude, GPT-4o, Ollama), Sentence-Transformers.
- **External Integration**: HTTPX for search engines.
