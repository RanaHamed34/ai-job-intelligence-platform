import chromadb
from sentence_transformers import SentenceTransformer
from database import SessionLocal
from models import Job

model = SentenceTransformer('all-MiniLM-L6-v2')

# Persistent client — data disk pe save hoga
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(name="jobs")

db = SessionLocal()
jobs = db.query(Job).all()
db.close()

print(f"Total jobs to embed: {len(jobs)}")

documents = []
ids = []

for job in jobs:
    text = f"{job.job_title} at {job.company}, {job.city}. Sector: {job.sector}. Skills: {job.skills_required}"
    documents.append(text)
    ids.append(str(job.id))

# Batch mein embed karo (10,500 ek saath karne se laptop pe slow/heavy ho sakta hai)
batch_size = 500
for i in range(0, len(documents), batch_size):
    batch_docs = documents[i:i+batch_size]
    batch_ids = ids[i:i+batch_size]
    embeddings = model.encode(batch_docs).tolist()
    collection.add(embeddings=embeddings, documents=batch_docs, ids=batch_ids)
    print(f"Embedded {i + len(batch_docs)} / {len(documents)}")

print("Done. Embeddings saved to ./chroma_data")