# GitHub RSS Discord Bot

Bot Discord sederhana yang hanya menggunakan GitHub Atom/RSS Search sebagai sumber informasi.

## Install

```bash
pip install -r requirements.txt
```

Buat `.env`:

```env
DISCORD_TOKEN=TOKEN_BOT_DISCORD
DISCORD_CHANNEL_ID=ID_CHANNEL_DISCORD
CHECK_INTERVAL_MINUTES=10
DB_FILE=github_rss.db
```

Jalankan:

```bash
python bot.py
```

## Commands

- `/scan` — scan GitHub sekarang
- `/feeds` — lihat keyword yang dimonitor
- `/test` — test Discord

Database SQLite digunakan supaya item yang sudah dikirim tidak dikirim ulang.

## Mengubah topik

Edit `SEARCH_QUERIES` di `bot.py`.

Contoh:

```python
SEARCH_QUERIES = [
    '"AI agent"',
    '"coding agent"',
    '"MCP server"',
    '"browser agent"',
    '"computer use agent"',
    '"AI coding"',
]
```

Catatan: GitHub menyediakan feed Atom untuk resource/feed tertentu. Untuk kebutuhan discovery repository berdasarkan search, bot ini menggunakan endpoint Atom Search GitHub. Jika GitHub mengubah atau membatasi endpoint tersebut, pendekatan ini perlu diganti ke GitHub API.
