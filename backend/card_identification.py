import os
import numpy as np
import pandas as pd
from keras.models import load_model
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
IDENT_DIR = os.path.join(BASE_DIR, "identification")

MODEL_PATH = os.path.join(IDENT_DIR, "Models", "encoder_best.keras")
EMBED_PATH = os.path.join(IDENT_DIR, "Reference", "card_index_embeddings.npy")
META_PATH = os.path.join(IDENT_DIR, "Reference", "card_index_metadata.csv")

model = load_model(MODEL_PATH)
embeddings = np.load(EMBED_PATH)
metadata = pd.read_csv(META_PATH)

def identify_card(image: Image.Image):
    img = image.resize((224, 224))
    arr = np.array(img) / 255.0
    arr = np.expand_dims(arr, axis=0)

    emb = model.predict(arr)[0]

    sims = embeddings @ emb / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(emb)
    )
    idx = int(np.argmax(sims))
    card = metadata.iloc[idx]

    return {
        "name": card["name"],
        "set": card.get("api_set_name") or card.get("set_folder") or "Unknown",
        "number": card["number"],
        "rarity": card.get("rarity", "Unknown"),
        "similarity": float(sims[idx]),
    }
