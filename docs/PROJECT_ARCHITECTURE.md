# Project Architecture

---

## System overview

```
┌─────────────────────────────────────────────────────────────┐
│  BROWSER — React 19 + Vite + TypeScript + Tailwind v4       │
│  Pages · Layouts · Context (auth, toast) · Axios client     │
└──────────────────────────┬──────────────────────────────────┘
                           │  JSON + multipart over HTTP
                           │  Authorization: Bearer <JWT>
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI  (backend/app)                                     │
│                                                             │
│  api/       routers, validation, auth dependency            │
│  schemas/   pydantic request + response contracts           │
│  services/  business logic, composes ML with knowledge base │
│  ml/        rule engine, image features, model loaders      │
│  models/    SQLAlchemy ORM                                  │
└────────┬──────────────────────┬──────────────────┬──────────┘
         │                      │                  │
    ┌────▼─────┐        ┌───────▼────────┐   ┌─────▼──────┐
    │  SQLite  │        │  data/*.json   │   │  models/   │
    │  (or PG) │        │ knowledge base │   │ artifacts  │
    └──────────┘        └────────────────┘   └────────────┘
```

---

## Mapping to the project block diagram

The system implements the pipeline from the project report:

| Report stage | Implementation |
|---|---|
| **1. Input data sources** (weather + simulated soil) | `IrrigationInput` schema; `weather_service` for live data; `simulate_soil_moisture()` for sensor-free soil moisture |
| **2. Data collection module** | API routers validate and normalise every input through pydantic |
| **3. Data preprocessing** | Range validation, enum coercion, unit normalisation (m/s → km/h); image EXIF rotation and resizing |
| **4. Feature extraction** | `FEATURE_ORDER` for irrigation; `extract_features()` for images |
| **5. AI / ML model** | RandomForest regressor + classifier, with the water-balance engine as fallback |
| **6. Irrigation decision module** | `decide()` converts the predicted requirement into priority, volume, duration and timing |
| **7. Scheduling output** | `IrrigationResult` — water in mm and litres, duration, best window, next check |
| **8. User interface** | React dashboard; results persisted to history |

The project's core idea — using **simulated soil-moisture data** where sensors
are unavailable — is implemented as
`POST /api/irrigation/simulate-soil-moisture`, surfaced in the UI as the
**Simulate** button next to the soil-moisture slider.

---

## Backend layering

Strict one-directional dependencies. Nothing lower imports from anything higher.

```
api/        HTTP concerns only — no agronomy, no SQL beyond simple queries
  ↓
services/   business logic; composes ML output with the knowledge base
  ↓
ml/         prediction and rules; no HTTP, no ORM
  ↓
models/     ORM; no business logic
```

`app/ml/irrigation_engine.py` sits at the bottom and depends on **nothing but
the standard library**. That is deliberate: the standalone training scripts in
`ml/` import it directly, so training and serving can never drift apart in their
agronomy.

### Key modules

| File | Responsibility |
|---|---|
| `core/config.py` | Settings from `.env`; all paths derived from `PROJECT_ROOT` so the app runs from any working directory |
| `core/security.py` | bcrypt hashing, JWT encode/decode. Uses bcrypt directly — passlib's version detection breaks with modern bcrypt releases |
| `core/deps.py` | `get_current_user` (401 on failure) and `get_optional_user` (returns `None`) |
| `database.py` | Engine, session factory, and `UTCDateTime` |
| `ml/irrigation_engine.py` | The water balance. All agronomy constants at the top |
| `ml/irrigation_model.py` | Loads the joblib bundle; falls back to the engine on any failure |
| `ml/image_features.py` | Colour masks, fragmentation, sharpness, quality assessment |
| `ml/disease_model.py`, `ml/soil_model.py` | Keras loader + demo heuristic, one interface |
| `ml/knowledge.py` | Cached JSON loaders with a runtime reload hook |

### One decision worth explaining: `UTCDateTime`

SQLite has no timezone support and silently drops `tzinfo`. A value written as
aware UTC comes back naive; serialised to JSON without an offset, the browser
parses it as *local* time and every timestamp is wrong by the local UTC offset —
which showed up as "6 h ago" for a record created two minutes earlier.

Rather than patching each schema, `database.py` defines a `TypeDecorator` that
normalises on write and re-attaches UTC on read. This fixes Pydantic
serialisation and direct `.isoformat()` calls in one place.

---

## The knowledge base

Four JSON files in `data/` hold **every agronomic claim the app makes**:

| File | Drives |
|---|---|
| `sugarcane_varieties.json` | Variety recommendations |
| `fertilizer_rules.json` | Stage priorities, soil adjustments, pH bands, split schedule |
| `disease_recommendations.json` | Symptoms, causes, recovery plans, prevention |
| `soil_profiles.json` | Soil descriptions, limitations, heuristic thresholds |

This separation is a design goal, not an implementation detail:

- **Correctness is editable by a domain expert** without touching Python.
- **The code never invents agronomy.** `variety_service.py` only *ranks* entries;
  it cannot state a property that is not in the file.
- Every file carries a `data_disclaimer` explaining its provenance.
- `POST /api/recommendations/reload-knowledge` re-reads them without a restart.

---

## Frontend

```
src/
├── main.tsx           Providers: Router → Toast → Auth → App
├── App.tsx            Route table with ProtectedRoute / PublicOnlyRoute
├── layouts/           PublicLayout (marketing), DashboardLayout (sidebar)
├── pages/             One file per route
├── components/
│   ├── ui.tsx         Card, Badge, StatCard, Alert, Skeleton, ProgressBar...
│   ├── ImageDropzone  Drag-and-drop with preview and object-URL cleanup
│   ├── ModelBadge     Renders model_source — the honesty contract
│   └── ProtectedRoute Route guards
├── context/           AuthContext (JWT lifecycle), ToastContext
├── services/          api.ts (axios + interceptors), endpoints.ts (typed calls)
├── hooks/useTheme     light / dark / system, no flash on load
├── types/             Mirrors the pydantic schemas
└── utils/format       Labels, dates, units, tone maps
```

### Design decisions

**`ModelBadge` is the honesty contract in UI form.** Every AI result renders
one. It is a single component so provenance labelling cannot be forgotten on a
new page.

**Auth is centralised.** A 401 on any request clears the token and flips the app
to signed-out via an axios interceptor wired to `AuthContext` — no page needs to
handle expiry itself.

**Errors are translated once.** `describeError()` turns any axios failure into
one readable sentence, including the "is the backend running?" case with the
exact command to start it.

**Shared result components.** `VarietyCard` and `FertilizerPanel` are exported
from their pages and reused by Soil Analysis, so the chained recommendations
look identical wherever they appear.

**Theme without flash.** `initTheme()` runs before React mounts.

**Tailwind v4**, configured CSS-first in `index.css` via `@theme`. Dark mode uses
an explicit `@custom-variant` on `.dark` rather than `prefers-color-scheme`, so
the Settings toggle actually controls it.

---

## Data model

```
users
  ├── plant_analyses      (image, condition, confidence, severity, full result JSON)
  ├── soil_analyses       (image, soil type, appearance, full result JSON)
  ├── irrigation_records  (9 inputs + outputs + full prediction JSON)
  └── chat_messages       (assistant history)
```

All children cascade-delete with the user.

Each analysis table stores both **scalar columns** (for querying, sorting and
charting) and a **full JSON payload** (so a saved result can be re-rendered
exactly as it appeared, even after the code that produced it changes). That
duplication is intentional — history should not silently change meaning when the
knowledge base is edited.

---

## Request lifecycle: a plant analysis

```
POST /api/plants/analyze  (multipart)
  │
  ├─ deps.get_current_user      JWT → User, or 401
  ├─ storage.read_image_upload  type, size, and decodability checks
  ├─ image_features.load_image  EXIF rotation → RGB
  │
  ├─ plant_service.analyse()
  │    ├─ disease_model.predict()
  │    │    ├─ trained Keras model if loaded …
  │    │    └─ … otherwise the demo heuristic
  │    ├─ estimate_severity()        from affected tissue fraction
  │    └─ knowledge.disease_kb()     symptoms, causes, recovery plan
  │
  ├─ storage.save_image()       uploads/plants/u{id}-{ts}-{rand}.jpg
  ├─ plant_service.save_analysis()
  └─ PlantAnalysisResult        includes model_source, is_demo, disclaimer
```

Note the ordering: the image is only written to disk **after** analysis
succeeds, so a failed request leaves no orphan files.

---

## Security

| Concern | Approach |
|---|---|
| Passwords | bcrypt with per-password salt; truncated to bcrypt's 72-byte limit |
| Sessions | Stateless JWT, HS256, 7-day expiry |
| Secrets | `.env`, gitignored; `.env.example` committed |
| Ownership | Every record query filters on `user_id`; cross-user access returns 404, not 403, so IDs are not enumerable |
| Uploads | Content-type allowlist, size cap, and a decode check before the bytes are used |
| Path traversal | Filenames are generated server-side; deletion is restricted to inside `UPLOAD_DIR` |
| SQL injection | SQLAlchemy parameterised queries throughout |
| CORS | Explicit origin allowlist |
| Enumeration | Login returns one message for unknown email and wrong password |

**Not production-hardened**: no rate limiting, no refresh-token rotation, no
email verification, no HTTPS enforcement. It is a local decision-support tool.
Before exposing it publicly, add rate limiting on auth, put it behind TLS, and
rotate `SECRET_KEY`.

---

## Testing

| Script | Coverage |
|---|---|
| `backend/smoke_test.py` | 75 checks — auth, JWT protection, all predictions, upload rejection, history, settings, cleanup |
| `backend/calibration_check.py` | 12 synthetic images asserting the demo heuristics respond to the right visual cues |
| `npm run build` | TypeScript strict-mode typecheck plus a production build |

`smoke_test.py` runs against an in-process `TestClient` — no server, no network.
It must be used as a context manager so the lifespan handler runs and creates
the tables.

---

## Extension points

| Goal | Where to start |
|---|---|
| Better agronomy for your region | Constants at the top of `ml/irrigation_engine.py` |
| Local varieties | `data/sugarcane_varieties.json` |
| Real disease model | `ml/disease_detection/train.py` + `docs/DATASET_GUIDE.md` |
| Kannada / Hindi | `INTENTS` and `HANDLERS` in `services/assistant_service.py`, plus a UI string table |
| PostgreSQL | Change `DATABASE_URL` — no code changes |
| IoT sensor ingest | New router posting readings; feed them where `simulate_soil_moisture` is used today |
| Pump control | Consume `IrrigationResult` in an ESP32 client; the decision layer is already separate from presentation |
