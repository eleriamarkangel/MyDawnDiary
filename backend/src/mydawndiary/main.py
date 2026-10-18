from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import auth, diaries, notes, records, reviews, social_drafts, trash


app = FastAPI(title="MyDawnDiary API", version="0.1.0")
app.include_router(auth.router)
app.include_router(diaries.router)
app.include_router(records.router)
app.include_router(notes.router)
app.include_router(trash.router)
app.include_router(social_drafts.router)
app.include_router(reviews.router)

frontend_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if frontend_dir.is_dir():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/", include_in_schema=False)
def frontend_home() -> RedirectResponse:
    return RedirectResponse(url="/app/" if frontend_dir.is_dir() else "/docs")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}
