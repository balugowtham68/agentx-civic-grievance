"""Civic complaint content validator: detects nonsense, gibberish, spam, and non-civic input."""

from __future__ import annotations

import re
from typing import Tuple

# Civic keyword vocabulary across major Indian languages
CIVIC_KEYWORDS = {
    # English
    "road", "pothole", "potholes", "water", "drain", "drainage", "sewage", "sewer",
    "garbage", "trash", "waste", "dump", "dustbin", "litter", "light", "streetlight",
    "streetlights", "lamp", "electric", "electricity", "power", "pole", "wire", "cable",
    "leak", "leakage", "burst", "overflow", "stink", "smell", "odor", "stench",
    "sanitation", "dog", "dogs", "animal", "animals", "mosquito", "mosquitoes",
    "traffic", "signal", "footpath", "sidewalk", "encroach", "encroachment", "park",
    "tree", "branch", "pipe", "pipeline", "manhole", "gutter", "broken", "damaged",
    "repair", "clean", "cleaning", "dead", "unclean", "hazard", "danger", "flood",
    "flooding", "waterlogging", "contamination", "supply", "tap", "borewell", "bill",
    # Telugu
    "రోడ్డు", "గుంత", "గుంతలు", "నీరు", "నీళ్ళు", "డ్రైనేజీ", "మురుగు", "చెత్త", "చెత్తకుండీ",
    "కరెంట్", "దీపం", "దీపాలు", "లైటు", "లైట్లు", "పైపు", "పైపులైన్", "కంపు", "దుర్వాసన",
    "కుక్కలు", "దోమలు", "పార్కు", "ట్రాఫిక్", "సిగ్నల్", "మరమ్మతు", "పగిలిపోయింది", "పనిచేయడం లేదు",
    # Hindi
    "सड़क", "गड्ढा", "गड्ढे", "पानी", "नाली", "सीवर", "कचरा", "कूड़ा", "बिजली",
    "बत्ती", "स्ट्रीटलाइट", "पाइप", "बदबू", "दुर्गंध", "सफाई", "मरम्मत", "टूटा", "टूटी",
    "मच्छर", "कुत्ता", "कुत्ते", "नाला", "जलजमाव", "खंभा", "तार",
    # Tamil
    "சாலை", "குப்பை", "தண்ணீர்", "சாக்கடை", "விளக்கு", "மின்சாரம்", "பழுது", "துர்நாற்றம்",
    "மழைநீர்", "கழிவுநீர்",
    # Kannada
    "ರಸ್ತೆ", "ಗುಂಡಿ", "ಕಸ", "ನೀರು", "ಚರಂಡಿ", "ದೀಪ", "ವಿದ್ಯುತ್", "ದುರ್ವಾಸನೆ", "ದುರಸ್ತಿ",
    "ಹಾಳಾಗಿದೆ", "ನೀರುಬೀಳುವಿಕೆ",
}

# Known test and dummy spam tokens
SPAM_PHRASES = {
    "test", "testing", "asdf", "asdfasdf", "qwerty", "zxcvbnm", "hello", "hi", "hey",
    "check", "checking", "sample", "dummy", "nothing", "none", "spam", "random", "text",
    "foo", "bar", "baz", "lorem", "ipsum", "lorem ipsum", "12345", "123456", "abc", "xyz",
    "bla bla", "blah blah", "haha", "hehe", "lol",
}

VOWELS = set("aeiouAEIOU")


def validate_civic_complaint(text: str) -> Tuple[bool, str | None]:
    """Validates citizen input text.

    Returns:
        (True, None) if the input is a valid civic grievance statement.
        (False, error_reason) if the input is nonsense, gibberish, spam, or lacks civic context.
    """
    if not text or not text.strip():
        return False, "Complaint description cannot be empty. Please describe the civic issue."

    cleaned = text.strip()

    # 1. Minimum meaningful length check
    if len(cleaned) < 8:
        return (
            False,
            "Complaint description is too short. Please provide a clear description of the civic problem (e.g. where it is, what is damaged, how long).",
        )

    words = re.findall(r"\b\w+\b", cleaned.lower())
    if len(words) < 2:
        return (
            False,
            "Please provide more detail about the civic grievance rather than a single word.",
        )

    # 2. Known dummy / spam phrase check
    lower_text = cleaned.lower()
    if lower_text in SPAM_PHRASES:
        return (
            False,
            "Please do not enter test or placeholder text. Describe a genuine civic problem affecting your locality.",
        )

    # All words are spam words (e.g., "test test test", "hello hi test")
    if all(w in SPAM_PHRASES for w in words):
        return (
            False,
            "Your input appears to be test or greeting text. Please describe an actual civic issue like potholes, garbage, or water leaks.",
        )

    # 3. Repeated character smashing check (e.g., 'aaaaa', 'zzzzz', '11111')
    if re.search(r"(.)\1{4,}", cleaned):
        return (
            False,
            "Your input contains repetitive characters. Please type a meaningful explanation of the civic grievance.",
        )

    # 4. Low unique character entropy check for keyboard smash (e.g., 'asdfasdfasdf', 'jkfdshjkfdsh')
    non_space_chars = [c.lower() for c in cleaned if c.isalnum()]
    if len(non_space_chars) >= 12:
        unique_ratio = len(set(non_space_chars)) / len(non_space_chars)
        if unique_ratio < 0.22:
            return (
                False,
                "Your input appears to be repetitive or random typing. Please enter a genuine civic complaint.",
            )

    # 5. Latin-script consonant spam check (e.g., 'fjdkslghqwrtp', 'bcdfghjkl')
    latin_words = [w for w in words if re.match(r"^[a-z]+$", w)]
    for w in latin_words:
        if len(w) >= 7 and not any(v in w for v in VOWELS):
            return (
                False,
                f"The word '{w}' appears to be random keyboard smashing without vowels. Please describe a real civic issue.",
            )

    # 6. Civic context check
    # Check if text contains any civic indicators or common issue tokens
    has_civic_signal = any(kw in lower_text for kw in CIVIC_KEYWORDS)
    if not has_civic_signal:
        # Check if text has words indicating an issue / malfunction / disturbance
        generic_problem_signals = {
            "problem", "issue", "complaint", "trouble", "bad", "worst", "danger",
            "not working", "overflowing", "fallen", "blocked", "blocking", "causing",
            "stench", "smell", "dirty", "unhygienic", "broken", "leak", "cut", "off",
            "days", "past", "urgent", "please fix", "help", "solve", "since",
            "సమస్య", "బాధ", "ఇబ్బంది", "పనిచేయట్లేదు", "సరిచేయండి",
            "समस्या", "परेशानी", "खराब", "काम नहीं कर रहा", "ठीक करें",
        }
        has_generic_signal = any(sig in lower_text for sig in generic_problem_signals)

        # If it has neither civic keywords nor problem signals and is conversational/banal
        conversational_starters = {"how are you", "what is your name", "who are you", "good morning", "good evening", "i love", "tell me", "can you sing"}
        if any(c in lower_text for c in conversational_starters):
            return (
                False,
                "SPANDAN AI is dedicated to civic grievances. Please report a public issue like streetlights, roads, drainage, or garbage.",
            )

        if not has_civic_signal and not has_generic_signal and len(words) < 5:
            return (
                False,
                "Your message does not appear to describe a civic grievance. Please mention the specific problem (such as road pothole, streetlight, garbage, or water supply).",
            )

    return True, None
