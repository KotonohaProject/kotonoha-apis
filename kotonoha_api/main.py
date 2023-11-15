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

redirect_uri = app.url_path_for("intermediate")

class UserInput(BaseModel):
    name: str
    user_id: str

class ConversationInput(BaseModel):
    user_id: str

@app.get("/")
async def root() -> dict:
    return {"message": "Hello World"}

client_id ="test"
client_secret = "test"
openai_redirect_uri = "test"

@app.get("/authorize")
async def authorize(request: Request):
    state = request.query_params.get('state')

    scope = "openid email profile"
    redirect_uri = app.url_path_for("intermediate")

    # Construct the Google OAuth URL with the state parameter and an intermediate redirect_uri
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return RedirectResponse(f"{google_auth_url}?{urlencode(params)}")


@app.get("/intermediate")
async def intermediate(request: Request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    # Redirect to OpenAI's callback URL with code and state

    params = {"code": code, "state": state}

    redirect_uri = request.query_params.get('redirect_uri')

    print(f"Intermediate redirect with params = {params} and redirect = {redirect_uri}")

    return RedirectResponse(f"{openai_redirect_uri}?{urlencode(params)}")


@app.post("/token")
async def token(request: Request):
    try:
        request_data = await request.form()
        code = request_data.get('code')

        print(f"token endpoint: request data = {request_data}")

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,  # Use the same redirect_uri as in /authorize
            "grant_type": "authorization_code"
        }

        response = requests.post(token_url, data=data)

        # Check if the response from Google is successful
        if response.status_code != 200:
            print("Error during token exchange with Google:", response.status_code, response.text)
            raise HTTPException(status_code=500, detail="Token exchange failed with Google")

        token_response = response.json()

        # Check if the necessary tokens are present in the response
        if "access_token" not in token_response or "refresh_token" not in token_response:
            print("Missing tokens in Google's response:", token_response)
            raise HTTPException(status_code=500, detail="Missing tokens in response from Google")

        # Return the formatted token response
        return {
            "access_token": token_response.get("access_token"),
            "token_type": "bearer",
            "refresh_token": token_response.get("refresh_token"),
            "expires_in": token_response.get("expires_in")
        }

    except requests.RequestException as e:
        print("Request exception during token exchange:", e, file=sys.stderr)
        raise HTTPException(status_code=500, detail="Token exchange request failed")

    except Exception as e:
        print("Unexpected error in /token endpoint:", e, file=sys.stderr)
        raise HTTPException(status_code=500, detail="Unexpected error in token exchange")
