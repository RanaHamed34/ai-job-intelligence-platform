from fastapi.testclient import TestClient
from main import app
from models import Application

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_register_new_user():
    import random
    random_email = f"test{random.randint(1000,9999)}@example.com"
    
    response = client.post("/register", json={
        "email": random_email,
        "password": "testpass123",
        "full_name": "Test User"
    })
    
    assert response.status_code == 200
    assert response.json()["email"] == random_email


def test_login_valid_credentials():
    import random
    random_email = f"logintest{random.randint(1000,9999)}@example.com"
    password = "testpass123"

    client.post("/register", json={
        "email": random_email,
        "password": password,
        "full_name": "Login Test User"
    })

    response = client.post("/login", json={
        "email": random_email,
        "password": password
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_credentials():
    response = client.post("/login", json={
        "email": "nonexistent_user@example.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 401

def test_get_all_jobs():
    response = client.get("/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_jobs_filter_by_city():
    response = client.get("/jobs", params={"city": "Lahore"})
    assert response.status_code == 200
    jobs = response.json()
    assert all(job["city"] == "Lahore" for job in jobs)

def test_match_job():
    import random

    # Setup 1: naya user register karo aur login se token lo
    email = f"matchtest{random.randint(1000,9999)}@example.com"
    password = "testpass123"

    client.post("/register", json={
        "email": email,
        "password": password,
        "full_name": "Match Test"
    })

    login_response = client.post("/login", json={
        "email": email,
        "password": password
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup 2: CV upload karo (real PDF file chahiye disk pe)
    with open(r"C:\Users\Rana\Desktop\Hamed CV2.pdf", "rb") as f:
        upload_response = client.post(
            "/upload-cv",
            files={"file": ("Hamed CV2.pdf", f, "application/pdf")},
            headers=headers
        )
    assert upload_response.status_code == 200

    # Setup 3: DB se ek existing job_id nikalo
    jobs_response = client.get("/jobs")
    job_id = jobs_response.json()[0]["id"]

    # Asal test: match endpoint call karo
    match_response = client.post(f"/match/{job_id}", headers=headers)
    assert match_response.status_code == 200

    body = match_response.json()
    assert "match_score" in body
    assert 0 <= body["match_score"] <= 100

def test_generate_application():
    import random
    email = f"apptest{random.randint(1000,9999)}@example.com"

    client.post("/register", json={"email": email, "password": "testpass123", "full_name": "App Test"})
    token = client.post("/login", json={"email": email, "password": "testpass123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with open(r"C:\Users\Rana\Desktop\Hamed CV2.pdf", "rb") as f:
        client.post("/upload-cv", files={"file": ("cv.pdf", f, "application/pdf")}, headers=headers)

    job_id = client.get("/jobs").json()[0]["id"]
    response = client.post(f"/generate-application/{job_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert len(response.json()["cover_letter"]) > 50

def test_get_applications():
    import random
    email = f"listtest{random.randint(1000,9999)}@example.com"

    client.post("/register", json={"email": email, "password": "testpass123", "full_name": "List Test"})
    token = client.post("/login", json={"email": email, "password": "testpass123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with open(r"C:\Users\Rana\Desktop\Hamed CV2.pdf", "rb") as f:
        client.post("/upload-cv", files={"file": ("cv.pdf", f, "application/pdf")}, headers=headers)

    job_id = client.get("/jobs").json()[0]["id"]
    client.post(f"/generate-application/{job_id}", headers=headers)

    response = client.get("/applications", headers=headers)

    assert response.status_code == 200
    apps = response.json()
    assert len(apps) == 1
    assert apps[0]["job_id"] == job_id

def test_approve_application():
    import random
    email = f"approvetest{random.randint(1000,9999)}@example.com"

    client.post("/register", json={"email": email, "password": "testpass123", "full_name": "Approve Test"})
    token = client.post("/login", json={"email": email, "password": "testpass123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with open(r"C:\Users\Rana\Desktop\Hamed CV2.pdf", "rb") as f:
        client.post("/upload-cv", files={"file": ("cv.pdf", f, "application/pdf")}, headers=headers)

    job_id = client.get("/jobs").json()[0]["id"]
    app_id = client.post(f"/generate-application/{job_id}", headers=headers).json()["id"]

    response = client.post(f"/applications/{app_id}/approve", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "approved"