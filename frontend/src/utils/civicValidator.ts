/**
 * Client-side validator for civic complaints: detects nonsense, gibberish, spam, and non-civic input.
 */

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

const CIVIC_KEYWORDS = [
  // English
  "road", "pothole", "potholes", "water", "drain", "drainage", "sewage", "sewer",
  "garbage", "trash", "waste", "dump", "dustbin", "light", "streetlight", "streetlights",
  "electric", "electricity", "power", "wire", "pole", "leak", "leakage", "overflow",
  "stink", "smell", "odor", "stench", "dog", "dogs", "animal", "animals", "mosquito",
  "mosquitoes", "traffic", "signal", "footpath", "park", "tree", "pipe", "pipeline",
  "manhole", "gutter", "broken", "damaged", "repair", "clean", "cleaning", "dead",
  "flood", "flooding", "waterlogging", "tap", "supply",
  // Telugu
  "రోడ్డు", "గుంత", "గుంతలు", "నీరు", "నీళ్ళు", "డ్రైనేజీ", "మురుగు", "చెత్త",
  "కరెంట్", "దీపం", "దీపాలు", "లైటు", "లైట్లు", "పైపు", "కంపు", "దుర్వాసన",
  "కుక్కలు", "దోమలు", "పార్కు", "ట్రాఫిక్", "సిగ్నల్", "మరమ్మతు", "పగిలిపోయింది",
  // Hindi
  "सड़क", "गड्ढा", "गड्ढे", "पानी", "नाली", "सीवर", "कचरा", "कूड़ा", "बिजली",
  "बत्ती", "स्ट्रीटलाइट", "पाइप", "बदबू", "दुर्गंध", "सफाई", "मरम्मत", "टूटा",
  // Tamil
  "சாலை", "குப்பை", "தண்ணீர்", "சாக்கடை", "விளக்கு", "மின்சாரம்", "பழுது", "துர்நாற்றம்",
  // Kannada
  "ರಸ್ತೆ", "ಗುಂಡಿ", "ಕಸ", "ನೀರು", "ಚರಂಡಿ", "ದೀಪ", "ವಿದ್ಯುತ್", "ದುರ್ವಾಸನೆ", "ದುರಸ್ತಿ",
];

const SPAM_PHRASES = [
  "test", "testing", "asdf", "asdfasdf", "qwerty", "zxcvbnm", "hello", "hi", "hey",
  "check", "checking", "sample", "dummy", "nothing", "none", "spam", "random", "text",
  "foo", "bar", "lorem", "ipsum", "12345", "123456", "abc", "xyz", "haha", "hehe", "lol",
];

const VOWELS = new Set(["a", "e", "i", "o", "u"]);

export function validateCivicInput(text: string): ValidationResult {
  const trimmed = text.trim();

  if (!trimmed) {
    return {
      isValid: false,
      error: "Complaint description cannot be empty. Please describe the civic issue.",
    };
  }

  if (trimmed.length < 8) {
    return {
      isValid: false,
      error: "Complaint description is too short. Please provide clear details about what is damaged, where it is, or how long the issue has persisted.",
    };
  }

  const words = trimmed.toLowerCase().match(/\b\w+\b/g) || [];
  if (words.length < 2) {
    return {
      isValid: false,
      error: "Please write a full statement describing the problem rather than a single word.",
    };
  }

  const lower = trimmed.toLowerCase();

  // Known dummy / placeholder strings
  if (SPAM_PHRASES.includes(lower) || words.every((w) => SPAM_PHRASES.includes(w))) {
    return {
      isValid: false,
      error: "Please avoid test or greeting phrases. Describe an actual civic problem like potholes, streetlights, garbage, or water supply.",
    };
  }

  // Repetitive character smashing (e.g., 'aaaaa', 'zzzzz', '11111')
  if (/(.)\1{4,}/.test(trimmed)) {
    return {
      isValid: false,
      error: "Your input contains repetitive characters. Please type a meaningful explanation of the problem.",
    };
  }

  // Low unique character entropy (keyboard smashing)
  const nonSpace = trimmed.replace(/\s+/g, "").toLowerCase();
  if (nonSpace.length >= 12) {
    const uniqueChars = new Set(nonSpace.split(""));
    if (uniqueChars.size / nonSpace.length < 0.22) {
      return {
        isValid: false,
        error: "Your input appears to be random keyboard smashing. Please describe a genuine civic issue.",
      };
    }
  }

  // Consonant spam in Latin words (e.g. 'qwrtypsdfg', 'bcdfghjkl')
  for (const w of words) {
    if (/^[a-z]+$/.test(w) && w.length >= 7) {
      const hasVowel = w.split("").some((c) => VOWELS.has(c));
      if (!hasVowel) {
        return {
          isValid: false,
          error: `The word "${w}" appears to be random letters without vowels. Please describe a genuine civic problem.`,
        };
      }
    }
  }

  // Civic relevance check
  const hasCivic = CIVIC_KEYWORDS.some((kw) => lower.includes(kw));
  const genericSignals = [
    "problem", "issue", "complaint", "trouble", "bad", "worst", "danger",
    "not working", "overflowing", "fallen", "blocked", "causing", "stench",
    "smell", "dirty", "unhygienic", "broken", "leak", "cut", "off", "repair",
    "సమస్య", "బాధ", "పనిచేయట్లేదు", "సరిచేయండి", "समस्या", "खराब", "काम नहीं कर रहा",
  ];
  const hasGeneric = genericSignals.some((sig) => lower.includes(sig));

  const conversational = [
    "how are you", "what is your name", "who are you", "good morning", "good evening",
    "i love", "tell me a joke", "can you sing",
  ];
  if (conversational.some((c) => lower.includes(c))) {
    return {
      isValid: false,
      error: "SPANDAN AI is dedicated to civic grievances. Please report a public issue like streetlights, roads, drainage, or garbage.",
    };
  }

  if (!hasCivic && !hasGeneric && words.length < 5) {
    return {
      isValid: false,
      error: "Your message does not appear to describe a civic grievance. Please mention the specific problem (such as road pothole, streetlight, garbage, or water supply).",
    };
  }

  return { isValid: true };
}
