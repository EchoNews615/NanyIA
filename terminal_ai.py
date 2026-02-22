import json
import os
import platform
import shlex
import sqlite3
import subprocess
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def build_llm_client() -> OpenAI:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("Defina OPENROUTER_API_KEY no .env")
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    if provider == "ollama":
        base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
        return OpenAI(api_key=os.getenv("OLLAMA_API_KEY", "ollama"), base_url=base)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Defina OPENAI_API_KEY no .env")
    return OpenAI(api_key=api_key)


try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

SYSTEM_PROMPT = """Você é a NanyIA, uma assistente de automação para PC/Codespaces.
Seu estilo é direto e altamente operacional.
Interprete comandos ambíguos e proponha a melhor ação automaticamente.
Priorize produtividade: código, arquivos, processos não críticos, navegador, git e documentação.
"""

MEMORY_DB = Path(".nanyia_memory.sqlite3")
SAFE_BLOCKED_PROCESSES = {
    "wininit",
    "csrss",
    "smss",
    "lsass",
    "services",
    "system",
    "registry",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add(self, content: str) -> str:
        self.conn.execute(
            "INSERT INTO notes(created_at, content) VALUES (?, ?)",
            (now_iso(), content),
        )
        self.conn.commit()
        return "Memória salva"

    def list_recent(self, limit: int = 8) -> str:
        rows = self.conn.execute(
            "SELECT created_at, content FROM notes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return "\n".join(f"- [{ts}] {c}" for ts, c in rows) if rows else "Sem memórias"


def run_shell(command: str) -> str:
    proc = subprocess.run(command, shell=True, text=True, capture_output=True)
    return json.dumps(
        {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-9000:],
            "stderr": proc.stderr[-9000:],
            "timestamp": now_iso(),
        },
        ensure_ascii=False,
    )


def read_file(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"Arquivo não encontrado: {p}"
    return p.read_text(encoding="utf-8")[:15000]


def write_file(path: str, content: str) -> str:
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"OK: arquivo salvo em {p}"


def open_chrome(url: str = "https://www.google.com") -> str:
    webbrowser.open(url)
    return f"Chrome/navegador aberto com: {url}"


def list_processes() -> str:
    if platform.system().lower().startswith("win"):
        return run_shell("tasklist")
    return run_shell("ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 30")


def terminate_process(process_name: str) -> str:
    base = process_name.strip().lower().replace(".exe", "")
    if base in SAFE_BLOCKED_PROCESSES:
        return f"Bloqueado por segurança: {process_name}"

    if platform.system().lower().startswith("win"):
        return run_shell(f"taskkill /IM {shlex.quote(process_name)} /F")
    return run_shell(f"pkill -f {shlex.quote(process_name)}")


def git_commit(message: str) -> str:
    return run_shell(f"git add -A && git commit -m {shlex.quote(message)}")


def git_push(remote: str = "origin", branch: str = "main") -> str:
    return run_shell(f"git push {shlex.quote(remote)} {shlex.quote(branch)}")


def web_fetch(url: str) -> str:
    return run_shell(f"curl -L --max-time 20 {shlex.quote(url)}")


def speak_text(text: str) -> str:
    if pyttsx3 is None:
        return "TTS indisponível. Instale pyttsx3."
    engine = pyttsx3.init()
    engine.say(text[:300])
    engine.runAndWait()
    return "Falado."


def listen_once(seconds: int = 6) -> str:
    if sr is None:
        return "SpeechRecognition indisponível. Instale SpeechRecognition + PyAudio."
    rec = sr.Recognizer()
    with sr.Microphone() as source:
        rec.adjust_for_ambient_noise(source, duration=0.6)
        audio = rec.listen(source, timeout=seconds, phrase_time_limit=seconds)
    try:
        txt = rec.recognize_google(audio, language="pt-BR")
        return txt
    except Exception as exc:
        return f"Falha ao reconhecer voz: {exc}"


def tool_specs():
    return [
        {"type": "function", "function": {"name": "run_shell", "description": "Executa comandos no shell", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
        {"type": "function", "function": {"name": "read_file", "description": "Lê arquivo", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "write_file", "description": "Escreve arquivo", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
        {"type": "function", "function": {"name": "open_chrome", "description": "Abre navegador com URL", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "list_processes", "description": "Lista processos", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "terminate_process", "description": "Encerra processo não crítico", "parameters": {"type": "object", "properties": {"process_name": {"type": "string"}}, "required": ["process_name"]}}},
        {"type": "function", "function": {"name": "git_commit", "description": "Commit git", "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
        {"type": "function", "function": {"name": "git_push", "description": "Push git", "parameters": {"type": "object", "properties": {"remote": {"type": "string"}, "branch": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "web_fetch", "description": "Busca web por URL", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
        {"type": "function", "function": {"name": "save_memory", "description": "Salva memória", "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}},
        {"type": "function", "function": {"name": "list_memories", "description": "Lista memórias", "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}}}},
        {"type": "function", "function": {"name": "listen_once", "description": "Captura comando de voz", "parameters": {"type": "object", "properties": {"seconds": {"type": "integer"}}}}},
        {"type": "function", "function": {"name": "speak_text", "description": "Fala um texto", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    ]


def execute_tool(name: str, args: dict, memory: MemoryStore) -> str:
    if name == "run_shell":
        return run_shell(**args)
    if name == "read_file":
        return read_file(**args)
    if name == "write_file":
        return write_file(**args)
    if name == "open_chrome":
        return open_chrome(**args)
    if name == "list_processes":
        return list_processes()
    if name == "terminate_process":
        return terminate_process(**args)
    if name == "git_commit":
        return git_commit(**args)
    if name == "git_push":
        return git_push(**args)
    if name == "web_fetch":
        return web_fetch(**args)
    if name == "save_memory":
        return memory.add(**args)
    if name == "list_memories":
        return memory.list_recent(**args)
    if name == "listen_once":
        return listen_once(**args)
    if name == "speak_text":
        return speak_text(**args)
    return f"Tool desconhecida: {name}"


def chat_loop() -> None:
    load_dotenv()
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")

    memory = MemoryStore(MEMORY_DB)
    client = build_llm_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("NanyIA online (texto+voz). Digite sair para encerrar.")

    while True:
        user_text = input("Você> ").strip()
        if user_text.lower() in {"sair", "exit", "quit"}:
            print("Até mais 👋")
            break

        messages.append({"role": "user", "content": f"[{now_iso()}] {user_text}"})

        while True:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tool_specs(),
                tool_choice="auto",
                temperature=0.2,
            )
            msg = response.choices[0].message

            assistant_msg = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
            messages.append(assistant_msg)

            if not msg.tool_calls:
                print(f"IA> {msg.content}\n")
                break

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                result = execute_tool(tc.function.name, args, memory)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": result,
                    }
                )


if __name__ == "__main__":
    chat_loop()
