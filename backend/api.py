import io
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from backend.card_identification import identify_card
from backend.gemini_grader import grade_card_with_gemini
from backend.pricing import get_prices_from_ocr, to_results_price

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-card")
async def process_card(
    front: UploadFile = File(...),
    back: UploadFile = File(...)
):
    # 1. Read images
    front_bytes = await front.read()
    back_bytes = await back.read()

    front_img = Image.open(io.BytesIO(front_bytes))
    back_img = Image.open(io.BytesIO(back_bytes))

    # 2. Identification
    ident = identify_card(front_img)

    # 3. Gemini grading
    grade = grade_card_with_gemini(front_img, back_img)

    # 4. Pricing
    pricing_raw = get_prices_from_ocr(
        ident["number"],
        ident["name"]
    )
    price = to_results_price(pricing_raw, int(round(grade["final_grade"])))

    # 5. Population (placeholder for now)
    population_total = 1000
    population_this_grade = 100

    # ⭐⭐ >>> PASTE YOUR RESULT BLOCK RIGHT HERE <<< ⭐⭐
    result = {
        "name": ident["name"],
        "set": ident["set"],
        "number": ident["number"],
        "rarity": ident.get("rarity", "Unknown"),

        "grade": int(round(grade["final_grade"])),

        "subgrades": {
            "centering": round(10.0 - grade["centering_penalty"], 2),
            "whitening": round(10.0 - grade["whitening_penalty"], 2),
            "scratches": round(10.0 - grade["scratches_penalty"], 2),
            "wear": round(10.0 - grade["wear_penalty"], 2),
            "print_defects": round(10.0 - grade["print_defects_penalty"], 2)
        },

        "price": {
            "market": float(price["market"]),
            "low": float(price["low"]),
            "high": float(price["high"])
        },

        "population": {
            "total": int(population_total),
            "thisGrade": int(population_this_grade)
        }
    }

    # 6. Return JSON to frontend
    return result
