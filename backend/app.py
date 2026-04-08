import os
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]

    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]


def _load_local_env():
    # Load .env from repo root (../.env) for local development.
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        logger.warning(f".env file not found at {env_path}")
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    
    logger.info("✓ Environment variables loaded from .env")


_load_local_env()

try:
    from routes.fact_check import router as fact_router
    from routes.voice import router as voice_router
    from routes.image_verify import router as image_router
except ModuleNotFoundError:
    from backend.routes.fact_check import router as fact_router
    from backend.routes.voice import router as voice_router
    from backend.routes.image_verify import router as image_router

app = FastAPI(title="Fact Lens API", version="1.0.0")

cors_origins = _parse_cors_origins()
allow_all_origins = cors_origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Called when the app starts"""
    logger.info("🚀 Fact Lens Backend Starting...")
    logger.info(f"API Documentation: http://localhost:8000/docs")
    logger.info(f"Health Check: http://localhost:8000/health")
    logger.info("CORS origins: %s", ", ".join(cors_origins))


@app.get("/health")
async def health():
    return {"status": "ok", "message": "Backend is running"}


@app.get("/check-models")
async def check_models():
    """Check if all required models/dependencies are available"""
    checks = {}
    
    try:
        from models.embeddings import get_embeddings
        emb = get_embeddings()
        checks["embeddings"] = "✓ Available" if emb else "✗ Not available"
    except Exception as e:
        checks["embeddings"] = f"✗ Error: {str(e)[:100]}"
    
    try:
        from services.retrieval import _ensure_vectorstore
        vs = _ensure_vectorstore()
        checks["faiss"] = "✓ Available" if vs else "✗ Not loaded yet"
    except Exception as e:
        checks["faiss"] = f"✗ Error: {str(e)[:100]}"
    
    try:
        from models.whisper_model import _get_whisper
        ws = _get_whisper()
        checks["whisper"] = "✓ Available" if ws else "✗ Not loaded yet"
    except Exception as e:
        checks["whisper"] = f"✗ Error: {str(e)[:100]}"
    
    try:
        import serpapi
        checks["serpapi"] = "✓ Installed"
    except Exception as e:
        checks["serpapi"] = "✗ Not installed"
    
    try:
        import openai
        checks["openai"] = "✓ Installed"
    except Exception as e:
        checks["openai"] = "✗ Not installed"
    
    return {
        "status": "ok",
        "checks": checks,
        "note": "Heavy models (embeddings, FAISS, Whisper) load on first use to save startup time"
    }


app.include_router(fact_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(image_router, prefix="/api")
