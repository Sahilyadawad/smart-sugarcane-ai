# Deployment

**Frontend → Vercel. Backend → a container host (Render, Railway, Fly.io).**

---

## Why the backend cannot go on Vercel

This is worth understanding before you start, because it is not a limitation of
the code.

Vercel runs Python as **serverless functions**, which imposes two hard limits
this project cannot meet:

**1. Size.** Vercel's limit is 250 MB uncompressed. Measured on this project:

| Package | Size |
|---|---|
| scipy | 109 MB |
| opencv-python-headless | 106 MB |
| pandas | 63 MB |
| numpy | 51 MB |
| scikit-learn | 45 MB |
| everything else | ~83 MB |
| **Total** | **457 MB** |

Dropping OpenCV (it is optional in the code) and pandas would still leave
roughly 250 MB before the 17 MB model file. Not viable.

**2. Ephemeral, read-only filesystem.** Serverless functions get a fresh
container per invocation with only `/tmp` writable, and nothing persists.
That breaks two things outright:

- **SQLite** — the database would vanish between requests
- **Uploaded photos** — `uploads/` would not survive

There is also a cold-start cost: loading the 17 MB RandomForest takes ~4 s, and
serverless would pay that repeatedly.

**A container host solves all of it**: one long-running process, the model
loaded once and kept warm, and a real filesystem.

---

## Part 1 — Frontend on Vercel

### 1. Push to GitHub

```bash
git init
```
```bash
git add -A
```
```bash
git commit -m "Smart Sugarcane AI"
```
```bash
git remote add origin https://github.com/<you>/smart-sugarcane-ai.git
```
```bash
git push -u origin main
```

### 2. Import into Vercel

1. [vercel.com/new](https://vercel.com/new) → import the repository.
2. **Set Root Directory to `frontend`.** This is the step people miss — without
   it Vercel tries to build the repo root and fails.
3. Framework preset: **Vite** (auto-detected). `frontend/vercel.json` already
   sets the build command, output directory and the SPA rewrite.

### 3. Environment variables

In **Settings → Environment Variables**, add both for *Production*, *Preview*
and *Development*:

| Name | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<your-backend>.onrender.com/api` |
| `VITE_MEDIA_BASE_URL` | `https://<your-backend>.onrender.com` |

`VITE_MEDIA_BASE_URL` is what makes uploaded photos display — the API returns
image paths like `/uploads/plants/x.jpg`, and this prefixes the backend origin.
Leave it blank and every image will 404.

> Vite inlines env vars **at build time**. Changing them requires a redeploy,
> not just a restart.

Deploy the backend first so you know the URL, or deploy the frontend twice.

---

## Part 2 — Backend on Render (free tier)

`render.yaml` and `Dockerfile` are already in the repo.

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
2. Select your repository. Render reads `render.yaml`.
3. Set the environment variables it prompts for:

| Name | Value |
|---|---|
| `CORS_ORIGINS` | `https://<your-project>.vercel.app` — no trailing slash |
| `SECRET_KEY` | Render generates this automatically |
| `OPENWEATHER_API_KEY` | Optional; leave blank |

4. Deploy. First build takes 5–10 minutes (it installs the scientific stack and
   trains the irrigation model).

Verify: `https://<your-backend>.onrender.com/api/system/health`

### Vercel preview deployments and CORS

Every Vercel preview gets its own URL, which the `CORS_ORIGINS` allowlist will
reject. Either add the preview URLs you care about, or test against production
only. Do **not** set it to `*` — the API sends credentials, and browsers reject
wildcard origins on credentialed requests anyway.

### Free-tier caveats — read these

**Cold starts.** Render's free tier sleeps after 15 minutes idle. The first
request then takes **30–60 seconds**. The frontend will show "Cannot reach the
backend" during that window. For a viva demo, hit the health endpoint a minute
beforehand to wake it.

**Data does not persist.** Free tier has no disk, so the SQLite database and all
uploaded photos are **wiped on every deploy and restart**. Accounts and history
disappear. Fine for a demo; not fine for real use.

To fix, pick one:

- **Postgres (recommended, free tier available).** Add a Render PostgreSQL
  instance or a free [Neon](https://neon.tech) / [Supabase](https://supabase.com)
  database, add `psycopg[binary]` to `backend/requirements.txt`, and set:
  ```
  DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
  ```
  No code changes — SQLAlchemy creates the tables on startup. Uploads still need
  separate handling.

- **Paid plan with a disk.** Uncomment the `disk:` block in `render.yaml`, then
  set `DATABASE_URL=sqlite:////var/data/smart_sugarcane.db` and
  `UPLOAD_DIR=/var/data/uploads`.

---

## Alternative hosts

The `Dockerfile` is host-agnostic. Build it **from the project root**, not from
`backend/` — the backend derives its paths from the project root and needs
`data/` and `models/` alongside it.

**Railway** — `railway up`, auto-detects the Dockerfile, offers a volume and
Postgres. No cold starts on the paid tier.

**Fly.io** — `fly launch`, then `fly volumes create sugarcane_data --size 1` and
mount at `/var/data`. Generous free allowance.

**Any VPS**:

```bash
docker build -t smart-sugarcane-api .
```
```bash
docker run -d -p 8000:8000 -e SECRET_KEY=... -e CORS_ORIGINS=https://your-frontend -v sugarcane:/var/data smart-sugarcane-api
```

> The Dockerfile has not been build-tested in this environment (Docker is not
> installed on the development machine). Its `COPY` paths, the `PROJECT_ROOT`
> resolution to `/app`, and the `.dockerignore` rules were verified by
> inspection. Expect to iterate once on the first real build.

---

## About the trained model

`models/*.joblib` is gitignored, so a fresh clone has no trained model. The
Dockerfile therefore **trains one during the image build** (~30 s) so the
deployed app behaves like your local one and reports `trained_model` rather
than falling back to the rule engine.

To skip it: `docker build --build-arg TRAIN_IRRIGATION_MODEL=0 .`
To ship your own instead: commit the `.joblib` (17 MB, within GitHub's 100 MB
file limit) and the build will use it as-is.

The image-analysis modules stay in DEMO mode in production, exactly as they do
locally, until you train and ship real models. That is intended — see
[ML_MODELS.md](ML_MODELS.md).

---

## Post-deployment checklist

- [ ] `https://<backend>/api/system/health` returns `{"status":"ok"}`
- [ ] `https://<backend>/api/system/status` shows `irrigation -> Trained model`
- [ ] Frontend loads and the landing page renders
- [ ] Register a new account — proves the database is writable
- [ ] Run an irrigation prediction — proves the model loaded
- [ ] Upload a plant photo and confirm **the image displays** — this is the
      check that catches a missing `VITE_MEDIA_BASE_URL`
- [ ] Open the browser console and confirm no CORS errors
- [ ] Footer "API documentation" link points at your backend, not localhost

---

## Security before going public

The local defaults are tuned for a laptop, not the internet.

- Set a strong `SECRET_KEY` (Render's `generateValue` handles this)
- Keep `CORS_ORIGINS` to your exact frontend origin
- There is **no rate limiting** on `/api/auth/login`. Add
  [slowapi](https://github.com/laurentS/slowapi) before exposing it publicly.
- There is no email verification, so anyone can register. Consider an invite
  code or disabling registration for a public demo.
- HTTPS is terminated by the platform; do not run this behind plain HTTP.
