# Cell 35: Updated Agent (adds tool-calling + retry logic for Groq's intermittent json_validate_failed)
import os
import json
import time
from groq import Groq

_client = None
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

STUDY_PLAN_SYSTEM_PROMPT = """You are a supportive academic tutor assistant. You receive a student's
predicted exam score (out of 20) along with their study habits and background data.
Your job is to write a short, encouraging, and CONCRETE study plan.

Rules:
- Reference the actual numbers given (predicted score, study time, absences, failures) - do not be generic.
- Focus advice on things the student can actually change (study time, attendance, extra support, going out less)
  - do not dwell on unchangeable factors like parental education.
- Structure your response with: (1) a one-line summary of where they stand, (2) exactly 3 specific action items,
  (3) one short encouraging closing line.
- Keep the ENTIRE response under 160 words total - be concise, each action item should be 1-2 sentences max.
- Always finish your closing line completely - never cut off mid-sentence.
- Be warm but honest, never alarmist. Do not diagnose or make medical/psychological claims."""


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=api_key)
    return _client


def _create_with_retry(max_retries=3, **kwargs):
    """Wraps client.chat.completions.create with retries.

    Groq's gpt-oss models occasionally return a 400 'json_validate_failed'
    error with an empty failed_generation when using tool calling or strict
    JSON mode - this is a known, intermittent issue on Groq's side, not a
    bug in our request. Retrying (usually) succeeds on the 2nd or 3rd try.
    """
    client = get_client()
    last_error = None

    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "json_validate_failed" in error_str or "400" in error_str:
                time.sleep(0.6 * (attempt + 1))  # brief backoff before retrying
                continue
            raise  # different error type - don't retry, surface it immediately

    raise last_error


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

Write the personalized study plan now. Remember: under 160 words total, and always finish your closing line."""

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": STUDY_PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=700,
    )

    content = response.choices[0].message.content
    if response.choices[0].finish_reason == "length":
        content += "\n\n_(Note: response was truncated.)_"
    return content


# ---------------------------------------------------------------------------
# Stretch goal: Practice Quiz Tool + Session Memory
# ---------------------------------------------------------------------------

SESSIONS = {}

TUTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_practice_question",
            "description": (
                "Generates a short multiple-choice practice question to quiz the student. "
                "Call this whenever the student asks to be quizzed, tested, or wants practice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "enum": ["math", "portuguese"],
                        "description": "The subject to generate a question for.",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "description": "How difficult the question should be.",
                    },
                },
                "required": ["subject", "difficulty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_quiz_result",
            "description": (
                "Logs whether the student answered the most recent practice question correctly. "
                "Call this immediately after grading the student's answer to a question you asked."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "is_correct": {
                        "type": "boolean",
                        "description": "Whether the student's answer was correct.",
                    }
                },
                "required": ["is_correct"],
            },
        },
    },
]


def _run_generate_practice_question(subject: str, difficulty: str) -> dict:
    """Tool implementation: asks Groq to produce a structured practice question."""
    prompt = f"""Create one {difficulty} multiple-choice practice question appropriate for a
high-school {subject} class. Respond with ONLY a JSON object in this exact shape, no other text:

{{
  "question": "...",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct_option": "A",
  "explanation": "..."
}}"""

    response = _create_with_retry(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=400,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {
            "question": "Could not generate a question right now - try again?",
            "options": {}, "correct_option": None, "explanation": "",
        }


def _run_record_quiz_result(session: dict, is_correct: bool) -> dict:
    session["quiz_stats"]["attempted"] += 1
    if is_correct:
        session["quiz_stats"]["correct"] += 1
    return session["quiz_stats"]


def _get_or_create_session(session_id: str, subject: str) -> dict:
    if session_id not in SESSIONS:
        system_prompt = f"""You are an encouraging peer tutor helping a student practice {subject}.
You have two tools available: generate_practice_question and record_quiz_result.

Rules:
- If the student asks to be quizzed, tested, or wants practice, call generate_practice_question.
- Present the question clearly with its lettered options (A-D) and ask them to answer with a letter.
- When the student replies with an answer, compare it to the correct_option from the question you
  were given, tell them clearly whether they're right, briefly explain why using the explanation
  provided, then call record_quiz_result with is_correct set appropriately.
- After recording a result, mention their running score (e.g. "You're at 2/3 correct") briefly.
- Keep every response under 100 words. Be warm, encouraging, and concise.
- Never diagnose or make claims outside academic performance."""

        SESSIONS[session_id] = {
            "messages": [{"role": "system", "content": system_prompt}],
            "quiz_stats": {"attempted": 0, "correct": 0},
        }
    return SESSIONS[session_id]


def tutor_chat(session_id: str, user_message: str, subject: str = "math") -> dict:
    """Runs one turn of the tutor chat, including any tool calls the agent decides to make."""
    session = _get_or_create_session(session_id, subject)
    session["messages"].append({"role": "user", "content": user_message})

    max_iterations = 4
    for _ in range(max_iterations):
        response = _create_with_retry(
            model=DEFAULT_MODEL,
            messages=session["messages"],
            tools=TUTOR_TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=500,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            session["messages"].append({"role": "assistant", "content": msg.content})
            return {"reply": msg.content, "quiz_stats": session["quiz_stats"]}

        session["messages"].append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)

            if tool_call.function.name == "generate_practice_question":
                result = _run_generate_practice_question(
                    args.get("subject", subject), args.get("difficulty", "medium")
                )
            elif tool_call.function.name == "record_quiz_result":
                result = _run_record_quiz_result(session, args.get("is_correct", False))
            else:
                result = {"error": f"Unknown tool {tool_call.function.name}"}

            session["messages"].append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return {
        "reply": "Let's try that again - could you repeat your last message?",
        "quiz_stats": session["quiz_stats"],
    }
