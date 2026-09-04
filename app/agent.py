# Cell 17: Groq Agent Logic
import os
from groq import Groq

_client = None
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """You are a supportive academic tutor assistant. You receive a student's
predicted exam score (out of 20) along with their study habits and background data.
Your job is to write a short, encouraging, and CONCRETE study plan.

Rules:
- Reference the actual numbers given (predicted score, study time, absences, failures) - do not be generic.
- Focus advice on things the student can actually change (study time, attendance, extra support, going out less)
  - do not dwell on unchangeable factors like parental education.
- Structure your response with: (1) a one-line summary of where they stand, (2) 3-4 specific action items,
  (3) one encouraging closing line.
- Keep it under 200 words. Be warm but honest, never alarmist.
- Do not diagnose or make medical/psychological claims."""


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


def generate_study_plan(predicted_score: float, key_factors: dict) -> str:
    client = get_client()

    user_prompt = f"""Predicted final grade: {predicted_score}/20

Student profile:
- Weekly study time category: {key_factors.get('studytime')} (1=<2hrs, 2=2-5hrs, 3=5-10hrs, 4=>10hrs)
- Absences this term: {key_factors.get('absences')}
- Past class failures: {key_factors.get('failures')}
- Extra school support: {key_factors.get('schoolsup')}
- Going out with friends (frequency, 1-5): {key_factors.get('goout')}
- Travel time to school (1-4 scale): {key_factors.get('traveltime')}

Write the personalized study plan now."""

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=450,
    )

    return response.choices[0].message.content
