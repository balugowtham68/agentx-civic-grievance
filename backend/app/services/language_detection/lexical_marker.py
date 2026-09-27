"""Lexical marker analyzer for native and Romanized Indian regional languages."""

from __future__ import annotations

import re
from app.services.language_detection.schemas import LexicalSignal

# Common English loanwords in Indian civic grievances that should NOT falsely classify as English
CIVIC_ENGLISH_LOANWORDS = {
    "street", "light", "lights", "road", "water", "drainage", "garbage",
    "pipe", "pipeline", "meter", "current", "wire", "pole", "problem",
    "complaint", "officer", "office", "collector", "corporation",
    "municipality", "panchayat", "hospital", "school", "bus", "area",
    "colony", "nagar", "ward", "line", "repair", "service", "tap",
    "leak", "leakage", "pothole", "potholes", "manhole", "tanker", "dustbin",
    "waste", "cleaning", "supply", "bill", "action", "days", "months", "hours"
}

# Strong distinctive markers for Romanized / Latin script Indian languages
ROMANIZED_MARKERS: dict[str, set[str]] = {
    "te": {
        # Pronouns, postpositions, verbs, common Telugu words in Roman script
        "maa", "ma", "naa", "na", "meeru", "miru", "memu", "manaki",
        "lo", "loo", "ki", "ku", "tho", "thoo", "ga", "gaa", "valana", "valla",
        "ledu", "ledhu", "leedu", "undhi", "undi", "unnayi", "unnaru", "unnadu",
        "pani", "cheyyatledu", "cheyatledu", "cheyyali", "chesaru", "cheyyandi",
        "cheppandi", "kavali", "kaavali", "ravadam", "raavadam", "raaledu", "ravatledu", "raavatledu",
        "veedhi", "veedhilo", "vidhi", "vidhilo", "eeroju", "ninna", "repu", "ippudu", "eppudu",
        "ela", "enti", "ikkada", "akkada", "enduku", "kaadu", "kadhu",
        "chudandi", "pettandi", "avvatledu", "avutundi", "avtundi", "ivvandi", "teesukondi",
        "rojulu", "rojuluga", "gantaluga", "samasyanu", "samasya", "mandhi", "illu",
        "padipoindi", "poyindi", "chedipoyindi", "pagilipoindi", "urlo", "oorlo"
    },
    "ta": {
        # Tamil markers in Roman script
        "enga", "engal", "namma", "naan", "neenga", "avanga",
        "la", "le", "ku", "kku", "oda", "ilirundhu", "aaga", "vazhiya",
        "illai", "ille", "illa", "irukku", "iruku", "irukanga", "irukkindrathu",
        "vela", "velai", "seyyala", "seyyavillai", "seyyavum", "pannunga", "pannala",
        "theru", "therula", "theruvil", "saalai", "kudineer", "thanni", "kannir",
        "varala", "varavillai", "varudhu", "varuthu", "venum", "vendum", "koodathu",
        "iniku", "netru", "naalaiki", "eppo", "eppadi", "enna", "enga",
        "inga", "anga", "solunga", "parunga", "edunga", "kudunga", "kodunga",
        "naatkalaga", "manineram", "pirachana", "pirachanai", "udanjurukku", "roatula"
    },
    "kn": {
        # Kannada markers in Roman script
        "namma", "nam", "naanu", "neevu", "naavu", "avaru",
        "alli", "ge", "kke", "inda", "annu", "alliye", "kooda",
        "illa", "ille", "ide", "ive", "idare", "iddare",
        "kelasa", "madtilla", "madadilla", "madi", "madiri", "madabeku", "agtidhe",
        "beedhi", "beedhili", "oni", "rasta", "neeru", "kudiyuva",
        "baralla", "barutilla", "barthilla", "bartilla", "beku", "beda",
        "eega", "ivatthu", "ninne", "naale", "yavaga", "hege", "yenu", "yaake",
        "illi", "alli", "helu", "heli", "nodi", "kodiri", "togo",
        "dinagalinda", "ganthe", "thondare", "samassye", "roadalli", "gundi", "kettide"
    },
    "hi": {
        # Hindi markers in Roman script
        "humari", "hamari", "mera", "meri", "aap", "hum", "yeh", "woh",
        "mein", "me", "ko", "se", "ka", "ki", "ke", "par", "pe", "liye",
        "nahi", "nahin", "na", "hai", "hain", "tha", "thi", "the", "hoga",
        "kaam", "nahi_kar", "karein", "kijiye", "karna", "karo", "chahiye",
        "gali", "sadak", "paani", "bijli", "kachra", "safai",
        "aa_raha", "aaya", "aayega", "bataiye", "suniye", "dekhiye",
        "aaj", "kal", "ab", "kab", "kaisa", "kaise", "kya", "kyun",
        "yahan", "wahan", "din", "dinon_se", "ghante", "pareshani", "samashya",
        "gaddha", "gaddhe", "kharab", "nahi_aa_raha"
    },
    "ml": {
        # Malayalam markers in Roman script
        "njangalude", "enikku", "nammude", "ningal",
        "il", "inu", "ode", "koodi", "aayi",
        "illa", "undu", "aayirunnu", "aavilla",
        "pani", "cheyyunnilla", "cheyyanam", "cheythu",
        "theruvil", "vellam", "veedu",
        "varunnilla", "varum", "venam",
        "innum", "innale", "naale", "eppol", "engane", "enthu",
        "evide", "ivide", "parayoo", "nokkoo", "thannu"
    },
    "en": {
        # Standard English grammatical markers (articles, auxiliary verbs, prepositions)
        "the", "a", "an", "is", "are", "was", "were", "has", "have", "had", "been",
        "this", "that", "these", "those", "for", "with", "from", "into", "on", "in", "at", "by",
        "about", "against", "between", "through", "during", "before", "after",
        "above", "below", "to", "of", "and", "or", "because", "as", "until",
        "while", "not", "no", "only", "our", "my", "your", "their", "please",
        "working", "broken", "since", "there", "here", "when", "where", "why",
        "how", "all", "any", "both", "each", "few", "more", "most", "other",
        "some", "such", "than", "too", "very", "can", "will", "just", "should"
    }
}


class LexicalMarkerAnalyzer:
    """Detects native and Romanized linguistic markers while discounting English loanwords."""

    def analyze(self, text: str) -> LexicalSignal:
        if not text:
            return LexicalSignal()

        # Extract all lowercase word tokens (letters only)
        tokens = re.findall(r"[a-zA-Z]+", text.lower())
        if not tokens:
            return LexicalSignal()

        token_set = set(tokens)
        english_loanwords = token_set & CIVIC_ENGLISH_LOANWORDS

        marker_scores: dict[str, int] = {lang: 0 for lang in ROMANIZED_MARKERS}
        matched_markers: list[str] = []

        # Count multi-word and single-word markers
        joined_text = " " + " ".join(tokens) + " "

        for lang, markers in ROMANIZED_MARKERS.items():
            score = 0
            for marker in markers:
                if "_" in marker:
                    # Multi-word phrase like "nahi_kar"
                    phrase = marker.replace("_", " ")
                    if f" {phrase} " in joined_text:
                        score += 3
                        matched_markers.append(f"{lang}:{phrase}")
                else:
                    if marker in token_set:
                        # Weight length of marker (longer distinctive markers have higher weight)
                        weight = 2 if len(marker) >= 5 else 1
                        score += weight
                        matched_markers.append(f"{lang}:{marker}")
                    elif any(
                        (t.startswith(marker) or t.endswith(marker))
                        for t in token_set
                        if len(marker) >= 4 and len(t) > len(marker)
                    ):
                        score += 1
                        matched_markers.append(f"{lang}:{marker}*")
            marker_scores[lang] = score

        # If English won solely because of civic loanwords, discount it
        # Real English text has grammar words like 'the', 'has', 'been', 'working'
        true_en_grammar_words = token_set & ROMANIZED_MARKERS["en"]
        marker_scores["en"] = len(true_en_grammar_words) * 2

        # Sort candidate languages by score
        sorted_scores = sorted(marker_scores.items(), key=lambda kv: kv[1], reverse=True)
        top_lang, top_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0

        # Calculate confidence
        confidence = 0.0
        if top_score > 0:
            diff = top_score - second_score
            if diff >= 3:
                confidence = min(0.92, 0.60 + 0.10 * diff)
            elif diff >= 1:
                confidence = min(0.78, 0.50 + 0.10 * diff)
            else:
                confidence = 0.50

        return LexicalSignal(
            language=top_lang if top_score > 0 else None,
            confidence=round(confidence, 3),
            marker_scores=marker_scores,
            matched_markers=matched_markers[:15],
            english_loanword_count=len(english_loanwords),
        )
