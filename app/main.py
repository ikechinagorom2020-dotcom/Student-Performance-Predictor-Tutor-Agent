
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.schemas import StudentInput, PredictionResponse, TutorChatRequest, TutorChatResponse
from app.model import predict_score
from app.agent import generate_study_plan, tutor_chat

app = FastAPI(title="Student Performance Predictor & Tutor Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/predict", response_model=PredictionResponse)
def predict(student: StudentInput):
    try:
        student_dict = student.dict()
        predicted_score, key_factors = predict_score(student_dict)
        study_plan = generate_study_plan(predicted_score, key_factors)
        return PredictionResponse(
            predicted_score=predicted_score,
            key_factors=key_factors,
            study_plan=study_plan,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tutor-chat", response_model=TutorChatResponse)
def chat(request: TutorChatRequest):
    try:
        result = tutor_chat(request.session_id, request.message, request.subject)
        return TutorChatResponse(reply=result["reply"], quiz_stats=result["quiz_stats"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
