import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.appointments import router as appointments_router

app = FastAPI(title="SER SALUD - Terapia Física API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appointments_router, prefix="/sersalud/appointments")


@app.get("/health")
def health():
    return {"status": "healthy"}


app.mount("/", StaticFiles(directory="static", html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
