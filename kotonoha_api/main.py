import dotenv

dotenv.load_dotenv()

from pathlib import Path
from fastapi import FastAPI, Header
from urllib.parse import urlencode

from pydantic import BaseModel
from openai import Client, OpenAI
from typing import Annotated
from starlette.middleware.cors import CORSMiddleware
from tempfile import TemporaryDirectory
import dotenv
import os
import datetime
from kotonoha_api.firebase_utils import db
from kotonoha_api.auth import get_user_collection, get_user_data

# 3e567ec8


client = OpenAI()


# storage = storage.bucket("speaking-53cb7.appspot.com")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

# Define Pydantic models for your API


class RolePlayMessage(BaseModel):
    message: str
    role: str
    fixed_message: Optional[str] = None


class Mission(BaseModel):
    mission: str
    completed: bool


class Mistake(BaseModel):
    title: str
    detailed_explanation: str


class Knowledge(BaseModel):
    knowledge: str
    translation: str
    explanation: str
    example_sentence: str
    example_sentence_translated: str


class RolePlayRequestBody(BaseModel):
    scenario_id: str
    messages: List[RolePlayMessage]
    missions_completed: List[Mission]
    mistakes: List[Mistake]
    knowledge: List[Knowledge]


class EssaySentence(BaseModel):
    original: str
    edited: str
    explanations: List[str]


class EssayRequestBody(BaseModel):
    topic_id: str
    comment: str
    sentences: List[EssaySentence]
    native_expressions: List[Knowledge]
    mistakes: List[Mistake]


# Define FastAPI endpoints


# get authentication header
@app.get("/role_plays")
async def get_user_role_play(authorization: str = Header()):
    # Process request here
    try:
        user = get_user_collection(authorization)
    except:
        user_language = get_user_data(authorization)["locale"]
        return {
            "status:": "User not found",
            "instructions": f"{user_language} Write prompt for GPT here on what to do if user is not found",
        }

    user_dict: dict = user.to_dict()
    scenario_dict: dict = user_dict["current_scenario"].get().to_dict()

    result = {
        "role_play_language": user_dict["target_language"],
        "explanation_language": user_dict["source_language"],
        "situation": scenario_dict["situation"],
        "missions": scenario_dict["missions"],
        "scenario_id": user_dict["current_scenario"].id,
    }
    return result


@app.post("/role_plays")
async def save_user_role_play(
    role_play_request: RolePlayRequestBody, authorization: str = Header()
):
    try:
        user = get_user_collection(authorization)
    except:
        user_language = get_user_data(authorization)["locale"]
        return {
            "status:": "User not found",
            "instructions": f"{user_language} Write prompt for GPT here on what to do if user is not found",
        }
    knowledges = role_play_request.knowledge
    knowledge_collections = []
    for knowledge in knowledges:
        knowledge_collections.append(db.collection("users").document(user.id).collection("mindles").add(
            {
                "mindle": knowledge.knowledge,
                "translation": knowledge.translation,
                "explanation": knowledge.explanation,
                "example_sentence": knowledge.example_sentence,
                "example_sentence_translated": knowledge.example_sentence_translated,
                "create_at": datetime.datetime.now(),
                "status": "not_saved"
            }
        ))
    
    mistakes = role_play_request.mistakes
    mistake_collections = []
    for mistake in mistakes:
        mistake_collections.append(db.collection("users").document(user.id).collection("mistakes").add(
            {
                "title": mistake.title,
                "explanation": mistake.detailed_explanation,
                "create_at": datetime.datetime.now(),
                "status": "learning"
            }
        ))
    




    scenario_document = db.collection("scenarios").document(role_play_request.scenario_id)
    if not scenario_document.get().exists:
        # use current scneario
        scenario_document = user.to_dict()["current_scenario"]
        
    db.collection("users").document(user.id).collection("conversations").add(
        {
            "scenario":  scenario_document,
            "messages": role_play_request.messages,
            "missions_completed": role_play_request.missions_completed,
            "mistakes": mistake_collections,
            "mindles": knowledge_collections,
            "create_at": datetime.datetime.now(),
        }
    )    
    
    return {"status": "OK"}


@app.get("/essays")
async def get_user_topic(user_id: str, authorization: str = Header()):
    # Process request here
    print(f"Received user_id: {user_id}")
    return {"status": "OK"}


@app.post("/essays")
async def save_essay_review(
    essay_request: EssayRequestBody, authorization: str = Header()
):
    print(essay_request)
    return {"status": "OK"}


@app.get("/privacy_policy")
async def get_privacy_policy():
    # return privacy_policy.txt as string
    policy_text = Path("privacy_policy.txt").read_text()
    return policy_text
