from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Job,User,Resume,JobMatch,Application
from schemas import JobCreate
from schemas import UserCreate, UserLogin
from auth import hash_password, verify_password, create_access_token
from models import User
from auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi import UploadFile, File
from models import Resume
from cv_analyzer import analyze_cv
from extract_pdf import extract_text_from_pdf
import shutil
import json
import ast
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
import os
from pydantic import BaseModel

embed_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma_client = chromadb.PersistentClient(path="./chroma_data")
jobs_collection = chroma_client.get_collection(name="jobs")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_jobs",
            "description": "Search for jobs by city, minimum salary, and sector",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. Lahore, Karachi"
                    },
                    "min_salary": {
                        "type": "integer",
                        "description": "Minimum salary in PKR"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Job sector, e.g. IT, Banking & Finance"
                    }
                },
                "required": []
            }
        }
    }
]


app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}

from typing import Optional

@app.get("/jobs")
def get_jobs(
    city: Optional[str] = None,
    min_salary: Optional[int] = None,
    sector: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Job)

    if city:
        query = query.filter(Job.city.ilike(city))
    if min_salary:
        query = query.filter(Job.salary_min >= min_salary)
    if sector:
        query = query.filter(Job.sector == sector)

    return query.all()

@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = Job(
        job_title=job.job_title,
        company=job.company,
        city=job.city,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        experience_required=job.experience_required,
        skills_required=job.skills_required,
        sector=job.sector
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.put("/jobs/{job_id}")
def update_job(job_id: int, updated_job: JobCreate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job.job_title = updated_job.job_title
    job.company = updated_job.company
    job.city = updated_job.city
    job.salary_min = updated_job.salary_min
    job.salary_max = updated_job.salary_max
    job.experience_required = updated_job.experience_required
    job.skills_required = updated_job.skills_required
    job.sector = updated_job.sector

    db.commit()
    db.refresh(job)
    return job

@app.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully"}

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password),
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email, "full_name": new_user.full_name}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": db_user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me")
def read_current_user(current_user_id: int = Depends(get_current_user)):
    return {"logged_in_user_id": current_user_id}

@app.post("/upload-cv")
def upload_cv(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cv_text = extract_text_from_pdf(temp_path)

    try:
        result = analyze_cv(cv_text)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    new_resume = Resume(
        user_id=current_user_id,
        extracted_skills=json.dumps(result["skills"]),
        extracted_education=result["education"],
        extracted_experience=result["experience"]
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    return new_resume

@app.post("/match/{job_id}")
def match_job(job_id: int, current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = db.query(Resume).filter(Resume.user_id == current_user_id).order_by(Resume.id.desc()).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume found, upload a CV first")

    resume_skills = set(json.loads(resume.extracted_skills))
    job_skills = set(ast.literal_eval(job.skills_required)) if job.skills_required.startswith("[") else set(s.strip() for s in job.skills_required.split(","))

    matched = resume_skills & job_skills
    missing = job_skills - resume_skills

    match_score = int(len(matched) / len(job_skills) * 100) if job_skills else 0

    new_match = JobMatch(
        user_id=current_user_id,
        job_id=job_id,
        match_score=match_score,
        matched_skills=json.dumps(list(matched)),
        missing_skills=json.dumps(list(missing))
    )
    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return new_match

class GenerateApplicationRequest(BaseModel):
    pass

@app.post("/generate-application/{job_id}")
def generate_application(job_id: int, current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = db.query(Resume).filter(Resume.user_id == current_user_id).order_by(Resume.id.desc()).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume found, upload a CV first")

    prompt = f"""You are a professional career coach writing a cover letter on behalf of a job applicant.

Candidate's background:
- Skills: {resume.extracted_skills}
- Education: {resume.extracted_education}
- Experience: {resume.extracted_experience}

Job details:
- Title: {job.job_title}
- Company: {job.company}
- Required skills: {job.skills_required}

Write a professional cover letter (3-4 short paragraphs) that connects the candidate's specific skills and experience to this job's requirements. Avoid generic opening phrases like "I am writing to express my interest." Be specific and reference actual skills from the candidate's background. Do not invent any experience or skills that were not listed above."""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )

    cover_letter_text = response.choices[0].message.content

    new_application = Application(
        user_id=current_user_id,
        job_id=job_id,
        cover_letter=cover_letter_text
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    return new_application

class NaturalSearchRequest(BaseModel):
    query: str
    n_results: int = 5
    
@app.post("/search-natural")
def search_natural(request: NaturalSearchRequest, current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    query = request.query
    n_results = request.n_results

    query_embedding = embed_model.encode(query).tolist()

    results = jobs_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    matched_ids = [int(job_id) for job_id in results["ids"][0]]

    matched_jobs_db = db.query(Job).filter(Job.id.in_(matched_ids)).all()

    matched_jobs = [
        {
            "id": job.id,
            "title": job.job_title,
            "company": job.company,
            "city": job.city,
            "sector": job.sector,
            "skills_required": job.skills_required
        }
        for job in matched_jobs_db
    ]

    context = "\n".join(
        f"- {job.job_title} at {job.company}, {job.city}. Sector: {job.sector}. Skills: {job.skills_required}"
        for job in matched_jobs_db
    )

    prompt = f"""Based on these job listings:
{context}

Answer this user query: {query}

Give a helpful, concise answer mentioning the most relevant jobs."""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "query": query,
        "matched_jobs": matched_jobs,
        "ai_answer": response.choices[0].message.content
    }

class SmartSearchRequest(BaseModel):
    query: str

@app.post("/smart-search")
def smart_search(request: SmartSearchRequest, current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    query = request.query

    # Call 1: LLM ko query do, tools ke sath — decide karne do function chalana hai ya nahi
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": query}],
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    if not message.tool_calls:
        # LLM ne function ki zaroorat nahi samjhi
        return {"answer": message.content, "function_called": None}

    tool_call = message.tool_calls[0]
    arguments = json.loads(tool_call.function.arguments)

    city = arguments.get("city")
    min_salary = arguments.get("min_salary")
    sector = arguments.get("sector")

    # Actual database query — LLM ke diye arguments ke saath
    job_query = db.query(Job)
    if city:
        job_query = job_query.filter(Job.city == city)
    if min_salary:
        job_query = job_query.filter(Job.salary_min >= min_salary)
    if sector:
        job_query = job_query.filter(Job.sector == sector)

    results = job_query.all()

    results_summary = [
        {"title": j.job_title, "company": j.company, "city": j.city, "sector": j.sector}
        for j in results
    ]

    # Sirf pehle 10 hi Call 2 (LLM) ko bhejo, taake token limit na cross ho
    context_for_llm = results_summary[:10]

    # Call 2: result LLM ko wapas do, taake woh natural-language answer bana sake
    follow_up = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": query},
            {"role": "assistant", "content": None, "tool_calls": message.tool_calls},
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(context_for_llm)
            }
        ]
    )

    final_answer = follow_up.choices[0].message.content

    return {
        "function_called": tool_call.function.name,
        "arguments_extracted": arguments,
        "raw_results": results_summary,
        "final_answer": final_answer
    }
@app.get("/applications")
def get_applications(current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Application).filter(Application.user_id == current_user_id).all()
@app.post("/applications/{application_id}/approve")
def approve_application(application_id: int, current_user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user_id
    ).first()

    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = "approved"
    db.commit()
    db.refresh(application)

    return application