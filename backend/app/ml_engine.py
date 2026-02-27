import os
import requests

HF_API_TOKEN = os.getenv("HF_API_TOKEN")

API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"

headers = {
    "Authorization": f"Bearer {HF_API_TOKEN}"
}


CATEGORY_WEIGHTS = {
    "threat": 3,
    "identity_hate": 3,
    "insult": 2,
    "toxic": 1,
    "severe_toxic": 2,
    "obscene": 1
}


def analyze_ml(text: str):

    payload = {"inputs": text}

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return 0, {}, "UNKNOWN"

    results = response.json()[0]

    weighted_score = 0
    category_breakdown = {}

    for item in results:
        label = item["label"]
        score = item["score"]

        category_breakdown[label] = round(score, 3)

        if label in CATEGORY_WEIGHTS:
            weighted_score += score * CATEGORY_WEIGHTS[label]

    # Simple sentiment fallback logic
    sentiment_label = "NEGATIVE" if weighted_score > 1 else "POSITIVE"

    return weighted_score, category_breakdown, sentiment_label