from pandastack import Client

client = Client()
db = client.databases.create(label="job-intelligence-db")
print(db["connection_url"])