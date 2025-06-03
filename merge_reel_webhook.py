from flask import Flask, request, jsonify
import numpy as np
from sklearn.cluster import DBSCAN
import os

app = Flask(__name__)

@app.route("/cluster", methods=["POST"])
def cluster_questions():
    input_data = request.json
    data = [{'question': q['question'], 'vector': list(map(float, q['embedding'].split(',')))} for q in input_data]
    vectors = np.array([d['vector'] for d in data])

    clustering = DBSCAN(eps=0.2, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_

    clustered = {}
    for idx, label in enumerate(labels):
        clustered.setdefault(label, []).append(data[idx]['question'])

    result = []
    cluster_id = 1
    for label, questions in clustered.items():
        if label == -1:
            continue
        result.append({
            "cluster": cluster_id,
            "representative": questions[0],
            "size": len(questions),
            "questions": questions
        })
        cluster_id += 1

    return jsonify(result)

# 🔥 Port binding for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
