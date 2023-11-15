from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from urllib.parse import urlencode
from fastapi.responses import StreamingResponse, RedirectResponse
from firebase_admin import credentials, firestore, initialize_app, storage
from pydantic import BaseModel
from openai import Client, OpenAI
from typing import Annotated
import io
from starlette.middleware.cors import CORSMiddleware
from tempfile import TemporaryDirectory
import requests
import sys
import hashlib
import uuid
import yaml

client = OpenAI()

#cred = credentials.Certificate("kotonoha-hack-firebase-adminsdk-6q5qk-5b0b0d0d1e.json")
#initialize_app(cred)
initialize_app()
db = firestore.client()
#storage = storage.bucket("speaking-53cb7.appspot.com")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserInput(BaseModel):
    email: str
    name: str
    password: str

class LoginInput(BaseModel):
    email: str
    password: str

def read_schema_file():
    with open('schema.yml', 'r') as file:
        return yaml.safe_load(file)

@app.get("/schema.yml")
def schema():
    schema_content = read_schema_file()
    return schema_content



@app.post("/login")
def login(user_input: UserInput):
    # hash password
    password = user_input.password
    hash = hashlib.md5(password.encode())
    hash = hash.hexdigest()
    user_input.password = hash
    # check if user exists
    user = db.collection("users").document(user_input.user_id).get()
    if user.exists:
        # check if password is correct
        if user_input.password == user.to_dict()["password_hash"]:
            # return user id
            return {"user_id": user_input.user_id}
        else:
            raise HTTPException(status_code=401, detail="Incorrect password")
    else:
        raise HTTPException(status_code=401, detail="User does not exist")


@app.post("/signup")
def signup(user_input: UserInput):
    # hash password
    password = user_input.password
    hash = hashlib.md5(password.encode())
    hash = hash.hexdigest()
    user_input.password = hash
    # create user id
    user_id =  uuid.uuid4().hex[:8]
    # check if user exists
    user = db.collection("users").document(user_id).get()
    if user.exists:
        raise HTTPException(status_code=401, detail="User already exists")
    else:
        # create user
        db.collection("users").document(user_id).set(user_input.model_dump())
        return {"user_id": user_id}
