export interface DiagnosticQuestion {
  id: string;
  question: string;
  options: string[];
}

export interface ProblemCategory {
  id: string;
  labels: Record<string, string>;
  icon: string;
  color: string;
  defaultText: Record<string, string>;
}

export const PROBLEM_CATEGORIES: ProblemCategory[] = [
  {
    id: "STREETLIGHT_OUTAGE",
    labels: {
      en: "Streetlight",
      te: "స్ట్రీట్ లైట్",
      ta: "தெருவிளக்கு",
      kn: "ಬೀದಿ ದೀಪ",
      hi: "स्ट्रीट लाइट",
    },
    icon: "Lightbulb",
    color: "from-amber-500 to-yellow-500",
    defaultText: {
      en: "Streetlight not working on main street, dark and unsafe at night",
      te: "మా వీధిలో స్ట్రీట్ లైట్లు వెలగడం లేదు, రాత్రి వేళ చీకటిగా ఉంది",
      ta: "தெருவிளக்கு எரியவில்லை, இரவில் இருட்டாக உள்ளது",
      kn: "ಬೀದಿ ದೀಪಗಳು ಉರಿಯುತ್ತಿಲ್ಲ, ರಾತ್ರಿ ಕತ್ತಲೆಯಾಗಿದೆ",
      hi: "हमारी गली में स्ट्रीट लाइट काम नहीं कर रही है, रात में अंधेरा रहता है",
    },
  },
  {
    id: "WATER_SUPPLY_LEAK",
    labels: {
      en: "Water Supply",
      te: "తాగునీరు",
      ta: "குடிநீர்",
      kn: "ಕುಡಿಯುವ ನೀರು",
      hi: "जल आपूर्ति",
    },
    icon: "Droplets",
    color: "from-cyan-500 to-blue-500",
    defaultText: {
      en: "Clean drinking water pipeline leaking on street, water wasted",
      te: "తాగునీటి పైపులైన్ పగిలి రోడ్డుపై నీరు వృధాగా పోతోంది",
      ta: "குடிநீர் குழாய் உடைந்து தண்ணீர் வீணாகிறது",
      kn: "ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್ ಒಡೆದು ನೀರು ಪೋಲಾಗುತ್ತಿದೆ",
      hi: "पीने के पानी की पाइपलाइन फूट गई है और पानी बर्बाद हो रहा है",
    },
  },
  {
    id: "ROAD_DAMAGE",
    labels: {
      en: "Roads & Potholes",
      te: "రోడ్లు / గుంతలు",
      ta: "சாலை / குழி",
      kn: "ರಸ್ತೆ / ಗುಂಡಿ",
      hi: "सड़क व गड्ढे",
    },
    icon: "AlertTriangle",
    color: "from-orange-500 to-amber-600",
    defaultText: {
      en: "Dangerous deep potholes on road causing vehicle damage and accidents",
      te: "రోడ్డుపై ప్రమాదకరమైన పెద్ద గుంతలు పడ్డాయి, వాహనాలు దెబ్బతింటున్నాయి",
      ta: "சாலையில் ஆபத்தான பெரிய குழிகள் உள்ளன, விபத்துகள் ஏற்படுகின்றன",
      kn: "ರಸ್ತೆಯಲ್ಲಿ ಅಪಾಯಕಾರಿ ಗುಂಡಿಗಳು ಬಿದ್ದಿದ್ದು ವಾಹನ ಸಂಚಾರಕ್ಕೆ ತೊಂದರೆಯಾಗಿದೆ",
      hi: "सड़क पर गहरे गड्ढे हैं जिससे दुर्घटनाओं का खतरा बना हुआ है",
    },
  },
  {
    id: "DRAINAGE_OVERFLOW",
    labels: {
      en: "Drainage",
      te: "మురుగు / కాలువ",
      ta: "சாக்கடை",
      kn: "ಒಳಚರಂಡಿ",
      hi: "नाली / सीवर",
    },
    icon: "Activity",
    color: "from-emerald-500 to-teal-500",
    defaultText: {
      en: "Drainage overflowing with foul smell on public street",
      te: "మురుగు కాలువ పొంగి రోడ్డుపై ప్రవహిస్తోంది, తీవ్ర దుర్వాసన వస్తోంది",
      ta: "சாக்கடை நீர் சாலையில் பெருக்கெடுத்து ஓடுகிறது, துர்நாற்றம் வீசுகிறது",
      kn: "ಚರಂಡಿ ನೀರು ರಸ್ತೆಯಲ್ಲಿ ತುಂಬಿ ಹರಿಯುತ್ತಿದ್ದು ದುರ್ವಾಸನೆ ಬರುತ್ತಿದೆ",
      hi: "नाली का गंदा पानी सड़क पर बह रहा है और भयंकर बदबू आ रही है",
    },
  },
  {
    id: "GARBAGE_ACCUMULATION",
    labels: {
      en: "Garbage Dump",
      te: "చెత్త కుప్ప",
      ta: "குப்பை",
      kn: "ಕಸದ ರಾಶಿ",
      hi: "कचरा ढेर",
    },
    icon: "Trash2",
    color: "from-rose-500 to-pink-500",
    defaultText: {
      en: "Garbage dump overflowing on street corner, not cleared for days",
      te: "వీధి మూలలో చెత్త కుప్ప పేరుకుపోయింది, కొన్ని రోజులుగా ఎత్తలేదు",
      ta: "தெரு மூலையில் குப்பை தேங்கி கிடக்கிறது, பல நாட்களாக அகற்றப்படவில்லை",
      kn: "ಬೀದಿ ಮೂಲೆಯಲ್ಲಿ ಕಸದ ರಾಶಿ ಬಿದ್ದಿದ್ದು ಹಲವು ದಿನಗಳಿಂದ ವಿಲೇವಾರಿ ಮಾಡಿಲ್ಲ",
      hi: "सड़क किनारे कचरे का बड़ा ढेर लगा है जिसे कई दिनों से नहीं उठाया गया",
    },
  },
];

export const MULTILINGUAL_DIAGNOSTICS: Record<
  string,
  Record<string, DiagnosticQuestion[]>
> = {
  STREETLIGHT_OUTAGE: {
    en: [
      {
        id: "condition",
        question: "What is the condition of the light?",
        options: [
          "Entire street is pitch dark (multiple poles out)",
          "Single pole light is flickering or off",
          "Pole damaged or wires hanging dangerously",
        ],
      },
      {
        id: "duration",
        question: "How long has this issue persisted?",
        options: ["1-2 days", "3-5 days", "More than a week"],
      },
    ],
    te: [
      {
        id: "condition",
        question: "లైట్ పరిస్థితి ఏమిటి?",
        options: [
          "వీధి మొత్తం చీకటిగా ఉంది (అనేక స్తంభాలు)",
          "ఒకే స్తంభంపై లైట్ వెలగడం లేదు లేదా మినుకుమినుకుమంటోంది",
          "స్తంభం విరిగింది లేదా వైర్లు ప్రమాదకరంగా వేలాడుతున్నాయి",
        ],
      },
      {
        id: "duration",
        question: "ఈ సమస్య ఎన్ని రోజులుగా ఉంది?",
        options: ["1-2 రోజులు", "3-5 రోజులు", "వారం కంటే ఎక్కువ రోజులుగా"],
      },
    ],
    ta: [
      {
        id: "condition",
        question: "விளக்கின் நிலை என்ன?",
        options: [
          "தெரு முழுவதும் இருட்டாக உள்ளது (பல விளக்குகள்)",
          "ஒரு மின்கம்ப விளக்கு மட்டும் எரியவில்லை",
          "மின்கம்பம் சேதமடைந்துள்ளது / கம்பிகள் தொங்குகின்றன",
        ],
      },
      {
        id: "duration",
        question: "எத்தனை நாட்களாக இந்த பிரச்சனை உள்ளது?",
        options: ["1-2 நாட்கள்", "3-5 நாட்கள்", "ஒரு வாரத்திற்கும் மேலாக"],
      },
    ],
    kn: [
      {
        id: "condition",
        question: "ಬೀದಿ ದೀಪದ ಸ್ಥಿತಿ ಏನು?",
        options: [
          "ಇಡೀ ಬೀದಿ ಕತ್ತಲೆಯಾಗಿದೆ (ಹಲವು ದೀಪಗಳು)",
          "ಒಂದೇ ಕಂಬದ ದೀಪ ಆಫ್ ಆಗಿದೆ ಅಥವಾ ಮಿನುಗುತ್ತಿದೆ",
          "ಕಂಬ ಮುರಿದಿದೆ ಅಥವಾ ತಂತಿಗಳು ನೇತಾಡುತ್ತಿವೆ",
        ],
      },
      {
        id: "duration",
        question: "ಈ ಸಮಸ್ಯೆ ಎಷ್ಟು ದಿನಗಳಿಂದ ಇದೆ?",
        options: ["1-2 ದಿನಗಳು", "3-5 ದಿನಗಳು", "ಒಂದು ವಾರಕ್ಕಿಂತ ಹೆಚ್ಚು"],
      },
    ],
    hi: [
      {
        id: "condition",
        question: "स्ट्रीट लाइट की क्या स्थिति है?",
        options: [
          "पूरी सड़क पर अंधेरा है (कई खंभों की लाइट बंद)",
          "एक ही खंभे की लाइट बंद है या टिमटिमा रही है",
          "खंभा क्षतिग्रस्त है या तार लटक रहे हैं",
        ],
      },
      {
        id: "duration",
        question: "यह समस्या कितने दिनों से है?",
        options: ["1-2 दिन", "3-5 दिन", "एक सप्ताह से अधिक"],
      },
    ],
  },
  WATER_SUPPLY_LEAK: {
    en: [
      {
        id: "issue_type",
        question: "What type of water problem is this?",
        options: [
          "No water supply for multiple days",
          "Dirty / contaminated muddy drinking water",
          "Main pipeline burst / continuous clean water leak",
        ],
      },
      {
        id: "scope",
        question: "How many houses are affected?",
        options: ["Entire colony / street", "A few adjacent houses", "Individual house"],
      },
    ],
    te: [
      {
        id: "issue_type",
        question: "తాగునీటి సమస్య ఏమిటి?",
        options: [
          "కొన్ని రోజులుగా నీటి సరఫరా నిలిచిపోయింది",
          "మురికి / కలుషితమైన తాగునీరు వస్తోంది",
          "ప్రధాన పైపులైన్ పగిలి రోడ్డుపై నీరు వృధాగా పోతోంది",
        ],
      },
      {
        id: "scope",
        question: "ఎన్ని ఇళ్లకు సమస్య ఉంది?",
        options: ["కాలనీ / వీధి మొత్తం", "కొన్ని ఇళ్లకు మాత్రమే", "మా ఒక్క ఇంటికే"],
      },
    ],
    ta: [
      {
        id: "issue_type",
        question: "தண்ணீர் பிரச்சனையின் வகை என்ன?",
        options: [
          "பல நாட்களாக குடிநீர் வரவில்லை",
          "அசுத்தமான / கலங்கலான குடிநீர் வருகிறது",
          "முக்கிய குழாய் உடைந்து தண்ணீர் வீணாகிறது",
        ],
      },
      {
        id: "scope",
        question: "எத்தனை வீடுகள் பாதிக்கப்பட்டுள்ளன?",
        options: ["முழு பகுதி / தெரு", "சில வீடுகள்", "தனி வீடு"],
      },
    ],
    kn: [
      {
        id: "issue_type",
        question: "ಕುಡಿಯುವ ನೀರಿನ ಸಮಸ್ಯೆ ಏನು?",
        options: [
          "ಹಲವು ದಿನಗಳಿಂದ ನೀರು ಬರುತ್ತಿಲ್ಲ",
          "ಕಲುಷಿತ / ಗಲೀಜು ನೀರು ಬರುತ್ತಿದೆ",
          "ಮುಖ್ಯ ಪೈಪ್ ಒಡೆದು ನೀರು ಪೋಲಾಗುತ್ತಿದೆ",
        ],
      },
      {
        id: "scope",
        question: "ಎಷ್ಟು ಮನೆಗಳಿಗೆ ತೊಂದರೆಯಾಗಿದೆ?",
        options: ["ಇಡೀ ಬಡಾವಣೆ / ಬೀದಿ", "ಕೆಲವು ಮನೆಗಳು", "ಒಂದೇ ಮನೆ"],
      },
    ],
    hi: [
      {
        id: "issue_type",
        question: "पानी की क्या समस्या है?",
        options: [
          "कई दिनों से पानी की आपूर्ति नहीं हो रही",
          "गंदा / दूषित पीने का पानी आ रहा है",
          "मुख्य पाइपलाइन फटने से पानी बह रहा है",
        ],
      },
      {
        id: "scope",
        question: "कितने घर प्रभावित हैं?",
        options: ["पूरी कॉलोनी / गली", "आस-पास के कुछ घर", "केवल मेरा घर"],
      },
    ],
  },
  ROAD_DAMAGE: {
    en: [
      {
        id: "condition",
        question: "What is the damage condition?",
        options: [
          "Deep dangerous potholes causing accidents",
          "Trench dug for utility work left open",
          "Entire asphalt washed away into muddy ditch",
        ],
      },
      {
        id: "traffic",
        question: "What type of road is this?",
        options: ["High-speed arterial road", "Residential colony lane", "Near school or hospital"],
      },
    ],
    te: [
      {
        id: "condition",
        question: "రోడ్డు సమస్య ఏమిటి?",
        options: [
          "ప్రమాదకరమైన పెద్ద గుంతలు పడ్డాయి",
          "రోడ్డు తవ్వి అలాగే వదిలేశారు",
          "తారు కొట్టుకుపోయి రోడ్డు అంతా బురదమయమైంది",
        ],
      },
      {
        id: "traffic",
        question: "ఇది ఎలాంటి రహదారి?",
        options: ["ప్రధాన రద్దీ రహదారి", "కాలనీ అంతర్గత వీధి", "పాఠశాల లేదా ఆసుపత్రి సమీపంలో"],
      },
    ],
    ta: [
      {
        id: "condition",
        question: "சாலையின் சேதம் என்ன?",
        options: [
          "ஆபத்தான பெரிய குழிகள் உள்ளன",
          "குழாய் பணிக்காக சாலை தோண்டப்பட்டு மூடப்படவில்லை",
          "சாலை அரித்து சேறும் சகதியுமாக உள்ளது",
        ],
      },
      {
        id: "traffic",
        question: "இது என்ன வகையான சாலை?",
        options: ["முக்கிய போக்குவரத்து சாலை", "குடியிருப்பு தெரு", "பள்ளி அல்லது மருத்துவமனை அருகில்"],
      },
    ],
    kn: [
      {
        id: "condition",
        question: "ರಸ್ತೆಯ ಸ್ಥಿತಿ ಏನು?",
        options: [
          "ಅಪಾಯಕಾರಿ ಆಳವಾದ ಗುಂಡಿಗಳು ಬಿದ್ದಿವೆ",
          "ಕಾಮಗಾರಿಗಾಗಿ ರಸ್ತೆ ಅಗೆದು ಬಿಡಲಾಗಿದೆ",
          "ಡಾಂಬರು ಕಿತ್ತುಹೋಗಿ ಕೆಸರುಮಯವಾಗಿದೆ",
        ],
      },
      {
        id: "traffic",
        question: "ಇದು ಎಂತಹ ರಸ್ತೆ?",
        options: ["ಮುಖ್ಯ ಸಂಚಾರ ರಸ್ತೆ", "ಬಡಾವಣೆಯ ಒಳರಸ್ತೆ", "ಶಾಲೆ ಅಥವಾ ಆಸ್ಪತ್ರೆಯ ಹತ್ತಿರ"],
      },
    ],
    hi: [
      {
        id: "condition",
        question: "सड़क की स्थिति क्या है?",
        options: [
          "सड़क पर खतरनाक बड़े गड्ढे हैं",
          "काम के लिए सड़क खोदी गई और खुली छोड़ी गई",
          "डामर बह गया और पूरी सड़क पर कीचड़ है",
        ],
      },
      {
        id: "traffic",
        question: "यह किस प्रकार की सड़क है?",
        options: ["मुख्य भारी यातायात सड़क", "आवासीय कॉलोनी की गली", "स्कूल या अस्पताल के पास"],
      },
    ],
  },
  DRAINAGE_OVERFLOW: {
    en: [
      {
        id: "severity",
        question: "What is the severity of the overflow?",
        options: [
          "Sewage actively flowing onto public road",
          "Manhole cover is broken or missing (immediate danger)",
          "Blocked gutter with stagnant wastewater and mosquitoes",
        ],
      },
      {
        id: "duration",
        question: "How long has it been overflowing?",
        options: ["Since today", "2 to 3 days", "Chronic recurring issue"],
      },
    ],
    te: [
      {
        id: "severity",
        question: "మురుగు సమస్య తీవ్రత ఏమిటి?",
        options: [
          "రోడ్డుపై మురుగునీరు పొంగిపొర్లుతోంది",
          "మ్యాన్‌హోల్ మూత పగిలిపోయింది / ప్రమాదకరం",
          "కాలువ పూడికతో దోమల బెడద మరియు దుర్వాసన",
        ],
      },
      {
        id: "duration",
        question: "ఎన్ని రోజులుగా పొంగుతోంది?",
        options: ["ఈ రోజే మొదలైంది", "2-3 రోజులుగా", "చాలా కాలంగా నిరంతర సమస్య"],
      },
    ],
    ta: [
      {
        id: "severity",
        question: "கழிவுநீர் வழிந்தோடும் நிலை என்ன?",
        options: [
          "தெருவில் கழிவுநீர் பெருக்கெடுத்து ஓடுகிறது",
          "மேன்ஹோல் மூடி உடைந்துள்ளது / ஆபத்தானது",
          "சாக்கடை அடைப்பால் துர்நாற்றம் மற்றும் கொசுக்கள்",
        ],
      },
      {
        id: "duration",
        question: "எத்தனை நாட்களாக இந்த பிரச்சனை?",
        options: ["இன்று முதல்", "2 முதல் 3 நாட்கள்", "நீண்ட நாட்களாக தொடரும் பிரச்சனை"],
      },
    ],
    kn: [
      {
        id: "severity",
        question: "ಚರಂಡಿ ನೀರಿನ ಸಮಸ್ಯೆಯ ತೀವ್ರತೆ ಏನು?",
        options: [
          "ರಸ್ತೆಯಲ್ಲಿ ಚರಂಡಿ ನೀರು ತುಂಬಿ ಹರಿಯುತ್ತಿದೆ",
          "ಮ್ಯಾನ್‌ಹೋಲ್ ಮುಚ್ಚಳ ಮುರಿದಿದೆ / ಅಪಾಯಕಾರಿ",
          "ಚರಂಡಿ ಕಟ್ಟಿಕೊಂಡು ದುರ್ವಾಸನೆ ಮತ್ತು ಸೊಳ್ಳೆಗಳು",
        ],
      },
      {
        id: "duration",
        question: "ಎಷ್ಟು ದಿನಗಳಿಂದ ತುಂಬಿ ಹರಿಯುತ್ತಿದೆ?",
        options: ["ಇಂದಿನಿಂದ", "2 ರಿಂದ 3 ದಿನಗಳು", "ದೀರ್ಘಕಾಲಿಕ ಸಮಸ್ಯೆ"],
      },
    ],
    hi: [
      {
        id: "severity",
        question: "नाली / सीवर की क्या स्थिति है?",
        options: [
          "सड़क पर गंदा नाली का पानी बह रहा है",
          "मैनहोल का ढक्कन टूटा या गायब है (खतरनाक)",
          "नाली जाम होने से बदबू और मच्छर",
        ],
      },
      {
        id: "duration",
        question: "यह कितने दिनों से बह रहा है?",
        options: ["आज से", "2 से 3 दिन", "लगातार बनी रहने वाली समस्या"],
      },
    ],
  },
  GARBAGE_ACCUMULATION: {
    en: [
      {
        id: "situation",
        question: "What is the garbage situation?",
        options: [
          "Open garbage dump overflowing on the road",
          "Door-to-door sanitation collection stopped",
          "Dead animal carcass requiring emergency sanitation",
        ],
      },
      {
        id: "location_type",
        question: "Where is the waste located?",
        options: [
          "Near residential houses or school",
          "Near commercial market or food stalls",
          "In an open vacant plot",
        ],
      },
    ],
    te: [
      {
        id: "situation",
        question: "చెత్త సమస్య ఏమిటి?",
        options: [
          "రోడ్డుపై చెత్త కుప్ప పేరుకుపోయింది",
          "ఇళ్ల వద్ద చెత్త సేకరించడం ఆగిపోయింది",
          "జంతువు కళేబరం పడి ఉంది (తక్షణ పారిశుధ్యం అవసరం)",
        ],
      },
      {
        id: "location_type",
        question: "చెత్త ఎక్కడ పేరుకుపోయింది?",
        options: [
          "నివాస గృహాలు లేదా పాఠశాల వద్ద",
          "మార్కెట్ లేదా తినుబండారాల వద్ద",
          "ఖాళీ స్థలంలో",
        ],
      },
    ],
    ta: [
      {
        id: "situation",
        question: "குப்பை நிலைமை என்ன?",
        options: [
          "சாலையில் குப்பை குவிந்து வழிகிறது",
          "வீடு தோறும் குப்பை சேகரிப்பு நிறுத்தப்பட்டுள்ளது",
          "இறந்த விலங்கின் உடல் கிடக்கிறது",
        ],
      },
      {
        id: "location_type",
        question: "குப்பை எங்கு குவிந்துள்ளது?",
        options: [
          "வீடுகள் அல்லது பள்ளி அருகில்",
          "சந்தை அல்லது உணவகங்கள் அருகில்",
          "காலியிடத்தில்",
        ],
      },
    ],
    kn: [
      {
        id: "situation",
        question: "ಕಸದ ಪರಿಸ್ಥಿತಿ ಏನು?",
        options: [
          "ರಸ್ತೆಯಲ್ಲಿ ಕಸದ ರಾಶಿ ಬಿದ್ದಿದೆ",
          "ಮನೆ ಮನೆ ಕಸ ಸಂಗ್ರಹಣೆ ನಿಂತಿದೆ",
          "ಸತ್ತ ಪ್ರಾಣಿಯ ಕಳೇಬರ ಬಿದ್ದಿದೆ",
        ],
      },
      {
        id: "location_type",
        question: "ತ್ಯಾಜ್ಯ ಎಲ್ಲಿ ಬಿದ್ದಿದೆ?",
        options: [
          "ಮನೆಗಳು ಅಥವಾ ಶಾಲೆಯ ಹತ್ತಿರ",
          "ಮಾರುಕಟ್ಟೆ ಅಥವಾ ಹೋಟೆಲ್ ಹತ್ತಿರ",
          "ಖಾಲಿ ನಿವೇಶನದಲ್ಲಿ",
        ],
      },
    ],
    hi: [
      {
        id: "situation",
        question: "कचरे की क्या स्थिति है?",
        options: [
          "सड़क पर कचरे का बड़ा ढेर लगा है",
          "घर-घर कचरा उठाना बंद हो गया है",
          "मृत पशु का शव पड़ा है (तुरंत सफाई जरूरी)",
        ],
      },
      {
        id: "location_type",
        question: "कचरा कहाँ जमा है?",
        options: [
          "आवासीय घरों या स्कूल के पास",
          "बाज़ार या खाने की दुकानों के पास",
          "खाली प्लॉट में",
        ],
      },
    ],
  },
};

export function getDiagnosticQuestions(
  category: string,
  lang: string = "en"
): DiagnosticQuestion[] {
  const cat = MULTILINGUAL_DIAGNOSTICS[category];
  if (!cat) return [];
  return cat[lang] || cat["en"] || [];
}
