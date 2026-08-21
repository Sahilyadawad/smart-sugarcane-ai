# Deployment

Two supported options. **Option A puts the whole app on Vercel** — frontend and
backend in one project, same origin, no CORS.

| | Option A — all on Vercel | Option B — Vercel + Render |
|---|---|---|
| Frontend | Vercel | Vercel |
| Backend | Vercel serverless function | Render container |
| Irrigation AI | Rule engine (no scikit-learn) | **Trained Random Forest** |
| Uploaded photos kept | No | Yes (paid plan) |
| Database | Hosted Postgres **required** | SQLite (wiped on deploy) or Postgres |
| Cold start | ~2 s | 30–60 s on free tier |
| CORS setup | None needed | Must set `CORS_ORIGINS` |

**Option A is the better demo** — faster cold starts and nothing to configure
between the two halves. **Option B keeps the trained model.** Pick A unless the
trained Random Forest specifically matters to your assessment.

---

## Option A — everything on Vercel

### What changes, and why it is honest

Vercel caps a Python function at **250 MB uncompressed**. The full dependency
stack measures **457 MB**:

| Package | Size |
|---|---|
| SciPy | 109 MB |
| OpenCV | 106 MB |
| pandas | 63 MB |
| NumPy | 51 MB |
| scikit-learn | 45 MB |
| everything else | ~83 MB |

The root `requirements.txt` therefore installs a trimmed set (~100 MB): NumPy and
Pillow stay, the rest go. The consequences are contained:

- **Irrigation** falls back to the water-balance rule engine. This is not a
  downgrade in accuracy so much as a change of implementation — the Random
  Forest was trained *to reproduce that engine* and scores R² 0.96 against it.
  The API reports `model_source: rule_engine`, and the UI badge says so.
- **OpenCV was always optional.** `image_features.py` has NumPy fallbacks for
  every OpenCV call, so disease and soil analysis are unaffected.
- **pandas** was only used to build the model's input frame, so it goes with it.

Uploaded photos are **not saved** — a serverless filesystem is read-only.
`settings.persist_uploads` detects the `VERCEL` environment variable and skips
storage; analyses still run and are saved, only the thumbnail is missing.

### Step 1 — get a free Postgres database (required)

SQLite cannot work on Vercel: the filesystem is wiped between invocations, so
every account and analysis would vanish. This step is not optional.

[neon.tech](https://neon.tech) is the fastest — sign up, create a project, copy
the connection string. [supabase.com](https://supabase.com) works too.

The string will look like:

```
postgresql://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require
```

Convert it for SQLAlchemy by changing the scheme to `postgresql+psycopg`:

```
postgresql+psycopg://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require
```

### Step 2 — push to GitHub

```bash
gh repo create smart-sugarcane-ai --private --source=. --push
```

> Your `gh` CLI is signed in as **Rakeshpatil-24** while your git email is
> **sahilyadawad123@gmail.com**. Check that is the account you want before
> pushing.

### Step 3 — deploy

```bash
vercel login
```

```bash
vercel --prod
```

Accept the defaults. **Keep the root directory as the repository root** — the
root `vercel.json` builds both halves.

### Step 4 — set the database URL

In the Vercel dashboard → your project → **Settings → Environment Variables**:

| Name | Value |
|---|---|
| `DATABASE_URL` | your `postgresql+psycopg://...` string |
| `SECRET_KEY` | run `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

Then redeploy so the function picks them up:

```bash
vercel --prod
```

You do **not** need `VITE_API_BASE_URL` — `vercel.json` already sets it to
`/api` at build time, because the frontend and API share an origin.

### Step 5 — verify

- `https://<you>.vercel.app/api/system/health` → `{"status":"ok"}`
- `https://<you>.vercel.app/api/system/status` → irrigation shows `rule_engine`
- Register an account — proves Postgres is connected
- Run an irrigation prediction
- Upload a plant photo — the analysis appears, the thumbnail does not. Expected.

---

## Option B — Vercel frontend + Render backend

Use this if you want the trained Random Forest and persistent uploads.

`render.yaml` and `Dockerfile` are in the repo. Deploy the backend first:

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
2. Select the repository; Render reads `render.yaml`
3. Set `CORS_ORIGINS` to your Vercel URL, no trailing slash

The Docker build trains the irrigation model (~30 s) because `models/*.joblib`
is gitignored, so the deployed app matches your local one.

Then deploy the frontend with these environment variables in Vercel:

| Name | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<backend>.onrender.com/api` |
| `VITE_MEDIA_BASE_URL` | `https://<backend>.onrender.com` |

`VITE_MEDIA_BASE_URL` is what makes uploaded photos display. Omit it and every
image 404s.

For Option B you must remove or bypass the root `vercel.json` (set Vercel's Root
Directory to `frontend`), otherwise Vercel will also try to build the API.

**Free-tier caveat:** Render sleeps after 15 minutes idle, so the first request
takes 30–60 seconds and the UI shows "Cannot reach the backend" meanwhile. Wake
it before a demo. Data is also wiped on each deploy unless you attach a paid
disk or use Postgres.

---

## Gotchas worth knowing

**Vite bakes environment variables in at build time.** Changing one in the
Vercel dashboard does nothing until you redeploy.

**Testing `VITE_API_BASE_URL=/api` on Windows Git Bash silently breaks.** MSYS
path conversion rewrites a leading `/api` into `C:/Program Files/Git/api`, and
it ends up in your bundle. Prefix with `MSYS_NO_PATHCONV=1`, or put the value in
a `.env` file. This does not affect Vercel, which builds on Linux.

**The 250 MB limit is on the unzipped function.** If you add a dependency and
the deploy starts failing, that is usually why. `.vercelignore` already excludes
`ml/`, `models/`, `docs/` and the test scripts.

---

## Post-deployment checklist

- [ ] `/api/system/health` returns ok
- [ ] `/api/system/status` reports the expected model sources
- [ ] Registration succeeds — proves the database is writable
- [ ] Irrigation prediction returns a result
- [ ] Browser console shows no CORS errors (Option A should have none at all)
- [ ] Footer "API documentation" link points at the deployment, not localhost

---

## Security before sharing the URL

- Set a strong `SECRET_KEY` — the default is a placeholder
- There is **no rate limiting** on `/api/auth/login`. Add
  [slowapi](https://github.com/laurentS/slowapi) before posting the link publicly.
- No email verification, so anyone can register. For a graded demo, consider
  seeding one account and disabling registration.
