import json
import re
from collections import Counter
from datetime import datetime, timedelta
from datetime import timezone

from sqlalchemy.orm import Session
from app.models import Offense
from .ml_engine import analyze_ml
from .escalation import time_based_escalation, repeat_escalation



# -----------------------------
# Trie-Based Toxic Detector
# -----------------------------
class AdvancedToxicDetector:
    def __init__(self):
        self.root = {}
        self.language_counters = Counter()
        self._load_extended_keywords()

    def _load_extended_keywords(self):

        keywords = [

            # ---------------- ENGLISH (20+) ----------------
            ("stupid", "english", 1),
            ("idiot", "english", 1),
            ("moron", "english", 1),
            ("dumb", "english", 1),
            ("ugly", "english", 2),
            ("fat", "english", 2),
            ("disgusting", "english", 2),
            ("gross", "english", 2),
            ("kill yourself", "english", 3),
            ("die", "english", 3),
            ("worthless", "english", 2),
            ("loser", "english", 1),
            ("trash", "english", 1),
            ("nobody likes you", "english", 3),
            ("you're nothing", "english", 3),
            ("pathetic", "english", 2),
            ("hate you", "english", 3),
            ("failure", "english", 1),
            ("shut up", "english", 1),
            ("useless", "english", 2),
            ("garbage", "english", 2),
            ("freak", "english", 2),
            ("go to hell", "english", 3),
            ("i will kill you", "english", 3),
            ("drop dead", "english", 3),
            ("end your life", "english", 3),

            # ---------------- HINDI (10) ----------------
            ("bewakoof", "hindi", 1),
            ("pagal", "hindi", 1),
            ("nikamma", "hindi", 2),
            ("ghatiya", "hindi", 2),
            ("chup ho ja", "hindi", 1),
            ("tum bekaar ho", "hindi", 2),
            ("tumse na ho payega", "hindi", 2),
            ("ganda insaan", "hindi", 2),
            ("mar ja", "hindi", 3),
            ("tum useless ho", "hindi", 2),
            ("ja ke mar", "hindi", 3),
            ("khud ko maar", "hindi", 3),
            ("zinda mat reh", "hindi", 3),
            ("tumhe maar dunga", "hindi", 3),
            ("tumhari koi value nahi", "hindi", 3),

            # ---------------- SPANISH (10) ----------------
            ("idiota", "spanish", 1),
            ("estupido", "spanish", 1),
            ("tonto", "spanish", 1),
            ("feo", "spanish", 2),
            ("asqueroso", "spanish", 2),
            ("callate", "spanish", 1),
            ("nadie te quiere", "spanish", 3),
            ("eres inutil", "spanish", 2),
            ("muérete", "spanish", 3),
            ("basura", "spanish", 2),
            ("vete al infierno", "spanish", 3),
            ("te voy a matar", "spanish", 3),
            ("acaba con tu vida", "spanish", 3),
            ("no mereces vivir", "spanish", 3),
            ("nadie te necesita", "spanish", 3),
        ]

        for word, language, severity in keywords:
            self._add_to_trie(word, language, severity)

    def _add_to_trie(self, word, language, severity):
        node = self.root
        for char in word:
            node = node.setdefault(char, {})
        node["#"] = (language, severity)

    def _search_trie(self, text):
        results = []
        for i in range(len(text)):
            node = self.root
            j = i
            matched = []

            while j < len(text) and text[j] in node:
                matched.append(text[j])
                node = node[text[j]]
                j += 1

                if "#" in node:
                    language, severity = node["#"]
                    self.language_counters[language] += 1
                    results.append(("".join(matched), language, severity))

        return results


# -----------------------------
# Cyberbullying System
# -----------------------------
class CyberbullyingSystem:
    def __init__(self):
        self.detector = AdvancedToxicDetector()
        self._load_config()

    def _load_config(self):
        try:
            with open("config.json") as f:
                self.config = json.load(f)
        except:
            self.config = {
               "severity_thresholds": {
               "clean": 0,
               "mild": 1,
               "moderate": 5,
               "severe": 10
        },
        "response_actions": {
            "clean": "allow",
            "mild": "warning",
            "moderate": "temporary_suspension",
            "severe": "permanent_ban",
        },
    }

    def _now(self):
        return datetime.now(timezone.utc)

    # -----------------------------
    # MAIN ANALYSIS FUNCTION
    # -----------------------------
    def analyze_message(self, text: str, user_id: str, db: Session):

        if self._is_lockout(user_id, db):
            return {
                "risk_level": "locked_out",
                "score": 0,
                "action": "locked",
                "matched_terms": [],
            }

        matches = self.detector._search_trie(text.lower())
        base_score = sum(sev for _, _, sev in matches)

        context_score = self._analyze_context(text)

        user_score, rapid = self._check_user_history(user_id, db)
        if rapid:
            base_score += 2

        total_score = base_score + context_score + user_score

        thresholds = self.config["severity_thresholds"]
        action, risk_level = self._determine_action(total_score, thresholds)

        self._update_user_profile(user_id, total_score, action, db)

        return {
            "risk_level": risk_level,
            "score": total_score,
            "action": action,
            "matched_terms": [(term, lang) for term, lang, _ in matches],
        }

    # -----------------------------
    # Context Analysis
    # -----------------------------
    def _analyze_context(self, text):
        score = 0
        if text.isupper():
            score += 2
        if any(c in text for c in "!?"):
            score += 1
        if len(re.findall(r"\b\w{15,}\b", text)) > 2:
            score += 1
        return score

    # -----------------------------
    # User History (PostgreSQL)
    # -----------------------------
    def _check_user_history(self, user_id, db: Session):
        offense = db.query(Offense).filter(Offense.user_id == user_id).first()

        if offense:
            if offense.last_offense:
                time_diff = (
                    self._now() - offense.last_offense
                ).total_seconds()

                if time_diff < 600:
                    return min(offense.count * 2, 5), True

            return min(offense.count, 5), False

        return 0, False

    # -----------------------------
    # Lockout Check
    # -----------------------------
    def _is_lockout(self, user_id, db: Session):
        offense = db.query(Offense).filter(Offense.user_id == user_id).first()

        if offense and offense.lockout_until:
            return self._now() < offense.lockout_until

        return False

    # -----------------------------
    # Determine Action
    # -----------------------------
    def _determine_action(self, score, thresholds):
        if score >= thresholds["severe"]:
            return self.config["response_actions"]["severe"], "severe"
        elif score >= thresholds["moderate"]:
            return self.config["response_actions"]["moderate"], "moderate"
        elif score >= thresholds["mild"]:
            return self.config["response_actions"]["mild"], "mild"

        return "no_action", "clean"

    # -----------------------------
    # Update Offense Record
    # -----------------------------
    def _update_user_profile(self, user_id, score, action, db: Session):

        offense = db.query(Offense).filter(Offense.user_id == user_id).first()

        lockout_until = None
        if action == "permanent_ban":
            lockout_until = self._now() + timedelta(hours=48)

        if offense:
            offense.count += 1
            offense.severity_score += score
            offense.last_offense = self._now()
            offense.lockout_until = lockout_until
        else:
            offense = Offense(
                user_id=user_id,
                count=1,
                severity_score=score,
                last_offense=self._now(),
                lockout_until=lockout_until,
            )
            db.add(offense)

        db.commit()

def hybrid_detect(text: str, keyword_score: int, user_id: str):

    # 1️⃣ ML Analysis
    ml_score, categories, sentiment_label = analyze_ml(text)

    # Normalize ML score (0–1 range → scale)
    ml_scaled = ml_score * 5

    # 2️⃣ Combine rule + ML
    final_score = (keyword_score * 2) + ml_scaled

    # 3️⃣ Sentiment adjustment
    if sentiment_label == "NEGATIVE":
        final_score += 1

    if sentiment_label == "POSITIVE" and keyword_score == 0:
        final_score -= 1

    # 4️⃣ Time escalation
    final_score = time_based_escalation(final_score)

    # 5️⃣ Repeat escalation
    final_score = repeat_escalation(user_id, final_score)

    return round(max(final_score, 0), 2), categories

def classify(score):
    if score >= 10:
        return "Severe"
    elif score >= 6:
        return "Moderate"
    elif score >= 2:
        return "Mild"
    else:
        return "Clean"