"""Unit and integration tests for Multi-Signal Language Identification System."""

import pytest
from fastapi.testclient import TestClient


def test_native_script_detection(client: TestClient):
    # Telugu Native Script
    res = client.post("/api/v1/language/detect", json={"text": "మా వీధిలో మూడు రోజులుగా స్ట్రీట్ లైట్ పని చేయడం లేదు."})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "te"
    assert data["confidence_tier"] == "HIGH"
    assert data["needs_confirmation"] is False

    # Tamil Native Script
    res = client.post("/api/v1/language/detect", json={"text": "எங்கள் தெருவில் மூன்று நாட்களாக தெருவிளக்கு வேலை செய்யவில்லை."})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "ta"
    assert data["confidence_tier"] == "HIGH"

    # Kannada Native Script
    res = client.post("/api/v1/language/detect", json={"text": "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ಮೂರು ದಿನಗಳಿಂದ ಸ್ಟ್ರೀಟ್ ಲೈಟ್ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ."})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "kn"
    assert data["confidence_tier"] == "HIGH"

    # Hindi Native Script
    res = client.post("/api/v1/language/detect", json={"text": "हमारी गली में तीन दिनों से स्ट्रीट लाइट काम नहीं कर रही है।"})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "hi"
    assert data["confidence_tier"] == "HIGH"


def test_romanized_indian_languages(client: TestClient):
    # Romanized Telugu
    res = client.post("/api/v1/language/detect", json={"text": "maa street lo light pani cheyyatledu"})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "te"
    assert data["confidence_tier"] == "HIGH"

    # Romanized Tamil
    res = client.post("/api/v1/language/detect", json={"text": "enga therula moonu naala street light vela seyyala"})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "ta"

    # Romanized Kannada
    res = client.post("/api/v1/language/detect", json={"text": "namma beedhili muru dinagalinda street light kelasa madtilla"})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "kn"

    # Romanized Hindi
    res = client.post("/api/v1/language/detect", json={"text": "humari gali mein street light kaam nahi kar rahi hai"})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "hi"


def test_code_mixed_speech(client: TestClient):
    # Telugu + English loanwords
    res = client.post("/api/v1/language/detect", json={"text": "మా colony లో drainage problem వల్ల చాలా smell వస్తోంది."})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "te"
    assert data["confidence_tier"] == "HIGH"
    assert data["signals"]["script"]["is_code_mixed"] is True


def test_short_utterance(client: TestClient):
    # Telugu short phrase
    res = client.post("/api/v1/language/detect", json={"text": "లైట్ లేదు"})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "te"


def test_english_standard(client: TestClient):
    res = client.post("/api/v1/language/detect", json={"text": "The street light in front of house number 42 has been broken for three days."})
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "en"
    assert data["confidence_tier"] == "HIGH"
