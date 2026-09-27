"""Evaluation and benchmarking script for Multi-Signal Language Identification."""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.services.language_detection.fusion_service import LanguageFusionService
from app.services.language_detection.schemas import LanguageDetectRequest


async def run_evaluation():
    dataset_path = Path(__file__).resolve().parent.parent / "tests" / "language_detection" / "evaluation_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    service = LanguageFusionService()

    classes = ["te", "ta", "kn", "hi", "en"]
    confusion_matrix = defaultdict(lambda: defaultdict(int))
    category_results = defaultdict(lambda: {"correct": 0, "total": 0})

    y_true = []
    y_pred = []

    print("=" * 70)
    print(f"RUNNING LANGUAGE IDENTIFICATION EVALUATION ({len(dataset)} SAMPLES)")
    print("=" * 70)

    for item in dataset:
        text = item["text"]
        expected = item["expected_language"]
        category = item["category"]

        req = LanguageDetectRequest(text=text)
        result = await service.detect(req)
        predicted = result.language or "und"

        y_true.append(expected)
        y_pred.append(predicted)

        confusion_matrix[expected][predicted] += 1
        category_results[category]["total"] += 1
        if predicted == expected:
            category_results[category]["correct"] += 1
        else:
            print(f"[FAIL] Expected: {expected} | Got: {predicted} | Cat: {category} | Text: {text}")

    # Compute Metrics
    total = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / total

    # Per-class precision, recall, f1
    metrics = {}
    f1_sum = 0.0
    for c in classes:
        tp = confusion_matrix[c][c]
        fp = sum(confusion_matrix[other][c] for other in classes if other != c)
        fn = sum(confusion_matrix[c][other] for other in classes + ["und"] if other != c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        metrics[c] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
        f1_sum += f1

    macro_f1 = f1_sum / len(classes)

    print("\n" + "=" * 70)
    print("SUMMARY METRICS")
    print("=" * 70)
    print(f"Overall Accuracy: {accuracy * 100:.2f}% ({correct}/{total})")
    print(f"Macro F1 Score:   {macro_f1 * 100:.2f}%\n")

    print(f"{'Language':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<8}")
    print("-" * 56)
    for c in classes:
        m = metrics[c]
        print(f"{c.upper():<12} {m['precision']*100:>8.2f}%    {m['recall']*100:>8.2f}%    {m['f1']*100:>8.2f}%    {m['support']:<8}")

    print("\n" + "=" * 70)
    print("CONFUSION MATRIX (Row = Expected, Col = Predicted)")
    print("=" * 70)
    header = f"{'':<6}" + "".join(f"{c.upper():>8}" for c in classes + ["UND"])
    print(header)
    print("-" * len(header))
    for r in classes:
        row_str = f"{r.upper():<6}" + "".join(f"{confusion_matrix[r][c]:>8}" for c in classes + ["und"])
        print(row_str)

    print("\n" + "=" * 70)
    print("KEY SPECIFICATION CONFUSION CHECKS")
    print("=" * 70)
    print(f"Telugu -> Kannada confusion: {confusion_matrix['te']['kn']}")
    print(f"Kannada -> Telugu confusion: {confusion_matrix['kn']['te']}")
    print(f"Telugu -> Tamil confusion:   {confusion_matrix['te']['ta']}")
    print(f"Tamil -> Telugu confusion:   {confusion_matrix['ta']['te']}")
    print(f"Hindi -> Telugu confusion:   {confusion_matrix['hi']['te']}")
    print(f"English -> Romanized Telugu: {confusion_matrix['en']['te']}")

    print("\n" + "=" * 70)
    print("PER-CATEGORY BREAKDOWN")
    print("=" * 70)
    for cat, res in category_results.items():
        cat_acc = (res['correct'] / res['total']) * 100 if res['total'] > 0 else 0.0
        print(f"{cat:<30}: {cat_acc:>6.2f}% ({res['correct']}/{res['total']})")

    return accuracy, macro_f1, metrics


if __name__ == "__main__":
    asyncio.run(run_evaluation())
