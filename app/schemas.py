# Cell 34: Updated Schemas (adds tutor chat models)
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional


class StudentInput(BaseModel):
    school: Literal["GP", "MS"]
    sex: Literal["F", "M"]
    age: int = Field(ge=15, le=22)
    address: Literal["U", "R"]
    famsize: Literal["LE3", "GT3"]
    Pstatus: Literal["T", "A"]
    Medu: int = Field(ge=0, le=4)
    Fedu: int = Field(ge=0, le=4)
    Mjob: Literal["teacher", "health", "services", "at_home", "other"]
    Fjob: Literal["teacher", "health", "services", "at_home", "other"]
    reason: Literal["home", "reputation", "course", "other"]
    guardian: Literal["mother", "father", "other"]
    traveltime: int = Field(ge=1, le=4)
    studytime: int = Field(ge=1, le=4)
    failures: int = Field(ge=0, le=4)
    schoolsup: Literal["yes", "no"]
    famsup: Literal["yes", "no"]
    paid: Literal["yes", "no"]
    activities: Literal["yes", "no"]
    nursery: Literal["yes", "no"]
    higher: Literal["yes", "no"]
    internet: Literal["yes", "no"]
    romantic: Literal["yes", "no"]
    famrel: int = Field(ge=1, le=5)
    freetime: int = Field(ge=1, le=5)
    goout: int = Field(ge=1, le=5)
    Dalc: int = Field(ge=1, le=5)
    Walc: int = Field(ge=1, le=5)
    health: int = Field(ge=1, le=5)
    absences: int = Field(ge=0, le=100)
    subject: Literal["math", "portuguese"]


class PredictionResponse(BaseModel):
    predicted_score: float
    key_factors: Dict[str, Any]
    study_plan: str


class TutorChatRequest(BaseModel):
    session_id: str
    message: str
    subject: Optional[Literal["math", "portuguese"]] = "math"


class TutorChatResponse(BaseModel):
    reply: str
    quiz_stats: Dict[str, int]
