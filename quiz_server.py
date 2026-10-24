"""Standalone quiz server (one process): dashboard + API + automatic indexing.

  python quiz_server.py          ->  http://127.0.0.1:8800
Everything is configured in .env (see .env.example). START.bat runs this for you."""
from __future__ import annotations

import logging
import os
import threading
import time
import webbrowser
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse

from app.quiz import indexer
from app.quiz.config import QuizSettings, project_path
from app.quiz.envfix import apply as fix_env, mask
from app.quiz.llm import LLMRegistry
from app.quiz.routes import build_quiz_router
from app.quiz.wiring import build_service

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("quiz.server")


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (no extra dependency). Real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.split(" #")[0].strip().strip('"').strip("'"))


def _ollama_up(url: str) -> bool:
    import httpx
    try:
        return httpx.get(f"{url.rstrip('/')}/api/tags", timeout=2.0).status_code == 200
    except Exception:
        return False


def effective_config(reg: LLMRegistry, s: QuizSettings) -> dict:
    """What the RUNNING app actually loaded. Secrets are reported as set/empty only."""
    prov = reg.default_provider
    return {"llm": {"provider": prov, "default_model": reg.default_id, "api_key_loaded": reg.key_loaded(prov),
                    "key_env": mask("API_KEY", reg.key_for(prov)), "fallback": os.getenv("QUIZ_LLM_FALLBACK") or None},
            "embedding": {"model": os.getenv("EMBED_MODEL", "bge-m3:latest"), "ollama_url": reg.ollama_url},
            "reranker": {"enabled": s.reranker_enabled, "provider": s.reranker_provider, "endpoint": s.reranker_endpoint,
                         "timeout": s.reranker_timeout, "fallback": s.reranker_fallback, "max_candidates": s.rerank_max_candidates},
            "paths": {"agents_dir": str(project_path(os.getenv("AGENTS_DIR", "agents"))),
                      "chroma_path": str(project_path(os.getenv("CHROMA_PATH", "data/chroma")))},
            "timeouts": {"llm": s.llm_timeout, "llm_retry_budget": s.llm_max_wait}}


def create_app(open_browser: bool = False, auto_index: bool = True) -> FastAPI:
    fix_env(ROOT / ".env", ROOT / ".env.example", say=lambda m: print(f"[env] {m}"))
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = QuizSettings.from_env()
    reg = LLMRegistry()
    svc = build_service(settings=s, llm_registry=reg)
    app = FastAPI(title="Quiz desk")
    app.include_router(build_quiz_router(lambda: svc, s))
    extra = APIRouter(prefix="/api/quiz", tags=["quiz"])
    manifest = project_path(os.getenv("CHROMA_PATH", "data/chroma")).parent / "index_manifest.json"
    agents = project_path(os.getenv("AGENTS_DIR", "agents"))

    @extra.get("/index-status")
    def index_status():
        return dict(indexer.STATUS)

    @extra.post("/index")
    def reindex():
        return {"started": indexer.start_background(svc.vector_client, agents, svc.embedder, manifest), "status": dict(indexer.STATUS)}

    @extra.get("/status")
    def status():
        rr = svc.reranker.health() if svc.reranker else {"ok": False, "provider": "none", "message": "reranking disabled"}
        return {**effective_config(reg, s), "ollama_reachable": _ollama_up(reg.ollama_url), "reranker_health": rr,
                "index": dict(indexer.STATUS)}
    app.include_router(extra)

    @app.get("/")
    def page():
        return FileResponse(ROOT / "frontend" / "quiz.html")

    def startup() -> None:
        cfg = effective_config(reg, s)
        print("[config] model=%s key_loaded=%s fallback=%s reranker=%s/%s agents=%s" % (
            cfg["llm"]["default_model"], cfg["llm"]["api_key_loaded"], cfg["llm"]["fallback"],
            "on" if s.reranker_enabled else "off", s.reranker_provider, cfg["paths"]["agents_dir"]))
        if not cfg["llm"]["api_key_loaded"]:
            print(f"[config] WARNING: no API key for {reg.default_provider}. Add it to .env (see .env.example).")
        if auto_index:
            indexer.start_background(svc.vector_client, agents, svc.embedder, manifest)

        def warm() -> None:                             # first requests are slow otherwise
            if svc.reranker is not None:
                import time
                last = None
                for _ in range(24):                     # the reranker window needs time to load the model
                    try:
                        svc.reranker.score("warm up", ["warm up passage"])
                        print("[warm-up] reranker ready")
                        last = None
                        break
                    except Exception as exc:
                        last = exc
                        time.sleep(5)
                if last is not None:
                    print(f"[warm-up] reranker still not ready after 2 min: {last}")
            if reg.default_provider == "ollama":
                import httpx
                try:
                    httpx.post(f"{reg.ollama_url}/api/generate", timeout=300, json={
                        "model": reg.default_id.split(":", 1)[1], "keep_alive": reg.cfg.keep_alive})
                except Exception as exc:
                    print(f"[warm-up] local model not loaded: {exc}")
        threading.Thread(target=warm, daemon=True).start()
        if open_browser:
            threading.Timer(2.0, lambda: webbrowser.open(f"http://127.0.0.1:{os.getenv('QUIZ_PORT', '8800')}")).start()
    app.router.on_startup.append(startup)
    return app


if __name__ == "__main__":
    import uvicorn
    load_env()
    uvicorn.run(create_app(open_browser=os.getenv("QUIZ_OPEN_BROWSER", "true").lower() != "false"),
                host=os.getenv("QUIZ_HOST", "127.0.0.1"), port=int(os.getenv("QUIZ_PORT", "8800")), log_level="warning")
