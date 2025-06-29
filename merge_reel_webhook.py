from flask import Flask, request, jsonify
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import os

app = Flask(__name__)

# In-memory cluster storage
stored_clusters = []

@app.route("/cluster", methods=["POST"])
def cluster_questions():
    global stored_clusters

    input_data = request.json
    data = [{'question': q['question'], 'vector': list(map(float, q['embedding'].split(',')))} for q in input_data]
    vectors = np.array([d['vector'] for d in data])

    clustering = DBSCAN(eps=0.2, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_

    clustered = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue  # skip noise
        clustered.setdefault(label, []).append(data[idx])

    result = []
    cluster_id = 1
    stored_clusters = []

    for label, group in clustered.items():
        questions = [item['question'] for item in group]
        vectors = np.array([item['vector'] for item in group])
        centroid = np.mean(vectors, axis=0).tolist()

        result.append({
            "cluster": cluster_id,
            "representative": questions[0],
            "size": len(questions),
            "questions": questions,
           # "embedding": centroid
        })

        stored_clusters.append({
            "cluster": cluster_id,
            "embedding": centroid,
            "questions": questions
        })

        cluster_id += 1

    return jsonify(result)

@app.route("/assign", methods=["POST"])
def assign_new_question():
    global stored_clusters

    payload = request.json
    question = payload.get("question")
    embedding = list(map(float, payload.get("embedding").split(',')))
    vec = np.array(embedding).reshape(1, -1)

    if not stored_clusters:
        return jsonify({"message": "No existing clusters to compare with."}), 400

    cluster_vectors = np.array([np.array(c["embedding"]) for c in stored_clusters])
    similarities = cosine_similarity(vec, cluster_vectors)[0]
    max_sim = np.max(similarities)
    best_idx = int(np.argmax(similarities))

    threshold = 0.8
    if max_sim >= threshold:
        assigned_cluster = stored_clusters[best_idx]["cluster"]
        stored_clusters[best_idx]["questions"].append(question)
        return jsonify({
            "assigned_cluster": assigned_cluster,
            "similarity": float(max_sim),
            "message": "Assigned to existing cluster"
        })
    else:
        return jsonify({
            "assigned_cluster": None,
            "similarity": float(max_sim),
            "message": "No matching cluster found"
        })
@app.route("/json-to-section-array", methods=["POST"])
@app.route("/json-to-section-array", methods=["POST"])
@app.route("/json-to-section-array", methods=["POST"])
def json_to_section_array():
    try:
        section_type = request.args.get("target")  # "StructuredSectionsJSON" or "SectionOverviewJSON"
        data = request.get_json(force=True)

        if section_type not in data:
            return jsonify({"error": f"'{section_type}' key not found in posted JSON"}), 400

        sections = data[section_type]
        result = []

        for name, value in sections.items():
            if isinstance(value, str):
                result.append({
                    "section_name": name,
                    "summary": value,
                    "relevance": "",
                    "keywords": []
                })
            elif isinstance(value, dict):
                result.append({
                    "section_name": name,
                    "summary": value.get("Summary", ""),
                    "relevance": value.get("Relevance", ""),
                    "keywords": value.get("Keywords", [])
                })
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    result.append({
                        "section_name": f"{name}[{i}]",
                        "summary": item.get("Q") or item.get("Purpose") or str(item),
                        "relevance": "",
                        "keywords": []
                    })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "Exception occurred", "details": str(e)}), 500

# Render-compatible port binding
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
