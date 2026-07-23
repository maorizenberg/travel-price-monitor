from fastapi import FastAPI

app = FastAPI(title="Travel Price Monitor", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Travel Price Monitor API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}