from flask import Flask, request, jsonify, render_template
import json
import os
import re

app = Flask(__name__)
ALARMS_FILE = "/home/kian/alarm_web/alarms.json"

TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def load_alarms():
    if not os.path.exists(ALARMS_FILE):
        return []
    try:
        with open(ALARMS_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return sorted(data)
            return []
    except Exception:
        return []


def save_alarms(alarms):
    alarms = sorted(set(alarms))
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f, indent=2)


def valid_time_string(t):
    if not TIME_PATTERN.match(t):
        return False
    hh, mm = t.split(":")
    h = int(hh)
    m = int(mm)
    return 0 <= h <= 23 and 0 <= m <= 59


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/alarms", methods=["GET"])
def get_alarms():
    return jsonify({"alarms": load_alarms()})


@app.route("/api/alarms", methods=["POST"])
def add_alarm():
    data = request.get_json(silent=True) or {}
    alarm_time = data.get("time", "").strip()

    if not valid_time_string(alarm_time):
        return jsonify({"success": False, "error": "Invalid time format. Use HH:MM"}), 400

    alarms = load_alarms()
    if alarm_time not in alarms:
        alarms.append(alarm_time)
        save_alarms(alarms)

    return jsonify({"success": True, "alarms": load_alarms()})


@app.route("/api/alarms/<alarm_time>", methods=["DELETE"])
def delete_alarm(alarm_time):
    alarms = load_alarms()
    new_alarms = [a for a in alarms if a != alarm_time]
    save_alarms(new_alarms)
    return jsonify({"success": True, "alarms": load_alarms()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
