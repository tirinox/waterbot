import time

import uasyncio as asyncio
from machine import Pin, PWM

from .const import BUZZER_PIN, BUZZER_ON_DUTY

# Set up buzzer on GPIO BUZZER_PIN
buzzer = PWM(Pin(BUZZER_PIN))


# Function to play one tone
def play_tone(freq, duration):
    if freq == 0:
        buzzer.duty(0)  # Silence
    else:
        buzzer.freq(freq)
        buzzer.duty(BUZZER_ON_DUTY)  # 50% duty
    time.sleep(duration)
    buzzer.duty(0)  # Turn off after playing
    time.sleep(0.05)  # Short pause between notes


NOTES = {
    # Octave 3
    'C3': 130, 'C#3': 138, 'Db3': 138,
    'D3': 146, 'D#3': 155, 'Eb3': 155,
    'E3': 164,
    'F3': 174, 'F#3': 185, 'Gb3': 185,
    'G3': 196, 'G#3': 207, 'Ab3': 207,
    'A3': 220, 'A#3': 233, 'Bb3': 233,
    'B3': 246,

    # Octave 4 (Middle C = C4)
    'C4': 261, 'C#4': 277, 'Db4': 277,
    'D4': 293, 'D#4': 311, 'Eb4': 311,
    'E4': 329,
    'F4': 349, 'F#4': 370, 'Gb4': 370,
    'G4': 392, 'G#4': 415, 'Ab4': 415,
    'A4': 440, 'A#4': 466, 'Bb4': 466,
    'B4': 493,

    # Octave 5
    'C5': 523, 'C#5': 554, 'Db5': 554,
    'D5': 587, 'D#5': 622, 'Eb5': 622,
    'E5': 659,
    'F5': 698, 'F#5': 740, 'Gb5': 740,
    'G5': 784, 'G#5': 831, 'Ab5': 831,
    'A5': 880, 'A#5': 932, 'Bb5': 932,
    'B5': 987,

    # Rest
    'R': 0
}

DURATIONS = {
    'w': 4.0,  # Whole not-e
    'h': 2.0,  # Half not-e
    'q': 1.0,  # Quarter not-e
    'e': 0.5,  # Eighth not-e
    's': 0.25,  # Sixteenth not-e
    'hq': 3.0,  # Dotted half
    'qe': 1.5,  # Dotted quarter
    'ee': 0.75,  # Dotted eighth
}


def duration_to_seconds(symbol, bpm):
    beats = DURATIONS.get(symbol.upper(), 1.0)
    return (60.0 / bpm) * beats


# Parse "NOTE-DURATION" string into list
def parse_melody_string(melody_str):
    parts = melody_str.strip().split()
    result = []
    for part in parts:
        if '-' not in part:
            continue
        note, dur = part.split('-')
        result.append((note.strip().upper(), dur.strip().upper()))
    return result


def play_melody_string(melody_str, bpm=120):
    sequence = parse_melody_string(melody_str)
    for note_name, dur_symbol in sequence:
        freq = NOTES.get(note_name, 0)
        duration = duration_to_seconds(dur_symbol, bpm)
        play_tone(freq, duration)


async def a_play_tone(freq, duration):
    if freq == 0:
        buzzer.duty(0)
    else:
        buzzer.freq(freq)
        buzzer.duty(BUZZER_ON_DUTY)
    await asyncio.sleep(duration)
    buzzer.duty(0)
    await asyncio.sleep(0.05)


# Async melody player
async def a_play_melody_string(melody_str, bpm=120):
    sequence = parse_melody_string(melody_str)
    for note_name, dur_symbol in sequence:
        freq = NOTES.get(note_name, 0)
        duration = duration_to_seconds(dur_symbol, bpm)
        await a_play_tone(freq, duration)


GRASSHOPPER_MELODY = """
C4-Q C4-Q E4-Q G4-Q
G4-Q E4-Q G4-H
E4-Q F4-Q G4-Q A4-Q
A4-Q G4-Q F4-H
"""
