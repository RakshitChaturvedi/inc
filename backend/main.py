from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import router

app = FastAPI(title="OceanEmbed API", version="1.0.0", description="OceanEmbed daily ocean subsurface prediction backend.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "oceanembed-backend",
    }