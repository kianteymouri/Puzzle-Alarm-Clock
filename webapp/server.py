from flask import Flask, request, jsonify, render_template
import json
import os
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = "/home/kian/alarm_web"
ALARMS_FILE = os.path.join(BASE_DIR, "alarms.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
ALLOWED_EXTENSIONS = {"mp3", "wav", "ogg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_alarms():
    if not os.path.exists(ALARMS_FILE):
        return []

    try:
        with open(ALARMS_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        normalized = []
        for item in data:
            if isinstance(item, str):
                # backward compatibility with old format
                normalized.append({"time": item, "song": None})
            elif isinstance(item, dict) and "time" in item:
                normalized.append({
                    "time": item["time"],
                    "song": item.get("song")
                })

        return sorted(normalized, key=lambda x: x["time"])
    except Exception as e:
        print(f"Could not load alarms: {e}")
        return []


def save_alarms(alarms):
    # dedupe by time
    unique = {}
    for alarm in alarms:
        unique[alarm["time"]] = {
            "time": alarm["time"],
            "song": alarm.get("song")
        }

    alarms_list = sorted(unique.values(), key=lambda x: x["time"])

    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms_list, f, indent=2)


def valid_time_string(t):
    if not TIME_PATTERN.match(t):
        return False
    hh, mm = t.split(":")
    h = int(hh)
    m = int(mm)
    return 0 <= h <= 23 and 0 <= m <= 59


def list_uploaded_songs():
    files = []
    try:
        for name in os.listdir(UPLOAD_FOLDER):
            full_path = os.path.join(UPLOAD_FOLDER, name)
            if os.path.isfile(full_path) and allowed_file(name):
                files.append(name)
    except Exception as e:
        print(f"Could not list songs: {e}")
    return sorted(files)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/alarms", methods=["GET"])
def get_alarms():
    return jsonify({
        "alarms": load_alarms(),
        "songs": list_uploaded_songs()
    })


@app.route("/api/alarms", methods=["POST"])
def add_alarm():
    data = request.get_json(silent=True) or {}
    alarm_time = str(data.get("time", "")).strip()
    song = data.get("song")

    if not valid_time_string(alarm_time):
        return jsonify({"success": False, "error": "Invalid time format. Use HH:MM"}), 400

    if song == "":
        song = None

    if song is not None and song not in list_uploaded_songs():
        return jsonify({"success": False, "error": "Selected song does not exist."}), 400

    alarms = load_alarms()

    existing = next((a for a in alarms if a["time"] == alarm_time), None)
    if existing:
        existing["song"] = song
    else:
        alarms.append({
            "time": alarm_time,
            "song": song
        })

    save_alarms(alarms)
    return jsonify({
        "success": True,
        "alarms": load_alarms(),
        "songs": list_uploaded_songs()
    })


@app.route("/api/alarms/<alarm_time>", methods=["DELETE"])
def delete_alarm(alarm_time):
    alarms = load_alarms()
    new_alarms = [a for a in alarms if a["time"] != alarm_time]
    save_alarms(new_alarms)
    return jsonify({
        "success": True,
        "alarms": load_alarms(),
        "songs": list_uploaded_songs()
    })


@app.route("/api/upload-song", methods=["POST"])
def upload_song():
    if "song" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["song"]

    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Only mp3, wav, and ogg files are allowed."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    return jsonify({
        "success": True,
        "message": f"Uploaded {filename}",
        "songs": list_uploaded_songs()
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
