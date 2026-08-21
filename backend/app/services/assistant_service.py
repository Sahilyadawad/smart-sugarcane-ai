"""Sugarcane Assistant - a transparent, rule-based farm assistant.

This is intent matching over the farmer's own saved analyses plus the JSON
knowledge base. It is NOT a large language model and it does not pretend to be
a certified agricultural expert: every answer states where its information came
from and how confident the match was.

Adding a language
-----------------
Intent detection is keyword based, so add the local-language keywords to
``INTENTS``, translate the answer builders registered in ``HANDLERS``, and add
the language code to ``SUPPORTED_LANGUAGES``. Until a language is listed there,
the assistant answers in English and says so rather than pretending.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import irrigation_model
from app.ml.knowledge import disease_kb, fertilizer_kb, soil_kb, varieties_kb
from app.models import ChatMessage, IrrigationRecord, PlantAnalysis, SoilAnalysis, User

SUPPORTED_LANGUAGES = ["en"]
PLANNED_LANGUAGES = ["kn", "hi"]

DISCLAIMER = (
    "I am a rule-based assistant, not a certified agricultural expert. For anything involving "
    "chemicals, disease confirmation or significant expense, please consult your local "
    "agricultural officer."
)

INTENTS: dict[str, list[str]] = {
    "irrigation_when": [
        "when should i irrigate", "when to irrigate", "should i water", "when water",
        "irrigation time", "need water", "irrigate today", "watering schedule",
    ],
    "irrigation_general": ["irrigation", "irrigate", "watering", "water requirement", "how much water"],
    "yellow_leaves": ["yellow leaf", "yellow leaves", "leaves turning yellow", "yellowing", "pale leaves"],
    "disease_help": [
        "disease", "infected", "red rot", "rust", "smut", "mosaic", "leaf scald",
        "sick plant", "spots on leaves", "improve this plant", "improve infected", "recover",
    ],
    "variety": ["variety", "varieties", "which cane", "which seed", "what to plant", "planting material", "cultivar"],
    "fertilizer": ["fertilizer", "fertiliser", "nutrient", "npk", "nitrogen", "urea", "potash", "phosphorus", "manure", "compost"],
    "water_saving": ["save water", "water saving", "reduce water", "less water", "water efficiency", "drip"],
    "soil_moisture_meaning": [
        "low soil moisture", "soil moisture mean", "what does moisture", "moisture level",
        "moisture reading", "what is soil moisture",
    ],
    "soil_type": ["soil type", "my soil", "black soil", "red soil", "sandy soil", "clay soil", "loamy", "soil analysis"],
    "weather": ["weather", "rain", "rainfall", "forecast", "temperature", "humidity"],
    "growth_stage": ["growth stage", "tillering", "grand growth", "maturation", "germination", "ratoon"],
    "greeting": ["hello", "hi", "hey", "namaste", "good morning", "good evening"],
    "capabilities": ["what can you do", "help", "how does this work", "features", "who are you"],
}

SUGGESTED_QUESTIONS = [
    "When should I irrigate my sugarcane?",
    "Why are my leaves turning yellow?",
    "Which variety is suitable for my soil?",
    "How can I improve an infected plant?",
    "What fertilizer should I consider?",
    "How can I save water?",
    "What does low soil moisture mean?",
]


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def detect_intent(message: str) -> tuple[str, float]:
    """Return (intent, match strength 0-1)."""
    text = _normalise(message)
    best_intent, best_score = "unknown", 0.0

    for intent, phrases in INTENTS.items():
        for phrase in phrases:
            if phrase in text:
                # Longer phrase matches are stronger signals than single keywords.
                score = min(1.0, 0.45 + len(phrase.split()) * 0.16)
                if score > best_score:
                    best_intent, best_score = intent, score
    return best_intent, best_score


# ---------------------------------------------------------------- user context
def gather_context(db: Session, user: User) -> dict[str, Any]:
    plant = db.scalars(
        select(PlantAnalysis).where(PlantAnalysis.user_id == user.id).order_by(PlantAnalysis.created_at.desc()).limit(1)
    ).first()
    soil = db.scalars(
        select(SoilAnalysis).where(SoilAnalysis.user_id == user.id).order_by(SoilAnalysis.created_at.desc()).limit(1)
    ).first()
    irrigation = db.scalars(
        select(IrrigationRecord)
        .where(IrrigationRecord.user_id == user.id)
        .order_by(IrrigationRecord.created_at.desc())
        .limit(1)
    ).first()
    return {"plant": plant, "soil": soil, "irrigation": irrigation, "user": user}


def _sources(context: dict[str, Any], used: list[str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    if "irrigation" in used and context.get("irrigation"):
        record: IrrigationRecord = context["irrigation"]
        sources.append(
            {
                "kind": "irrigation",
                "label": "Your latest irrigation check",
                "detail": (
                    f"{record.created_at:%d %b %Y}: soil moisture {record.soil_moisture:.0f} %, "
                    f"{'irrigation recommended' if record.irrigation_required else 'no irrigation needed'} "
                    f"({record.priority} priority)"
                ),
            }
        )
    if "plant" in used and context.get("plant"):
        record = context["plant"]
        sources.append(
            {
                "kind": "plant",
                "label": "Your latest plant analysis",
                "detail": f"{record.created_at:%d %b %Y}: {record.condition_label} ({record.severity}), "
                f"{record.confidence * 100:.0f} % confidence",
            }
        )
    if "soil" in used and context.get("soil"):
        record = context["soil"]
        sources.append(
            {
                "kind": "soil",
                "label": "Your latest soil analysis",
                "detail": f"{record.created_at:%d %b %Y}: {record.soil_label} "
                f"({record.confidence * 100:.0f} % visual confidence)",
            }
        )
    if "knowledge" in used:
        sources.append(
            {
                "kind": "knowledge",
                "label": "Knowledge base",
                "detail": "data/ JSON files - editable agronomy guidance, not a live expert opinion",
            }
        )
    return sources


# ------------------------------------------------------------------- answers
def _answer_irrigation(context: dict[str, Any], specific: bool) -> tuple[str, list[str], str]:
    record: IrrigationRecord | None = context.get("irrigation")
    if record is None:
        return (
            "I have no irrigation check saved for you yet.\n\n"
            "Open the Smart Irrigation page, enter your soil moisture, temperature, humidity and "
            "rainfall, then press Get AI Recommendation. I will then be able to explain your result "
            "here in plain language.\n\n"
            "As a general rule for sugarcane: irrigate when soil moisture falls below roughly 50 % "
            "during tillering and 55 % during grand growth, and reduce irrigation as the crop ripens.",
            ["knowledge"],
            "low",
        )

    prediction = record.prediction or {}
    lines = [
        f"Your last irrigation check was on {record.created_at:%d %B %Y}.",
        "",
        f"**Result:** {'Irrigation recommended' if record.irrigation_required else 'No irrigation needed right now'} "
        f"({record.priority.upper()} priority).",
    ]
    if record.irrigation_required:
        lines.append(
            f"**Water:** about {record.water_requirement_mm:.0f} mm net, roughly "
            f"{record.duration_minutes} minutes with {record.irrigation_method.replace('_', ' ')} irrigation."
        )
        window = prediction.get("recommended_window")
        if window:
            lines.append(f"**Best time:** {window}")
    lines.extend(["", f"**Why:** {prediction.get('reason', record.prediction.get('reason', ''))}"])

    if prediction.get("rain_forecast_note"):
        lines.append(f"**Rain:** {prediction['rain_forecast_note']}")

    next_check = prediction.get("next_check_hours")
    if next_check:
        lines.append(f"**Next check:** in about {next_check} hours.")

    lines.extend(
        [
            "",
            "Before you start the pump, dig 15-20 cm and squeeze a handful of soil. If it holds "
            "together and feels damp, you can usually wait.",
        ]
    )
    if specific:
        lines.append("Conditions change quickly, so re-run the irrigation check if the weather has changed since then.")
    return "\n".join(lines), ["irrigation", "knowledge"], "high"


def _answer_yellow_leaves(context: dict[str, Any]) -> tuple[str, list[str], str]:
    kb = disease_kb().get("conditions", {})
    plant: PlantAnalysis | None = context.get("plant")

    lines = ["Yellowing in sugarcane has several common causes, and they are distinguishable in the field:", ""]
    lines.append(
        "1. **Nitrogen deficiency** - uniform pale yellowing that starts on the older lower leaves. "
        "Usually the most common cause."
    )
    lines.append(
        "2. **Waterlogging** - yellowing with soft, unhealthy roots. Check whether water is standing "
        "after irrigation or rain."
    )
    lines.append(
        "3. **Moisture stress** - yellowing with rolled leaves and drying tips, worst during the hottest part of the day."
    )
    lines.append(
        "4. **Yellow Leaf Disease** - the giveaway is yellowing of the **midrib on the underside** of the leaf, "
        "spreading into the blade. Turn a leaf over and look at the midrib specifically."
    )
    lines.append(
        "5. **Red rot** - drying and yellowing of the third or fourth leaf from the top while lower leaves "
        "still look green. Split a suspect stalk to check for internal reddening."
    )

    used = ["knowledge"]
    confidence = "medium"
    if plant is not None:
        used.append("plant")
        confidence = "high"
        lines.extend(
            [
                "",
                f"**Your last plant analysis** ({plant.created_at:%d %b %Y}) reported "
                f"**{plant.condition_label}** with {plant.confidence * 100:.0f} % confidence "
                f"({plant.severity} severity).",
            ]
        )
        entry = kb.get(plant.detected_condition, {})
        if entry.get("symptoms"):
            lines.append("Symptoms recorded for that condition: " + "; ".join(entry["symptoms"][:3]) + ".")

    lines.extend(["", "Upload a close-up photo of the affected leaf on the Plant Analysis page and I can be more specific."])
    return "\n".join(lines), used, confidence


def _answer_disease(context: dict[str, Any], message: str) -> tuple[str, list[str], str]:
    kb = disease_kb().get("conditions", {})
    text = _normalise(message)

    named = None
    for key in kb:
        if key == "unknown":
            continue
        label = _normalise(kb[key].get("label", key))
        if label and label in text:
            named = key
            break
        if key.replace("_", " ") in text:
            named = key
            break

    plant: PlantAnalysis | None = context.get("plant")
    used = ["knowledge"]
    confidence = "medium"

    if named is None and plant is not None:
        named = plant.detected_condition
        used.append("plant")
        confidence = "high"

    if named is None or named not in kb:
        return (
            "Upload a clear photo of the affected leaf or stalk on the Plant Analysis page and I will "
            "walk you through the recovery plan for whatever the analysis reports.\n\n"
            "Whatever the condition turns out to be, these four steps almost always apply:\n"
            "1. Stop moving setts, soil or tools from the affected patch into clean blocks.\n"
            "2. Improve drainage so water is not standing.\n"
            "3. Remove and safely dispose of severely affected clumps including the stubble.\n"
            "4. Never take seed cane from an affected field.",
            used,
            "low",
        )

    entry = kb[named]
    lines = [f"**{entry.get('label', named)}** - {entry.get('short_description', '')}", ""]
    if plant is not None and plant.detected_condition == named:
        lines.append(
            f"Your analysis from {plant.created_at:%d %b %Y} rated this **{plant.severity}** severity. "
            f"{entry.get('severity_guidance', {}).get(plant.severity, '')}"
        )
        lines.append("")

    lines.append("**Do this first:**")
    lines.extend(f"- {item}" for item in entry.get("immediate_actions", [])[:4])
    lines.append("")
    lines.append("**Then manage it:**")
    lines.extend(f"- {item}" for item in entry.get("management", [])[:3])
    lines.append("")
    irrigation = entry.get("irrigation_advice", {})
    if irrigation.get("summary"):
        lines.append(f"**Irrigation:** {irrigation['summary']}")
    if entry.get("nutrient_advice"):
        lines.append(f"**Nutrition:** {entry['nutrient_advice'][0]}")
    lines.append("")
    lines.append(
        "I deliberately do not name pesticide products or dosages. Get those from your agricultural "
        "officer after they have seen the field."
    )
    return "\n".join(lines), used, confidence


def _answer_variety(context: dict[str, Any]) -> tuple[str, list[str], str]:
    kb = varieties_kb()
    soil: SoilAnalysis | None = context.get("soil")
    used = ["knowledge"]
    lines: list[str] = []

    if soil is not None:
        used.append("soil")
        result = soil.result or {}
        matches = (result.get("varieties") or {}).get("matches", [])
        lines.append(
            f"Based on your soil analysis from {soil.created_at:%d %b %Y} "
            f"(**{soil.soil_label}**, {soil.confidence * 100:.0f} % visual confidence), "
            "these ranked highest:"
        )
        lines.append("")
        for match in matches[:3]:
            lines.append(
                f"- **{match['name']}** - {match['match_label']} ({match['match_score']:.0f} %). "
                f"{match['why_suitable'][0] if match.get('why_suitable') else ''}"
            )
        confidence = "high"
    else:
        lines.append(
            "I have no soil analysis saved for you yet. Upload a soil photo on the Soil Analysis page, "
            "add your region and water availability, and I will rank varieties for your conditions."
        )
        lines.append("")
        lines.append(f"The knowledge base currently holds {len(kb.get('varieties', []))} varieties, including:")
        for variety in kb.get("varieties", [])[:4]:
            lines.append(
                f"- **{variety['name']}** - {variety.get('maturity', '').replace('_', '-')}, "
                f"{variety.get('water_requirement')} water requirement, "
                f"suited to {', '.join(variety.get('soil_suitability', [])[:3])} soils."
            )
        confidence = "low"

    lines.extend(
        [
            "",
            "Match scores rank knowledge-base entries against your stated conditions. They are not "
            "guaranteed yields. Confirm seed availability and the current disease reaction with your "
            "local Sugarcane Research Station or factory cane department before buying seed.",
        ]
    )
    return "\n".join(lines), used, confidence


def _answer_fertilizer(context: dict[str, Any]) -> tuple[str, list[str], str]:
    kb = fertilizer_kb()
    soil: SoilAnalysis | None = context.get("soil")
    irrigation: IrrigationRecord | None = context.get("irrigation")
    used = ["knowledge"]

    stage_key = irrigation.growth_stage if irrigation else "tillering"
    stage = kb.get("growth_stages", {}).get(stage_key, {})
    if irrigation:
        used.append("irrigation")

    lines = [
        f"**Stage: {stage.get('label', stage_key)}** ({stage.get('typical_window', '')})",
        "",
        stage.get("focus", ""),
        "",
        "**Nutrient priority at this stage:**",
    ]
    for nutrient, priority in (stage.get("nutrient_priority", {})).items():
        lines.append(f"- {nutrient.title()}: **{priority}** priority")

    if soil is not None:
        used.append("soil")
        adjust = kb.get("soil_type_adjustments", {}).get(soil.soil_type, {})
        lines.extend(["", f"**For {soil.soil_label}:** {adjust.get('nitrogen_note', '')}"])
        if adjust.get("split_note"):
            lines.append(adjust["split_note"])

    lines.extend(["", "**Practices that apply almost everywhere:**"])
    lines.extend(f"- {item}" for item in kb.get("general_practices", [])[:4])
    lines.extend(
        [
            "",
            "I do not give kg/ha quantities, because a safe quantity depends on your soil test, your "
            "variety and your state recommendation. "
            + kb.get("final_disclaimer", ""),
        ]
    )
    return "\n".join(lines), used, "medium" if soil is None else "high"


def _answer_water_saving(context: dict[str, Any]) -> tuple[str, list[str], str]:
    irrigation: IrrigationRecord | None = context.get("irrigation")
    used = ["knowledge"]
    lines = ["Sugarcane is water-intensive, so small efficiency gains add up quickly:", ""]

    if irrigation is not None:
        used.append("irrigation")
        method = irrigation.irrigation_method
        tips = (irrigation.prediction or {}).get("water_saving_tips", [])
        lines.append(f"You are currently using **{method.replace('_', ' ')}** irrigation. Based on your last check:")
        lines.append("")
        lines.extend(f"- {tip}" for tip in tips[:4])
        confidence = "high"
    else:
        lines.extend(
            [
                "- Switch from flood to furrow, or better, alternate-furrow irrigation. Flood loses "
                "roughly 45 % of applied water.",
                "- Drip irrigation with fertigation delivers the same crop water use with far less "
                "applied water. Check state subsidy schemes for micro-irrigation.",
                "- Trash mulch between rows to cut surface evaporation.",
                "- Irrigate early morning or evening, never at midday on a clear windy day.",
                "- Irrigate on soil moisture readings rather than a fixed calendar schedule.",
            ]
        )
        confidence = "medium"

    lines.extend(
        [
            "",
            "The single biggest saving usually comes from irrigating on measured need rather than on a "
            "fixed schedule. That is exactly what the Smart Irrigation page is for.",
        ]
    )
    return "\n".join(lines), used, confidence


def _answer_soil_moisture(context: dict[str, Any]) -> tuple[str, list[str], str]:
    irrigation: IrrigationRecord | None = context.get("irrigation")
    used = ["knowledge"]
    lines = [
        "Soil moisture here is the percentage of the soil's available water that is still in the root zone.",
        "",
        "**What the numbers mean for sugarcane:**",
        "- Above 70 % - plenty of moisture. Check that water is not standing.",
        "- 50-70 % - comfortable range for most stages.",
        "- 35-50 % - the crop is drawing down reserves. Irrigation is usually due in the next day or two.",
        "- 20-35 % - visible stress is likely: rolled leaves, slowed growth.",
        "- Below 20 % - critical. Grand growth stage losses at this level are hard to recover.",
        "",
        "**Low soil moisture means** the crop has to work harder to pull water from the soil. During "
        "grand growth that directly costs cane length and therefore yield. During ripening a "
        "controlled drop is actually useful, because it encourages sugar accumulation.",
    ]

    if irrigation is not None:
        used.append("irrigation")
        lines.extend(
            [
                "",
                f"**Your last reading** was {irrigation.soil_moisture:.0f} % on "
                f"{irrigation.created_at:%d %b %Y} - "
                f"{(irrigation.prediction or {}).get('soil_moisture_status', 'status not recorded')}.",
            ]
        )
        confidence = "high"
    else:
        confidence = "medium"

    lines.extend(
        [
            "",
            "No sensor? The app can simulate soil moisture from a water balance, and you can always "
            "check by hand: dig 15-20 cm, squeeze a handful. If it holds shape and leaves your palm "
            "damp, moisture is adequate. If it crumbles apart, it is dry.",
        ]
    )
    return "\n".join(lines), used, confidence


def _answer_soil_type(context: dict[str, Any]) -> tuple[str, list[str], str]:
    soil: SoilAnalysis | None = context.get("soil")
    kb = soil_kb()
    used = ["knowledge"]

    if soil is None:
        lines = [
            "Upload a photo of bare, freshly turned soil on the Soil Analysis page and I will give you "
            "a visual estimate of the soil category.",
            "",
            "Be aware of the limits, though:",
        ]
        lines.extend(f"- {item}" for item in kb.get("limitations", [])[:4])
        return "\n".join(lines), used, "low"

    used.append("soil")
    profile = kb.get("profiles", {}).get(soil.soil_type, {})
    lines = [
        f"Your soil analysis from {soil.created_at:%d %b %Y} estimated **{soil.soil_label}** "
        f"({soil.confidence * 100:.0f} % visual confidence).",
        "",
        profile.get("visual_description", ""),
        "",
        "**What that usually means:**",
    ]
    lines.extend(f"- {item}" for item in profile.get("general_properties", [])[:4])
    lines.extend(["", f"**Irrigation:** {profile.get('irrigation_note', '')}"])
    lines.extend(["", f"**Suitability for sugarcane:** {profile.get('sugarcane_suitability', '')}"])
    lines.extend(
        [
            "",
            "Remember this is a visual estimate from a photograph. Laboratory soil testing provides "
            "accurate nutrient and pH values.",
        ]
    )
    return "\n".join(lines), used, "high"


def _answer_weather(context: dict[str, Any]) -> tuple[str, list[str], str]:
    irrigation: IrrigationRecord | None = context.get("irrigation")
    used = ["knowledge"]
    lines = [
        "Weather drives the irrigation decision through three routes:",
        "",
        "- **Temperature** raises evaporation, so the crop uses more water per day.",
        "- **Humidity** works the other way: humid air slows water loss from soil and leaves.",
        "- **Rainfall** is credited directly against the water requirement. Measured rain counts at "
        "about 75 % effectiveness because some runs off.",
        "",
        "A high rain forecast will make the system defer a small irrigation rather than waste water.",
    ]
    if irrigation is not None:
        used.append("irrigation")
        lines.extend(
            [
                "",
                f"At your last check: {irrigation.temperature:.0f} °C, {irrigation.humidity:.0f} % humidity, "
                f"{irrigation.rainfall:.0f} mm rainfall, {irrigation.rain_probability:.0f} % chance of rain.",
            ]
        )
    lines.extend(["", "Add an OpenWeatherMap API key in backend/.env to pull live weather into the irrigation form."])
    return "\n".join(lines), used, "medium"


def _answer_growth_stage() -> tuple[str, list[str], str]:
    kb = fertilizer_kb().get("growth_stages", {})
    lines = ["Sugarcane growth stages and what matters at each:", ""]
    for key in ["germination", "tillering", "grand_growth", "maturation", "ratoon_initiation"]:
        stage = kb.get(key, {})
        if not stage:
            continue
        lines.append(f"**{stage.get('label', key)}** ({stage.get('typical_window', '')})")
        lines.append(f"{stage.get('goal', '')} {stage.get('focus', '')}")
        lines.append("")
    lines.append(
        "Water demand peaks during grand growth, and that is where moisture stress costs the most yield."
    )
    return "\n".join(lines), ["knowledge"], "high"


def _answer_capabilities(context: dict[str, Any]) -> tuple[str, list[str], str]:
    status = irrigation_model.status()
    lines = [
        "I am the Sugarcane Assistant. I can explain the results this app produces and give general "
        "sugarcane guidance. Here is what I can help with:",
        "",
        "- **Irrigation** - explain your latest recommendation, water amount, timing and priority.",
        "- **Disease** - walk through the recovery plan for a detected condition.",
        "- **Soil** - explain your soil estimate and what it means for management.",
        "- **Varieties** - explain why particular varieties ranked highly for your conditions.",
        "- **Fertilizer** - stage-based nutrient priorities and split timing.",
        "- **Water saving** - practical efficiency measures for your irrigation method.",
        "",
        "**How I work:** keyword matching over your saved analyses plus editable JSON knowledge files. "
        "I am not a large language model, so I will not invent an answer. If I do not have the "
        "information, I will say so.",
        "",
        f"**Irrigation model status:** {'trained model loaded' if status['trained_model_available'] else 'rule engine (no trained model file)'}.",
    ]
    return "\n".join(lines), ["knowledge"], "high"


def _answer_greeting(context: dict[str, Any]) -> tuple[str, list[str], str]:
    user: User = context["user"]
    first_name = user.name.split()[0] if user.name else "there"
    lines = [f"Hello {first_name}. How can I help with your sugarcane crop today?", ""]

    bits = []
    if context.get("irrigation"):
        record = context["irrigation"]
        bits.append(
            f"your last irrigation check ({record.created_at:%d %b}) "
            f"{'recommended irrigation' if record.irrigation_required else 'said no irrigation was needed'}"
        )
    if context.get("plant"):
        bits.append(f"your last plant analysis reported {context['plant'].condition_label}")
    if context.get("soil"):
        bits.append(f"your soil was estimated as {context['soil'].soil_label}")

    if bits:
        lines.append("For reference, " + "; ".join(bits) + ".")
    else:
        lines.append(
            "You have not saved any analyses yet. Try the Smart Irrigation page or upload a plant photo "
            "to get started."
        )
    return "\n".join(lines), ["knowledge"], "high"


def _answer_unknown() -> tuple[str, list[str], str]:
    lines = [
        "I did not confidently understand that one, and I would rather say so than guess.",
        "",
        "I can help with irrigation timing and water amounts, disease recovery plans, soil "
        "interpretation, variety selection, fertilizer timing and water saving.",
        "",
        "Try rephrasing with a keyword like *irrigation*, *disease*, *soil*, *variety* or *fertilizer*, "
        "or pick one of the suggested questions below.",
    ]
    return "\n".join(lines), [], "low"


HANDLERS = {
    "irrigation_when": lambda ctx, msg: _answer_irrigation(ctx, specific=True),
    "irrigation_general": lambda ctx, msg: _answer_irrigation(ctx, specific=False),
    "yellow_leaves": lambda ctx, msg: _answer_yellow_leaves(ctx),
    "disease_help": lambda ctx, msg: _answer_disease(ctx, msg),
    "variety": lambda ctx, msg: _answer_variety(ctx),
    "fertilizer": lambda ctx, msg: _answer_fertilizer(ctx),
    "water_saving": lambda ctx, msg: _answer_water_saving(ctx),
    "soil_moisture_meaning": lambda ctx, msg: _answer_soil_moisture(ctx),
    "soil_type": lambda ctx, msg: _answer_soil_type(ctx),
    "weather": lambda ctx, msg: _answer_weather(ctx),
    "growth_stage": lambda ctx, msg: _answer_growth_stage(),
    "greeting": lambda ctx, msg: _answer_greeting(ctx),
    "capabilities": lambda ctx, msg: _answer_capabilities(ctx),
}


def answer(db: Session, user: User, message: str, language: str = "en") -> dict[str, Any]:
    context = gather_context(db, user)
    intent, strength = detect_intent(message)

    handler = HANDLERS.get(intent)
    if handler is None:
        reply, used, confidence = _answer_unknown()
    else:
        reply, used, confidence = handler(context, message)

    if strength < 0.5 and intent != "unknown":
        confidence = "low" if confidence == "high" else confidence
        reply += "\n\n*(I matched this to a general topic rather than an exact question - rephrase if this missed the point.)*"

    if language not in SUPPORTED_LANGUAGES:
        reply += (
            f"\n\n*Note: '{language}' is not available yet. The assistant currently answers in English. "
            f"Planned: {', '.join(PLANNED_LANGUAGES)}.*"
        )

    db.add(ChatMessage(user_id=user.id, role="user", content=message, topic=intent))
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply, topic=intent))
    db.commit()

    return {
        "reply": reply,
        "topic": intent,
        "confidence": confidence,
        "used_context": _sources(context, used),
        "suggested_questions": SUGGESTED_QUESTIONS,
        "disclaimer": DISCLAIMER,
        "created_at": datetime.now(timezone.utc),
    }


def history(db: Session, user: User, limit: int = 50) -> list[ChatMessage]:
    rows = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
    )
    rows.reverse()
    return rows


def clear_history(db: Session, user: User) -> int:
    rows = list(db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id)))
    for row in rows:
        db.delete(row)
    db.commit()
    return len(rows)


def info() -> dict[str, Any]:
    return {
        "engine": "rule_based_intent_matching",
        "languages_supported": SUPPORTED_LANGUAGES,
        "languages_planned": PLANNED_LANGUAGES,
        "notes": [
            "Keyword intent matching over your saved analyses plus the JSON knowledge base.",
            "Not a large language model - it will say when it does not know rather than inventing an answer.",
            "Answers cite which of your records they used.",
            "To add Kannada or Hindi, extend PHRASES and INTENTS in app/services/assistant_service.py.",
        ],
    }
