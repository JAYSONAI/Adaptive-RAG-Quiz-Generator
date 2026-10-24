# Quiz Showdown

**An adaptive, book-grounded exam-practice game. Pick your own study material, and get cited quiz questions in a "Who Wants to Be a Millionaire"-style interface.**

Built to prepare for the **Microsoft AI-103** exam, but it works with any PDF, DOCX, TXT, Markdown or HTML you put in the knowledge folder.

<img width="1163" height="920" alt="docslobby" src="https://github.com/user-attachments/assets/35aa4342-4f2f-4218-a88a-249f9d8ec6b2" />
<img width="1175" height="705" alt="docsgame" src="https://github.com/user-attachments/assets/12ec10df-634b-45e3-aae4-dfc1fd40a12f" />

---

## Table of Contents
- [Why this project](#why-this-project)
- [Features](#features)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [API](#api)
- [Testing](#testing)
- [Screenshots](#screenshots)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [License](#license)

## Why this project
Generic quiz generators invent facts. This one only writes questions from the books you select, cites the source of each one, and reports an error instead of making something up when the evidence is not enough.

## Features
- **Multi-source knowledge base:** select one or several books; questions come only from the selected sources. Add more books at any time.
- **Source-constrained hybrid retrieval:** per-book search with metadata filters, rank fusion, and a post-filter that drops anything from unselected sources.
- **BGE reranking:** `BAAI/bge-reranker-v2-m3` picks the most relevant passages (with a clearly reported fallback if the reranker is down).
- **7 question types:** multiple choice, true/false, fill in the blank, short answer, case study, drag and drop, interactive lab.
- **Adaptive difficulty:** easy / medium / hard policy based on recent results.
- **Duplicate prevention:** within the current quiz and against supplied history.
- **Strict validation:** JSON schema (Pydantic), citation checks, a lexical grounding check, and bounded regeneration. Failed questions are rejected, never fabricated.
- **Model dropdown:** local Ollama models and Groq models, with a configurable default.
- **Resilient LLM layer:** classified HTTP 429 handling, bounded retries with exponential backoff and jitter, request coalescing, caching, token budgeting, and an opt-in, always-reported fallback to a local model.
- **One-click startup:** `START.bat` sets up the environment, indexes new or changed books in the background, warms up the models and opens the dashboard.
- **Game-show dashboard:** prize ladder, lifelines (50:50, simulated poll, skip), lock-in suspense, optional timer, sound, confetti and keyboard controls.

## How it works
```
Selected books
   |
   v
Per-source hybrid retrieval (vector + keyword, metadata filter)
   |
   v
Isolation check (drop any chunk from an unselected source)
   |
   v
BGE reranker (top N passages)
   |
   v
LLM question writer (Groq or Ollama, JSON mode)
   |
   v
Validation: schema -> citations -> grounding -> duplicates -> regenerate if needed
   |
   v
Learner view (answers hidden until you lock in) -> game dashboard
```

## Tech stack
| Area | Technology | Purpose |
|---|---|---|
| Language / API | Python 3.10+, FastAPI, Uvicorn | Backend and REST API |
| Validation | Pydantic v2 | Typed question schemas, strict parsing |
| Vector store | ChromaDB (Qdrant supported) | Document embeddings and filtered search |
| Embeddings | Ollama `bge-m3` | Document and query vectors |
| Reranking | FlagEmbedding, `bge-reranker-v2-m3` | Passage relevance scoring |
| LLMs | Groq API, Ollama (e.g. `llama3.2:3b`) | Question generation |
| Documents | pypdf, python-docx | Text extraction |
| HTTP | httpx | Service and LLM calls |
| Frontend | HTML, CSS, vanilla JavaScript, WebAudio | Game-show dashboard |
| Tests | pytest, jsdom | Backend and dashboard tests |

## Project structure
```
quiz_agent/
├── START.bat                 One-click launcher (Windows)
├── quiz_server.py            App entry point: serves dashboard + API, auto-index, warm-up
├── .env.example              Settings template (copy to .env)
├── requirements-quiz.txt     Server dependencies
├── requirements-reranker.txt Reranker dependencies
├── agents/library/knowledge/ PUT YOUR BOOKS HERE (add more shelves: agents/<name>/knowledge/)
├── app/quiz/
│   ├── service.py            Orchestrates the pipeline
│   ├── retrieval.py          Per-source hybrid retrieval and fusion
│   ├── reranker.py           BGE reranker (in-process or HTTP service)
│   ├── llm.py                Groq/Ollama clients, retries, budgets, fallback, model list
│   ├── prompts.py            Prompt construction
│   ├── schemas.py            Question types and request/response models
│   ├── validator.py          Schema, citation and grounding checks
│   ├── adaptive.py           Difficulty policy
│   ├── duplicates.py         Duplicate detection
│   ├── indexer.py            Built-in document indexer
│   ├── envfix.py             .env auto-repair
│   ├── routes.py             API endpoints
│   └── sources.py, adapters.py, wiring.py, ports.py, config.py
├── frontend/quiz.html        Game-show dashboard
├── tools/reranker_service.py Local reranker HTTP service
├── eval/quiz_eval.py         Quiz quality evaluation
└── tests/                    pytest suite
```

## Installation
**Prerequisites:** Windows, Python 3.10+, [Ollama](https://ollama.com) running. Optional: a [Groq](https://console.groq.com) API key.

1. Clone the repository and open the folder.
   ```
   git clone https://github.com/<your-username>/quiz-showdown.git
   cd quiz-showdown
   ```
2. Pull the models:
   ```
   ollama pull bge-m3
   ollama pull llama3.2:3b
   ```
3. (Recommended) Create the reranker environment once. It must be able to import `FlagEmbedding`. By default the launcher looks for `%USERPROFILE%\.venv-reranker`.
   ```
   py -3 -m venv %USERPROFILE%\.venv-reranker
   %USERPROFILE%\.venv-reranker\Scripts\pip install -r requirements-reranker.txt
   ```
4. Put your books in `agents\library\knowledge\`.
5. (Optional) Add `GROQ_API_KEY=...` to `.env` after the first run.

## Usage
1. Double-click **`START.bat`**. It creates `.env` if needed, installs packages, starts the reranker window, indexes your books and opens http://127.0.0.1:8800.
2. In the lobby, books are pre-selected. Choose a model from the dropdown, question types, count and difficulty.
3. Press **PLAY**.
4. Answer with the mouse or keyboard (A-D / 1-4, T/F, Enter to lock in). Use lifelines if you get stuck.
5. Review your results, citations and the model used on the results screen.

Keep the black START.bat window open while you play.

## Configuration
Copy `.env.example` to `.env` (done automatically). Key settings:

| Variable | Meaning |
|---|---|
| `QUIZ_LLM_PROVIDER`, `QUIZ_LLM_MODEL` | Default model (e.g. `ollama` / `llama3.2:3b`) |
| `GROQ_API_KEY` | Enables Groq models in the dropdown |
| `QUIZ_LLM_FALLBACK` | `true` allows a reported fallback to a local model on rate limits |
| `QUIZ_LLM_MAX_RETRIES`, `QUIZ_LLM_MAX_WAIT` | Bounds for 429 retries |
| `RERANKER_ENABLED`, `RERANKER_TIMEOUT`, `RERANKER_FALLBACK` | Reranker behaviour |
| `AGENTS_DIR`, `CHROMA_PATH` | Where books and the vector store live |

Never commit your `.env`. Only `.env.example` belongs in the repository.

## API
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/quiz/agents` | List knowledge shelves |
| GET | `/api/quiz/sources?agent=` | List indexed books |
| GET | `/api/quiz/models` | Models for the dropdown |
| GET | `/api/quiz/status` | Model, Ollama, reranker and index status |
| GET | `/api/quiz/health` | Health check |
| POST | `/api/quiz/generate` | Generate a quiz |

```json
{"agent":"library","selected_source_ids":["src_1a2b3c"],"type":"mixed","count":5,
 "difficulty":"medium","include_answers":false}
```

## Testing
```
python -m pytest
```
The suite (about 175 tests) uses in-memory Chroma/Qdrant and scripted mock servers for the LLM, Ollama and the reranker, so it needs no network. The dashboard was checked with jsdom against the real API.


- **Lobby:** select books, choose a model from the dropdown, pick question types, and press PLAY.
- **Game screen:** a cited question with answer plates, prize ladder and lifelines.
- **Results:** score, source citations, and which model wrote the quiz.

## Known limitations
- The grounding check is lexical: it catches unsupported answers, not subtle factual errors.
- Scanned (image-only) PDFs are reported as failed because OCR is not included.
- The "Poll" lifeline is simulated and labelled as such.
- Windows launchers are provided; other platforms can run `python quiz_server.py` manually.
- Output quality depends on the model. Small local models can struggle with complex question types.

## Roadmap
- OCR for scanned PDFs
- Server-side grading and learner history
- Spaced repetition and weak-topic review
- Export to PDF / Anki
- Docker setup and cross-platform launcher
- Evaluation dashboard for question quality


