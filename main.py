from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Job,User,Resume,JobMatch
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
        query = query.filter(Job.city == city)
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