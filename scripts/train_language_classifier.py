import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.knowledge.embeddings import HashingNgramEmbedder

# Very minimal dataset for demo purposes
DATASET = [
    ("Tell us what went wrong. We'll help take your complaint forward.", "en"),
    ("The street light near the main gate has not worked for three days.", "en"),
    ("There is a massive pothole on MG Road causing accidents.", "en"),
    ("Garbage is not being collected from my street for a week.", "en"),

    ("మా వీధిలో మూడు రోజులుగా స్ట్రీట్ లైట్ పని చేయడం లేదు.", "te"),
    ("ఏం జరిగిందో మాకు చెప్పండి", "te"),
    ("నా ఇంటి ముందు మురుగునీరు నిలిచిపోయింది.", "te"),
    ("నగరంలో ట్రాఫిక్ సిగ్నల్స్ పని చేయడం లేదు.", "te"),

    ("எங்கள் தெருவில் மூன்று நாட்களாக தெருவிளக்கு வேலை செய்யவில்லை.", "ta"),
    ("பிரதான வீதியில் பெரிய குழிகள் உள்ளன.", "ta"),
    ("குடிநீர் வரவில்லை, தயவுசெய்து சரிசெய்யவும்.", "ta"),
    
    ("ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ಮೂರು ದಿನಗಳಿಂದ ಸ್ಟ್ರೀಟ್ ಲೈಟ್ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ.", "kn"),
    ("ಕಸದ ವಿಲೇವಾರಿ ಸರಿಯಾಗಿ ಆಗುತ್ತಿಲ್ಲ.", "kn"),
    ("ನೀರಿನ ಪೈಪ್ ಒಡೆದು ನೀರು ಪೋಲಾಗುತ್ತಿದೆ.", "kn"),

    ("हमारी गली में तीन दिन से स्ट्रीट लाइट काम नहीं कर रही है।", "hi"),
    ("सड़क पर बहुत बड़ा गड्ढा है।", "hi"),
    ("पीने का पानी नहीं आ रहा है।", "hi"),
    
    ("ഞങ്ങളുടെ തെരുവിൽ മൂന്നു ദിവസമായി തെരുവുവിളക്ക് പ്രവർത്തിക്കുന്നില്ല.", "ml"),
    ("റോഡിൽ വലിയ കുഴികൾ ഉണ്ട്.", "ml")
]

class HashingEmbedderTransformer(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.embedder = HashingNgramEmbedder(dimension=1024)

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.array(self.embedder.embed(X))

def main():
    print("Training Logistic Regression Language Classifier...")
    X_train = [text for text, label in DATASET]
    y_train = [label for text, label in DATASET]
    
    pipeline = Pipeline([
        ('embedder', HashingEmbedderTransformer()),
        ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced'))
    ])
    
    pipeline.fit(X_train, y_train)
    
    # Evaluate briefly on training set
    acc = pipeline.score(X_train, y_train)
    print(f"Training accuracy: {acc * 100:.2f}%")
    
    model_dir = Path(__file__).parent.parent / "app" / "models" / "ml"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / "language_classifier.joblib"
    joblib.dump(pipeline, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    main()
