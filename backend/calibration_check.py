"""Calibration check for the DEMO image heuristics.

Renders synthetic images with each condition's defining visual signature and
confirms the heuristic picks the right class. This does NOT validate the
heuristic against real sugarcane photographs - nothing here claims diagnostic
accuracy. It is a regression guard: it catches the case where a change to the
feature extractor silently makes every image classify as one class.

    cd backend
    venv\\Scripts\\python calibration_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

from app.ml import disease_model, soil_model  # noqa: E402


def leaf(
    base: tuple[int, int, int],
    spots: int = 0,
    spot_colour: tuple[int, int, int] | None = None,
    spot_size: tuple[int, int] = (18, 9),
    streak: tuple[int, int, int] | None = None,
    mottle: bool = False,
) -> Image.Image:
    """Leaf tissue filling the whole frame, as a real close-up photo would."""
    image = Image.new("RGB", (500, 400), base)
    draw = ImageDraw.Draw(image)
    for y in range(0, 400, 26):  # faint vein shading
        draw.line([(0, y), (500, y)], fill=tuple(max(0, c - 14) for c in base), width=2)
    if mottle:
        for i in range(70):
            x, y = (i * 57) % 470, (i * 83) % 370
            draw.ellipse([x, y, x + 34, y + 22], fill=(150, 190, 90))
    if spots and spot_colour:
        for i in range(spots):
            x, y = (i * 43) % 470, (i * 97) % 380
            draw.ellipse([x, y, x + spot_size[0], y + spot_size[1]], fill=spot_colour)
    if streak:
        for x in range(40, 500, 90):
            draw.line([(x, 0), (x, 400)], fill=streak, width=7)
    return image


def soil(base: tuple[int, int, int], grains: int = 0) -> Image.Image:
    image = Image.new("RGB", (400, 400), base)
    draw = ImageDraw.Draw(image)
    for i in range(grains):
        x, y = (i * 37) % 400, (i * 71) % 400
        draw.ellipse([x, y, x + 3, y + 3], fill=tuple(min(255, c + 45) for c in base))
    return image


DISEASE_CASES: list[tuple[str, Image.Image]] = [
    ("healthy", leaf((52, 120, 48))),
    ("rust", leaf((78, 124, 54), 130, (168, 92, 38), (9, 6))),
    ("red_rot", leaf((104, 112, 48), 9, (138, 44, 26), (110, 70))),
    ("smut", leaf((30, 52, 28), 30, (14, 12, 11), (60, 120))),
    ("yellow_leaf", leaf((196, 198, 66), streak=(224, 222, 74))),
    ("leaf_scald", leaf((58, 122, 52), streak=(248, 248, 244))),
    ("mosaic", leaf((62, 132, 54), mottle=True)),
]

SOIL_CASES: list[tuple[str, Image.Image]] = [
    ("black", soil((42, 38, 34))),
    ("red", soil((150, 78, 45), 300)),
    ("sandy", soil((214, 186, 132), 900)),
    ("clay", soil((140, 120, 100))),
    ("loamy", soil((110, 82, 55), 250)),
]


def main() -> int:
    failures: list[str] = []

    print("\nDEMO DISEASE HEURISTIC")
    print("-" * 72)
    for expected, image in DISEASE_CASES:
        result = disease_model.predict(image)
        got = result["condition"]
        runner_up = sorted(result["probabilities"].items(), key=lambda kv: -kv[1])[1]
        ok = got == expected
        if not ok:
            failures.append(f"disease: expected {expected}, got {got}")
        print(
            f"  {'PASS' if ok else 'FAIL'}  {expected:<12} -> {got:<12} "
            f"{result['confidence'] * 100:5.1f} %   (2nd: {runner_up[0]} {runner_up[1] * 100:.0f} %)"
        )

    print("\nDEMO SOIL HEURISTIC")
    print("-" * 72)
    for expected, image in SOIL_CASES:
        result = soil_model.predict(image)
        got = result["soil_type"]
        runner_up = sorted(result["probabilities"].items(), key=lambda kv: -kv[1])[1]
        ok = got == expected
        if not ok:
            failures.append(f"soil: expected {expected}, got {got}")
        print(
            f"  {'PASS' if ok else 'FAIL'}  {expected:<12} -> {got:<12} "
            f"{result['confidence'] * 100:5.1f} %   (2nd: {runner_up[0]} {runner_up[1] * 100:.0f} %)"
        )

    print("-" * 72)
    if failures:
        print(f"{len(failures)} calibration failure(s):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("All calibration cases classified correctly.")
    print(
        "\nReminder: these are synthetic images built from each condition's textbook\n"
        "visual signature. Passing here means the heuristic responds to the right\n"
        "visual cues - it does NOT mean it is accurate on real field photographs.\n"
        "Train a real model (ml/disease_detection/train.py) for that."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
