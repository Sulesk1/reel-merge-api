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
    try:
        files = request.files
        print("✅ Received fields:", list(files.keys()))

        narration = files.get("audio")
        subtitle = files.get("subtitle")
        videos = [files.get(f"video{i}") for i in range(1, 6) if files.get(f"video{i}")]

        if not narration:
            return "❌ Missing 'audio' file", 400
        if len(videos) < 1:
            return "❌ No video clips provided", 400

        # Save uploaded video files
        video_filenames = []
        for i, file in enumerate(videos):
            filename = f"clip{i}.mp4"
            filepath = os.path.join(UPLOAD_DIR, filename)
            file.save(filepath)
            video_filenames.append(filename)

        print("✅ Saved video files:", video_filenames)

        # Save narration
        audio_filename = "narration.mp3"
        audio_path = os.path.join(UPLOAD_DIR, audio_filename)
        narration.save(audio_path)
        print("✅ Saved audio as:", audio_path)

        # Save subtitle if provided
        subtitle_filename = None
        if subtitle:
            subtitle_filename = "subs.srt"
            subtitle_path = os.path.join(UPLOAD_DIR, subtitle_filename)
            subtitle.save(subtitle_path)
            print("✅ Saved subtitle as:", subtitle_path)

        # Confirm temp folder contents
        print("📁 TEMP DIR CONTENT:", os.listdir(UPLOAD_DIR))

        # Create concat list
        concat_list_path = os.path.join(UPLOAD_DIR, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for filename in video_filenames:
                f.write(f"file '{filename}'\n")
        print("✅ Created concat list at:", concat_list_path)

        cwd = os.path.abspath(UPLOAD_DIR)

        # Merge clips
        merged_filename = f"merged_{uuid.uuid4().hex}.mp4"
        print("🚀 Running clip merge:", merged_filename)
        try:
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
                "-c", "copy", merged_filename
            ], check=True, cwd=cwd, capture_output=True)
        except subprocess.CalledProcessError as e:
            print("❌ FFmpeg concat error:")
            print(e.stderr.decode() if e.stderr else e)
            return f"Concat error:\n{e.stderr.decode() if e.stderr else e}", 500

        # Add audio + subtitles
        final_filename = f"final_{uuid.uuid4().hex}.mp4"
        command = [
            "ffmpeg", "-i", merged_filename, "-i", audio_filename,
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-shortest"
        ]
        if subtitle_filename:
            command += ["-vf", f"subtitles={subtitle_filename}"]
        command += [final_filename]

        print("🚀 Running audio + subtitle merge...")
        try:
            subprocess.run(command, check=True, cwd=cwd, capture_output=True)
        except subprocess.CalledProcessError as e:
            print("❌ FFmpeg final merge error:")
            print(e.stderr.decode() if e.stderr else e)
            return f"Final merge error:\n{e.stderr.decode() if e.stderr else e}", 500

        print("✅ Returning final video:", final_filename)
        return send_file(os.path.join(cwd, final_filename), mimetype="video/mp4")

    except Exception as e:
        print("🔥 Unexpected error:", str(e))
        return f"Internal error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
