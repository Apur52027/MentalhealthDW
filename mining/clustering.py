"""CLUSTERING - discover groups of students with similar academic / lifestyle / mental-health profiles."""
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from mining.features import load_dataset

CLUSTER_FEATURES = ["gpa", "attendance_pct", "study_hours", "sleep_hours", "exercise_days",
                    "social_media_hours", "depression_score", "stress_score", "anxiety_score"]
SEED = 42


def run_clustering(k=None, k_range=range(2, 7)):
    df = load_dataset()
    X = StandardScaler().fit_transform(df[CLUSTER_FEATURES])

    scores = {}
    for kk in k_range:
        labels = KMeans(n_clusters=kk, n_init=10, random_state=SEED).fit_predict(X)
        scores[kk] = round(float(silhouette_score(X, labels)), 3)
    best_k = k or max(scores, key=scores.get)

    km = KMeans(n_clusters=best_k, n_init=10, random_state=SEED).fit(X)
    df["cluster"] = km.labels_
    coords = PCA(n_components=2, random_state=SEED).fit_transform(X)
    df["pc1"], df["pc2"] = coords[:, 0], coords[:, 1]

    profile = df.groupby("cluster").agg(
        students=("student_id", "size"),
        **{c: (c, "mean") for c in CLUSTER_FEATURES},
        high_risk_pct=("risk_level", lambda s: 100 * (s == "High").mean()),
    ).round(2)
    profile["share_pct"] = (100 * profile["students"] / len(df)).round(1)

    # descriptive names by average depression score (low -> high)
    order = profile["depression_score"].sort_values().index.tolist()
    names = {}
    for rank, cid in enumerate(order):
        if rank == 0:
            names[cid] = "Low-distress / healthy habits"
        elif rank == len(order) - 1:
            names[cid] = "High-distress / needs support"
        else:
            names[cid] = f"Moderate-distress (group {rank})"
    df["cluster_name"] = df["cluster"].map(names)
    profile.insert(0, "cluster_name", profile.index.map(names))
    profile = profile.loc[order].reset_index()

    return {"data": df, "profile": profile, "silhouette_by_k": scores, "k": best_k}
