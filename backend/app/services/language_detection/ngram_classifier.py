"""Multilingual character and subword n-gram language classifier."""

from __future__ import annotations

import math
import re
from app.services.language_detection.schemas import NgramClassifierSignal

# Training profiles compiled from civic grievance datasets across regional languages
# Includes native script, romanized variants, and common civic morphology
CORPUS_PROFILES: dict[str, list[str]] = {
    "te": [
        # Native script patterns
        "మా వీధిలో", "స్ట్రీట్ లైట్", "పని చేయడం లేదు", "మూడు రోజులుగా", "నీటి సమస్య",
        "డ్రైనేజీ సమస్య", "రోడ్డు మీద గుంతలు", "చెత్త తీయడం లేదు", "మంచినీరు రావడం లేదు",
        "కరెంట్ పోయింది", "పైపులైన్ లీకేజ్", "మున్సిపాలిటీ అధికారి", "ఫిర్యాదు చేయాలి",
        "రెండు రోజులు", "నాలుగు రోజులు", "వారం రోజులుగా", "మా ప్రాంతంలో", "ఎవరూ రాలేదు",
        "దయచేసి పరిష్కరించండి", "లైట్ వెలగడం లేదు", "ట్రాఫిక్ సిగ్నల్", "పరిశుభ్రత లేదు",
        # Romanized patterns
        "maa street lo", "street light pani cheyyatledu", "moodu rojuluga", "neellu ravadam ledu",
        "drainage problem valla", "road meeda gunthalu", "chetha theeyatledu", "current poyindi",
        "pipeline leakage", "officer ki complaint", "rendu rojulu", "nalugu rojuluga",
        "maa area lo", "evaru raaledu", "dayachesi chudandi", "light velagatledu",
        "pani cheyatledu", "water ravatledu", "complaint register cheyyali", "chala kashtam ga undi",
        "maa colony lo light ledu", "eppudu repair chestaru", "cheyyandi", "kavali", "undi"
    ],
    "ta": [
        # Native script patterns
        "எங்கள் தெருவில்", "தெருவிளக்கு எரியவில்லை", "மூன்று நாட்களாக", "குடிநீர் வரவில்லை",
        "சாக்கடை நீர் தேங்கியுள்ளது", "சாலையில் பெரிய குழிகள்", "குப்பை அள்ளப்படவில்லை",
        "மின்சாரம் இல்லை", "குழாய் உடைந்து தண்ணீர் வீணாகிறது", "நகராட்சி அதிகாரி",
        "புகார் அளிக்க வேண்டும்", "இரண்டு நாட்கள்", "நான்கு நாட்களாக", "ஒரு வாரமாக",
        "தயவுசெய்து சரிசெய்யவும்", "போக்குவரத்து நெரிசல்", "எங்கள் பகுதியில்",
        # Romanized patterns
        "enga therula", "street light vela seyyala", "eriyavillai", "moonu naala",
        "kudineer varala", "saakkadai thanni", "road la periya kuli", "kuppai edukala",
        "current illa", "kuzhai odanjurukku", "complaint pannanum", "rendu naal",
        "naalu naatkalaga", "oru vaarama", "dayavuseithu sari seyyavum", "enga area la",
        "thanni varavillai", "velai seyyavillai", "pirachana irukku", "eppadi sari panradhu"
    ],
    "kn": [
        # Native script patterns
        "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ", "ಸ್ಟ್ರೀಟ್ ಲೈಟ್ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ", "ಮೂರು ದಿನಗಳಿಂದ", "ಕುಡಿಯುವ ನೀರು ಬರುತ್ತಿಲ್ಲ",
        "ಚರಂಡಿ ನೀರು ರಸ್ತೆಯಲ್ಲಿ ಹರಿಯುತ್ತಿದೆ", "ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿಗಳು", "ಕಸ ವಿಲೇವಾರಿ ಆಗಿಲ್ಲ",
        "ವಿದ್ಯುತ್ ಇಲ್ಲ", "ಪೈಪ್ ಒಡೆದು ನೀರು ಪೋಲಾಗುತ್ತಿದೆ", "ನಗರಸಭೆ ಅಧಿಕಾರಿ", "ದೂರು ನೀಡಬೇಕು",
        "ಎರಡು ದಿನಗಳಿಂದ", "ನಾಲ್ಕು ದಿನಗಳಿಂದ", "ಒಂದು ವಾರದಿಂದ", "ದಯವಿಟ್ಟು ಸರಿಪಡಿಸಿ",
        # Romanized patterns
        "namma beedhili", "street light kelasa madtilla", "muru dinagalinda", "neeru barthilla",
        "charandi neeru", "road alli dodda gundigalu", "kasa thegedilla", "current illa",
        "pipe odedu neeru", "complaint madabeku", "eradu dina", "naalaku dinagalinda",
        "ondhu vaaradhinda", "dayavittu nodi", "namma area alli", "samasye ide", "beku"
    ],
    "hi": [
        # Native script patterns
        "हमारी गली में", "स्ट्रीट लाइट काम नहीं कर रही है", "तीन दिनों से", "पीने का पानी नहीं आ रहा",
        "सीवर का पानी सड़क पर बह रहा है", "सड़क पर गहरे गड्ढे हैं", "कचरा उठाने कोई नहीं आया",
        "बिजली चली गई है", "पाइपलाइन फट गई है", "नगर निगम अधिकारी", "शिकायत दर्ज करानी है",
        "दो दिन से", "चार दिनों से", "एक हफ्ते से", "कृपया तुरंत समाधान करें",
        # Romanized patterns
        "humari gali mein", "street light kaam nahi kar rahi hai", "teen dinon se",
        "paani nahi aa raha", "sewer ka paani", "sadak par gaddhe", "kachra nahi uthaya",
        "bijli chali gayi", "pipeline leak ho gaya", "complaint karni hai", "do din se",
        "chaar dinon se", "ek hafte se", "kripya theek karein", "humare area mein", "pareshani hai"
    ],
    "ml": [
        # Native script patterns
        "ഞങ്ങളുടെ തെരുവിൽ", "തെരുവുവിളക്ക് കത്തുന്നില്ല", "മൂന്ന് ദിവസമായി", "കുടിവെള്ളം വരുന്നില്ല",
        "ഓടയിലെ വെള്ളം റോഡിലേക്ക്", "റോഡിൽ വലിയ കുഴികൾ", "മാലിന്യം നീക്കം ചെയ്തിട്ടില്ല",
        "വൈദ്യുതി ഇല്ല", "പൈപ്പ് പൊട്ടി വെള്ളം പാഴാകുന്നു", "പഞ്ചായത്ത് സെക്രട്ടറി", "പരാതി നൽകണം",
        # Romanized patterns
        "njangalude theruvil", "street light kathunnilla", "moonu divasamayi", "vellam varunnilla",
        "roddil kuzhikal", "malinyam maattiyilla", "current illa", "pipe potti", "parathi tharanam"
    ],
    "en": [
        # English patterns
        "the street light is not working", "street light has been broken for three days",
        "there is a major water leak in our area", "garbage has not been collected for a week",
        "huge potholes on the main road causing accidents", "drainage overflow on the street",
        "no water supply since yesterday morning", "power outage in our locality for five hours",
        "please repair the leaking pipe immediately", "sanitation workers did not visit our ward",
        "filing a complaint regarding continuous electricity issues", "requesting urgent road repair"
    ]
}


def _extract_ngrams(text: str, n: int = 3) -> dict[str, int]:
    """Extracts character n-grams from normalized text."""
    clean = re.sub(r"\s+", " ", text.lower().strip())
    clean = f" {clean} "
    ngrams: dict[str, int] = {}
    for i in range(len(clean) - n + 1):
        gram = clean[i:i + n]
        ngrams[gram] = ngrams.get(gram, 0) + 1
    return ngrams


def _cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    """Computes cosine similarity between two sparse frequency vectors."""
    dot = sum(vec1[k] * vec2[k] for k in vec1 if k in vec2)
    mag1 = math.sqrt(sum(v * v for v in vec1.values()))
    mag2 = math.sqrt(sum(v * v for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class NgramLanguageClassifier:
    """Cosine similarity classifier using character 3-gram and 4-gram frequency distributions."""

    def __init__(self) -> None:
        self._models: dict[str, dict[str, float]] = {}
        self._build_models()

    def _build_models(self) -> None:
        """Builds normalized centroid vector models for each supported language."""
        for lang, examples in CORPUS_PROFILES.items():
            combined_text = " ".join(examples)
            trigrams = _extract_ngrams(combined_text, 3)
            fourgrams = _extract_ngrams(combined_text, 4)
            # Combine trigrams and 4-grams
            vector: dict[str, float] = {}
            for k, v in trigrams.items():
                vector[k] = float(v)
            for k, v in fourgrams.items():
                vector[k] = float(v * 1.5)  # 4-grams carry higher specificity
            # Normalize vector to unit length
            mag = math.sqrt(sum(v * v for v in vector.values()))
            if mag > 0:
                self._models[lang] = {k: v / mag for k, v in vector.items()}

    def predict(self, text: str) -> NgramClassifierSignal:
        if not text or len(text.strip()) < 2:
            return NgramClassifierSignal()

        # Build query vector
        trigrams = _extract_ngrams(text, 3)
        fourgrams = _extract_ngrams(text, 4)
        query: dict[str, float] = {}
        for k, v in trigrams.items():
            query[k] = float(v)
        for k, v in fourgrams.items():
            query[k] = float(v * 1.5)

        mag = math.sqrt(sum(v * v for v in query.values()))
        if mag == 0:
            return NgramClassifierSignal()
        query_norm = {k: v / mag for k, v in query.items()}

        raw_scores: dict[str, float] = {}
        for lang, model in self._models.items():
            score = _cosine_similarity(query_norm, model)
            raw_scores[lang] = score

        # Apply softmax temperature to convert cosine similarities to probabilities
        temperature = 0.15
        exp_scores = {k: math.exp(v / temperature) for k, v in raw_scores.items()}
        total_exp = sum(exp_scores.values())
        probabilities = {k: round(v / total_exp, 3) for k, v in exp_scores.items()}

        sorted_probs = sorted(probabilities.items(), key=lambda kv: kv[1], reverse=True)
        top_lang, top_prob = sorted_probs[0]

        return NgramClassifierSignal(
            predicted_language=top_lang,
            confidence=top_prob,
            probabilities=probabilities,
        )
