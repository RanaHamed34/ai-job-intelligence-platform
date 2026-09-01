# AI Job Intelligence Platform

A full-stack AI-powered job platform combining software engineering, real job-market data, and generative AI — built as a portfolio project extending my [Pakistan Job Market Dashboard](link-to-that-repo).

## What it does

- User registration/login with JWT authentication
- Search and filter 10,500+ real Pakistani job postings by city, salary, and sector
- Upload a CV (PDF) — AI extracts skills, education, and experience using an LLM (Groq)
- Get a transparent, code-computed match score against any job, with matched and missing skills clearly shown (not an AI-hallucinated number — the score itself is deterministic set-based logic; AI is only used for CV parsing)

## Tech stack

- **Backend:** FastAPI, SQLAlchemy
- **Database:** MySQL
- **Auth:** JWT (python-jose) + bcrypt password hashing
- **AI/LLM:** Groq API (`openai/gpt-oss-120b`), structured output validated with Pydantic
- **PDF parsing:** pypdf
- **Frontend:** Streamlit

## Architecture

Frontend (Streamlit) → FastAPI backend → MySQL database, with a separate AI service layer (CV analysis via Groq) that validates LLM output before it ever touches the database.

## Running locally

1. Clone the repo, create a virtual environment, `pip install -r requirements.txt`
2. Create a `.env` file with `DATABASE_URL`, `SECRET_KEY`, and `GROQ_API_KEY`
3. Run the backend: `uvicorn main:app --reload`
4. Run the frontend: `streamlit run frontend.py`

## What I learned

Building this taught me the real engineering problem behind LLM integration — an LLM only produces text, so getting reliable structured data out of it means treating its output as untrusted input: validating it with Pydantic, and never letting AI compute the actual match score (that logic is deterministic code, not a model guess).

## Limitations

This is a learning/portfolio project. Job matching is skill-list-based only (no semantic similarity yet), and error handling/testing coverage is not production-grade.
