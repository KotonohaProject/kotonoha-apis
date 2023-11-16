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
import dotenv
import os
import datetime
from typing import Literal


#3e567ec8

dotenv.load_dotenv()

client = OpenAI()

if os.getenv("ENVIRONEMENT") == "local":
    cred = credentials.Certificate("kotonoha_api/firebase_key.json")
    initialize_app(cred)
else:
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
    password: str

class LoginInput(BaseModel):
    email: str
    password: str

class WordInput(BaseModel):
    user_id: str
    gpt_id: str
    word: str
    meaning: str
    example: str

class EssayInput(BaseModel):
    user_id: str
    gpt_id: str
    essay: str

class Conversation(BaseModel):
    content: str
    role: str

class ConversationInput(BaseModel):
    user_id: str
    gpt_id: str
    role_play_id: str
    conversations: list[Conversation]

class RolePlay(BaseModel):
    situation: str
    objective: str
    emoji: str

class RolePlayInput(BaseModel):
    user_id: str
    role_plays: list[RolePlay]

class SetRolePlayInput(BaseModel):
    user_id: str
    role_play_id: str

class Mistake(BaseModel):
    mistake_title: str
    mistake_explanation: str
    mistake_type: str

class MistakeInput(BaseModel):
    user_id: str
    gpt_id: str
    mistakes: list[Mistake]

def read_schema_file():
    with open('kotonoha_api/schema.yml', 'r') as file:
        # return the content as text
        return file.read()

@app.get("/schema.yml")
def schema():
    schema_content = read_schema_file()
    return schema_content

# these are for GPTs
@app.post("/login")
def login(user_input: UserInput):
    # hash password
    password = user_input.password
    hash = hashlib.md5(password.encode())
    hash = hash.hexdigest()
    user_input.password = hash
    users = db.collection("users").where("email", "==", user_input.email).stream()
    users = list(users)
    print(users)
    if len(users) == 0:
        raise HTTPException(status_code=401, detail="User not found")

    for user in users:
        user = user.to_dict()
        if user["password"] == user_input.password:
            return {"user_id": user["user_id"]}
        else:
            raise HTTPException(status_code=401, detail="Wrong password")


@app.post("/signup")
def signup(user_input: UserInput):
    #check if user already exists
    users = db.collection("users").where("email", "==", user_input.email).stream()
    users = list(users)
    if len(users) > 0:
        raise HTTPException(status_code=401, detail="User already exists")
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
        user_data = user_input.model_dump()
        user_data["user_id"] = user_id
        db.collection("users").document(user_id).set(user_data)
        return {"user_id": user_id}

@app.post("/words/learning")
def add_word_to_learning(word: WordInput):
    user_id = word.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    word_dict = word.model_dump()
    word_dict["date"] = datetime.datetime.now()
    word_dict["word"] = word_dict["word"].lower()

    db.collection("users").document(word.user_id).collection("words_learning").document(word_dict["word"]).set(word_dict)
    return {"message": "success"}

@app.get("/words/learning")
def get_learning_words(user_id: str):
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")
    words = db.collection("users").document(user_id).collection("words_learning").stream()
    words = [word.to_dict() for word in words]
    #
    return {"words": words}

@app.post("/words/active")
def add_word_to_active(word: WordInput):
    user_id = word.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    word_dict = word.model_dump()
    word_dict["date"] = datetime.datetime.now()
    word_dict["word"] = word_dict["word"].lower()

    db.collection("users").document(word.user_id).collection("words_active").document(word_dict["word"]).set(word_dict)
    # check if the word is in learning, then delete it
    db.collection("users").document(word.user_id).collection("words_learning").document(word_dict["word"]).delete()
    return {"message": "success"}


@app.get("/words/active")
def get_active_words(user_id: str):
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")
    words = db.collection("users").document(user_id).collection("active").stream()
    words = [word.to_dict() for word in words]
    words = words[:10]
    return {"words": words}

@app.post("/essays")
def add_essay(essay_input: EssayInput):
    user_id = essay_input.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    essay_id = uuid.uuid4().hex[:8]
    essay_dict = essay_input.model_dump()
    essay_dict["date"] = datetime.datetime.now()

    db.collection("users").document(essay_input.user_id).collection("essays").document(essay_id).set(essay_dict)
    return {"message": "success"}

@app.post("/conversations")
def add_conversation(conversation_input: ConversationInput):
    user_id = conversation_input.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    # finishe role play
    role_play_id = conversation_input.role_play_id
    role_play = db.collection("users").document(user_id).collection("role_plays").document(role_play_id).get().to_dict()
    role_play["finished"] = True
    db.collection("users").document(user_id).collection("role_plays").document(role_play_id).set(role_play)

    conversation_id = uuid.uuid4().hex[:8]
    conversation_dict = conversation_input.model_dump()
    conversation_dict["date"] = datetime.datetime.now()

    db.collection("users").document(conversation_input.user_id).collection("conversations").document(conversation_id).set(conversation_dict)
    return {"message": "success"}

@app.post("/convesations")
def add_conversation(conversation_input: ConversationInput):
    user_id = conversation_input.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    conversation_id = uuid.uuid4().hex[:8]
    conversation_dict = conversation_input.model_dump()
    conversation_dict["date"] = datetime.datetime.now()

    db.collection("users").document(conversation_input.user_id).collection("conversations").document(conversation_id).set(conversation_dict)
    return {"message": "success"}


@app.post("/role_plays")
def add_role_play(role_play_input: RolePlayInput):
    user_id = role_play_input.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")


    role_play_dict = role_play_input.model_dump()
    role_plays = role_play_dict["role_plays"]
    for role_play in role_plays:
        role_play_id = uuid.uuid4().hex[:8]
        role_play["role_play_id"] = role_play_id
        role_play["date"] = datetime.datetime.now()
        role_play["finished"] = False
        db.collection("users").document(role_play_input.user_id).collection("role_plays").document(role_play_id).set(role_play)

    return {"message": "success"}


@app.get("/current_role_play")
def get_current_role_play(user_id: str):
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")
    user = db.collection("users").document(user_id).get().to_dict()
    role_play_id = user["current_role_play"]
    role_play = db.collection("users").document(user_id).collection("role_plays").document(role_play_id).get().to_dict()
    return {"role_play": role_play}



@app.post("/current_role_play")
def set_current_role_play(set_role_play_input: SetRolePlayInput):
    user_id = set_role_play_input.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    db.collection("users").document(set_role_play_input.user_id).update({"current_role_play": set_role_play_input.role_play_id})

    return {"message": "success"}

@app.get("/current_word_review")
def get_current_word_review(user_id: str):
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")
    user = db.collection("users").document(user_id).get().to_dict()
    word = db.collection("users").document(user_id).collection("words_learning").document(user["current_word_review"]).get().to_dict()
    return {"word": word}

@app.post("/mistakes")
def add_mistake(mistake_input: MistakeInput):
    user_id = mistake_input.user_id
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")

    mistake_id = uuid.uuid4().hex[:8]
    mistake_dict = mistake_input.model_dump()
    mistakes = mistake_dict["mistakes"]
    for mistake in mistakes:
        mistake_id = uuid.uuid4().hex[:8]
        mistake["date"] = datetime.datetime.now()
        mistake["archived"] = False
        db.collection("users").document(mistake_input.user_id).collection("mistakes").document(mistake_id).set(mistake)

    return {"message": "success"}


@app.get("/essays")
def get_essays(user_id: str):
    if not db.collection("users").document(user_id).get().exists:
        raise HTTPException(status_code=401, detail="User not found")
    essays = db.collection("users").document(user_id).collection("essays").stream()
    essays = [essay.to_dict() for essay in essays]
    return {"essays": essays}
