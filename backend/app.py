from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.fact_check import router as fact_router
from routes.voice import router as voice_router
from routes.image_verify import router as image_router

app = FastAPI(title="Fact Lens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(fact_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(image_router, prefix="/api")
