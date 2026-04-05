# ===== ONLY SHOWING CHANGED / NEW CORE PARTS =====
# (Everything else from your previous main.py stays the same unless replaced below)

MODES = {
    "easy": ["math"],
    "boss": ["led", "math", "led"],
    "puzzle": ["led", "math_hard", "led", "math_hard", "math_hard"]
}

# ============================================================
# HARDER MATH
# ============================================================

def _generate_math_problem(hard=False):
    while True:
        op = random.choice(["+", "-", "*"])

        if hard:
            a = random.randint(10, 99)
            b = random.randint(0, 20)
        else:
            a = random.randint(0, 50)
            b = random.randint(0, 50)

        if op == "-":
            a, b = max(a, b), min(a, b)

        ans = eval(f"{a}{op}{b}")

        if 0 <= ans <= 99:
            return a, op, b, ans

def run_math(hard=False):
    a, op, b, answer = _generate_math_problem(hard)

    while True:
        if alarm_state.should_cancel():
            return False

        lcd_show_temp("Solve:", f"{a}{op}{b}", 2)

        tens = _choose_digit("Tens")
        ones = _choose_digit("Ones")
        user = tens * 10 + ones

        if user == answer:
            lcd_show_temp("Correct!", "", 1.5)
            return True

        lcd_show_temp("Wrong", "Try again", 2)
        flash_all_leds(2)

# ============================================================
# LED PATTERN (adjustable difficulty)
# ============================================================

def run_led(length=5):
    pattern = [random.choice(COLORS) for _ in range(length)]

    while True:
        if alarm_state.should_cancel():
            return False

        _show_pattern(pattern)
        user = _get_user_pattern(length)

        if user == pattern:
            lcd_show_temp("Correct!", "", 1.5)
            return True

        lcd_show_temp("Wrong", "Retry", 2)

# ============================================================
# PUZZLE ENGINE
# ============================================================

def run_mode(mode: str):
    steps = MODES.get(mode, ["math"])

    for step in steps:
        if alarm_state.should_cancel():
            return False

        if step == "math":
            if not run_math(False):
                return False

        elif step == "math_hard":
            if not run_math(True):
                return False

        elif step == "led":
            length = 5 if mode != "puzzle" else 7
            if not run_led(length):
                return False

    return True

# ============================================================
# UPDATED ALARM RUNNER
# ============================================================

def run_alarm(alarm_time: str, mode: str):
    print(f"[alarm] firing: {alarm_time} mode={mode}")
    alarm_state.set_active(True)

    start_audio(None)  # always buzzer

    try:
        if not run_mode(mode):
            return

        lcd_show_temp("Done!", "Good morning", 2)

    finally:
        stop_audio()
        all_leds_off()
        alarm_state.set_active(False)

# ============================================================
# ALARM CHECKER UPDATE
# ============================================================

def alarm_checker():
    while True:
        if not alarm_state.alarm_active:
            alarms = load_alarms()
            now_time = strftime("%H:%M")
            stamp = strftime("%Y-%m-%d %H:%M")

            for a in alarms:
                if a["time"] == now_time and not alarm_state.already_triggered(stamp):
                    alarm_state.mark_triggered(stamp)

                    threading.Thread(
                        target=run_alarm,
                        args=(now_time, a.get("mode", "easy")),
                        daemon=True
                    ).start()
                    break

        time.sleep(1)

# ============================================================
# API UPDATE (ADD MODE)
# ============================================================

@app.route("/api/alarms", methods=["POST"])
def api_add_alarm():
    data = request.get_json()
    time_val = data.get("time")
    mode = data.get("mode", "easy")

    alarms = load_alarms()

    alarms.append({
        "time": time_val,
        "mode": mode
    })

    save_alarms(alarms)
    return jsonify({"success": True, "alarms": alarms})
