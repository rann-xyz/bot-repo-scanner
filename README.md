# AI Repo Radar — Discord Bot

Discord bot yang memonitor repository GitHub baru yang berkaitan dengan AI Agent, AI Coding, MCP, AI Tools, RAG, dan LLM.

## Fitur

- Scheduled GitHub repository discovery.
- Multi-query discovery.
- Deduplication dengan SQLite.
- Rule-based relevance scoring.
- Optional Ollama local LLM analysis.
- Discord Embed notification.
- Slash commands:
  - `/scan`
  - `/stats`
  - `/latest`
  - `/test`
- Configurable category keywords.
- Rate-limit friendly serial GitHub requests.
- Docker support.

## 1. Buat Discord bot

Buka Discord Developer Portal dan buat application + bot.

Bot membutuhkan permission untuk:
- View Channels
- Send Messages
- Embed Links

Undang bot ke server menggunakan OAuth2 URL Generator.

Bot menggunakan slash commands, jadi tidak perlu `message_content` intent untuk fungsi utama.

## 2. GitHub token

Gunakan GitHub Personal Access Token atau GitHub App token. Token disimpan di `.env`.

GitHub menyatakan authenticated requests memiliki rate limit lebih tinggi daripada unauthenticated requests.

## 3. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Isi:

```env
DISCORD_TOKEN=...
DISCORD_CHANNEL_ID=...
GITHUB_TOKEN=...
```

## 4. Jalankan

```bash
python main.py
```

Bot akan scan sesuai `POLL_INTERVAL_MINUTES`.

## 5. Docker

```bash
docker compose up -d --build
```

## Cara kerja

```text
Scheduler
   |
   v
GitHub Search API
   |
   v
Candidate repositories
   |
   v
SQLite deduplication
   |
   v
Keyword/category scoring
   |
   +---- optional Ollama analysis
   |
   v
Score threshold
   |
   v
Discord Embed
```

## Catatan

Bot menggunakan polling untuk discovery. GitHub merekomendasikan webhook/event bila tersedia untuk kasus yang cocok, dan jika polling diperlukan, polling harus dilakukan secara efisien agar tidak terkena rate limit.

Search API GitHub memiliki rate limit tersendiri, sehingga jangan menurunkan interval polling terlalu agresif.

## Ollama

Jika ingin analisis LLM lokal:

```bash
ollama pull llama3.2:3b
```

Lalu:

```env
ENABLE_LLM=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

Jika Ollama gagal, bot otomatis kembali menggunakan analisis rule-based.

## Produksi

Untuk production, pertimbangkan:
- PostgreSQL
- GitHub App
- queue worker
- retry/backoff
- webhook untuk event yang memang dapat di-webhook
- metrics/health check
- Docker restart policy
