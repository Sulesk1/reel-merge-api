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

    if not narration:
        return "Missing 'audio' file", 400
    if len(videos) < 1:
        return "No video clips provided", 400

    # Save uploaded video clips
    video_filenames = []
    for i, file in enumerate(videos):
        filename = f"clip{i}.mp4"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)
        video_filenames.append(filename)  # Only filename, not full path

    # Save narration
    audio_filename = "narration.mp3"
    audio_path = os.path.join(UPLOAD_DIR, audio_filename)
    narration.save(audio_path)

    # Save subtitle if provided
    subtitle_filename = None
    if subtitle:
        subtitle_filename = "subs.srt"
        subtitle_path = os.path.join(UPLOAD_DIR, subtitle_filename)
        subtitle.save(subtitle_path)

    # Create concat list (relative to cwd)
    concat_list_path = os.path.join(UPLOAD_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for filename in video_filenames:
            f.write(f"file '{filename}'\n")

    cwd = os.path.abspath(UPLOAD_DIR)

    # Merge clips using concat
    merged_filename = f"merged_{uuid.uuid4().hex}.mp4"
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c", "copy", merged_filename
    ], check=True, cwd=cwd)

    # Add audio (and optional subtitles)
    final_filename = f"final_{uuid.uuid4().hex}.mp4"
    command = [
        "ffmpeg", "-i", merged_filename, "-i", audio_filename,
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-shortest"
    ]

    if subtitle_filename:
        command += ["-vf", f"subtitles={subtitle_filename}"]

    command += [final_filename]

    subprocess.run(command, check=True, cwd=cwd)

    # Return finished video
    return send_file(os.path.join(cwd, final_filename), mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
