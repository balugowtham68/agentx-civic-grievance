"""Civic Grievance Relevance & Nonsense Filtering with Multilingual Diagnostic Questions.

Prevents gibberish, spam, greetings, and non-civic chat queries from being
mistakenly accepted and filed as municipal complaints. Also provides guided
diagnostic questions for valid civic categories in the citizen's detected language.
"""

from __future__ import annotations

import re
from typing import Any
from pydantic import BaseModel


class CivicValidationResult(BaseModel):
    is_civic: bool
    confidence: float
    category: str | None = None
    reason: str | None = None
    message: str | None = None
    suggested_questions: list[dict[str, Any]] = []


# Known greeting and conversational chit-chat phrases (case-insensitive)
NON_CIVIC_PATTERNS = [
    r"^(hi|hello|hey|namaste|vanakkam|namaskaram|good\s*(morning|afternoon|evening|night)|hola)[\s!.]*$",
    r"^(how\s*are\s*you|who\s*are\s*you|what\s*can\s*you\s*do|what\s*is\s*your\s*name)[\s?.]*$",
    r"^(tell\s*me\s*a\s*joke|sing\s*a\s*song|who\s*is\s*the\s*prime\s*minister|what\s*is\s*the\s*weather)[\s?.]*$",
    r"^(test|testing|check|123|1234|abc|asdf|qwerty|xyz)[\s!.]*$",
    r"^(thank\s*you|thanks|ok|okay|bye|goodbye|see\s*you)[\s!.]*$",
]

# Civic domain keywords across English, Telugu, Tamil, Kannada, Hindi
CIVIC_KEYWORD_MAP: dict[str, list[str]] = {
    "STREETLIGHT_OUTAGE": [
        "streetlight", "street light", "light", "lights", "lamp", "pole", "bulb", "dark",
        "power", "electricity", "transformer", "wire", "blackout", "current",
        # Telugu
        "స్ట్రీట్ లైట్", "లైట్", "దీపం", "వీధి దీపం", "కరెంట్", "కరెంటు", "పోల్", "స్తంభం", "చీకటి",
        # Tamil
        "தெருவிளக்கு", "விளக்கு", "மின்சாரம்", "மின் கம்பம்", "இருட்டு",
        # Kannada
        "ಬೀದಿ ದೀಪ", "ದೀಪ", "ಕರೆಂಟ್", "ವಿದ್ಯುತ್", "ಕಂಬ", "ಕತ್ತಲೆ",
        # Hindi
        "स्ट्रीट लाइट", "बत्ती", "बिजली", "खंभा", "अंधेरा", "लाइट",
    ],
    "WATER_SUPPLY_LEAK": [
        "water", "tap", "pipe", "pipeline", "leak", "leaking", "burst", "dirty water", "drinking water",
        "shortage", "supply", "motor", "borewell", "contamination", "pressure",
        # Telugu
        "నీరు", "నీళ్ళు", "తాగే నీరు", "పైపు", "కుళాయి", "లీకేజీ", "లీక్", "నీటి సరఫరా", "మంచి నీళ్ళు",
        # Tamil
        "தண்ணீர்", "குடிநீர்", "குழாய்", "கசிவு", "தண்ணீர் வரவில்லை",
        # Kannada
        "ನೀರು", "ಕುಡಿಯುವ ನೀರು", "ಪೈಪ್", "ಸೋರಿಕೆ", "ಕೊಳವೆ",
        # Hindi
        "पानी", "नल", "पाइप", "लीकेज", "पीने का पानी", "सप्लाई", "गंदा पानी",
    ],
    "DRAINAGE_OVERFLOW": [
        "drain", "drainage", "sewer", "sewage", "manhole", "gutter", "overflow", "stagnant",
        "clogged", "blocked", "foul smell", "septic",
        # Telugu
        "డ్రైనేజీ", "డ్రైనేజ్", "మురుగు", "కాలువ", "కాల్వ", "మోరీ", "మ్యాన్‌హోల్", "కంపు", "మురుగునీరు",
        # Tamil
        "சாக்கடை", "கழிவுநீர்", "சாக்கடை நீர்", "அடைப்பு",
        # Kannada
        "ಚರಂಡಿ", "ಒಳಚರಂಡಿ", "ಮೋರಿ", "ಚರಂಡಿ ನೀರು", "ತುಂಬಿ",
        # Hindi
        "नाली", "सीवर", "गटर", "मैनहोल", "बदबू", "गंदा पानी",
    ],
    "GARBAGE_ACCUMULATION": [
        "garbage", "waste", "trash", "dump", "bin", "dustbin", "stink", "smell", "sanitation",
        "cleaning", "sweeping", "dead animal", "debris", "plastic",
        # Telugu
        "చెత్త", "చెత్తకుండీ", "డంప్", "దుర్వాసన", "స్వీపింగ్", "పరిశుభ్రత", "వ్యర్థాలు",
        # Tamil
        "குப்பை", "குப்பைத்தொட்டி", "துர்நாற்றம்", "சுகாதாரம்",
        # Kannada
        "ಕಸ", "ಕಸದ ತೊಟ್ಟಿ", "ದುರ್ವಾಸನೆ", "ಸ್ವಚ್ಛತೆ",
        # Hindi
        "कचरा", "कूड़ा", "डस्टबिन", "सफाई", "बदबू", "गंदगी",
    ],
    "ROAD_DAMAGE": [
        "road", "pothole", "potholes", "tar", "asphalt", "crater", "broken road", "footpath",
        "pavement", "divider", "speed breaker", "accident",
        # Telugu
        "రోడ్డు", "రోడ్", "గుంత", "గుంతలు", "రహదారి", "ఫుట్‌పాత్", "స్పీడ్ బ్రేకర్",
        # Tamil
        "சாலை", "குழி", "ரோடு", "நடைபாதை",
        # Kannada
        "ರಸ್ತೆ", "ಗುಂಡಿ", "ಗುಂಡಿಗಳು", "ಪಾದಚಾರಿ ರಸ್ತೆ",
        # Hindi
        "सड़क", "गड्ढा", "गड्ढे", "रोड", "फुटपाथ",
    ],
    "PUBLIC_HEALTH_HAZARD": [
        "mosquito", "mosquitoes", "fogging", "dengue", "malaria", "stray dog", "dog bite",
        "encroachment", "illegal", "noise",
        # Telugu
        "దోమలు", "కుక్కలు", "పిచ్చి కుక్కలు", "డెంగ్యూ", "ఆక్రమణ",
        # Tamil
        "கொசு", "தெரு நாய்", "ஆக்கிரமிப்பு",
        # Kannada
        "ಸೊಳ್ಳೆ", "ಬೀದಿ ನಾಯಿ",
        # Hindi
        "मच्छर", "आवारा कुत्ता", "कुत्ते", "अतिक्रमण",
    ],
}

MULTILINGUAL_QUESTIONS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "STREETLIGHT_OUTAGE": {
        "en": [
            {
                "id": "condition",
                "question": "What is the condition of the light?",
                "options": [
                    "Entire street is pitch dark (multiple poles out)",
                    "Single pole light is flickering or off",
                    "Pole damaged or wires hanging dangerously",
                ],
            },
            {
                "id": "duration",
                "question": "How long has this issue persisted?",
                "options": ["1-2 days", "3-5 days", "More than a week"],
            },
        ],
        "te": [
            {
                "id": "condition",
                "question": "లైట్ పరిస్థితి ఏమిటి?",
                "options": [
                    "వీధి మొత్తం చీకటిగా ఉంది (అనేక స్తంభాలపై లైట్లు వెలగడం లేదు)",
                    "ఒకే స్తంభంపై లైట్ వెలగడం లేదు లేదా మినుకుమినుకుమంటోంది",
                    "స్తంభం విరిగిపోయింది లేదా వైర్లు ప్రమాదకరంగా వేలాడుతున్నాయి",
                ],
            },
            {
                "id": "duration",
                "question": "ఈ సమస్య ఎన్ని రోజులుగా ఉంది?",
                "options": ["1-2 రోజులు", "3-5 రోజులు", "వారం కంటే ఎక్కువ రోజులుగా"],
            },
        ],
        "ta": [
            {
                "id": "condition",
                "question": "விளக்கின் நிலை என்ன?",
                "options": [
                    "தெரு முழுவதும் இருட்டாக உள்ளது (பல விளக்குகள் எரியவில்லை)",
                    "ஒரு மின்கம்ப விளக்கு மட்டும் எரியவில்லை",
                    "மின்கம்பம் சேதமடைந்துள்ளது / கம்பிகள் தொங்குகின்றன",
                ],
            },
            {
                "id": "duration",
                "question": "எத்தனை நாட்களாக இந்த பிரச்சனை உள்ளது?",
                "options": ["1-2 நாட்கள்", "3-5 நாட்கள்", "ஒரு வாரத்திற்கும் மேலாக"],
            },
        ],
        "kn": [
            {
                "id": "condition",
                "question": "ಬೀದಿ ದೀಪದ ಸ್ಥಿತಿ ಏನು?",
                "options": [
                    "ಇಡೀ ಬೀದಿ ಕತ್ತಲೆಯಾಗಿದೆ (ಹಲವು ದೀಪಗಳು ಉರಿಯುತ್ತಿಲ್ಲ)",
                    "ಒಂದೇ ಕಂಬದ ದೀಪ ಆಫ್ ಆಗಿದೆ ಅಥವಾ ಮಿನುಗುತ್ತಿದೆ",
                    "ಕಂಬ ಮುರಿದಿದೆ ಅಥವಾ ತಂತಿಗಳು ಅಪಾಯಕಾರಿಯಾಗಿ ನೇತಾಡುತ್ತಿವೆ",
                ],
            },
            {
                "id": "duration",
                "question": "ಈ ಸಮಸ್ಯೆ ಎಷ್ಟು ದಿನಗಳಿಂದ ಇದೆ?",
                "options": ["1-2 ದಿನಗಳು", "3-5 ದಿನಗಳು", "ಒಂದು ವಾರಕ್ಕಿಂತ ಹೆಚ್ಚು"],
            },
        ],
        "hi": [
            {
                "id": "condition",
                "question": "स्ट्रीट लाइट की क्या स्थिति है?",
                "options": [
                    "पूरी सड़क पर अंधेरा है (कई खंभों की लाइट बंद है)",
                    "एक ही खंभे की लाइट बंद है या टिमटिमा रही है",
                    "खंभा क्षतिग्रस्त है या तार लटक रहे हैं",
                ],
            },
            {
                "id": "duration",
                "question": "यह समस्या कितने दिनों से है?",
                "options": ["1-2 दिन", "3-5 दिन", "एक सप्ताह से अधिक"],
            },
        ],
    },
    "WATER_SUPPLY_LEAK": {
        "en": [
            {
                "id": "issue_type",
                "question": "What type of water problem is this?",
                "options": [
                    "No water supply for multiple days",
                    "Dirty / contaminated muddy drinking water",
                    "Main pipeline burst / continuous clean water leak",
                ],
            },
            {
                "id": "scope",
                "question": "How many houses are affected?",
                "options": ["Entire colony / street", "A few adjacent houses", "Individual house"],
            },
        ],
        "te": [
            {
                "id": "issue_type",
                "question": "తాగునీటి సమస్య ఏమిటి?",
                "options": [
                    "కొన్ని రోజులుగా నీటి సరఫరా పూర్తిగా నిలిచిపోయింది",
                    "మురికి / కలుషితమైన తాగునీరు వస్తోంది",
                    "ప్రధాన పైపులైన్ పగిలి రోడ్డుపై నీరు వృధాగా పోతోంది",
                ],
            },
            {
                "id": "scope",
                "question": "ఎన్ని ఇళ్లకు సమస్య ఉంది?",
                "options": ["కాలనీ / వీధి మొత్తం", "కొన్ని ఇళ్లకు మాత్రమే", "మా ఒక్క ఇంటికే"],
            },
        ],
        "ta": [
            {
                "id": "issue_type",
                "question": "தண்ணீர் பிரச்சனையின் வகை என்ன?",
                "options": [
                    "பல நாட்களாக குடிநீர் வரவில்லை",
                    "அசுத்தமான / கலங்கலான குடிநீர் வருகிறது",
                    "முக்கிய குழாய் உடைந்து தண்ணீர் வீணாகிறது",
                ],
            },
            {
                "id": "scope",
                "question": "எத்தனை வீடுகள் பாதிக்கப்பட்டுள்ளன?",
                "options": ["முழு பகுதி / தெரு", "சில வீடுகள்", "தனி வீடு"],
            },
        ],
        "kn": [
            {
                "id": "issue_type",
                "question": "ಕುಡಿಯುವ ನೀರಿನ ಸಮಸ್ಯೆ ಏನು?",
                "options": [
                    "ಹಲವು ದಿನಗಳಿಂದ ನೀರು ಬರುತ್ತಿಲ್ಲ",
                    "ಕಲುಷಿತ / ಗಲೀಜು ನೀರು ಬರುತ್ತಿದೆ",
                    "ಮುಖ್ಯ ಪೈಪ್ ಒಡೆದು ನೀರು ಪೋಲಾಗುತ್ತಿದೆ",
                ],
            },
            {
                "id": "scope",
                "question": "ಎಷ್ಟು ಮನೆಗಳಿಗೆ ತೊಂದರೆಯಾಗಿದೆ?",
                "options": ["ಇಡೀ ಬಡಾವಣೆ / ಬೀದಿ", "ಕೆಲವು ಮನೆಗಳು", "ಒಂದೇ ಮನೆ"],
            },
        ],
        "hi": [
            {
                "id": "issue_type",
                "question": "पानी की क्या समस्या है?",
                "options": [
                    "कई दिनों से पानी की आपूर्ति नहीं हो रही है",
                    "गंदा / दूषित मटमैला पीने का पानी आ रहा है",
                    "मुख्य पाइपलाइन फटने से पानी बह रहा है",
                ],
            },
            {
                "id": "scope",
                "question": "कितने घर प्रभावित हैं?",
                "options": ["पूरा मोहल्ला / गली", "कुछ आस-पास के घर", "सिर्फ एक घर"],
            },
        ],
    },
    "DRAINAGE_OVERFLOW": {
        "en": [
            {
                "id": "severity",
                "question": "What is the severity of the overflow?",
                "options": [
                    "Sewage actively flowing onto public road",
                    "Manhole cover is broken or missing (immediate danger)",
                    "Blocked gutter with stagnant wastewater and mosquitoes",
                ],
            },
            {
                "id": "duration",
                "question": "How long has it been overflowing?",
                "options": ["Since today", "2 to 3 days", "Chronic recurring issue"],
            },
        ],
        "te": [
            {
                "id": "severity",
                "question": "మురుగు కాలువ సమస్య ఎంత తీవ్రంగా ఉంది?",
                "options": [
                    "మురుగునీరు నేరుగా రోడ్డుపై ప్రవహిస్తోంది",
                    "మ్యాన్‌హోల్ మూత విరిగిపోయింది / లేదు (తీవ్ర ప్రమాదం)",
                    "కాలువ పూడిక పేరుకుపోయి దోమలు, దుర్వాసన వస్తోంది",
                ],
            },
            {
                "id": "duration",
                "question": "ఎన్ని రోజులుగా పొంగుతోంది?",
                "options": ["ఈ రోజు నుంచే", "2-3 రోజులుగా", "ఎప్పుడూ ఉండే సమస్య"],
            },
        ],
        "ta": [
            {
                "id": "severity",
                "question": "சாக்கடை பிரச்சனையின் தீவிரம் என்ன?",
                "options": [
                    "சாக்கடை நீர் சாலையில் பெருக்கெடுத்து ஓடுகிறது",
                    "மேன்ஹோல் மூடி உடைந்துள்ளது / இல்லை",
                    "சாக்கடை அடைப்பு ஏற்பட்டு கொசுக்கள் உற்பத்தியாகின்றன",
                ],
            },
            {
                "id": "duration",
                "question": "எத்தனை நாட்களாக பொங்குகிறது?",
                "options": ["இன்று முதல்", "2-3 நாட்கள்", "தொடர்ச்சியான பிரச்சனை"],
            },
        ],
        "kn": [
            {
                "id": "severity",
                "question": "ಒಳಚರಂಡಿ ಸಮಸ್ಯೆಯ ತೀವ್ರತೆ ಎಷ್ಟು?",
                "options": [
                    "ಚರಂಡಿ ನೀರು ರಸ್ತೆಯ ಮೇಲೆ ಹರಿಯುತ್ತಿದೆ",
                    "ಮ್ಯಾನ್‌ಹೋಲ್ ಮುಚ್ಚಳ ಮುರಿದಿದೆ / ಕಣ್ಮರೆಯಾಗಿದೆ",
                    "ಚರಂಡಿ ಕಟ್ಟಿಕೊಂಡು ಸೊಳ್ಳೆಗಳು ಹೆಚ್ಚಾಗಿವೆ",
                ],
            },
            {
                "id": "duration",
                "question": "ಎಷ್ಟು ದಿನಗಳಿಂದ ಹರಿಯುತ್ತಿದೆ?",
                "options": ["ಇಂದಿನಿಂದ", "2-3 ದಿನಗಳು", "ನಿರಂತರ ಸಮಸ್ಯೆ"],
            },
        ],
        "hi": [
            {
                "id": "severity",
                "question": "नाली की समस्या कितनी गंभीर है?",
                "options": [
                    "गंदा नाली का पानी सड़क पर बह रहा है",
                    "मैनहोल का ढक्कन टूटा या गायब है (बड़ा खतरा)",
                    "नाली जाम होने से बदबू और मच्छर बढ़ गए हैं",
                ],
            },
            {
                "id": "duration",
                "question": "यह कितने दिनों से बह रहा है?",
                "options": ["आज से", "2-3 दिनों से", "बार-बार होने वाली समस्या"],
            },
        ],
    },
    "GARBAGE_ACCUMULATION": {
        "en": [
            {
                "id": "situation",
                "question": "What is the garbage situation?",
                "options": [
                    "Open garbage dump overflowing on the road",
                    "Door-to-door sanitation collection stopped",
                    "Dead animal carcass requiring emergency sanitation",
                ],
            },
            {
                "id": "location_type",
                "question": "Where is the waste located?",
                "options": [
                    "Near residential houses or school",
                    "Near commercial market or food stalls",
                    "In an open vacant plot",
                ],
            },
        ],
        "te": [
            {
                "id": "situation",
                "question": "చెత్త సమస్య ఏమిటి?",
                "options": [
                    "రోడ్డుపై చెత్త కుప్ప పేరుకుపోయి దుర్వాసన వస్తోంది",
                    "ఇంటింటికీ వచ్చే చెత్త వాహనం రావడం లేదు",
                    "చనిపోయిన జంతువు కళేబరం ఉంది (తక్షణ పరిశుభ్రత అవసరం)",
                ],
            },
            {
                "id": "location_type",
                "question": "చెత్త ఎక్కడ పేరుకుపోయింది?",
                "options": [
                    "నివాస గృహాలు లేదా పాఠశాల దగ్గర",
                    "మార్కెట్ లేదా హోటళ్ల దగ్గర",
                    "ఖాళీ స్థలంలో",
                ],
            },
        ],
        "ta": [
            {
                "id": "situation",
                "question": "குப்பை பிரச்சனை என்ன?",
                "options": [
                    "சாலையில் குப்பை குவிந்து துர்நாற்றம் வீசுகிறது",
                    "வீட்டுக்கு வரும் குப்பை வண்டி வரவில்லை",
                    "இறந்த விலங்கின் உடல் கிடக்கிறது",
                ],
            },
            {
                "id": "location_type",
                "question": "குப்பை எங்கு சேர்ந்துள்ளது?",
                "options": [
                    "வீடுகள் அல்லது பள்ளி அருகில்",
                    "சந்தை அருகில்",
                    "வெற்று இடத்தில்",
                ],
            },
        ],
        "kn": [
            {
                "id": "situation",
                "question": "ಕಸದ ಸಮಸ್ಯೆ ಏನು?",
                "options": [
                    "ರಸ್ತೆಯಲ್ಲಿ ಕಸ ತುಂಬಿ ದುರ್ವಾಸನೆ ಬರುತ್ತಿದೆ",
                    "ಮನೆ ಬಾಗಿಲಿಗೆ ಬರುವ ಕಸದ ವಾಹನ ಬಂದಿಲ್ಲ",
                    "ಸತ್ತ ಪ್ರಾಣಿಯ ಶವ ಬಿದ್ದಿದೆ",
                ],
            },
            {
                "id": "location_type",
                "question": "ಕಸ ಎಲ್ಲಿ ಸಂಗ್ರಹವಾಗಿದೆ?",
                "options": [
                    "ಮನೆಗಳು ಅಥವಾ ಶಾಲೆಯ ಬಳಿ",
                    "ಮಾರುಕಟ್ಟೆಯ ಬಳಿ",
                    "ಖಾಲಿ ಜಾಗದಲ್ಲಿ",
                ],
            },
        ],
        "hi": [
            {
                "id": "situation",
                "question": "कचरे की क्या समस्या है?",
                "options": [
                    "सड़क पर कचरे का ढेर लगा है और बदबू आ रही है",
                    "घर-घर कचरा उठाने वाली गाड़ी नहीं आ रही है",
                    "मरा हुआ जानवर पड़ा है (तुरंत सफाई की जरूरत)",
                ],
            },
            {
                "id": "location_type",
                "question": "कचरा कहाँ फैला हुआ है?",
                "options": [
                    "घरों या स्कूल के पास",
                    "बाजार के पास",
                    "खाली प्लॉट में",
                ],
            },
        ],
    },
    "ROAD_DAMAGE": {
        "en": [
            {
                "id": "condition",
                "question": "What is the condition of the road?",
                "options": [
                    "Deep dangerous craters causing vehicle accidents",
                    "Road dug up for utility work and left unrestored",
                    "Entire asphalt washed away into muddy ditch",
                ],
            },
            {
                "id": "traffic",
                "question": "What type of road is this?",
                "options": ["High-speed arterial road", "Residential colony lane", "Near school or hospital"],
            },
        ],
        "te": [
            {
                "id": "condition",
                "question": "రోడ్డు పరిస్థితి ఏమిటి?",
                "options": [
                    "పెద్ద గుంతలు పడి వాహన ప్రమాదాలు జరుగుతున్నాయి",
                    "పైపులైన్/కేబుల్ పనుల కోసం తవ్వి వదిలేశారు",
                    "రోడ్డు మొత్తం కొట్టుకుపోయి బురదమయంగా మారింది",
                ],
            },
            {
                "id": "traffic",
                "question": "ఇది ఎలాంటి రోడ్డు?",
                "options": ["ప్రధాన రహదారి", "కాలనీ వీధి", "పాఠశాల / ఆసుపత్రి దగ్గర"],
            },
        ],
        "ta": [
            {
                "id": "condition",
                "question": "சாலையின் நிலை என்ன?",
                "options": [
                    "விபத்துக்களை ஏற்படுத்தும் ஆழமான குழிகள்",
                    "பணிகளுக்காக தோண்டப்பட்டு மூடப்படாமல் உள்ளது",
                    "சாலை முற்றிலும் சேதமடைந்துள்ளது",
                ],
            },
            {
                "id": "traffic",
                "question": "இது என்ன வகையான சாலை?",
                "options": ["முக்கிய சாலை", "குடியிருப்பு தெரு", "பள்ளி / மருத்துவமனை அருகில்"],
            },
        ],
        "kn": [
            {
                "id": "condition",
                "question": "ರಸ್ತೆಯ ಸ್ಥಿತಿ ಹೇಗಿದೆ?",
                "options": [
                    "ಅಪಘಾತಗಳಿಗೆ ಕಾರಣವಾಗುವ ಆಳವಾದ ಗುಂಡಿಗಳು",
                    "ಕಾಮಗಾರಿಗಾಗಿ ಅಗೆದು ಹಾಗೆಯೇ ಬಿಡಲಾಗಿದೆ",
                    "ರಸ್ತೆ ಸಂಪೂರ್ಣವಾಗಿ ಹಾಳಾಗಿದೆ",
                ],
            },
            {
                "id": "traffic",
                "question": "ಇದು ಯಾವ ರೀತಿಯ ರಸ್ತೆ?",
                "options": ["ಮುಖ್ಯ ರಸ್ತೆ", "ಬಡಾವಣೆಯ ರಸ್ತೆ", "ಶಾಲೆ / ಆಸ್ಪತ್ರೆ ಬಳಿ"],
            },
        ],
        "hi": [
            {
                "id": "condition",
                "question": "सड़क की क्या स्थिति है?",
                "options": [
                    "गहरे गड्ढे जिनसे दुर्घटनाएं हो रही हैं",
                    "काम के लिए सड़क खोदी गई और ठीक नहीं की गई"
                    "पूरी सड़क उखड़कर कच्ची हो गई है",
                ],
            },
            {
                "id": "traffic",
                "question": "यह किस प्रकार की सड़क है?",
                "options": ["मुख्य सड़क", "आवासीय मोहल्ले की सड़क", "स्कूल / अस्पताल के पास"],
            },
        ],
    },
}


def is_gibberish(text: str) -> bool:
    """Detects random keyboard mash, single-character spam, or low-entropy strings."""
    cleaned = text.strip()
    if len(cleaned) < 4:
        return True

    # Check for excessive repetition of single characters (e.g. "aaaaaaa", "asdfasdf")
    if re.search(r"(.)\1{4,}", cleaned):
        return True

    # Check for pure non-alphanumeric noise
    alnum_chars = [c for c in cleaned if c.isalnum()]
    if len(alnum_chars) < 3:
        return True

    # Check for random keyboard patterns
    lower = cleaned.lower()
    if lower in ("asdfghjk", "asdf", "qwerty", "zxcvbnm", "123456", "111111", "testtest"):
        return True

    return False


def detect_script_language(text: str) -> str | None:
    """Detects Indian regional language from Unicode character blocks."""
    for ch in text:
        code = ord(ch)
        if 0x0C00 <= code <= 0x0C7F:
            return "te"
        elif 0x0B80 <= code <= 0x0BFF:
            return "ta"
        elif 0x0C80 <= code <= 0x0CFF:
            return "kn"
        elif 0x0900 <= code <= 0x097F:
            return "hi"
    return None


def get_diagnostic_questions(category: str, language: str = "en") -> list[dict[str, Any]]:
    """Returns diagnostic questions in the citizen's preferred or detected language."""
    cat_data = MULTILINGUAL_QUESTIONS.get(category, {})
    # Fallback to requested language, then English
    if language in cat_data:
        return cat_data[language]
    return cat_data.get("en", [])


def validate_civic_intent(text: str, language: str | None = None) -> CivicValidationResult:
    """Validates whether citizen input describes an authentic civic grievance."""
    cleaned = text.strip()

    # Determine regional language (respect explicit selection, otherwise detect script)
    if not language or language in ("auto", "en"):
        detected = detect_script_language(cleaned)
        if detected:
            language = detected
    if not language:
        language = "en"

    # 1. Gibberish check
    if is_gibberish(cleaned):
        return CivicValidationResult(
            is_civic=False,
            confidence=0.0,
            reason="GIBBERISH_OR_NOISE",
            message="Your input appears too short or indistinct. Please describe a specific civic issue you are facing (e.g., broken streetlights, water pipeline leak, or potholes).",
        )

    # 2. Conversational greetings and non-civic chit-chat check
    lower = cleaned.lower()
    for pattern in NON_CIVIC_PATTERNS:
        if re.search(pattern, lower):
            return CivicValidationResult(
                is_civic=False,
                confidence=0.05,
                reason="CASUAL_CONVERSATION",
                message="Greetings! SPANDAN AI is dedicated to resolving civic and municipal grievances. Please describe a civic problem in your area (like streetlights, water supply, garbage, or roads).",
            )

    # 3. Match against civic domain taxonomy
    best_category: str | None = None
    max_matches = 0

    for cat, keywords in CIVIC_KEYWORD_MAP.items():
        matches = 0
        for kw in keywords:
            if kw in lower or (len(kw) > 3 and kw in cleaned):
                matches += 1
        if matches > max_matches:
            max_matches = matches
            best_category = cat

    if max_matches > 0 and best_category:
        questions = get_diagnostic_questions(best_category, language=language)
        return CivicValidationResult(
            is_civic=True,
            confidence=min(0.70 + 0.10 * max_matches, 0.98),
            category=best_category,
            reason="CIVIC_KEYWORD_MATCH",
            suggested_questions=questions,
        )

    # 4. If no explicit civic keyword matched, check if it's at least a descriptive sentence (> 6 words)
    word_count = len(cleaned.split())
    if word_count >= 6:
        urgency_q_map = {
            "te": ("ఈ సమస్య ఎంత అత్యవసరమైనది?", ["తక్షణ భద్రతా ప్రమాదం", "మధ్యస్థ సమస్య", "సాధారణ మరమ్మత్తు అవసరం"]),
            "ta": ("இந்த பிரச்சனை எவ்வளவு அவசரமானது?", ["உடனடி பாதுகாப்பு ஆபத்து", "மிதமான பாதிப்பு", "வழக்கமான பராமரிப்பு"]),
            "kn": ("ಈ ಸಮಸ್ಯೆ ಎಷ್ಟು ತುರ್ತಾಗಿದೆ?", ["ತಕ್ಷಣದ ಸುರಕ್ಷತಾ ಅಪಾಯ", "ಮಧ್ಯಮ ಸಮಸ್ಯೆ", "ಸಾಮಾನ್ಯ ನಿರ್ವಹಣೆ"]),
            "hi": ("यह समस्या कितनी गंभीर और जरूरी है?", ["तत्काल सुरक्षा खतरा", "मध्यम व्यवधान", "सामान्य रखरखाव की आवश्यकता"]),
            "en": ("How urgent is this municipal problem?", ["Immediate safety hazard", "Moderate disruption", "Routine maintenance needed"]),
        }
        q_text, opts = urgency_q_map.get(language, urgency_q_map["en"])
        questions = [
            {
                "id": "urgency",
                "question": q_text,
                "options": opts,
            }
        ]
        return CivicValidationResult(
            is_civic=True,
            confidence=0.60,
            category="GENERAL_CIVIC_COMPLAINT",
            reason="DESCRIPTIVE_INPUT",
            suggested_questions=questions,
        )

    return CivicValidationResult(
        is_civic=False,
        confidence=0.20,
        reason="NO_CIVIC_RELEVANCE",
        message="We could not identify a municipal civic issue in your message. SPANDAN AI assists with city problems such as streetlights, water supply, potholes, overflowing drainage, or garbage collection. Please provide details about the civic problem.",
    )
