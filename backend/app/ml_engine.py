from transformers import pipeline
from functools import lru_cache

# Load once only (prevents crash & reload issues)
@lru_cache()
def get_toxic_classifier():
    return pipeline(
        "text-classification",
        model="unitary/toxic-bert",
        return_all_scores=True
    )

@lru_cache()
def get_sentiment_classifier():
    return pipeline("sentiment-analysis")


# CATEGORY WEIGHTING (Production Smart Logic)
CATEGORY_WEIGHTS = {
    "threat": 3,
    "identity_hate": 3,
    "insult": 2,
    "toxic": 1,
    "severe_toxic": 2,
    "obscene": 1
}


def analyze_ml(text: str):
    classifier = get_toxic_classifier()
    sentiment_model = get_sentiment_classifier()

    results = classifier(text)[0]
    sentiment = sentiment_model(text)[0]

    weighted_score = 0
    category_breakdown = {}

    for item in results:
        label = item["label"]
        score = item["score"]

        category_breakdown[label] = round(score, 3)

        if label in CATEGORY_WEIGHTS:
            weighted_score += score * CATEGORY_WEIGHTS[label]

    sentiment_label = sentiment["label"]

    return weighted_score, category_breakdown, sentiment_label