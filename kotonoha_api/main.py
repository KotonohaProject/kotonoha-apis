from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from firebase_admin import credentials, firestore, initialize_app, storage
from pydantic import BaseModel
from openai import Client, OpenAI
from typing import Annotated
import io
from starlette.middleware.cors import CORSMiddleware
from tempfile import TemporaryDirectory

client = OpenAI()

ASSISTANT_ID = "asst_DBYwpIgQOS2gHV2edTNwlZ1s"

#cred = credentials.Certificate("kotonoha-hack-firebase-adminsdk-6q5qk-5b0b0d0d1e.json")
#initialize_app(cred)
initialize_app()
db = firestore.client()
storage = storage.bucket("speaking-53cb7.appspot.com")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserInput(BaseModel):
    name: str
    user_id: str

class ConversationInput(BaseModel):
    user_id: str

@app.get("/")
async def root() -> dict:
    return {"message": "Hello World"}
