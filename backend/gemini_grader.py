import json
import os
import io
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.5-flash"

def _build_prompt():
    return (
        "You are an expert trading card grader. "
        "You are given TWO images of the same Pokémon card: the FRONT and the BACK.\n\n"
        "Evaluate the card's condition based on these five attributes:\n"
        "1. Centering\n"
        "2. Whitening\n"
        "3. Scratches (front surface & holofoil)\n"
        "4. Edge and corner wear\n"
        "5. Print defects (front only)\n\n"
        "Assign a numeric penalty between 0.0 and 2.0 for each attribute:\n"
        "- 0.0 = no visible issue\n"
        "- 0.1–0.5 = very minor issue\n"
        "- 0.6–1.0 = moderate issue\n"
        "- 1.1–2.0 = severe issue\n\n"
        "Start from a base grade of 10.0 and subtract the sum of all penalties.\n"
        "final_grade = 10.0 - (centering_penalty + whitening_penalty + scratches_penalty + wear_penalty + print_defects_penalty)\n\n"
        "Map final_grade to PSA-equivalent:\n"
        "- 9.80–10.0 → PSA 10\n"
        "- 8.70–9.79 → PSA 9\n"
        "- 7.70–8.69 → PSA 8\n"
        "- 6.70–7.69 → PSA 7\n"
        "- below 6.70 → PSA 6 or lower\n\n"
        "Respond ONLY in strict JSON with keys:\n"
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

def grade_card_with_gemini(front_image, back_image) -> dict:
    prompt = _build_prompt()
    raw_text = call_gemini(prompt, front_image, back_image)

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
