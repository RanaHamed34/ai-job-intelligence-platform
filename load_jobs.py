import pandas as pd
from database import SessionLocal
from models import Job

df = pd.read_csv(r"C:\Users\Rana\Desktop\job_market_intelligence\data\processed\job_market_cleaned.csv")

def clean(value):
    if pd.isna(value):
        return None
    return value

db = SessionLocal()

for _, row in df.iterrows():
    job = Job(
        job_title=clean(row["Job Title"]),
        company=clean(row["Company"]),
        city=clean(row["City"]),
        salary_min=clean(row["Salary_Min"]),
        salary_max=clean(row["Salary_Max"]),
        experience_required=clean(row["Experience Required"]),
        skills_required=str(row["Skills_List"]) if pd.notna(row["Skills_List"]) else None,
        sector=clean(row["Sector"])
    )
    db.add(job)

db.commit()
db.close()

print("Done. Rows inserted:", len(df))