import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="NanyIA Mobile Bridge", version="2.0")

origins_env = os.getenv("MOBILE_API_CORS_ORIGINS", "*")
origins: List[str] = [o.strip() for o in origins_env.split(",") if o.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    message: str
    model: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    system_prompt: str = "Você é a NanyIA para celular. Seja objetiva e útil."


@app.get("/health")
def health():
    return {"ok": True, "service": "nanyia-mobile-bridge"}


@app.post("/chat")
def chat(payload: ChatIn):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "OPENAI_API_KEY ausente"}

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=payload.model,
        messages=[
            {"role": "system", "content": payload.system_prompt},
            {"role": "user", "content": payload.message},
        ],
        temperature=0.2,
    )
    return {"reply": resp.choices[0].message.content}
