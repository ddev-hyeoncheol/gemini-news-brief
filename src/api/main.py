import os

from fastapi import FastAPI

app = FastAPI(title="Gemini News Brief API")


@app.get("/health")
async def health_check():
    return {"status": "health", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "Welcome to Gemini News Brief API"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=False)
