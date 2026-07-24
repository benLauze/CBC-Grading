import json
import os
import io
import time
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.1-flash-lite"

def _build_prompt():
    return (
        "You are an expert trading card grader. You must grade CONSERVATIVELY.\n"
        "You are given TWO images of the same Pokémon card: the FRONT and the BACK.\n\n"

        "Evaluate the card's condition based on these five attributes:\n"
        "1. Centering (strict, numeric)\n"
        "2. Whitening\n"
        "3. Scratches (front surface & holofoil)\n"
        "4. Edge and corner wear\n"
        "5. Print defects (front only)\n\n"

        "============================\n"
        "CENTERING — STRICT NUMERIC RULES\n"
        "============================\n"
        "You MUST calculate centering using PSA-style ratio math.\n"
        "For each side (left, right, top, bottom):\n"
        "- Measure the border thickness visually.\n"
        "- Compute the centering ratio as: larger_border / smaller_border.\n"
        "- Example: left=3mm, right=2mm → ratio = 3/2 = 1.50.\n\n"

        "PSA tolerances:\n"
        "- PSA 10 front centering must be ≤ 1.10 ratio.\n"
        "- PSA 10 back centering must be ≤ 1.25 ratio.\n"
        "- PSA 9 front centering must be ≤ 1.25 ratio.\n"
        "- PSA 9 back centering must be ≤ 1.40 ratio.\n"
        "- Anything above these thresholds should receive meaningful penalties.\n\n"

        "Centering penalty rules:\n"
        "- ratio ≤ 1.10 (front) and ≤ 1.25 (back): 0.0–0.1 (only if visually perfect)\n"
        "- ratio 1.11–1.25: 0.2–0.4 (slightly off)\n"
        "- ratio 1.26–1.40: 0.5–0.8 (noticeably off)\n"
        "- ratio 1.41–1.60: 0.9–1.2 (poor centering)\n"
        "- ratio > 1.60: 1.3–2.0 (severe centering issue)\n\n"

        "You MUST report the centering ratio in the explanation.\n"
        "If ANY border is visibly uneven, centering_penalty must NOT be 0.0.\n\n"

        "============================\n"
        "WHITENING RULES\n"
        "============================\n"
        "- ANY whitening spot: at least 0.2.\n"
        "- Multiple whitening spots: 0.5–1.0.\n"
        "- Heavy whitening: 1.0–2.0.\n\n"

        "============================\n"
        "SCRATCH RULES\n"
        "============================\n"
        "- Holo scratches count heavily.\n"
        "- Light surface scratches: 0.2–0.4.\n"
        "- Multiple scratches: 0.5–1.0.\n"
        "- Deep or long scratches: 1.0–2.0.\n\n"

        "============================\n"
        "EDGE & CORNER WEAR\n"
        "============================\n"
        "- Minor corner wear: 0.2–0.4.\n"
        "- Multiple worn corners: 0.5–1.0.\n"
        "- Heavy wear: 1.0–2.0.\n\n"

        "============================\n"
        "PRINT DEFECTS\n"
        "============================\n"
        "- Minor print dots: 0.1–0.3.\n"
        "- Noticeable defects: 0.4–0.7.\n"
        "- Major defects: 1.0–2.0.\n\n"

        "============================\n"
        "GRADE CALCULATION\n"
        "============================\n"
        "Start from a base grade of 10.0 and subtract the sum of all penalties.\n"
        "final_grade = 10.0 - (centering_penalty + whitening_penalty + scratches_penalty + wear_penalty + print_defects_penalty)\n\n"

        "PSA-equivalent mapping:\n"
        "- 9.80–10.0 → PSA 10 (only if NO visible flaws)\n"
        "- 8.70–9.79 → PSA 9\n"
        "- 7.70–8.69 → PSA 8\n"
        "- 6.70–7.69 → PSA 7\n"
        "- below 6.70 → PSA 6 or lower\n\n"

        "============================\n"
        "STRICT JSON OUTPUT ONLY\n"
        "============================\n"
        "{\n"
        '  "centering_penalty": float,\n'
        '  "whitening_penalty": float,\n'
        '  "scratches_penalty": float,\n'
        '  "wear_penalty": float,\n'
        '  "print_defects_penalty": float,\n'
        '  "final_grade": float,\n'
        '  "psa_equivalent": string,\n'
        '  "explanation": string\n'
        "}\n\n"
        "Do not include any text outside the JSON."
    )

def _map_psa_equivalent(final_grade: float) -> str:
    if final_grade >= 9.8:
        return "PSA 10"
    elif final_grade >= 8.7:
        return "PSA 9"
    elif final_grade >= 7.7:
        return "PSA 8"
    elif final_grade >= 6.7:
        return "PSA 7"
    else:
        return "PSA 6 or lower"

def _clamp_penalty(value: float) -> float:
    return max(0.0, min(2.0, float(value)))

def call_gemini(prompt, front_image, back_image):
    front_buffer = io.BytesIO()
    front_image.save(front_buffer, format="JPEG")
    front_bytes = front_buffer.getvalue()

    back_buffer = io.BytesIO()
    back_image.save(back_buffer, format="JPEG")
    back_bytes = back_buffer.getvalue()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(data=front_bytes, mime_type="image/jpeg"),
            types.Part.from_bytes(data=back_bytes, mime_type="image/jpeg"),
        ],
        config={"response_mime_type": "application/json"},
    )

    return response.text

def call_gemini_with_retry(prompt, front_image, back_image, retries=3, delay=1.5):
    for attempt in range(retries):
        try:
            return call_gemini(prompt, front_image, back_image)
        except Exception as e:
            # Retry only on Gemini overload
            if "503" in str(e) and attempt < retries - 1:
                time.sleep(delay)
                continue
            raise

def grade_card_with_gemini(front_image, back_image) -> dict:
    prompt = _build_prompt()
    raw_text = call_gemini_with_retry(prompt, front_image, back_image)

    try:
        gemini_output = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini did not return valid JSON: {raw_text!r}") from e

    centering_penalty = _clamp_penalty(gemini_output.get("centering_penalty", 0.0))
    whitening_penalty = _clamp_penalty(gemini_output.get("whitening_penalty", 0.0))
    scratches_penalty = _clamp_penalty(gemini_output.get("scratches_penalty", 0.0))
    wear_penalty = _clamp_penalty(gemini_output.get("wear_penalty", 0.0))
    print_defects_penalty = _clamp_penalty(gemini_output.get("print_defects_penalty", 0.0))

    total_penalty = (
        centering_penalty
        + whitening_penalty
        + scratches_penalty
        + wear_penalty
        + print_defects_penalty
    )

    final_grade = max(0.0, min(10.0, 10.0 - total_penalty))

    psa_equivalent = gemini_output.get("psa_equivalent") or _map_psa_equivalent(final_grade)
    explanation = gemini_output.get("explanation", "")

    return {
        "centering_penalty": round(centering_penalty, 2),
        "whitening_penalty": round(whitening_penalty, 2),
        "scratches_penalty": round(scratches_penalty, 2),
        "wear_penalty": round(wear_penalty, 2),
        "print_defects_penalty": round(print_defects_penalty, 2),
        "final_grade": round(final_grade, 2),
        "psa_equivalent": psa_equivalent,
        "explanation": explanation,
    }
