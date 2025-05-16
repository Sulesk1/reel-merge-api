# filename: merge_reel_webhook.py

import os
import subprocess
from flask import Flask, request, send_file
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/render", methods=["POST"])
def render_video():
    files = request.files
    narration = files.get("audio")
    subtitle = files.get("subtitle")
    videos = [files.get(f"video{i}") for i in range(1, 6) if files.get(f"video{i}")]

    # Save uploaded files
    video_paths = []
    for i, file in enumerate(videos):
        path = os.path.join(UPLOAD_DIR, f"clip{i}.mp4")
        file.save(path)
        video_paths.append(path)

    audio_path = os.path.join(UPLOAD_DIR, "narration.mp3")
    narration.save(audio_path)

    subtitle_path = None
    if subtitle:
        subtitle_path = os.path.join(UPLOAD_DIR, "subs.srt")
        subtitle.save(subtitle_path)

    # Create a file list for concatenation
    list_path = os.path.join(UPLOAD_DIR, "concat_list.txt")
    with open(list_path, "w") as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    merged_video = os.path.join(UPLOAD_DIR, f"merged_{uuid.uuid4().hex}.mp4")

    # Merge clips
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", merged_video
    ], check=True)

    # Add audio + subtitles
    final_output = os.path.join(UPLOAD_DIR, f"final_{uuid.uuid4().hex}.mp4")
    command = ["ffmpeg", "-i", merged_video, "-i", audio_path, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-shortest"]

    if subtitle_path:
        command += ["-vf", f"subtitles={subtitle_path}"]

    command += [final_output]
    subprocess.run(command, check=True)

    return send_file(final_output, mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
