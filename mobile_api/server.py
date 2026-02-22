import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI


def build_llm_client() -> OpenAI:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY ausente")
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    if provider == "ollama":
        base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
        return OpenAI(api_key=os.getenv("OLLAMA_API_KEY", "ollama"), base_url=base)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ausente")
    return OpenAI(api_key=api_key)


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
    try:
        client = build_llm_client()
    except RuntimeError as exc:
        return {"error": str(exc)}
    resp = client.chat.completions.create(
        model=payload.model,
        messages=[
            {"role": "system", "content": payload.system_prompt},
            {"role": "user", "content": payload.message},
        ],
        temperature=0.2,
    )
    return {"reply": resp.choices[0].message.content}


@app.get("/servers")
def servers():
    raw = os.getenv("SHARED_NANYIA_SERVERS", "")
    peers = [x.strip() for x in raw.split(",") if x.strip()]
    return {"self": "local", "peers": peers}
