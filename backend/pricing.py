import os
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "pokemon-tcg-api.p.rapidapi.com",
    "Content-Type": "application/json",
}

SEARCH_URL = "https://pokemon-tcg-api.p.rapidapi.com/search"
CARD_URL = "https://pokemon-tcg-api.p.rapidapi.com/cards/"

def find_card_id(card_number, card_name=None):
    query = f"{card_name} {card_number}" if card_name else card_number
    params = {"q": query}
    r = requests.get(SEARCH_URL, headers=HEADERS, params=params)
    data = r.json()
    if "data" not in data or not data["data"]:
        return None
    return data["data"][0]["id"]

def get_psa_prices(card_id):
    r = requests.get(f"{CARD_URL}{card_id}", headers=HEADERS)
    data = r.json().get("data", {})
    prices = data.get("prices", {})

    ebay_psa = prices.get("ebay", {}).get("graded", {}).get("psa", {})
    eb_psa10 = ebay_psa.get("10", {}).get("median_price")
    eb_psa9 = ebay_psa.get("9", {}).get("median_price")
    eb_psa8 = ebay_psa.get("8", {}).get("median_price")

    return {
        "card_id": card_id,
        "card_name": data.get("name"),
        "set_name": data.get("episode", {}).get("name"),
        "psa10": {"ebay": eb_psa10},
        "psa9": {"ebay": eb_psa9},
        "psa8": {"ebay": eb_psa8},
    }

def get_prices_from_ocr(card_number, card_name=None):
    card_id = find_card_id(card_number, card_name)
    if not card_id:
        return {"error": "Card not found from OCR output"}
    return get_psa_prices(card_id)

def to_results_price(pricing, grade):
    # Map PSA prices to the shape ResultsScreen expects
    market = pricing.get(f"psa{grade}", {}).get("ebay")
    low = pricing.get("psa8", {}).get("ebay")
    high = pricing.get("psa10", {}).get("ebay")
    return {
        "market": market or 0.0,
        "low": low or 0.0,
        "high": high or 0.0,
    }
