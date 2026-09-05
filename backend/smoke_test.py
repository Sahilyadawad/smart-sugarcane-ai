"""End-to-end smoke test for the Smart Sugarcane AI backend.

Exercises every user-facing flow against an in-process FastAPI test client, so
it needs no running server and no network. Run it after any backend change:

    cd backend
    venv\\Scripts\\python smoke_test.py          (Windows)
    ./venv/bin/python smoke_test.py             (macOS / Linux)

Exit code 0 means every check passed.
"""

from __future__ import annotations

import io
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.main import app  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(f"{name}: {detail}")
        print(f"  FAIL  {name}  {detail}")


def make_image(kind: str) -> bytes:
    """Synthesise a plausible test photo so the analysers have real pixels."""
    image = Image.new("RGB", (640, 480), (30, 90, 40))
    draw = ImageDraw.Draw(image)
    if kind == "healthy_leaf":
        for x in range(0, 640, 40):
            draw.line([(x, 0), (x + 60, 480)], fill=(46, 125, 50), width=22)
    elif kind == "diseased_leaf":
        for x in range(0, 640, 40):
            draw.line([(x, 0), (x + 60, 480)], fill=(70, 120, 50), width=22)
        for i in range(28):
            cx, cy = (i * 37) % 620, (i * 91) % 460
            draw.ellipse([cx, cy, cx + 26, cy + 14], fill=(150, 55, 25))
    elif kind == "soil_black":
        image = Image.new("RGB", (640, 480), (42, 38, 34))
        draw = ImageDraw.Draw(image)
        for i in range(400):
            x, y = (i * 71) % 640, (i * 137) % 480
            draw.point((x, y), fill=(56, 50, 45))
    elif kind == "soil_red":
        image = Image.new("RGB", (640, 480), (150, 78, 45))
        draw = ImageDraw.Draw(image)
        for i in range(600):
            x, y = (i * 53) % 640, (i * 97) % 480
            draw.ellipse([x, y, x + 3, y + 3], fill=(172, 96, 58))

    elif kind == "portrait":
        # Neutral studio backdrop with a skin-tone oval: the shape of image that
        # came back as "Clay Soil, 62 % confidence" before the gate existed.
        image = Image.new("RGB", (640, 480), (204, 204, 204))
        draw = ImageDraw.Draw(image)
        draw.ellipse([220, 90, 420, 350], fill=(198, 156, 124))
        draw.rectangle([180, 330, 460, 480], fill=(232, 214, 210))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def user_count(email: str) -> int:
    """How many accounts exist for this email - used to verify cleanup."""
    from sqlalchemy import func, select

    from app.database import SessionLocal
    from app.models import User

    with SessionLocal() as session:
        return int(session.scalar(select(func.count()).select_from(User).where(User.email == email)) or 0)


def remove_test_user(email: str) -> None:
    """Delete the throwaway account this run created, cascading to its records."""
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import User

    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == email)).first()
        if user is not None:
            session.delete(user)
            session.commit()


def main() -> int:
    # TestClient must be used as a context manager, otherwise the lifespan handler
    # (which calls init_db) never runs and every query hits a missing table.
    with TestClient(app) as client:
        return run_checks(client)


def run_checks(client: TestClient) -> int:
    email = f"smoke-{secrets.token_hex(4)}@example.com"
    password = "TestPassword123"

    print("\n=== 1. System ===")
    response = client.get("/api/system/health")
    check("health endpoint", response.status_code == 200, str(response.status_code))

    response = client.get("/api/system/status")
    status_body = response.json() if response.status_code == 200 else {}
    check("system status", response.status_code == 200, str(response.status_code))
    if status_body:
        for module in ("irrigation", "disease", "soil"):
            print(f"        {module:<11} -> {status_body['models'][module]['label']}")
        check(
            "knowledge base loaded",
            all(entry.get("loaded") for entry in status_body["knowledge_base"].values()),
            str(status_body["knowledge_base"]),
        )

    print("\n=== 2. Authentication ===")
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Smoke Test Farmer",
            "email": email,
            "password": password,
            "phone": "9999999999",
            "farm_location": "Belagavi, Karnataka",
        },
    )
    check("register", response.status_code == 201, response.text[:160])
    token = response.json().get("access_token", "") if response.status_code == 201 else ""
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/auth/register", json={"name": "Dup", "email": email, "password": password})
    check("duplicate email rejected", response.status_code == 409, str(response.status_code))

    response = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword1"})
    check("bad password rejected", response.status_code == 401, str(response.status_code))

    response = client.post("/api/auth/login", json={"email": email, "password": password})
    check("login", response.status_code == 200, response.text[:160])
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/auth/me", headers=headers)
    check("JWT protected /me", response.status_code == 200 and response.json()["email"] == email)

    check("unauthenticated /me rejected", client.get("/api/auth/me").status_code == 401)

    print("\n=== 3. Irrigation ===")
    dry_field = {
        "soil_moisture": 22,
        "temperature": 38,
        "humidity": 32,
        "rainfall": 0,
        "rain_probability": 5,
        "wind_speed": 14,
        "weather_condition": "clear",
        "soil_type": "black",
        "growth_stage": "grand_growth",
        "irrigation_method": "furrow",
        "area_hectares": 1.5,
    }
    response = client.post("/api/irrigation/predict", json=dry_field, headers=headers)
    check("irrigation predict (dry)", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        result = response.json()
        print(
            f"        required={result['irrigation_required']} priority={result['priority']} "
            f"water={result['water_requirement_mm']} mm duration={result['duration_minutes']} min "
            f"source={result['model_source']}"
        )
        check("dry field needs irrigation", result["irrigation_required"] is True)
        check("priority is elevated", result["priority"] in {"high", "critical"}, result["priority"])
        check("saved to history", result.get("record_id") is not None)
        check("explanation present", len(result["explanation"]) >= 3)

    wet_field = {**dry_field, "soil_moisture": 88, "temperature": 26, "humidity": 85, "rainfall": 30,
                 "rain_probability": 90, "weather_condition": "rainy"}
    response = client.post("/api/irrigation/predict", json=wet_field, headers=headers)
    check("irrigation predict (wet)", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        result = response.json()
        check("wet field needs no irrigation", result["irrigation_required"] is False, str(result["irrigation_required"]))

    response = client.post("/api/irrigation/predict", json={**dry_field, "soil_moisture": 250})
    check("out-of-range input rejected", response.status_code == 422, str(response.status_code))

    response = client.post(
        "/api/irrigation/simulate-soil-moisture",
        json={"days_since_irrigation": 6, "starting_moisture": 90, "soil_type": "sandy",
              "growth_stage": "grand_growth", "temperature": 36, "humidity": 35,
              "wind_speed": 10, "weather_condition": "clear", "rainfall_since": 0},
    )
    check("soil moisture simulation", response.status_code == 200, response.text[:160])
    if response.status_code == 200:
        print(f"        simulated moisture = {response.json()['simulated_soil_moisture']} %")

    check("irrigation options", client.get("/api/irrigation/options").status_code == 200)
    check("irrigation model status", client.get("/api/irrigation/model-status").status_code == 200)
    check("irrigation chart", client.get("/api/irrigation/chart", headers=headers).status_code == 200)

    print("\n=== 4. Plant disease analysis ===")
    response = client.post(
        "/api/plants/analyze",
        files={"file": ("diseased.jpg", make_image("diseased_leaf"), "image/jpeg")},
        data={"growth_stage": "grand_growth", "save": "true"},
        headers=headers,
    )
    check("plant analyze (diseased)", response.status_code == 200, response.text[:200])
    plant_id = None
    if response.status_code == 200:
        result = response.json()
        plant_id = result["id"]
        print(
            f"        {result['condition_label']} | confidence {result['confidence'] * 100:.0f} % | "
            f"severity {result['severity']} | source {result['model_source']}"
        )
        check("recovery plan present", len(result["recovery"]["immediate_action"]) > 0)
        check("probabilities present", len(result["probabilities"]) >= 5)
        check("disclaimer present", "qualified agricultural expert" in result["disclaimer"])
        check("image saved", bool(result.get("image_url")))

    response = client.post(
        "/api/plants/analyze",
        files={"file": ("healthy.jpg", make_image("healthy_leaf"), "image/jpeg")},
        data={"growth_stage": "tillering", "save": "true"},
        headers=headers,
    )
    check("plant analyze (healthy)", response.status_code == 200, response.text[:200])

    response = client.post(
        "/api/plants/analyze",
        files={"file": ("notanimage.txt", b"this is not an image", "text/plain")},
        headers=headers,
    )
    check("non-image upload rejected", response.status_code in {400, 415}, str(response.status_code))

    response = client.get("/api/plants/trend", headers=headers)
    check("plant trend", response.status_code == 200, response.text[:160])
    if response.status_code == 200:
        print(f"        trend = {response.json()['direction']}")

    check("plant model status", client.get("/api/plants/model-status").status_code == 200)

    print("")
    print("=== 4b. Image gate: no sugarcane, no analysis ===")
    response = client.post(
        "/api/plants/validate",
        files={"file": ("cane.jpg", make_image("healthy_leaf"), "image/jpeg")},
        headers=headers,
    )
    check("validate endpoint responds", response.status_code == 200, response.text[:160])
    if response.status_code == 200:
        check("sugarcane photo accepted", response.json()["isSugarcane"] is True)

    response = client.post(
        "/api/plants/analyze",
        files={"file": ("person.jpg", make_image("portrait"), "image/jpeg")},
        data={"save": "false"},
        headers=headers,
    )
    check("portrait rejected by plant analysis", response.status_code == 422, response.text[:160])

    response = client.post(
        "/api/soil/analyze",
        files={"file": ("person.jpg", make_image("portrait"), "image/jpeg")},
        data={"save": "false"},
        headers=headers,
    )
    check("portrait rejected by soil analysis", response.status_code == 422, response.text[:160])
    if response.status_code == 422:
        detail = response.json().get("detail", {})
        check("rejection explains why", bool(detail.get("message")))
        check("rejection carries validation payload", "validation" in detail)

    response = client.post(
        "/api/soil/analyze",
        files={"file": ("leaf.jpg", make_image("healthy_leaf"), "image/jpeg")},
        data={"save": "false"},
        headers=headers,
    )
    check("leaf photo rejected by soil analysis", response.status_code == 422, response.text[:160])

    response = client.post(
        "/api/plants/analyze",
        files={"file": ("soil.jpg", make_image("soil_black"), "image/jpeg")},
        data={"save": "false"},
        headers=headers,
    )
    check("soil photo rejected by plant analysis", response.status_code == 422, response.text[:160])

    print("\n=== 5. Soil analysis ===")
    response = client.post(
        "/api/soil/analyze",
        files={"file": ("soil.jpg", make_image("soil_black"), "image/jpeg")},
        data={
            "region": "Karnataka",
            "district": "Belagavi",
            "climate": "tropical",
            "irrigation_available": "true",
            "water_availability": "medium",
            "planting_season": "adsali",
            "save": "true",
        },
        headers=headers,
    )
    check("soil analyze", response.status_code == 200, response.text[:250])
    soil_id = None
    if response.status_code == 200:
        result = response.json()
        soil_id = result["id"]
        estimate = result["estimate"]
        print(
            f"        {estimate['soil_label']} | confidence {estimate['confidence'] * 100:.0f} % | "
            f"moisture {estimate['moisture_appearance']} | source {result['model_source']}"
        )
        check("limitations stated", len(result["limitations"]) >= 4)
        check("lab notice present", "laboratory soil testing" in result["lab_test_notice"].lower())
        check("varieties chained in", len(result["varieties"]["matches"]) > 0)
        check("fertilizer chained in", len(result["fertilizer"]["nutrient_focus"]) == 3)
        top = result["varieties"]["matches"][0]
        print(f"        top variety: {top['name']} ({top['match_label']}, {top['match_score']} %)")

    response = client.post(
        "/api/soil/analyze",
        files={"file": ("red.jpg", make_image("soil_red"), "image/jpeg")},
        data={"region": "Tamil Nadu", "water_availability": "low", "save": "true"},
        headers=headers,
    )
    check("soil analyze (red, low water)", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        top = response.json()["varieties"]["matches"][0]
        print(f"        low-water top variety: {top['name']} ({top['water_requirement']} water need)")

    print("\n=== 6. Recommendations ===")
    response = client.post(
        "/api/recommendations/variety",
        json={"soil_type": "black", "region": "Karnataka", "climate": "tropical",
              "water_availability": "medium", "planting_season": "adsali", "limit": 4},
    )
    check("variety recommendation", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        data = response.json()
        check("ranked descending", all(
            data["matches"][i]["match_score"] >= data["matches"][i + 1]["match_score"]
            for i in range(len(data["matches"]) - 1)
        ))
        check("first is Best Match", data["matches"][0]["match_label"] in {"Best Match", "Weak Match"})

    for stage in ("germination", "tillering", "grand_growth", "maturation", "ratoon_initiation"):
        response = client.post(
            "/api/recommendations/fertilizer",
            json={"growth_stage": stage, "soil_type": "black", "water_availability": "medium"},
        )
        ok = response.status_code == 200
        if ok and stage == "maturation":
            nitrogen = next(n for n in response.json()["nutrient_focus"] if n["nutrient"] == "Nitrogen")
            ok = nitrogen["priority"] == "low"
        check(f"fertilizer: {stage}", ok, response.text[:120])

    response = client.post(
        "/api/recommendations/fertilizer",
        json={"growth_stage": "tillering", "soil_type": "red", "nitrogen_kg_ha": 180,
              "phosphorus_kg_ha": 30, "potassium_kg_ha": 90, "soil_ph": 5.2},
    )
    check("fertilizer with lab values", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        data = response.json()
        check("lab values acknowledged", data["lab_values_used"] is True)
        check("pH note produced", bool(data["ph_note"]))
        nitrogen = next(n for n in data["nutrient_focus"] if n["nutrient"] == "Nitrogen")
        check("low N raises priority", nitrogen["lab_rating"] == "low" and nitrogen["priority"] == "high",
              f"{nitrogen['lab_rating']} / {nitrogen['priority']}")

    check("variety knowledge base", client.get("/api/recommendations/varieties").status_code == 200)

    print("\n=== 7. Assistant ===")
    for question in (
        "When should I irrigate my sugarcane?",
        "Why are my leaves turning yellow?",
        "Which variety is suitable for my soil?",
        "How can I improve an infected plant?",
        "What fertilizer should I consider?",
        "How can I save water?",
        "What does low soil moisture mean?",
        "qwertyuiop nonsense input",
    ):
        response = client.post("/api/assistant/chat", json={"message": question}, headers=headers)
        ok = response.status_code == 200 and len(response.json()["reply"]) > 40
        check(f'assistant: "{question[:38]}"', ok, response.text[:120])
    response = client.post("/api/assistant/chat", json={"message": "hello"}, headers=headers)
    check("assistant history", client.get("/api/assistant/history", headers=headers).status_code == 200)

    print("\n=== 8. Dashboard & history ===")
    response = client.get("/api/dashboard/summary", headers=headers)
    check("dashboard summary", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        summary = response.json()
        print(f"        totals: {summary['totals']}")
        check("dashboard has latest plant", summary["latest_plant"] is not None)
        check("dashboard has latest soil", summary["latest_soil"] is not None)
        check("dashboard has latest irrigation", summary["latest_irrigation"] is not None)

    response = client.get("/api/history", headers=headers)
    check("history list", response.status_code == 200, response.text[:200])
    if response.status_code == 200:
        page = response.json()
        print(f"        {page['total']} history items: {page['counts']}")
        check("history sorted newest first", all(
            page["items"][i]["created_at"] >= page["items"][i + 1]["created_at"]
            for i in range(len(page["items"]) - 1)
        ))

    for kind in ("plant", "soil", "irrigation"):
        check(f"history filter: {kind}",
              client.get("/api/history", params={"kind": kind}, headers=headers).status_code == 200)

    if plant_id:
        response = client.get(f"/api/history/plant/{plant_id}", headers=headers)
        check("history detail", response.status_code == 200, response.text[:160])
    if soil_id:
        response = client.delete(f"/api/history/soil/{soil_id}", headers=headers)
        check("history delete", response.status_code == 200, response.text[:160])
        check("deleted record is gone",
              client.get(f"/api/history/soil/{soil_id}", headers=headers).status_code == 404)

    print("\n=== 9. Settings & weather ===")
    response = client.patch("/api/auth/me", json={"theme": "dark", "language": "en",
                                                  "farm_location": "Sankeshwar"}, headers=headers)
    check("update profile", response.status_code == 200 and response.json()["theme"] == "dark",
          response.text[:160])

    response = client.post("/api/auth/me/password",
                           json={"current_password": password, "new_password": "NewPassword456"},
                           headers=headers)
    check("change password", response.status_code == 200, response.text[:160])
    check("login with new password",
          client.post("/api/auth/login", json={"email": email, "password": "NewPassword456"}).status_code == 200)

    response = client.get("/api/weather/current")
    check("weather endpoint responds", response.status_code == 200, str(response.status_code))
    if response.status_code == 200:
        available = response.json().get("available")
        print(f"        live weather available: {available}"
              f"{' (no API key configured - expected)' if not available else ''}")

    print("\n=== 10. Cleanup ===")
    response = client.delete("/api/history", headers=headers)
    check("clear all history", response.status_code == 200, response.text[:160])

    # Remove the throwaway account as well, so repeated runs do not accumulate
    # "Smoke Test Farmer" rows in the developer's database.
    remove_test_user(email)
    check("test account removed", user_count(email) == 0)

    print("\n" + "=" * 72)
    print(f"PASSED: {len(PASSED)}    FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for failure in FAILED:
            print(f"  - {failure}")
        print("=" * 72)
        return 1
    print("All checks passed.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
