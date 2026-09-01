from pydantic import BaseModel
from typing import List

class JobCreate(BaseModel):
    job_title: str
    company: str
    city: str
    salary_min: int
    salary_max: int
    experience_required: str
    skills_required: str
    sector: str

from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    email: str
    password: str = Field(..., max_length=72)
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str




class CVAnalysis(BaseModel):
    skills: List[str]
    education: str
    experience: str