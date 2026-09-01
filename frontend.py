import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.title("AI Job Intelligence Platform")

if "token" not in st.session_state:
    st.session_state.token = None

if st.session_state.token is None:
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = requests.post(f"{API_URL}/login", json={"email": email, "password": password})
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.rerun()
        else:
            st.error("Invalid credentials")

else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    if st.button("Logout"):
        st.session_state.token = None
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Job Search", "Upload CV", "Match Jobs"])

    with tab1:
        st.subheader("Search Jobs")
        city = st.text_input("City (optional)")

        if st.button("Search"):
            params = {}
            if city:
                params["city"] = city
            jobs = requests.get(f"{API_URL}/jobs", params=params).json()
            st.write(f"Found {len(jobs)} jobs")
            for job in jobs[:20]:
                st.write(f"**{job['job_title']}** at {job['company']} — {job['city']} — PKR {job['salary_min']}-{job['salary_max']} (ID: {job['id']})")

    with tab2:
        st.subheader("Upload your CV")
        uploaded_file = st.file_uploader("Choose a PDF", type="pdf")

        if uploaded_file and st.button("Analyze CV"):
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            response = requests.post(f"{API_URL}/upload-cv", headers=headers, files=files)
            if response.status_code == 200:
                result = response.json()
                st.success("CV analyzed!")
                st.write("**Skills:**", result["extracted_skills"])
                st.write("**Education:**", result["extracted_education"])
                st.write("**Experience:**", result["extracted_experience"])
            else:
                st.error(f"Error: {response.text}")

    with tab3:
        st.subheader("Match Against a Job")
        job_id = st.number_input("Job ID", min_value=1, step=1)

        if st.button("Check Match"):
            response = requests.post(f"{API_URL}/match/{job_id}", headers=headers)
            if response.status_code == 200:
                result = response.json()
                st.metric("Match Score", f"{result['match_score']}%")
                st.write("**Matched Skills:**", result["matched_skills"])
                st.write("**Missing Skills:**", result["missing_skills"])
            else:
                st.error(f"Error: {response.text}")