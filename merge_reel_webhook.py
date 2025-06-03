from flask import Flask, request, jsonify
import numpy as np
from sklearn.cluster import DBSCAN

app = Flask(__name__)

@app.route("/cluster", methods=["POST"])
def cluster_questions():
    input_data = request.json

    # Extract embeddings and questions
    data = [{'question': q['question'], 'vector': list(map(float, q['embedding'].split(',')))} for q in input_data]
    vectors = np.array([d['vector'] for d in data])

    # Perform DBSCAN clustering with cosine distance
    clustering = DBSCAN(eps=0.2, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_

    # Group by cluster label
    clustered = {}
    for idx, label in enumerate(labels):
        clustered.setdefault(label, []).append(data[idx]['question'])

    # Build output
    result = []
    cluster_id = 1
    for label, questions in clustered.items():
        if label == -1:
            continue  # Skip noise
        result.append({
            "cluster": cluster_id,
            "representative": questions[0],
            "size": len(questions),
            "questions": questions
        })
        cluster_id += 1

    return jsonify(result)
