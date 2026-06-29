"""
evaluate.py
Runs precision@k evaluation against a ground_truth.csv file.
You fill in ground_truth.csv manually, then run this to see how
well the matcher is actually doing.

Usage:
    python evaluate.py
    python evaluate.py --csv path/to/data.csv --truth path/to/ground_truth.csv

Dependencies:
    pip install pandas scikit-learn
"""

import argparse
import os
import sys

import pandas as pd

from matcher import load_scholarships, build_vectorizer, make_profile, match


DEFAULT_CSV   = os.path.join(os.path.dirname(__file__), "data", "clean", "scholarships_clean.csv")
DEFAULT_TRUTH = os.path.join(os.path.dirname(__file__), "evaluation", "ground_truth.csv")

# We check precision at these two values of k
K_VALUES = [3, 5]

# ground_truth.csv needs exactly these columns
REQUIRED_TRUTH_COLUMNS = [
    "profile_id", "gpa", "level", "language",
    "courses", "interests", "location", "relevant_ids",
]


def precision_at_k(ranked_ids: list, relevant_ids: set, k: int) -> float:
    # How many of the top k results are actually good matches?
    # relevant_ids is the set of IDs we marked as correct in ground_truth.csv
    if k <= 0:
        return 0.0
    top_k = ranked_ids[:k]
    hits = sum(1 for id_ in top_k if id_ in relevant_ids)
    return hits / k


def run_evaluation(
    csv_path: str,
    truth_path: str,
    k_values: list = K_VALUES,
) -> pd.DataFrame:
    # Loads ground truth, runs the matcher on each profile, scores the results
    if not os.path.exists(truth_path):
        raise FileNotFoundError(f"ground_truth.csv not found: {truth_path}")

    gt = pd.read_csv(truth_path)

    missing = [c for c in REQUIRED_TRUTH_COLUMNS if c not in gt.columns]
    if missing:
        raise ValueError(f"ground_truth.csv is missing columns: {missing}")

    print(f"Loading scholarships from: {csv_path}")
    df = load_scholarships(csv_path)
    vectorizer, matrix = build_vectorizer(df)
    print(f"Loaded {len(df)} scholarships.")
    print(f"Running evaluation on {len(gt)} profiles...\n")

    rows = []

    for _, row in gt.iterrows():
        profile = make_profile(
            gpa=float(row["gpa"]),
            courses=[c.strip() for c in str(row["courses"]).split(";")],
            interests=[i.strip() for i in str(row["interests"]).split(";")],
            location=str(row["location"]),
            level=str(row["level"]),
            language=str(row["language"]),
        )

        # relevant_ids in the CSV are semicolon separated e.g. "SCH001;SCH003"
        relevant = set(str(row["relevant_ids"]).split(";"))

        results = match(profile, df, vectorizer, matrix, top_k=max(k_values))
        ranked_ids = results["id"].tolist()

        result_row = {"profile_id": row["profile_id"]}
        for k in k_values:
            result_row[f"precision@{k}"] = precision_at_k(ranked_ids, relevant, k)

        rows.append(result_row)

    return pd.DataFrame(rows)


def print_results(results: pd.DataFrame, k_values: list = K_VALUES):
    print("=" * 50)
    print("  Results")
    print("=" * 50)
    print(results.to_string(index=False))
    print()

    for k in k_values:
        col = f"precision@{k}"
        mean = results[col].mean()
        print(f"  Mean precision@{k} = {mean:.3f}")

    print()

    # Simple pass/fail based on a 0.5 threshold
    # Means at least half the results in the top k were correct
    p3 = results["precision@3"].mean()
    if p3 >= 0.5:
        print("  precision@3 is above 0.5 which is a reasonable baseline.")
    else:
        print("  precision@3 is below 0.5. Check your ground_truth.csv or tweak the model.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the FirstStep matcher")
    parser.add_argument("--csv",   default=DEFAULT_CSV,   help="Path to scholarships_clean.csv")
    parser.add_argument("--truth", default=DEFAULT_TRUTH, help="Path to ground_truth.csv")
    args = parser.parse_args()

    csv_path = args.csv
    if not os.path.exists(csv_path):
        fallback = os.path.join(os.path.dirname(__file__), "data", "raw", "Scholarships.csv")
        if os.path.exists(fallback):
            print(f"[evaluate] Clean CSV not found, using raw: {fallback}\n")
            csv_path = fallback
        else:
            print(f"[evaluate] ERROR: No CSV found at {csv_path} or {fallback}")
            sys.exit(1)

    results = run_evaluation(csv_path, args.truth)
    print_results(results)
