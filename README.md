# NanyIA 🚀

Suite completa com:

1. **Assistente terminal/Codespaces** (`terminal_ai.py`) com automações locais, web, voz e memória.
2. **Controle por mão** (`hand_control_mediapipe.py`) para mouse/clique/volume.
3. **Bridge API mobile** (`mobile_api/server.py`) para acesso pelo celular em qualquer IP configurado.
4. **App Android base** (`android_client/`) com Buildozer e serviço em segundo plano (stub).
5. **Bot Discord New Clan** (`discord_bot.py`) com moderação, tickets e cargos automáticos.

## 1) NanyIA terminal (PC + GitHub)

### Recursos
- Cria/edita código e arquivos (`write_file`, `read_file`).
- Executa comandos shell e git (`run_shell`, `git_commit`, `git_push`).
- Busca web (`web_fetch`) e abre navegador (`open_chrome`).
- Lista/encerra processos não críticos (`list_processes`, `terminate_process`).
- Voz: capta mic (`listen_once`) e fala (`speak_text`).
- Memória local SQLite (`save_memory`, `list_memories`).

### Rodar
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python terminal_ai.py
```

## 2) Mobile bridge (local ou servidor central)

```bash
uvicorn mobile_api.server:app --host 0.0.0.0 --port 8000
```

No Android, configure URL da API no topo da interface:
- local: `http://IP_DA_SUA_MAQUINA:8000/chat`
- servidor central: `https://seu-dominio/chat`

## 3) Android APK (Buildozer)

Arquivos:
- `android_client/main.py`
- `android_client/service.py` (base para segundo plano)
- `android_client/buildozer.spec`

Build (Linux):
```bash
cd android_client
buildozer android debug
```

APK em `android_client/bin/`.

## 4) Bot Discord New Clan

### Recursos
- `/setup_clan_roles` cria cargos (Lider, SubLider, Recrutador, etc.).
- `/ticket` abre ticket; `/close_ticket` fecha ticket.
- `/mute` e `/ban` para moderação.
- Responde quando alguém mencionar "bot" na frase.
- Detecta palavras tóxicas e alerta canal admin.

### Rodar
```bash
cp .env.example .env
python discord_bot.py
```

Configure no `.env`:
- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `DISCORD_ADMIN_ALERT_CHANNEL_ID`
- `DISCORD_TICKET_CATEGORY_ID`
- `DISCORD_MUTED_ROLE_NAME`

## 5) Prompt mestre

Use `PROMPT_NANYIA.md` para comportamento operacional da IA.


## Automação: sync + build APK + push

Para automatizar remote/push/build em uma máquina com internet e toolchain Android:

```bash
bash scripts/sync_and_build_apk <URL_DO_REPO_GITHUB> [branch]
# ou
bash scripts/sync_and_build_apk.sh <URL_DO_REPO_GITHUB> [branch]
```

Exemplo:

```bash
bash scripts/sync_and_build_apk https://github.com/seu-user/nanyia.git work
```

O script:
- configura `origin` se não existir;
- tenta instalar `buildozer`;
- compila os arquivos Python;
- gera APK com `buildozer android debug`;
- faz push para o GitHub.


> Pode rodar a partir de qualquer diretório: o script detecta automaticamente a raiz do repositório.
