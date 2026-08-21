# Setup Guide

Step-by-step installation, with the errors you are most likely to hit and how to
fix them.

---

## 1. Check your tools

```bash
python --version
```

Needs to be **3.10 – 3.12**. On Windows, `py -0` lists every installed version.

> **Python 3.13+**: some scientific packages may not have wheels yet. If
> `pip install` fails to build something, install Python 3.12 and create the
> venv with `py -3.12 -m venv venv`.

```bash
node --version
```

Needs to be **18 or newer**.

---

## 2. Backend

### 2.1 Create the virtual environment

```bash
cd backend
```

```bash
python -m venv venv
```

This creates `backend/venv/`. It is gitignored — each developer makes their own.

### 2.2 Activate it

**Windows (PowerShell or the VS Code terminal):**

```bash
venv\Scripts\activate
```

**Windows (Git Bash):**

```bash
source venv/Scripts/activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

Your prompt should now start with `(venv)`. **Every backend command below
assumes the venv is active.**

> **PowerShell blocks the activate script?**
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2.3 Install dependencies

```bash
python -m pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

About 150 MB. TensorFlow is deliberately **not** in this list — see
[ML_MODELS.md](ML_MODELS.md).

### 2.4 Create your `.env`

**Windows:**

```bash
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

The defaults work immediately. Before letting anyone else reach the server,
generate a real secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

and paste it into `SECRET_KEY`.

### 2.5 Start the server

```bash
uvicorn app.main:app --reload
```

You should see a startup banner reporting which models loaded:

```
Smart Sugarcane AI v1.0.0
Model mode: auto
  Irrigation : RULE ENGINE (no model file)
  Disease    : DEMO HEURISTIC (no model file)
  Soil       : DEMO HEURISTIC (no model file)
```

The database file `backend/smart_sugarcane.db` is created automatically on
first start — there is no migration step.

Verify: open http://localhost:8000/docs

---

## 3. Frontend

Open a **second terminal** — leave the backend running.

```bash
cd frontend
```

```bash
npm install
```

```bash
copy .env.example .env
```

```bash
npm run dev
```

Verify: http://localhost:5173 opens automatically.

---

## 4. Train the irrigation model (optional, 30 seconds)

From the **project root**, with the backend venv active:

```bash
python ml/irrigation/train.py
```

Expected output ends with something like:

```
  R2   : 0.9624
  MAE  : 1.354 mm
  Accuracy : 96.42 %
Saved model bundle : .../models/irrigation_model.joblib
```

Restart the backend. The banner now reads `Irrigation : TRAINED MODEL`.

> Those metrics measure how well the forest reproduces the water-balance model
> it was trained on — **not** real-world irrigation accuracy. See
> [ML_MODELS.md](ML_MODELS.md).

---

## 5. Verify the whole thing works

```bash
cd backend
```

```bash
venv\Scripts\python smoke_test.py
```

Expected: `PASSED: 75    FAILED: 0`.

```bash
venv\Scripts\python calibration_check.py
```

Expected: `All calibration cases classified correctly.`

---

## 6. Optional: live weather

1. Get a free key at [openweathermap.org/api](https://openweathermap.org/api)
   (the "Current Weather Data" plan is free).
2. Put it in `backend/.env`:

```env
OPENWEATHER_API_KEY=your_key_here
DEFAULT_WEATHER_CITY=Belagavi,IN
```

3. Restart the backend.

The **Use weather** button on the irrigation page now fills temperature,
humidity, rainfall, rain probability and wind automatically. Soil moisture,
soil type and growth stage still have to come from you — no weather service
knows those.

Without a key, every feature still works; the weather panel just says it is not
configured.

---

## 7. Common problems

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | Running uvicorn from the wrong directory | `cd backend` first |
| `'uvicorn' is not recognized` | venv not active | `venv\Scripts\activate` |
| `no such table: users` | Startup lifespan did not run | Start with `uvicorn app.main:app`, not by importing the module directly |
| Frontend: "Cannot reach the backend" | Backend down, wrong port, **or the IPv6 `localhost` trap** | Check http://127.0.0.1:8000/api/system/health. If that works, see the note below the table |
| CORS error in console | Frontend origin not allowed | Add it to `CORS_ORIGINS` in `backend/.env`, restart |
| Images upload but do not display | Backend not running (dev proxy fails) | Start the backend; or set `VITE_MEDIA_BASE_URL` |
| `Port 8000 is already in use` | Another process on that port | `uvicorn app.main:app --reload --port 8001` and update `VITE_API_BASE_URL` |
| Tailwind classes have no effect | Dev server started before `npm install` finished | Stop and re-run `npm run dev` |
| `npm ERR! code EACCES` | Permission problem | Do not use `sudo`; fix npm's directory permissions |

### The IPv6 `localhost` trap

On Windows, `localhost` resolves to `::1` (IPv6) **before** `127.0.0.1`, but
uvicorn binds to IPv4 only by default. The browser tries IPv6 first, gets
`ERR_CONNECTION_REFUSED`, and the app reports it cannot reach the backend — even
though the server is running perfectly.

`curl http://localhost:8000` will appear to work, because curl silently falls
back to IPv4. **A working curl does not rule this out.** Test IPv6 explicitly:

```bash
curl "http://[::1]:8000/api/system/health"
```

If that fails while `127.0.0.1` succeeds, this is your problem. The project
ships with `VITE_API_BASE_URL=http://127.0.0.1:8000/api` for exactly this
reason. If you changed it to `localhost`, change it back and restart Vite —
`.env` is only read at startup.

To serve both stacks instead: `uvicorn app.main:app --reload --host ::`

---

## 8. Resetting

**Wipe all data and start fresh:**

```bash
rm backend/smart_sugarcane.db
```

```bash
rm -rf uploads/plants/* uploads/soil/*
```

Restart the backend — the database is recreated empty.

**Rebuild the backend environment:**

```bash
rm -rf backend/venv
```

Then repeat step 2.

---

## 9. Moving to PostgreSQL later

The code is database-agnostic — only the connection string changes.

```bash
pip install "psycopg[binary]"
```

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/smart_sugarcane
```

Restart. SQLAlchemy creates the tables on startup exactly as it does for SQLite.
The SQLite-specific `check_same_thread` argument in `app/database.py` is applied
conditionally, so nothing else needs touching.
