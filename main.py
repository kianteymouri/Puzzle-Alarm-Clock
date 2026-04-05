"""
main.py  —  Smart Alarm Clock (single entry point)
Starts Flask web server, clock display, and alarm checker in one process.

Run with:
    source ~/lcdenv/bin/activate
    python main.py
"""

import threading
import time
import random
import json
import os
import re
import subprocess
import fcntl
from time import strftime

import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
from flask import Flask, request, jsonify, render_template

# ============================================================
# CONFIG
# ============================================================

ALARMS_FILE  = "/home/kian/alarm_web/alarms.json"
UPLOADS_DIR  = "/home/kian/alarm_web/uploads"
FLASK_HOST   = "0.0.0.0"
FLASK_PORT   = 5000

# GPIO pin numbers (BCM)
GREEN_BTN    = 17
YELLOW_BTN   = 27
RED_BTN      = 22
RED_LED      = 23
YELLOW_LED   = 24
GREEN_LED    = 25
BUZZER_PIN   = 26

# Alarm challenge settings
PATTERN_LENGTH  = 5
FLASH_ON_TIME   = 0.5
FLASH_OFF_TIME  = 0.25
DEBOUNCE_TIME   = 0.2
NOTE_DURATION   = 0.18
NOTE_GAP        = 0.03

# ============================================================
# GPIO / HARDWARE SETUP
# ============================================================

GPIO.setmode(GPIO.BCM)
GPIO.setup(GREEN_BTN,  GPIO.IN,  pull_up_down=GPIO.PUD_UP)
GPIO.setup(YELLOW_BTN, GPIO.IN,  pull_up_down=GPIO.PUD_UP)
GPIO.setup(RED_BTN,    GPIO.IN,  pull_up_down=GPIO.PUD_UP)
GPIO.setup(RED_LED,    GPIO.OUT)
GPIO.setup(YELLOW_LED, GPIO.OUT)
GPIO.setup(GREEN_LED,  GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

buzzer_pwm = GPIO.PWM(BUZZER_PIN, 200)

LED_PINS = {"red": RED_LED, "yellow": YELLOW_LED, "green": GREEN_LED}
BTN_PINS = {"red": RED_BTN, "yellow": YELLOW_BTN, "green": GREEN_BTN}
COLORS   = ["red", "yellow", "green"]

# ============================================================
# LCD SETUP
# ============================================================

lcd = CharLCD('PCF8574', 0x27)

lcd_lock      = threading.Lock()
_last_line1   = None
_last_line2   = None
_msg_override = threading.Event()   # blocks clock while showing temp message
_stop_clock   = threading.Event()

# ============================================================
# MUSICAL NOTES
# ============================================================

C4=262; D4=294; E4=330; F4=349; G4=392; A4=440; B4=494
C5=523; D5=587; E5=659; F5=698; G5=784
B3=247

TUNE = [
    C4, E4, G4, C5, E5, G4, C5, E5,
    C4, E4, G4, C5, E5, G4, C5, E5,
    C4, D4, G4, D5, F5, G4, D5, F5,
    C4, D4, G4, D5, F5, G4, D5, F5,
    B3, D4, G4, D5, F5, G4, D5, F5,
    C4, E4, G4, C5, E5, G4, C5, E5,
]

# ============================================================
# SHARED ALARM STATE
# ============================================================

class AlarmState:
    """
    Thread-safe container for runtime alarm state.
    Flask and the alarm checker both hold a reference to this object.
    """
    def __init__(self):
        self._lock             = threading.Lock()
        self.triggered_stamps  = set()   # "YYYY-MM-DD HH:MM" stamps already fired
        self.alarm_active      = False   # True while challenge is running
        self.cancel_requested  = False   # set by Flask /api/cancel endpoint

    def mark_triggered(self, stamp: str):
        with self._lock:
            self.triggered_stamps.add(stamp)

    def already_triggered(self, stamp: str) -> bool:
        with self._lock:
            return stamp in self.triggered_stamps

    def set_active(self, value: bool):
        with self._lock:
            self.alarm_active = value
            if not value:
                self.cancel_requested = False  # reset on deactivate

    def request_cancel(self):
        with self._lock:
            self.cancel_requested = True

    def should_cancel(self) -> bool:
        with self._lock:
            return self.cancel_requested


alarm_state = AlarmState()

# ============================================================
# FILE I/O  (with advisory lock to prevent concurrent corruption)
# ============================================================

TIME_RE = re.compile(r"^\d{2}:\d{2}$")

def _valid_time(t: str) -> bool:
    if not TIME_RE.match(t):
        return False
    h, m = t.split(":")
    return 0 <= int(h) <= 23 and 0 <= int(m) <= 59

def load_alarms() -> list[dict]:
    """
    Returns a list of alarm dicts:
        {"time": "07:30", "song": "morning.mp3"}   # song is optional
    Handles both legacy flat-list format and new dict format transparently.
    """
    if not os.path.exists(ALARMS_FILE):
        return []
    try:
        with open(ALARMS_FILE, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)

        # Migrate legacy flat list  ["07:00", "08:30"]  →  dict format
        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, str):
                    normalized.append({"time": item, "song": None})
                elif isinstance(item, dict) and "time" in item:
                    item.setdefault("song", None)
                    normalized.append(item)
            return normalized
        return []
    except Exception as e:
        print(f"[alarm] load error: {e}")
        return []

def save_alarms(alarms: list[dict]):
    """Deduplicate by time, sort, then write atomically."""
    seen = {}
    for a in alarms:
        t = a.get("time", "")
        if t not in seen:
            seen[t] = a
    ordered = sorted(seen.values(), key=lambda x: x["time"])

    tmp = ALARMS_FILE + ".tmp"
    with open(tmp, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(ordered, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)
    os.replace(tmp, ALARMS_FILE)   # atomic on Linux

def get_song_for_alarm(alarm_time: str) -> str | None:
    """Return the song filename for a given HH:MM, or None."""
    for a in load_alarms():
        if a["time"] == alarm_time:
            return a.get("song")
    return None

# ============================================================
# LCD HELPERS
# ============================================================

def lcd_show(line1: str = "", line2: str = "", force: bool = False):
    global _last_line1, _last_line2
    line1 = line1[:16].ljust(16)
    line2 = line2[:16].ljust(16)
    with lcd_lock:
        if force or line1 != _last_line1:
            lcd.cursor_pos = (0, 0)
            lcd.write_string(line1)
            _last_line1 = line1
        if force or line2 != _last_line2:
            lcd.cursor_pos = (1, 0)
            lcd.write_string(line2)
            _last_line2 = line2

def lcd_show_temp(line1: str = "", line2: str = "", duration: float = 1.5):
    global _last_line1, _last_line2
    _msg_override.set()
    with lcd_lock:
        lcd.clear()
        _last_line1 = None
        _last_line2 = None
    lcd_show(line1, line2, force=True)
    time.sleep(duration)
    _msg_override.clear()

# ============================================================
# CLOCK DISPLAY THREAD
# ============================================================

def clock_loop():
    last_time_str = last_date_str = None
    while not _stop_clock.is_set():
        if not _msg_override.is_set():
            now_date = strftime('%m/%d/%Y')
            now_time = strftime('%I:%M %p')
            if now_date != last_date_str or now_time != last_time_str:
                lcd_show(now_date, now_time)
                last_date_str = now_date
                last_time_str = now_time
        time.sleep(0.2)

# ============================================================
# LED / BUZZER HELPERS
# ============================================================

def all_leds_off():
    for pin in LED_PINS.values():
        GPIO.output(pin, GPIO.LOW)

def flash_led(color: str, on_time=FLASH_ON_TIME, off_time=FLASH_OFF_TIME):
    all_leds_off()
    GPIO.output(LED_PINS[color], GPIO.HIGH)
    time.sleep(on_time)
    GPIO.output(LED_PINS[color], GPIO.LOW)
    time.sleep(off_time)

def flash_all_leds(times=3, on_time=0.3, off_time=0.3):
    for _ in range(times):
        for pin in LED_PINS.values():
            GPIO.output(pin, GPIO.HIGH)
        time.sleep(on_time)
        all_leds_off()
        time.sleep(off_time)

def play_note(freq: int, duration: float):
    buzzer_pwm.ChangeFrequency(freq)
    buzzer_pwm.start(50)
    time.sleep(duration)
    buzzer_pwm.stop()
    time.sleep(NOTE_GAP)

# ============================================================
# AUDIO
# ============================================================

_audio_proc   = None
_audio_lock   = threading.Lock()
_stop_music   = threading.Event()

def start_audio(song_filename: str | None):
    """
    Play a custom song on loop, or fall back to buzzer melody.
    song_filename is just the basename, e.g. "morning.mp3"
    """
    global _audio_proc
    _stop_music.clear()

    if song_filename:
        path = os.path.join(UPLOADS_DIR, song_filename)
        if os.path.exists(path):
            _start_file_audio(path)
            return
        print(f"[audio] file not found: {path}, falling back to buzzer")

    # Buzzer fallback
    t = threading.Thread(target=_buzzer_loop, daemon=True)
    t.start()

def _start_file_audio(path: str):
    """Launch mpg123 or aplay in a looping subprocess."""
    global _audio_proc

    def _run():
        global _audio_proc
        ext = os.path.splitext(path)[1].lower()
        cmd = (["mpg123", "--loop", "-1", path] if ext == ".mp3"
               else ["aplay", path])
        while not _stop_music.is_set():
            with _audio_lock:
                _audio_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            _audio_proc.wait()
            if ext != ".mp3":
                # aplay doesn't loop natively; we loop manually
                continue
            break  # mpg123 --loop -1 handles looping itself

    threading.Thread(target=_run, daemon=True).start()

def _buzzer_loop():
    while not _stop_music.is_set():
        for note in TUNE:
            if _stop_music.is_set():
                break
            play_note(note, NOTE_DURATION)

def stop_audio():
    """Stop all audio immediately."""
    _stop_music.set()
    with _audio_lock:
        if _audio_proc and _audio_proc.poll() is None:
            _audio_proc.terminate()
            try:
                _audio_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _audio_proc.kill()
    try:
        buzzer_pwm.stop()
    except Exception:
        pass

# ============================================================
# BUTTON INPUT
# ============================================================

def wait_for_button_press(timeout: float | None = None) -> str | None:
    """
    Block until a button is pressed and released.
    Returns "red" / "yellow" / "green", or None on timeout.
    """
    deadline = (time.monotonic() + timeout) if timeout else None
    while True:
        for color, pin in BTN_PINS.items():
            if GPIO.input(pin) == GPIO.LOW:
                while GPIO.input(pin) == GPIO.LOW:
                    time.sleep(0.01)
                time.sleep(DEBOUNCE_TIME)
                return color
        if deadline and time.monotonic() >= deadline:
            return None
        time.sleep(0.01)

# ============================================================
# ALARM CHALLENGE — PATTERN GAME
# ============================================================

def _show_pattern(pattern: list[str]):
    lcd_show_temp("Watch pattern", "", 1.0)
    time.sleep(0.3)
    for color in pattern:
        flash_led(color)

def _get_user_pattern(length: int) -> list[str]:
    entered = []
    lcd_show_temp("Enter pattern", "", 1.0)
    for i in range(length):
        pressed = wait_for_button_press()
        entered.append(pressed)
        GPIO.output(LED_PINS[pressed], GPIO.HIGH)
        time.sleep(0.15)
        GPIO.output(LED_PINS[pressed], GPIO.LOW)
    return entered

def _run_pattern_challenge() -> bool:
    """Returns True when the user gets the pattern right."""
    pattern = [random.choice(COLORS) for _ in range(PATTERN_LENGTH)]
    while True:
        if alarm_state.should_cancel():
            return False
        _show_pattern(pattern)
        user = _get_user_pattern(PATTERN_LENGTH)
        if user == pattern:
            lcd_show_temp("Pattern correct", "", 1.8)
            return True
        lcd_show_temp("Incorrect", "Try again", 2.0)
        flash_all_leds(times=3)
        time.sleep(1)

# ============================================================
# ALARM CHALLENGE — MATH
# ============================================================

def _generate_math_problem():
    while True:
        op = random.choice(["+", "-", "*"])
        if op == "+":
            a, b = random.randint(0, 50), random.randint(0, 49)
        elif op == "-":
            a = random.randint(0, 99)
            b = random.randint(0, a)
        else:
            a, b = random.randint(0, 9), random.randint(0, 9)
        ans = eval(f"{a}{op}{b}")   # safe: only our own ints/ops
        if 0 <= ans <= 99:
            return a, op, b, ans

def _choose_digit(label: str) -> int:
    digit = 0
    while True:
        lcd_show(label, f"Digit: {digit}", force=True)
        pressed = wait_for_button_press()
        if pressed == "red":
            digit = (digit + 1) % 10
            GPIO.output(RED_LED, GPIO.HIGH); time.sleep(0.12); GPIO.output(RED_LED, GPIO.LOW)
        elif pressed == "yellow":
            digit = (digit - 1) % 10
            GPIO.output(YELLOW_LED, GPIO.HIGH); time.sleep(0.12); GPIO.output(YELLOW_LED, GPIO.LOW)
        elif pressed == "green":
            GPIO.output(GREEN_LED, GPIO.HIGH); time.sleep(0.2); GPIO.output(GREEN_LED, GPIO.LOW)
            return digit

def _run_math_challenge() -> bool:
    """Returns True when the user answers correctly."""
    a, op, b, answer = _generate_math_problem()
    while True:
        if alarm_state.should_cancel():
            return False
        question = f"{a}{op}{b}=?"
        lcd_show_temp("Solve this:", question, 2.0)
        tens = _choose_digit("Select tens")
        ones = _choose_digit("Select ones")
        user_answer = tens * 10 + ones
        lcd_show_temp("Your answer:", str(user_answer), 1.2)
        if user_answer == answer:
            lcd_show_temp("Math correct!", "Nice job", 2.0)
            return True
        lcd_show_temp("Incorrect", "Try again", 2.0)
        flash_all_leds(times=3)
        time.sleep(0.8)

# ============================================================
# ALARM RUNNER
# ============================================================

def run_alarm(alarm_time: str):
    """Called in its own thread when an alarm fires."""
    print(f"[alarm] firing: {alarm_time}")
    alarm_state.set_active(True)

    song = get_song_for_alarm(alarm_time)
    start_audio(song)

    try:
        if not _run_pattern_challenge():
            print("[alarm] cancelled during pattern")
            return
        if not _run_math_challenge():
            print("[alarm] cancelled during math")
            return
        lcd_show_temp("Alarm solved!", "Good morning", 2.5)
        print("[alarm] challenge complete")
    finally:
        stop_audio()
        all_leds_off()
        alarm_state.set_active(False)

# ============================================================
# ALARM CHECKER LOOP (main thread)
# ============================================================

def alarm_checker():
    print("[alarm] checker started")
    while True:
        if not alarm_state.alarm_active:
            alarms     = load_alarms()
            now_time   = strftime('%H:%M')
            now_stamp  = strftime('%Y-%m-%d %H:%M')

            for alarm in alarms:
                t = alarm.get("time", "")
                if t == now_time and not alarm_state.already_triggered(now_stamp):
                    alarm_state.mark_triggered(now_stamp)
                    t = threading.Thread(
                        target=run_alarm, args=(now_time,), daemon=True
                    )
                    t.start()
                    break   # only fire one alarm per tick

        time.sleep(1)

# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__,
    template_folder="/home/kian/alarm_web/templates",
    static_folder="/home/kian/alarm_web/static"
)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg"}

def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/alarms", methods=["GET"])
def api_get_alarms():
    return jsonify({"alarms": load_alarms()})

@app.route("/api/alarms", methods=["POST"])
def api_add_alarm():
    data       = request.get_json(silent=True) or {}
    alarm_time = data.get("time", "").strip()
    song       = data.get("song", None)   # optional

    if not _valid_time(alarm_time):
        return jsonify({"success": False, "error": "Invalid time format. Use HH:MM"}), 400

    alarms = load_alarms()
    # Update existing entry if time already present
    existing = next((a for a in alarms if a["time"] == alarm_time), None)
    if existing:
        if song is not None:
            existing["song"] = song
    else:
        alarms.append({"time": alarm_time, "song": song})

    save_alarms(alarms)
    return jsonify({"success": True, "alarms": load_alarms()})

@app.route("/api/alarms/<alarm_time>", methods=["DELETE"])
def api_delete_alarm(alarm_time):
    alarms = [a for a in load_alarms() if a["time"] != alarm_time]
    save_alarms(alarms)
    return jsonify({"success": True, "alarms": load_alarms()})

@app.route("/api/alarms/<alarm_time>/song", methods=["POST"])
def api_assign_song(alarm_time):
    """Assign an already-uploaded song to a specific alarm."""
    data = request.get_json(silent=True) or {}
    song = data.get("song", "").strip()
    alarms = load_alarms()
    for a in alarms:
        if a["time"] == alarm_time:
            a["song"] = song or None
            save_alarms(alarms)
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Alarm not found"}), 404

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400
    if not _allowed_file(f.filename):
        return jsonify({"success": False, "error": "File type not allowed"}), 400

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    # Sanitise filename: keep only safe characters
    safe_name = re.sub(r"[^a-zA-Z0-9._\-]", "_", os.path.basename(f.filename))
    dest = os.path.join(UPLOADS_DIR, safe_name)
    f.save(dest)
    return jsonify({"success": True, "filename": safe_name})

@app.route("/api/songs", methods=["GET"])
def api_list_songs():
    """Return list of uploaded audio files."""
    if not os.path.exists(UPLOADS_DIR):
        return jsonify({"songs": []})
    songs = [
        fn for fn in os.listdir(UPLOADS_DIR)
        if os.path.splitext(fn)[1].lower() in ALLOWED_EXTENSIONS
    ]
    return jsonify({"songs": sorted(songs)})

@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    """Request cancellation of the currently running alarm challenge."""
    if alarm_state.alarm_active:
        alarm_state.request_cancel()
        return jsonify({"success": True, "message": "Cancel requested"})
    return jsonify({"success": False, "message": "No alarm active"})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "alarm_active": alarm_state.alarm_active,
        "current_time": strftime('%H:%M'),
    })

# ============================================================
# ENTRY POINT
# ============================================================

def main():
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Clock display thread
    clock_thread = threading.Thread(target=clock_loop, daemon=True)
    clock_thread.start()

    # Flask in a background thread (use_reloader=False is critical here)
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=False,
            use_reloader=False,   # MUST be False when running in a thread
        ),
        daemon=True,
    )
    flask_thread.start()

    print(f"[main] Web UI: http://raspberrypi.local:{FLASK_PORT}")
    print("[main] Alarm checker running. Ctrl+C to exit.")

    try:
        alarm_checker()   # runs forever in main thread
    except KeyboardInterrupt:
        print("\n[main] Shutting down...")
    finally:
        _stop_clock.set()
        _stop_music.set()
        stop_audio()
        all_leds_off()
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        with lcd_lock:
            lcd.clear()
        GPIO.cleanup()
        print("[main] Clean exit.")


if __name__ == "__main__":
    main()
