#Quiz Showdown
Adaptive RAG quiz generator that writes cited, validated exam questions only from the books you choose, played in a game-show-style dashboard. Built for Microsoft AI-103 prep.
Project Overview

What it does: Indexes your PDF, DOCX, TXT, Markdown and HTML study material, then generates practice questions from only the books you select. Each question cites its source and passes schema, citation, grounding and duplicate checks before you see it.

Why it was built: To practice for the Microsoft AI-103 exam with questions grounded in real study material instead of invented facts. It is not tied to one subject: change the files and it adapts.

Who it is for: Exam candidates, students, teachers and trainers who want self-testing from their own notes; developers learning RAG.

Key benefits:

Questions trace back to your material.
Works with several books at once; add more any time.
Runs locally (Ollama) or with Groq models.
Honest failure: an error message, never made-up questions.

Features
Multi-source knowledge base: select any combination of books.
Hybrid retrieval with source isolation: per-book filtered search; chunks from unselected books are dropped.
BGE reranking: picks the most relevant passages; fallback is reported, not hidden.
7 question types: multiple choice, true/false, fill in the blank, short answer, case study, drag and drop, interactive lab.
Adaptive difficulty: easy, medium, hard based on recent performance.
Duplicate prevention: within a quiz and against history.
Strict validation: Pydantic schemas, citation and grounding checks, bounded regeneration.
Model dropdown: local Ollama and Groq models with a default.
Resilient LLM layer: 429 classification, backoff with jitter, coalescing, caching, token budgets, opt-in fallback.
One-click startup: auto-setup, background indexing, model warm-up.
Game-show dashboard: ladder, lifelines, timer, sound, animations, keyboard controls.
5. Tech Stack
Python, FastAPI, Uvicorn: backend and REST API.
Pydantic v2: typed question schemas and strict parsing.
ChromaDB (Qdrant supported): vector storage with metadata filters.
Ollama (bge-m3): embeddings; also local LLMs such as llama3.2:3b.
FlagEmbedding (bge-reranker-v2-m3): reranking.
Groq API: hosted LLMs such as openai/gpt-oss-20b.
pypdf, python-docx: document text extraction.
httpx: HTTP clients.
HTML, CSS, JavaScript, WebAudio: dashboard.
pytest, jsdom: tests.
6. Folder Structure
START.bat: one-click launcher.
quiz_server.py: server entry point.
agents/<shelf>/knowledge/: where you put books; each shelf is a separate library.
app/quiz/: the engine (retrieval, reranker, LLM layer, validation, adaptive logic, indexer, API routes).
frontend/quiz.html: game-show dashboard.
tools/reranker_service.py: local reranker service.
eval/: quiz quality evaluation.
tests/: pytest suite.
7. Installation Guide
Install Python 3.10+ and Ollama.
git clone https://github.com/<your-username>/quiz-showdown.git and open the folder.
ollama pull bge-m3 and ollama pull llama3.2:3b.
Create the reranker environment once: py -3 -m venv %USERPROFILE%\.venv-reranker, then %USERPROFILE%\.venv-reranker\Scripts\pip install -r requirements-reranker.txt.
Put your books in agents\library\knowledge\.
(Optional) add GROQ_API_KEY to .env after the first run.
8. Usage Guide

Double-click START.bat, wait for the dashboard to open, pick a model, press PLAY. Keep the black window open while playing.

9. Screenshots Section (captions)
Lobby: "Choose your books, model, question types and difficulty. Everything is pre-selected, so you just press PLAY."
Game screen: "A source-cited question with answer plates, prize ladder and lifelines."
Reveal: "Correct answers show the explanation and the book the question came from."
Results: "Score, source citations and the model that wrote the quiz."
Status chips: "Live status of the model, Ollama, reranker and book index."
10. Example Workflow
Add ai-103-notes.pdf and azure-ai-guide.docx to the knowledge folder.
Double-click START.bat; both books are indexed in the background.
In the lobby, keep both books selected, choose groq: openai/gpt-oss-20b, 10 questions, mixed types, medium.
Press PLAY. The server retrieves from each book, reranks, writes and validates the questions.
Answer each question, lock in, see the explanation and citation.
On the results screen, review mistakes and play again at a higher difficulty.
11. Architecture Summary

The dashboard calls a FastAPI service. For each request the service resolves the selected sources, runs filtered hybrid retrieval per book, removes any chunk from an unselected source, and reranks the rest with a BGE cross-encoder. A prompt with only that evidence goes to the chosen LLM in JSON mode. The reply is parsed and validated (schema, citations, grounding, duplicates); invalid or duplicate questions trigger bounded regeneration. The learner view hides answers until you lock in. A separate LLM layer handles rate limits, retries, token budgets and caching, and a background indexer keeps the vector store in sync with the knowledge folder.

12. Future Improvements

OCR for scanned PDFs; server-side grading and learner history; spaced repetition; export to PDF or Anki; Docker and cross-platform launcher; question-quality evaluation dashboard; optional LangChain or LlamaIndex integration; multi-user accounts.

13. Challenges Solved
Keeping questions strictly inside the selected books (source isolation before reranking).
Distinguishing and handling Groq per-minute vs daily rate limits without retry storms.
Empty or truncated LLM output caused by token budgets (finish_reason=length) with a controlled larger-budget retry.
Small local models returning incomplete JSON (strict validation, regeneration, tolerant handling of a missing headline field on scenario types).
Slow reranker calls (candidate cap, passage truncation, warm-up, honest fallback).
First-run friction on Windows (auto .env repair, background indexing, one-click launcher).
