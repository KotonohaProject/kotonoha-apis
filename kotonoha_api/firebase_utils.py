from firebase_admin import credentials, firestore, initialize_app, storage
import os

if os.getenv("ENVIRONEMENT") == "local":
    cred = credentials.Certificate("kotonoha_api/firebase_key.json")
    initialize_app(cred)
else:
    initialize_app()
db = firestore.client()
