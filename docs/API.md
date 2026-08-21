# API Reference

Base URL: `http://localhost:8000/api`
Interactive docs: `http://localhost:8000/docs`

All request and response bodies are JSON unless stated otherwise. Image uploads
use `multipart/form-data`.

---

## The honesty contract

Every AI response carries these fields. The frontend uses them to render the
badge you see on each result — nothing is presented without provenance.

| Field | Values | Meaning |
|---|---|---|
| `model_source` | `trained_model` | A trained ML model file produced this |
| | `rule_engine` | The documented water-balance calculation produced this |
| | `demo_heuristic` | A transparent colour/texture estimate produced this — illustrative only |
| `model_label` | string | Human-readable description of the above |
| `model_notes` | string[] | Caveats, metrics, and what the result does not mean |
| `is_demo` | boolean | Image endpoints only |
| `disclaimer` | string | The user-facing warning to display |

Check what is currently loaded with `GET /api/system/status`.

---

## Authentication

JWT bearer tokens. Send `Authorization: Bearer <token>` on protected endpoints.

### `POST /api/auth/register`

```json
{
  "name": "Rohan Bhangi",
  "email": "farmer@example.com",
  "password": "SugarCane2026",
  "phone": "9876543210",
  "farm_location": "Belagavi, Karnataka"
}
```

`201` →

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": { "id": 1, "name": "Rohan Bhangi", "email": "farmer@example.com", "...": "..." }
}
```

Errors: `409` email already registered, `422` validation (password under 8 characters).

### `POST /api/auth/login`

```json
{ "email": "farmer@example.com", "password": "SugarCane2026" }
```

`200` → same shape as register. `401` on bad credentials — the message is
identical for an unknown email and a wrong password, so the endpoint does not
leak which accounts exist.

### `GET /api/auth/me` 🔒

Returns the current user.

### `PATCH /api/auth/me` 🔒

Partial update. Any of `name`, `phone`, `farm_location`, `language`, `theme`,
`notifications_enabled`.

### `POST /api/auth/me/password` 🔒

```json
{ "current_password": "...", "new_password": "..." }
```

### `POST /api/auth/logout` 🔒

JWTs are stateless, so this returns a confirmation message and the client
discards the token. There is no server-side session to destroy.

### `POST /api/auth/forgot-password`

```json
{ "email": "farmer@example.com" }
```

**Deliberately does not send email.** No mail provider is configured, and
pretending to send a reset link would be worse than saying so. To finish this
flow: add a `password_reset_tokens` table (token hash, user id, expiry, used
flag), generate a single-use token here, email it with a link to a reset page,
and add `POST /api/auth/reset-password` that validates the token and calls
`hash_password`.

---

## Irrigation

### `POST /api/irrigation/predict`

Works without authentication so the feature can be demonstrated; the result is
only saved to history when a valid token is sent.

```json
{
  "soil_moisture": 26,
  "temperature": 37,
  "humidity": 38,
  "rainfall": 0,
  "rain_probability": 10,
  "wind_speed": 8,
  "weather_condition": "clear",
  "soil_type": "black",
  "growth_stage": "grand_growth",
  "irrigation_method": "furrow",
  "area_hectares": 1.5,
  "save": true
}
```

| Field | Type | Range / values |
|---|---|---|
| `soil_moisture` | float | 0–100 (% of available water in the root zone) |
| `temperature` | float | −10 to 60 °C |
| `humidity` | float | 0–100 % |
| `rainfall` | float | 0–500 mm, last 24 h |
| `rain_probability` | float | 0–100 %, next 24 h |
| `wind_speed` | float | 0–150 km/h |
| `weather_condition` | enum | `clear`, `partly_cloudy`, `cloudy`, `rainy`, `stormy`, `humid`, `dry_wind` |
| `soil_type` | enum | `black`, `red`, `sandy`, `clay`, `loamy`, `mixed` |
| `growth_stage` | enum | `germination`, `tillering`, `grand_growth`, `maturation`, `ratoon_initiation` |
| `irrigation_method` | enum | `flood`, `furrow`, `sprinkler`, `drip` |
| `area_hectares` | float | > 0 |

`200` →

```json
{
  "irrigation_required": true,
  "priority": "high",
  "water_requirement_mm": 41.0,
  "water_volume_liters": 631100,
  "duration_minutes": 118,
  "recommended_window": "Early morning 5:00-8:00 AM, or evening after 6:00 PM",
  "next_check_hours": 14,
  "soil_moisture_status": "Low - visible stress likely",
  "deficit_mm": 34.8,
  "crop_water_use_mm": 8.9,
  "reference_et_mm": 7.1,
  "crop_coefficient": 1.25,
  "effective_rain_mm": 0.8,
  "reason": "Irrigation is recommended because ...",
  "explanation": ["..."],
  "water_saving_tips": ["..."],
  "rain_forecast_note": "No significant rainfall expected in the next 24 h.",
  "feature_contributions": [{ "feature": "soil_moisture", "label": "Soil moisture deficit", "value": 26, "impact": 34.8, "note": "..." }],
  "model_source": "trained_model",
  "model_confidence": 0.98,
  "model_notes": ["..."],
  "disclaimer": "...",
  "record_id": 12
}
```

### `POST /api/irrigation/simulate-soil-moisture`

Estimates soil moisture from a water balance when no sensor is available.

```json
{
  "days_since_irrigation": 6,
  "starting_moisture": 88,
  "soil_type": "sandy",
  "growth_stage": "grand_growth",
  "temperature": 36,
  "humidity": 35,
  "wind_speed": 10,
  "weather_condition": "clear",
  "rainfall_since": 0
}
```

Returns the simulated value plus the daily crop water use and root-zone capacity
used to derive it, and a note that it is not a sensor reading.

### `GET /api/irrigation/options`

Enum values **and every agronomy assumption** the engine uses — crop
coefficients, moisture triggers, available water per soil type, application
efficiencies. Nothing is hidden in the code.

### `GET /api/irrigation/history?limit=20` 🔒
### `GET /api/irrigation/chart?limit=10` 🔒
### `GET /api/irrigation/model-status`
### `POST /api/irrigation/reload-model` 🔒

Reload the model file from disk without restarting the server.

---

## Plant analysis

### `POST /api/plants/analyze` 🔒

`multipart/form-data`:

| Field | Required | Notes |
|---|---|---|
| `file` | yes | JPG / PNG / WEBP / BMP / TIFF, max 10 MB |
| `growth_stage` | no | Tailors the recovery plan |
| `notes` | no | Free text stored with the record |
| `save` | no | Default `true` |

```bash
curl -X POST http://localhost:8000/api/plants/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@leaf.jpg" \
  -F "growth_stage=grand_growth"
```

`200` →

```json
{
  "id": 5,
  "image_url": "/uploads/plants/u1-20260821-094734-a1b2c3d4.jpg",
  "detected_condition": "rust",
  "condition_label": "Rust",
  "pathogen_type": "fungal",
  "confidence": 0.628,
  "severity": "mild",
  "severity_note": "About 4 % of the visible tissue shows symptoms - early stage.",
  "health_score": 88.0,
  "short_description": "...",
  "symptoms": ["..."],
  "causes": ["..."],
  "management": ["..."],
  "prevention": ["..."],
  "recovery": {
    "immediate_action": ["..."],
    "recovery_plan": ["..."],
    "irrigation_advice": { "summary": "...", "details": ["..."] },
    "soil_and_nutrient_advice": ["..."],
    "prevention_plan": ["..."],
    "monitoring_schedule": ["..."]
  },
  "probabilities": [{ "key": "rust", "label": "Rust", "probability": 0.628 }],
  "image_quality": { "rating": "good", "score": 0.9, "issues": [], "resolution": "500 x 400" },
  "model_source": "demo_heuristic",
  "is_demo": true,
  "disclaimer": "AI-based result. Please verify important disease or chemical treatment decisions with a qualified agricultural expert."
}
```

Classes: `healthy`, `red_rot`, `rust`, `smut`, `mosaic`, `leaf_scald`,
`yellow_leaf`, plus `unknown` when confidence falls below the floor.

Errors: `400` unreadable file, `413` over the size limit, `415` unsupported type.

### `GET /api/plants/trend?limit=12` 🔒

Plant Health History — points over time plus `direction`
(`improving` / `stable` / `deteriorating` / `insufficient_data`) and a
comparison of first vs latest.

### `GET /api/plants/history?limit=20` 🔒
### `GET /api/plants/{id}` 🔒
### `GET /api/plants/model-status`
### `POST /api/plants/reload-model` 🔒

---

## Soil analysis

### `POST /api/soil/analyze` 🔒

`multipart/form-data`:

| Field | Required | Notes |
|---|---|---|
| `file` | yes | Photo of bare soil |
| `region`, `district` | no | Improves variety ranking |
| `climate` | no | `tropical`, `subtropical`, `semi_arid`, `unknown` |
| `irrigation_available` | no | Default `true` |
| `water_availability` | no | `low`, `medium`, `high` |
| `planting_season` | no | `adsali`, `pre_seasonal`, `suru`, `spring`, `autumn`, `general` |
| `soil_type_override` | no | Overrides the image estimate if you know it from a lab test |

Returns the visual estimate, the limitations, photo tips, **and** chained
variety and fertilizer recommendations derived from the detected soil.

The response always includes:

```json
"lab_test_notice": "Visual AI estimate - laboratory soil testing provides more accurate nutrient and pH values.",
"limitations": [
  "A photograph alone cannot determine exact NPK values",
  "A photograph alone cannot determine soil pH",
  "..."
]
```

---

## Recommendations

### `POST /api/recommendations/variety`

```json
{
  "soil_type": "black",
  "region": "Karnataka",
  "district": "Belagavi",
  "climate": "tropical",
  "irrigation_available": true,
  "water_availability": "medium",
  "planting_season": "adsali",
  "limit": 4
}
```

Returns ranked matches with `match_score` (0–100), `match_label`
(Best Match / Good Match / Alternative / Weak Match), `why_suitable`,
`cautions`, `disease_notes` and a `source_note`.

Weights: soil 30 %, region 24 %, water 20 %, climate 12 %, season 9 %,
irrigation 5 %.

### `POST /api/recommendations/fertilizer`

```json
{
  "growth_stage": "grand_growth",
  "soil_type": "black",
  "water_availability": "medium",
  "irrigation_available": true,
  "plant_condition": "rust",
  "organic_matter_appearance": "moderate",
  "nitrogen_kg_ha": 180,
  "phosphorus_kg_ha": 30,
  "potassium_kg_ha": 90,
  "soil_ph": 5.2
}
```

All the lab fields are optional. Supplying them shifts each nutrient's priority
based on standard Indian soil-test rating classes.

**Returns qualitative priorities and timing only — never a kg/ha dose.** That is
a deliberate safety decision, not a missing feature.

### `GET /api/recommendations/varieties`

The full variety knowledge base as stored in `data/sugarcane_varieties.json`.

### `GET /api/recommendations/fertilizer-rules`
### `POST /api/recommendations/reload-knowledge`

Re-read the `data/*.json` files after editing them, without restarting.

---

## History

### `GET /api/history?kind=plant&page=1&page_size=20` 🔒

`kind` is optional: `plant`, `soil`, `irrigation`, or omitted for all. Returns a
unified, newest-first feed with per-kind counts.

### `GET /api/history/{kind}/{id}` 🔒
### `DELETE /api/history/{kind}/{id}` 🔒

Also deletes the uploaded image file.

### `DELETE /api/history` 🔒

Deletes every analysis and image for the account. The account itself remains.

---

## Assistant

### `POST /api/assistant/chat` 🔒

```json
{ "message": "When should I irrigate my sugarcane?", "language": "en" }
```

`200` →

```json
{
  "reply": "Your last irrigation check was on 21 August 2026...",
  "topic": "irrigation_when",
  "confidence": "high",
  "used_context": [
    { "kind": "irrigation", "label": "Your latest irrigation check", "detail": "21 Aug 2026: soil moisture 26 %, irrigation recommended (high priority)" }
  ],
  "suggested_questions": ["..."],
  "disclaimer": "I am a rule-based assistant, not a certified agricultural expert..."
}
```

Rule-based keyword intent matching, not an LLM. `used_context` names exactly
which of your records the answer drew on. Only `en` is implemented; requesting
another language returns English with a note saying so.

### `GET /api/assistant/history?limit=50` 🔒
### `DELETE /api/assistant/history` 🔒
### `GET /api/assistant/info`
### `GET /api/assistant/suggestions`

---

## Dashboard, weather and system

### `GET /api/dashboard/summary` 🔒

Everything the dashboard needs in one call: totals, latest of each analysis
type, weather summary, plant trend, irrigation chart series, contextual tips and
model status.

### `GET /api/weather/current?city=Belagavi,IN`
### `GET /api/weather/irrigation-prefill?city=Belagavi,IN`

Both return `{"available": false, "reason": "...", "notice": "..."}` when no
API key is configured rather than inventing values.

### `GET /api/system/health`
### `GET /api/system/status`

The single source of truth on which models are loaded, whether OpenCV is
available, and whether each knowledge-base file parsed.

---

## Errors

| Code | Meaning |
|---|---|
| 400 | Bad request (unreadable image, empty file) |
| 401 | Missing, invalid or expired token |
| 404 | Record not found, or not owned by you |
| 409 | Email already registered |
| 413 | Upload exceeds `MAX_UPLOAD_MB` |
| 415 | Unsupported image type |
| 422 | Validation failure |

Validation errors are reshaped into something a UI can display directly:

```json
{
  "detail": "Some of the values sent were not valid.",
  "problems": ["soil_moisture: Input should be less than or equal to 100"]
}
```

🔒 = requires `Authorization: Bearer <token>`
