from fastapi import FastAPI

from . import auth, diaries, notes, records, reviews, social_drafts, trash


app = FastAPI(title="MyDawnDiary API", version="0.1.0")
app.include_router(auth.router)
app.include_router(diaries.router)
app.include_router(records.router)
app.include_router(notes.router)
app.include_router(trash.router)
app.include_router(social_drafts.router)
app.include_router(reviews.router)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}
