# Adaptive multi-source quiz agent

Pick one or more books, set options, and get questions written only from those books.

## What was built (and how it is verified)
| Area | Module | Verified |
|---|---|---|
| Source registry (every file in `agents/<agent>/knowledge/` is a book; status from the index) | `app/quiz/sources.py` | tests, real Chroma |
| Source-constrained retrieval, RRF fusion, post-filter before rerank | `app/quiz/retrieval.py` | tests, real Chroma + Qdrant (in-memory) |
| BGE reranker (in-process or local HTTP service) | `app/quiz/reranker.py`, `tools/reranker_service.py` | tests with fakes; **real model not run here** |
| 7 typed question schemas + answer hiding | `app/quiz/schemas.py` | tests |
| Output validator (citations, grounding, duplicates) | `app/quiz/validator.py` | tests |
| Adaptive difficulty, policy-driven | `app/quiz/adaptive.py` | tests |
| Orchestration | `app/quiz/service.py` | tests |
| API | `app/quiz/routes.py` | tests (FastAPI TestClient) |
| Dashboard | `frontend/quiz.html` | jsdom: sample mode (7 types) + live mode against the real router |
| Evaluation | `eval/quiz_eval.py` | unit tests; needs your fixtures |

Retrieval flow: per selected book, run each retriever with a metadata filter -> drop anything whose source is missing or unselected -> fuse -> rerank (BGE) -> top N -> LLM -> strict JSON parse -> schema, citation, grounding, duplicate checks -> bounded regeneration -> learner-facing view.

## Quick start: one click
1. Install Python 3.10+ and Ollama; run `ollama pull bge-m3` and `ollama pull llama3.2:3b`.
2. Put books in `agents\library\knowledge\` (PDF, DOCX, TXT, MD, HTML).
3. Double-click **START.bat**. It creates/repairs `.env`, installs packages (only when needed), starts the reranker window, indexes new/changed books in the background, warms up the models and opens the dashboard.
4. In the dashboard everything is pre-selected: just press **PLAY**. Pick a model from the dropdown (default comes from `QUIZ_LLM_PROVIDER`/`QUIZ_LLM_MODEL`). Groq models appear once `GROQ_API_KEY` is set in `.env`.
New book later? Drop it in the folder; the server indexes it on next start (or `POST /api/quiz/index`). Scanned PDFs are reported as failed (no OCR).

### Game controls
A-D / 1-4 pick an answer, Enter locks in, T/F for true/false. Lifelines: 50:50, Poll (simulated and labelled as such), Skip.

### Groq 429 / empty-answer handling (`app/quiz/llm.py`)
- 429s are classified from the response body and headers (per-minute vs daily, tokens vs requests). The server log line is `LLM HTTP 429 provider=... request_id=... limit=... retry_after=... headers=... body=...` (keys and Authorization are never logged). Check it to see which limit you hit.
- Retries are bounded (`QUIZ_LLM_MAX_RETRIES`, `QUIZ_LLM_MAX_WAIT`), honour Retry-After / reset headers with backoff and jitter; a daily quota fails immediately with the reset time.
- One LLM call at a time, identical in-flight requests are coalesced, results cached briefly (`QUIZ_LLM_CACHE_TTL`).
- `finish_reason=length` retries once with a doubled budget; the `reasoning` field is never used as an answer.
- Switching to Ollama on failure is **opt-in** (`QUIZ_LLM_FALLBACK=true`) and always reported in the results.

## Using your existing project instead (optional)
1. Unzip this folder anywhere. Double-click `run_standalone.bat`; on first run it creates `.env` and opens it.
2. Edit `.env`: set `AGENTS_DIR` and `CHROMA_PATH` to your real project's `agents` and `data\chroma` folders,
   choose `QUIZ_LLM_PROVIDER` / `QUIZ_LLM_MODEL`, and put your API key in `QUIZ_LLM_API_KEY` (not needed for Ollama).
3. Run `run_standalone.bat` again, open http://127.0.0.1:8800 and switch to **Live API**.
Your project must already have indexed the books (its normal startup sync does this) with the same embedding model (`bge-m3`).

## Installing into your project instead
1. Copy `app/quiz/`, `tools/reranker_service.py`, `eval/quiz_eval.py`, `frontend/quiz.html`, `tests/test_*quiz*` (and the quiz tests) into the matching folders.
2. `pip install -r requirements-quiz.txt`; append `.env.quiz.example` to `.env`.
3. In `main.py`:
   ```python
   from app.quiz.wiring import mount
   mount(app, lambda system, user: my_llm_call(system, user))   # return the model's raw text
   ```
   `my_llm_call` should reuse your existing `app/llm` client and ask for JSON output.
4. Serve `frontend/quiz.html` with your other static pages (or open it; set the API address under Connection).

**You must check these assumptions against your code** (they were not visible when this was written):
- chunk metadata field holding the file name (`QUIZ_SOURCE_META_KEY`, default `source`),
- collection name per agent (`QUIZ_COLLECTION_TEMPLATE`),
- Qdrant payload text key (`text`).

## Reranker on Windows (PowerShell)
Your `.venv-reranker` is not visible to the app's interpreter, so run it as a service:
```powershell
# start_reranker.bat installs fastapi and uvicorn if they are missing (the model must already be cached)
& "$env:USERPROFILE\.venv-reranker\Scripts\pip.exe" install fastapi uvicorn
.\start_reranker.bat            # http://127.0.0.1:8765, localhost only
# in .env: RERANKER_PROVIDER=http
Invoke-RestMethod http://127.0.0.1:8765/health
```
`HF_HUB_OFFLINE=1` stops runtime downloads. If the service is down, requests fail with `reranker_unavailable` unless `RERANKER_FALLBACK=true`, in which case the response says reranking was **not applied**.

## Starting everything
`start_quiz.bat` opens the reranker in its own window, then runs your existing `start.bat` (unchanged). Use `start.bat` alone if reranking is disabled.

## API
`GET /api/quiz/agents` | `GET /api/quiz/sources?agent=` | `GET /api/quiz/health` | `POST /api/quiz/generate`
```json
{"agent":"clientA","selected_source_ids":["src_1a2b3c"],"type":"mixed","count":5,"topic":"optional",
 "adaptive":true,"include_answers":false,"feedback_mode":"end_of_exam","min_per_source":1}
```
Statuses: `ok`, `partial`, `insufficient_context`, `configuration_error` (HTTP 422), `error` (HTTP 502; codes such as `retrieval_failed`, `reranker_unavailable`, `generator_failed`, `generation_invalid`). Technical failures are never reported as insufficient context.

## Adding more books
Put the file in `agents/<agent>/knowledge/` and restart; startup sync indexes it and it appears as a new spine. Optional titles: `knowledge/sources.json` -> `{"file.pdf": {"title": "Nice title"}}`.

## Limits you should know
- Grounding check is lexical (answer words must appear in cited chunks). It catches unsupported answers, not subtle factual errors.
- Duplicate prevention covers the supplied history and the current batch only.
- The game dashboard requests answers (it reveals them as you play); the API's answer-hiding exam mode has no server-side grading.
- The dashboard sends learner history from the browser. Provide a `LearnerStateProvider` for a trusted server-side source; nothing here writes learner state.
- Not run: the real BGE model, Ollama, your LLM, your Chroma/Qdrant data, `run_eval.bat`, and your 168 existing tests.
