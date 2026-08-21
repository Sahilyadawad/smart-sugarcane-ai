# Backend — Smart Sugarcane AI API

FastAPI + SQLAlchemy + SQLite. Serves every prediction endpoint and the React
frontend's data.

## Run it

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
copy .env.example .env
```

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Model status: http://localhost:8000/api/system/status

> Run uvicorn **from this directory**, not the project root, or `app` will not
> be importable.

## Test it

```bash
venv\Scripts\python smoke_test.py
```

75 checks against an in-process test client — no server or network needed.

```bash
venv\Scripts\python calibration_check.py
```

Confirms the demo image heuristics still respond to the right visual cues.

## Layout

```
app/
├── api/         routers — HTTP concerns only
├── core/        config, security (JWT + bcrypt), dependencies
├── models/      SQLAlchemy ORM
├── schemas/     pydantic contracts
├── services/    business logic
├── ml/          rule engine, image features, model loaders
├── database.py  engine, session, UTCDateTime
└── main.py      app factory, CORS, static uploads, lifespan
```

Dependencies flow one way: `api → services → ml → models`. `ml/irrigation_engine.py`
imports nothing outside the standard library, so the training scripts in `ml/`
can share it.

## Notes

- The database file is created automatically on first startup. There is no
  migration step.
- TensorFlow is **not** in `requirements.txt` on purpose — the API runs fine
  without it, in clearly-labelled demo image mode. Install it only to train the
  image models: `pip install -r ../ml/disease_detection/requirements.txt`.
- Every AI response carries `model_source`, so the frontend can label how the
  result was produced. Keep that contract when adding endpoints.

Full details: [`../docs/API.md`](../docs/API.md) and
[`../docs/PROJECT_ARCHITECTURE.md`](../docs/PROJECT_ARCHITECTURE.md).
