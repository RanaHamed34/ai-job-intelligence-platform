# AI Job Intelligence Platform

A full-stack AI-powered job platform combining software engineering, real job-market data, and generative AI — built as a portfolio project extending my [Pakistan Job Market Dashboard](https://pakistan-job-market-dashboard.streamlit.app/).

## Live Demo

- Backend API (Swagger docs): https://ai-job-intelligence-platform-production.up.railway.app/docs
- Frontend (Streamlit): https://ai-job-intelligence-platform.streamlit.app/

## What it does

- User registration/login with JWT authentication
- Search and filter 10,500+ real Pakistani job postings by city, salary, and sector
- Upload a CV (PDF) — AI extracts skills, education, and experience using an LLM (Groq)
- Get a transparent, code-computed match score against any job, with matched and missing skills clearly shown (not an AI-hallucinated number — the score itself is deterministic set-based logic; AI is only used for CV parsing)
- **Natural language job search (RAG)** — ask in plain English (e.g. "IT jobs in Lahore paying over 100k") and get semantically relevant jobs, found via vector embeddings (ChromaDB + sentence-transformers) and summarized by an LLM
- **AI function calling** — a smart search endpoint where the LLM decides which backend function to call and with what arguments, based on a natural language query
- **Auto-Apply Agent** — generates a personalized, LLM-written cover letter for a job based on the user's actual resume data, with a human-in-the-loop approval step before anything is considered "sent" (no cover letter goes out without explicit approval)

## Tech stack

- **Backend:** FastAPI, SQLAlchemy
- **Database:** PostgreSQL
- **Auth:** JWT (python-jose) + bcrypt password hashing
- **AI/LLM:** Groq API (`openai/gpt-oss-120b`), structured output validated with Pydantic
- **Vector search:** ChromaDB (persistent) with `sentence-transformers` (`all-MiniLM-L6-v2`) embeddings
- **PDF parsing:** pypdf
- **Frontend:** Streamlit
- **Testing:** pytest

## Architecture

Frontend (Streamlit) → FastAPI backend → PostgreSQL database, with a separate AI service layer (CV analysis, RAG search, function calling, and cover letter generation, all via Groq) that validates LLM output with Pydantic before it ever touches the database or reaches the user.

## Running locally

1. Clone the repo, create a virtual environment, `pip install -r requirements.txt`
2. Create a `.env` file with `DATABASE_URL`, `SECRET_KEY`, and `GROQ_API_KEY`
3. Create the database tables: `python init_db.py`
4. Run the backend: `uvicorn main:app --reload`
5. Run the frontend: `streamlit run frontend.py`

## Testing

Run `pytest` to execute the test suite, covering authentication, job search/filtering, skill-gap matching, and the auto-apply cover letter flow.

## What I learned

Building this taught me the real engineering problem behind LLM integration — an LLM only produces text, so getting reliable structured data out of it means treating its output as untrusted input: validating it with Pydantic, and never letting AI compute the actual match score (that logic is deterministic code, not a model guess). I also learned that a working deployment isn't a one-time event — I hit a case where GitHub auto-deploy silently stopped syncing with my Railway service, and separately found that `requirements.txt` had drifted from what was actually installed locally. Both were invisible until I forced a fresh deploy, which is now something I check for rather than assume is fine.

## Limitations

This is a learning/portfolio project. Job matching combines exact skill-list logic (for scoring) with semantic search (for natural language queries), but there's no fine-tuned ranking model. Error handling and test coverage are solid for the core flows but not exhaustive, and the Auto-Apply Agent stops at generating and approving cover letters — it does not send emails.
