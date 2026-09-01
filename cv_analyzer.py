import os
import json
from dotenv import load_dotenv
from groq import Groq
from schemas import CVAnalysis
from pydantic import ValidationError

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_cv(cv_text: str):
    prompt = f"""Extract skills, education, and experience from this resume.
Respond ONLY with valid JSON in this exact format, no extra text:
{{"skills": ["skill1", "skill2"], "education": "summary here", "experience": "summary here"}}

Resume:
{cv_text}
"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )
    raw_output = response.choices[0].message.content

    try:
        parsed = json.loads(raw_output)
        validated = CVAnalysis(**parsed)
        return validated.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"AI response was not in the expected format: {e}")