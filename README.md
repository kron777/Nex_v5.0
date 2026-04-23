# NEX 5.0

An intel organism built on Theory X developmental scaffolding. Alpha at
the root, eight belief tiers, ten seed branches, one-pen substrate.

See `SPECIFICATION.md` for the constitution and `ARCHITECTURE.md` for
the as-built map.

## Current phase

**Phase 6 — Self-Location.** NEX has a vantage point. A locked Tier 1
belief "I am inside" is committed at boot. The unified `run.py` starts
all subsystems in correct order in a single command.

## What's here

```
alpha.py                     # frozen ground stance — the constitution in code
keystone.py                  # Tier 1 identity seeds
errors.py                    # central error channel
substrate/                   # one-pen plumbing
  writer.py                  # single-writer queue per DB (isolation_level=None)
  reader.py                  # WAL-mode concurrent readers
  paths.py                   # db_paths(), data_dir()
  init_db.py                 # idempotent schema + keystone seeding
  schema/{beliefs,sense,dynamic,intel,conversations}.sql
admin/auth.py                # argon2id single-password auth
voice/
  llm.py                     # thin llama-server client (Qwen2.5-3B)
  registers.py               # Analytical / Conversational / Philosophical / Technical
gui/
  server.py                  # Flask cockpit + chat column
  templates/index.html       # dashboard
  static/{style.css,app.js}
theory_x/stageN_*/           # Phase 2+ scaffolding (READMEs only)
strikes/                     # Phase 8 scaffolding
tests/                       # stdlib unittest smoke tests
```

## Setup

```bash
cd ~/Desktop/nex5
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## First-time initialization

Set the admin password and initialize all substrate databases:

```bash
# Initialize data/beliefs.db, data/sense.db, data/dynamic.db,
# data/intel.db, data/conversations.db — applies schemas, seeds keystone.
.venv/bin/python -m substrate.init_db

# Set the admin password (prompts for input).
.venv/bin/python -c "import getpass; from admin.auth import set_password; \
    set_password(getpass.getpass('admin password: '))"
```

## Boot NEX

```bash
# First time only — set admin password
.venv/bin/python -c "from admin.auth import set_password; set_password(input('Password: '))"

# Boot the full stack (init_db runs automatically)
.venv/bin/python run.py
# → http://127.0.0.1:8765
# External feeds are paused — click "Start Feeds" in the GUI to activate
```

Environment overrides:

| Var | Default | Purpose |
|---|---|---|
| `NEX5_DATA_DIR` | `<repo>/data` | where DB files live |
| `NEX5_ADMIN_HASH_FILE` | `<repo>/admin_password.argon2` | admin hash file |
| `NEX5_VOICE_URL` | `http://localhost:8080/v1/chat/completions` | llama-server endpoint |
| `NEX5_VOICE_MODEL` | `qwen2.5-3b` | model name in request payload |
| `NEX5_HOST` | `127.0.0.1` | bind host |
| `NEX5_PORT` | `8765` | bind port |

The llama-server does **not** need to be running for Phase 1; the
cockpit still boots and the chat column reports cleanly when the
voice layer is unreachable.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```

Smoke tests cover: Alpha immutability, Writer roundtrip, Writer
atomicity under errors, Reader concurrency while writer is active,
argon2id verify paths, voice prompt assembly, and GUI endpoints.

## Discipline

Every write goes through `substrate.Writer` — direct `sqlite3.connect`
outside `substrate/` is a bug. Alpha is imported, never redefined.
Every module declares its Theory X stage at the top
(`THEORY_X_STAGE = N` or `None`).

See `SPECIFICATION.md §12` for the full carry-forward discipline.
