import json
import re
from collections import Counter
from datetime import datetime, timedelta
from datetime import timezone

from sqlalchemy.orm import Session
from app.models import Offense


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
                "severity_thresholds": {"mild": 1, "moderate": 3, "severe": 5},
                "response_actions": {
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