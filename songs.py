"""
songs.py  —  RTTTL song library + PWM buzzer player
RTTTL strings sourced from:
  granadaxronos/120-SONG_NOKIA_RTTTL_RINGTONE_PLAYER_FOR_ARDUINO_UNO

Usage:
    from songs import SONGS, SONG_NAMES, play_rtttl

    import RPi.GPIO as GPIO, threading
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(26, GPIO.OUT)
    pwm  = GPIO.PWM(26, 440)
    stop = threading.Event()
    play_rtttl(SONGS["Tetris"], pwm, stop, loop=True)

Standalone test:
    python songs.py "Tetris"
    python songs.py            # plays Super Mario by default
    python songs.py --list     # print all song names
"""

import time
import threading
import sys

# ── Note → frequency table (Hz, equal temperament) ──────────────────────────

NOTE_FREQ: dict[str, int] = {}

_BASE = {
    "c":  261.63, "c#": 277.18, "d":  293.66, "d#": 311.13,
    "e":  329.63, "f":  349.23, "f#": 369.99, "g":  392.00,
    "g#": 415.30, "a":  440.00, "a#": 466.16, "b":  493.88,
}

for _oct in range(3, 8):
    _mul = 2 ** (_oct - 4)
    for _n, _f in _BASE.items():
        NOTE_FREQ[f"{_n}{_oct}"] = int(_f * _mul)


# ── Song library ─────────────────────────────────────────────────────────────
# RTTTL format:  Name:d=<dur>,o=<oct>,b=<bpm>:<notes>
# Notes:  [duration]<note>[octave][.]   e.g. 8e6  16f#  4g.5  p (rest)

SONGS: dict[str, str] = {

    # ── Video game ────────────────────────────────────────────────────────
    "Super Mario": (
        "smb:d=4,o=5,b=100:"
        "16e6,16e6,32p,8e6,16c6,8e6,8g6,8p,8g,8p,"
        "8c6,16p,8g,16p,8e,16p,8a,8b,16a#,8a,16g.,16e6,16g6,8a6,16f6,8g6,8e6,16c6,16d6,8b,"
        "16p,8c6,16p,8g,16p,8e,16p,8a,8b,16a#,8a,16g.,16e6,16g6,8a6,16f6,8g6,8e6,16c6,16d6,8b"
    ),

    "Super Mario Underground": (
        "smb_under:d=4,o=6,b=100:"
        "32c,32p,32c7,32p,32a5,32p,32a,32p,32a#5,32p,32a#,2p,"
        "32c,32p,32c7,32p,32a5,32p,32a,32p,32a#5,32p,32a#,2p,"
        "32f5,32p,32f,32p,32d5,32p,32d,32p,32d#5,32p,32d#,2p,"
        "32f5,32p,32f,32p,32d5,32p,32d,32p,32d#5,32p,32d#"
    ),

    "Super Mario 2": (
        "smario2:d=4,o=5,b=125:"
        "8g,16c,8e,8g.,16c,8e,16g,16c,16e,16g,8b,a,8p,"
        "16c,8g,16c,8e,8g.,16c,8e,16g,16c#,16e,16g,8b,a,8p,"
        "16b,8c6,16b,8c6,8a.,16c6,8b,16a,8g,16f#,8g,8e.,16c,8d,16e,8f,16e,8f,8b.4,16e,8d.,c"
    ),

    "Tetris": (
        "Tetris:d=4,o=5,b=160:"
        "e6,8b5,8c6,d6,8c6,8b5,"
        "a5,8a5,8c6,e6,8d6,8c6,"
        "b5,8b5,8c6,d6,e6,c6,a5,a5,p,"
        "8d6,8f6,a6,8g6,8f6,"
        "e6,8c6,e6,8d6,8c6,"
        "b5,8b5,8c6,d6,e6,c6,a5"
    ),

    "Zelda": (
        "Zelda1:d=4,o=5,b=125:"
        "a#,f.,8a#,16a#,16c6,16d6,16d#6,2f6,8p,8f6,16f.6,16f#6,16g#.6,2a#.6,"
        "16a#.6,16g#6,16f#.6,8g#.6,16f#.6,2f6,f6,8d#6,16d#6,16f6,2f#6,"
        "8f6,8d#6,8c#6,16c#6,16d#6,2f6,8d#6,8c#6,8c6,16c6,16d6,2e6,"
        "g6,8f6,16f,16f,8f,16f,16f,8f,16f,16f,8f,8f"
    ),

    "Duck Tales": (
        "ducktales:d=4,o=5,b=112:"
        "8e6,8e6,16p,16g6,8b6,g#6,p,8e6,8d6,8c6,8d6,"
        "8e6,8d6,8c6,8d6,8e6,8e6,16p,16g6,8b6,g#6,p,"
        "8e6,8d6,8c6,8d6,8e6,8d6,8c6,8g6,8e6,8e6"
    ),

    "Pacman": (
        "Pacman:d=4,o=5,b=140:"
        "32b,32p,32b6,32p,32f#6,32p,32d#6,32p,32b6,8f#6,16d#6,"
        "8d6,8c#6,8c6,8e,8f,8f#,8g,"
        "16g,8d#6,16f6,8d6,8c#6,8c6,8d6,8p,"
        "8d6,8c#6,8c6,8e,8f,8f#,8g"
    ),

    # ── TV / Film ─────────────────────────────────────────────────────────
    "Star Wars": (
        "StarWars:d=4,o=5,b=45:"
        "32p,32f#,32f#,32f#,8b.,8f#.6,32e6,32d#6,32c#6,8b.6,16f#.6,"
        "32e6,32d#6,32c#6,8b.6,16f#.6,32e6,32d#6,32e6,8c#.6,"
        "32f#,32f#,32f#,8b.,8f#.6,32e6,32d#6,32c#6,8b.6,16f#.6,"
        "32e6,32d#6,32c#6,8b.6,16f#.6,32e6,32d#6,32e6,8c#6"
    ),

    "Indiana Jones": (
        "Indiana:d=4,o=5,b=250:"
        "e,8p,8f,8g,8p,1c6,8p.,d,8p,8e,1f,p.,"
        "g,8p,8a,8b,8p,1f6,p,a,8p,8b,2c6,2d6,2e6,"
        "e,8p,8f,8g,8p,1c6,p,d6,8p,8e6,1f.6,"
        "g,8p,8g,e.6,8p,d6,8p,8g,e.6,8p,d6,8p,8g,f.6,8p,e6,8p,8d6,2c6"
    ),

    "Mission Impossible": (
        "MissionImp:d=16,o=6,b=95:"
        "32d,32d#,32d,32d#,32d,32d#,32d,32d#,32d,32d,32d#,32e,32f,32f#,32g,"
        "g,8p,g,8p,a#,p,c7,p,g,8p,g,8p,f,p,f#,p,"
        "g,8p,g,8p,a#,p,c7,p,g,8p,g,8p,f,p,f#,p,"
        "a#,g,2d,32p,a#,g,2c#,32p,a#,g,2c,a#5,8c,2p,32p,"
        "a#5,g5,2f#,32p,a#5,g5,2f,32p,a#5,g5,2e,d#,8d"
    ),

    "The Simpsons": (
        "The Simpsons:d=4,o=5,b=160:"
        "c.6,e6,f#6,8a6,g.6,e6,c6,8a,8f#,8f#,8f#,2g,8p,8p,"
        "8f#,8f#,8f#,8g,a#.,8c6,8c6,8c6,c6"
    ),

    "X-Files": (
        "Xfiles:d=4,o=5,b=125:"
        "e,b,a,b,d6,2b.,1p,"
        "e,b,a,b,e6,2b.,1p,"
        "g6,f#6,e6,d6,e6,2b.,1p,"
        "g6,f#6,e6,d6,f#6,2b.,1p,"
        "e,b,a,b,d6,2b.,1p,"
        "e,b,a,b,e6,2b.,1p,e6,2b."
    ),

    "Pink Panther": (
        "PinkPanther:d=4,o=5,b=160:"
        "8d#,8e,2p,8f#,8g,2p,8d#,8e,16p,8f#,8g,16p,"
        "8c6,8b,16p,8d#,8e,16p,8b,2a#,2p,16a,16g,16e,16d,2e"
    ),

    "Knight Rider": (
        "KnightRider:d=4,o=5,b=125:"
        "16e,16p,16f,16e,16e,16p,16e,16e,16f,16e,16e,16e,16d#,16e,16e,16e,"
        "16e,16p,16f,16e,16e,16p,16f,16e,16f,16e,16e,16e,16d#,16e,16e,16e,"
        "16d,16p,16e,16d,16d,16p,16e,16d,16e,16d,16d,16d,16c,16d,16d,16d,"
        "16d,16p,16e,16d,16d,16p,16e,16d,16e,16d,16d,16d,16c,16d,16d,16d"
    ),

    "Axel F": (
        "axelf:d=4,o=5,b=160:"
        "f#,8a.,8f#,16f#,8a#,8f#,8e,"
        "f#,8c.6,8f#,16f#,8d6,8c#6,8a,8f#,8c#6,"
        "8f#6,16f#,8e,16e,8c#,8g#,f#."
    ),

    "Entertainer": (
        "Entertainer:d=4,o=5,b=140:"
        "8d,8d#,8e,c6,8e,c6,8e,2c.6,8c6,8d6,8d#6,8e6,8c6,8d6,e6,8b,d6,2c6,p,"
        "8d,8d#,8e,c6,8e,c6,8e,2c.6,8p,8a,8g,8f#,8a,8c6,e6,8d6,8c6,8a,2d6"
    ),

    "James Bond": (
        "Bond:d=4,o=5,b=80:"
        "32p,16c#6,32d#6,32d#6,16d#6,8d#6,16c#6,16c#6,16c#6,16c#6,"
        "32e6,32e6,16e6,8e6,16d#6,16d#6,16d#6,16c#6,"
        "32d#6,32d#6,16d#6,8d#6,16c#6,16c#6,16c#6,16c#6,"
        "32e6,32e6,16e6,8e6,16d#6,16d6,16c#6,16c#7,c.7,16g#6,16f#6,g#.6"
    ),

    "Jeopardy": (
        "Jeopardy:d=4,o=6,b=125:"
        "c,f,c,f5,c,f,2c,c,f,c,f,a.,8g,8f,8e,8d,8c#,"
        "c,f,c,f5,c,f,2c,f.,8d,c,a#5,a5,g5,f5,p,"
        "d#,g#,d#,g#5,d#,g#,2d#,d#,g#,d#,g#,c.7,8a#,8g#,8g,8f,8e,"
        "d#,g#,d#,g#5,d#,g#,2d#,g#.,8f,d#,c#,c,p,a#5,p,g#.5,d#,g#"
    ),

    "Munsters": (
        "munsters:d=4,o=5,b=160:"
        "d,8f,8d,8g#,8a,d6,8a#,8a,2g,8f,8g,a,8a4,8d#4,8a4,8b4,c#,8d,p,"
        "c,c6,c6,2c6,8a#,8a,8a#,8g,8a,f,p,g,g,2g,8f,8e,8f,8d,8e,2c#,p,"
        "d,8f,8d,8g#,8a,d6,8a#,8a,2g,8f,8g,a,8d#4,8a4,8d#4,8b4,c#,2d"
    ),

    "Peter Gunn": (
        "PeterGunn:d=4,o=5,b=112:"
        "8e,8e,8f#,8e,8g,8e,8a,8g,"
        "8e,8e,8f#,8e,8g,8e,8a,8g,"
        "1e,c#,2p,p,1e,8c#6,8g,2p"
    ),

    "Star Trek": (
        "StarTrek:d=4,o=5,b=63:"
        "8f.,16a#,d#.6,8d6,16a#.,16g.,16c.6,f6"
    ),

    "Looney Tunes": (
        "Looney:d=4,o=5,b=140:"
        "c6,8f6,8e6,8d6,8c6,a.,8c6,8f6,8e6,8d6,8d#6,"
        "e.6,8e6,8e6,8c6,8d6,8c6,8e6,8c6,8d6,8a,8c6,8g,8a#,8a,8f"
    ),

    # ── Pop / Rock ────────────────────────────────────────────────────────
    "Take On Me": (
        "TakeOnMe:d=4,o=4,b=160:"
        "8f#5,8f#5,8f#5,8d5,8p,8b,8p,"
        "8e5,8p,8e5,8p,8e5,8g#5,8g#5,8a5,8b5,"
        "8a5,8a5,8a5,8e5,8p,8d5,8p,"
        "8f#5,8p,8f#5,8p,8f#5,8e5,8e5,8f#5,8e5"
    ),

    "Smoke on the Water": (
        "Smoke:d=4,o=5,b=112:"
        "c,d#,f.,c,d#,8f#,f,p,"
        "c,d#,f.,d#,c,2p,8p,"
        "c,d#,f.,c,d#,8f#,f,p,"
        "c,d#,f.,d#,c,p"
    ),

    "Barbie Girl": (
        "girl:d=4,o=5,b=125:"
        "8g#,8e,8g#,8c#6,a,p,"
        "8f#,8d#,8f#,8b,g#,8f#,8e,p,"
        "8e,8c#,f#,c#,p,"
        "8f#,8e,g#,f#"
    ),

    "Wannabe": (
        "Wannabe:d=4,o=5,b=125:"
        "16g,16g,16g,16g,8g,8a,8g,8e,8p,16c,16d,16c,8d,8d,8c,e,p,"
        "8g,8g,8g,8a,8g,8e,8p,c6,8c6,8b,8g,8a,16b,16a,g"
    ),

    "Macarena": (
        "Macarena:d=4,o=5,b=180:"
        "f,8f,8f,f,8f,8f,8f,8f,8f,8f,8f,8a,8c,8c,"
        "f,8f,8f,f,8f,8f,8f,8f,8f,8f,8d,8c,p,"
        "f,8f,8f,f,8f,8f,8f,8f,8f,8f,8f,8a,p,"
        "2c.6,a,8c6,8a,8f,p,2p"
    ),

    "Funky Town": (
        "FunkyTown:d=4,o=4,b=125:"
        "8c6,8c6,8a#5,8c6,8p,8g5,8p,8g5,"
        "8c6,8f6,8e6,8c6,2p,"
        "8c6,8c6,8a#5,8c6,8p,8g5,8p,8g5,"
        "8c6,8f6,8e6,8c6"
    ),

    "Final Countdown": (
        "countdown:d=4,o=5,b=125:"
        "p,8p,16b,16a,b,e,p,8p,16c6,16b,8c6,8b,a,"
        "p,8p,16c6,16b,c6,e,p,8p,16a,16g,8a,8g,8f#,8a,"
        "g.,16f#,16g,a.,16g,16a,8b,8a,8g,8f#,"
        "e,c6,2b.,16b,16c6,16b,16a,1b"
    ),

    # ── Classical ─────────────────────────────────────────────────────────
    "Greensleeves": (
        "Greensleaves:d=4,o=5,b=140:"
        "g,2a#,c6,d.6,8d#6,d6,2c6,a,f.,8g,a,2a#,g,g.,8f,g,2a,f,2d,"
        "g,2a#,c6,d.6,8e6,d6,2c6,a,f.,8g,a,a#.,8a,g,f#.,8e,f#,2g"
    ),

    "Canon in D": (
        "Canon:d=4,o=5,b=80:"
        "8d,8f#,8a,8d6,8c#,8e,8a,8c#6,8d,8f#,8b,8d6,8a,8c#,8f#,8a,"
        "8b,8d,8g,8b,8a,8d,8f#,8a,8b,8f#,8g,8b,8c#,8e,8a,8c#6,"
        "f#6,8f#,8a,e6,8e,8a,d6,8f#,8a,c#6,8c#,8e,b,8d,8g,a,8f#,8d,b,8d,8g,c#.6"
    ),

    "Bolero": (
        "Bolero:d=4,o=5,b=80:"
        "c6,8c6,16b,16c6,16d6,16c6,16b,16a,8c6,16c6,16a,"
        "c6,8c6,16b,16c6,16a,16g,16e,16f,2g,"
        "16g,16f,16e,16d,16e,16f,16g,16a,"
        "g,g,16g,16a,16b,16a,16g,16f,16e,16d,16e,16d,"
        "8c,8c,16c,16d,8e,8f,d,2g"
    ),

    "Fur Elise": (
        "FurElise:d=8,o=5,b=125:"
        "e6,d#6,e6,d#6,e6,b,d6,c6,a,p,c,e,a,b,p,e,g#,b,c6,"
        "p,e,e6,d#6,e6,d#6,e6,b,d6,c6,a,p,c,e,a,b,p,e,c6,b,a"
    ),

    # ── Fun / Novelty ─────────────────────────────────────────────────────
    "Nokia Tune": (
        "NokiaTune:d=4,o=5,b=225:"
        "8e6,8d6,f#5,g#5,8c#6,8b5,d5,e5,8b5,8a5,c#5,e5,a5"
    ),

    "Muppets": (
        "Muppets:d=4,o=5,b=250:"
        "c6,c6,a,b,8a,b,g,p,c6,c6,a,8b,8a,8p,g.,p,"
        "e,e,g,f,8e,f,8c6,8c,8d,e,8e,8e,8p,8e,g,2p,"
        "c6,c6,a,b,8a,b,g,p,c6,c6,a,8b,a,g.,p,"
        "e,e,g,f,8e,f,8c6,8c,8d,e,8e,d,8d,c"
    ),

    "Peanuts": (
        "peanuts:d=4,o=5,b=160:"
        "f,8g,a,8a,8g,f,2g,f,p,"
        "f,8g,a,1a,2p,"
        "f,8g,a,8a,8g,f,2g,2f,2f,8g,1g"
    ),

    "Halloween": (
        "Halloween:d=4,o=5,b=180:"
        "8d6,8g,8g,8d6,8g,8g,8d6,8g,8d#6,8g,"
        "8d6,8g,8g,8d6,8g,8g,8d6,8g,8d#6,8g,"
        "8c#6,8f#,8f#,8c#6,8f#,8f#,8c#6,8f#,8d6,8f#,"
        "8c#6,8f#,8f#,8c#6,8f#,8f#,8c#6,8f#,8d6,8f#"
    ),

    "Axel F": (
        "axelf:d=4,o=5,b=160:"
        "f#,8a.,8f#,16f#,8a#,8f#,8e,"
        "f#,8c.6,8f#,16f#,8d6,8c#6,8a,8f#,8c#6,"
        "8f#6,16f#,8e,16e,8c#,8g#,f#."
    ),

    "Happy Birthday": (
        "HappyBirthday:d=4,o=5,b=125:"
        "8d.,8d,e,d,g,2f#,"
        "8d.,8d,e,d,a,2g,"
        "8d.,8d,d6,b,g,f#,2e,"
        "8c6.,8c6,b,g,a,2g"
    ),
}

# Sorted list exposed to the web UI
SONG_NAMES: list[str] = sorted(SONGS.keys())


# ── RTTTL parser ─────────────────────────────────────────────────────────────

def _parse_rtttl(rtttl: str) -> list[tuple[int, float]]:
    """
    Parse RTTTL string → list of (freq_hz, dur_sec).
    freq_hz == 0 means a rest/pause.
    """
    rtttl = rtttl.strip()
    try:
        _name, defaults_str, notes_str = rtttl.split(":", 2)
    except ValueError:
        raise ValueError(f"Bad RTTTL (need 2 colons): {rtttl[:60]}")

    # Defaults
    defaults: dict[str, int] = {}
    for item in defaults_str.split(","):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            try:
                defaults[k.strip()] = int(v.strip())
            except ValueError:
                pass

    default_dur = defaults.get("d", 4)
    default_oct = defaults.get("o", 6)
    bpm         = defaults.get("b", 63)
    whole_sec   = 240.0 / bpm   # 60s/beat * 4 beats/whole

    result: list[tuple[int, float]] = []

    for raw in notes_str.split(","):
        token = raw.strip().lower()
        if not token:
            continue

        dotted = "." in token
        token  = token.replace(".", "")

        # Leading digits → duration divisor
        i, dur_str = 0, ""
        while i < len(token) and token[i].isdigit():
            dur_str += token[i]; i += 1
        dur_div = int(dur_str) if dur_str else default_dur

        # Note name (letters, may include #)
        note = ""
        while i < len(token) and not token[i].isdigit():
            note += token[i]; i += 1

        # Optional explicit octave
        oct_str = token[i:]
        octave  = int(oct_str) if oct_str.isdigit() else default_oct

        dur_sec = (whole_sec / dur_div) * (1.5 if dotted else 1.0)

        if not note or note == "p":
            freq = 0
        else:
            freq = NOTE_FREQ.get(f"{note}{octave}", 0)
            if freq == 0:
                # Graceful octave fallback (handles rare out-of-range notes)
                freq = (NOTE_FREQ.get(f"{note}{octave+1}", 0) or
                        NOTE_FREQ.get(f"{note}{octave-1}", 0))

        result.append((freq, dur_sec))

    return result


# ── Player ───────────────────────────────────────────────────────────────────

_GAP  = 0.10    # silence between notes as fraction of note duration
_TICK = 0.005   # sleep resolution for fast interruption


def _sleep(secs: float, stop: threading.Event) -> bool:
    """Sleep up to `secs`; return True if stop_event fired early."""
    end = time.monotonic() + secs
    while not stop.is_set():
        rem = end - time.monotonic()
        if rem <= 0:
            return False
        time.sleep(min(_TICK, rem))
    return True


def play_rtttl(
    rtttl: str,
    pwm,
    stop_event: threading.Event,
    loop: bool = True,
) -> None:
    """
    Play RTTTL on a GPIO.PWM instance until stop_event is set.

    Args:
        rtttl:      RTTTL string from SONGS dict
        pwm:        RPi.GPIO.PWM instance (not yet started)
        stop_event: set this to stop playback immediately
        loop:       repeat song from start when it ends
    """
    try:
        notes = _parse_rtttl(rtttl)
    except Exception as e:
        print(f"[songs] parse error: {e}")
        return

    if not notes:
        return

    while not stop_event.is_set():
        for freq, dur in notes:
            if stop_event.is_set():
                break

            gap      = dur * _GAP
            note_dur = max(0.0, dur - gap)

            if freq > 0:
                try:
                    pwm.ChangeFrequency(freq)
                    pwm.start(50)
                    if _sleep(note_dur, stop_event):
                        break
                    pwm.stop()
                except Exception:
                    pass
            else:
                if _sleep(dur, stop_event):
                    break

            if gap > 0 and not stop_event.is_set():
                _sleep(gap, stop_event)

        if not loop:
            break

    try:
        pwm.stop()
    except Exception:
        pass


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import RPi.GPIO as GPIO   # noqa: only needed when running standalone

    BUZZER_PIN = 26

    if "--list" in sys.argv:
        print("Available songs:")
        for name in SONG_NAMES:
            print(f"  {name}")
        sys.exit(0)

    song_name = sys.argv[1] if len(sys.argv) > 1 else "Super Mario"

    if song_name not in SONGS:
        print(f"Unknown song: '{song_name}'")
        print("Run  python songs.py --list  to see all songs.")
        sys.exit(1)

    print(f"Playing: {song_name}   (Ctrl+C to stop, plays once)")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    pwm  = GPIO.PWM(BUZZER_PIN, 440)
    stop = threading.Event()

    try:
        play_rtttl(SONGS[song_name], pwm, stop, loop=False)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        try:
            pwm.stop()
        except Exception:
            pass
        GPIO.cleanup()
        print("Done.")
