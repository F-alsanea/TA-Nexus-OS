from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Dummy(BaseModel):
    id: str

@app.get("/")
def root():
    return {"status": "operational", "at": "root"}

@app.get("/api/health")
def health_check():
    return {"status": "operational", "test": "pure fastapi minimal limit"}

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return {"received_path": full_path, "msg": "Catch-all triggered"}

handler = app
