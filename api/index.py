from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Dummy(BaseModel):
    id: str

@app.get("/api/health")
def health_check():
    return {"status": "operational", "test": "pure fastapi minimal limit"}

handler = app
