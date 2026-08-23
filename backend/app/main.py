from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import eval as eval_router
from .routers import manuals, query

app = FastAPI(title="CarManualRAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(manuals.router)
app.include_router(query.router)
app.include_router(eval_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
