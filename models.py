from sqlalchemy import Column, Integer, String, Text
from database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String(255), nullable=False)
    company = Column(String(255))
    city = Column(String(100))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    experience_required = Column(String(100))
    skills_required = Column(Text)
    sector = Column(String(100))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    extracted_skills = Column(Text)
    extracted_education = Column(Text)
    extracted_experience = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    match_score = Column(Integer)
    matched_skills = Column(Text)
    missing_skills = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)