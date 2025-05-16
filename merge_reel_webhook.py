import os
import subprocess
from flask import Flask, request, send_file
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

        # Automatically get video1–video5
        videos = [files.get(f"video{i}") for i in range(1, 6) if files.get(f"video{i}")]
        if not narration:
            return "❌ Missing 'audio' file", 400
        if len(videos) == 0:
            return "❌ No video clips provided", 400

        video_filenames = []

        # ✅ Step 1: Save and re-encode each video to FFmpeg-safe format
        for i, file in enumerate(videos):
            raw_path = os.path.join(UPLOAD_DIR, f"raw{i}.mp4")
            safe_path = os.path.join(UPLOAD_DIR, f"clip{i}.mp4")
            file.save(raw_path)

            print(f"🔁 Re-encoding raw{i}.mp4 → clip{i}.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_path,
                "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
                safe_path
            ], check=True)

            video_filenames.append(f"clip{i}.mp4")

        # ✅ Step 2: Save narration
        audio_path = os.path.join(UPLOAD_DIR, "narration.mp3")
        narration.save(audio_path)
        print("✅ Saved narration as:", audio_path)

        # ✅ Step 3: Save subtitle if present
        subtitle_filename = None
        if subtitle:
            subtitle_filename = "subs.srt"
            subtitle_path = os.path.join(UPLOAD_DIR, subtitle_filename)
            subtitle.save(subtitle_path)
            print("✅ Saved subtitle as:", subtitle_path)

        # ✅ Step 4: Create concat list
        concat_list_path = os.path.join(UPLOAD_DIR, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for filename in video_filenames:
                f.write(f"file '{filename}'\n")

        cwd = os.path.abspath(UPLOAD_DIR)
        print("📁 TEMP FILES:", os.listdir(UPLOAD_DIR))

        # ✅ Step 5: Concat all clips
        merged_filename = f"merged_{uuid.uuid4().hex}.mp4"
        try:
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
                "-c", "copy", merged_filename
            ], check=True, cwd=cwd, capture_output=True)
        except subprocess.CalledProcessError as e:
            print("❌ FFmpeg concat failed:", e.stderr.decode() if e.stderr else str(e))
            return f"Concat error:\n{e.stderr.decode() if e.stderr else str(e)}", 500

        # ✅ Step 6: Add audio and optional subtitles
        final_filename = f"final_{uuid.uuid4().hex}.mp4"
        command = [
            "ffmpeg", "-y", "-i", merged_filename, "-i", "narration.mp3",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-shortest"
        ]
        if subtitle_filename:
            command += ["-vf", f"subtitles={subtitle_filename}"]
        command += [final_filename]

        try:
            subprocess.run(command, check=True, cwd=cwd, capture_output=True)
        except subprocess.CalledProcessError as e:
            print("❌ FFmpeg final merge failed:", e.stderr.decode() if e.stderr else str(e))
            return f"Final merge error:\n{e.stderr.decode() if e.stderr else str(e)}", 500

        print("🎉 Final video ready:", final_filename)
        return send_file(os.path.join(cwd, final_filename), mimetype="video/mp4")

    except Exception as e:
        print("🔥 Unexpected error:", str(e))
        return f"Internal error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
