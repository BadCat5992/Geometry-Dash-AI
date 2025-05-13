import json
import random
import time
import threading
import cv2
import numpy as np
from PIL import ImageGrab
from pynput import keyboard
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Live-Status-Infos für Web-GUI
live_status = {
    "run": 0,
    "distance": 0,
    "max_distance": 0,
    "current_actions": 0,
    "status": "Waiting..."
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Geometry Dash AI</title>
    <meta http-equiv="refresh" content="1">
    <style>
        body { font-family: sans-serif; background: #111; color: #0f0; text-align: center; padding-top: 50px; }
        h1 { color: #0ff; }
        .box { border: 2px solid #0f0; border-radius: 10px; padding: 20px; display: inline-block; }
    </style>
</head>
<body>
    <h1>Geometry Dash AI Web UI</h1>
    <div class="box">
        <p><b>Versuch:</b> {{ run }}</p>
        <p><b>Distanz:</b> {{ distance }}</p>
        <p><b>Rekord:</b> {{ max_distance }}</p>
        <p><b>Aktionen:</b> {{ current_actions }}</p>
        <p><b>Status:</b> {{ status }}</p>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, **live_status)

class GeometryDashAI:
    def __init__(self, death_template_path):
        self.base_actions = []
        self.current_actions = []
        self.max_distance = 0
        self.current_distance = 0
        self.run_count = 0
        self.template_threshold = 0.8
        self.running = True
        self.base_iteration = 0

        self.death_template = cv2.imread(death_template_path, 0)
        if self.death_template is None:
            raise ValueError("Konnte Template nicht laden")

        self.keyboard = keyboard.Controller()

        self.load_progress()

    def load_progress(self):
        try:
            with open('gd_progress.json', 'r') as f:
                data = json.load(f)
                self.base_actions = data.get('base_actions', [])
                self.max_distance = data.get('max_distance', 0)
                self.base_iteration = data.get('base_iteration', 0)
                print(f"Geladener Fortschritt: Basis-Länge {len(self.base_actions)}, Rekord: {self.max_distance}")
        except:
            pass

    def save_progress(self):
        data = {
            'base_actions': self.base_actions,
            'max_distance': self.max_distance,
            'base_iteration': self.base_iteration
        }
        with open('gd_progress.json', 'w') as f:
            json.dump(data, f)

    def jump(self):
        self.keyboard.press(keyboard.Key.space)
        time.sleep(0.05)
        self.keyboard.release(keyboard.Key.space)
        self.current_actions.append(self.current_distance)

    def is_player_alive(self):
        try:
            screenshot = np.array(ImageGrab.grab())
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(gray, self.death_template, cv2.TM_CCOEFF_NORMED)
            return np.max(res) < self.template_threshold
        except Exception as e:
            print(f"Fehler bei Bilderkennung: {e}")
            return True

    def create_variation(self):
        if not self.base_actions:
            return []

        variation = self.base_actions.copy()
        if len(variation) >= 3:
            last_jump_pos = variation[-3]
            variation = variation[:-3]
            for i in range(3):
                variation.append(last_jump_pos + random.randint(-4, 4))
        return variation

    def countdown(self, seconds):
        print(f"\nStart in {seconds} Sekunden... Wechsle zu Geometry Dash!")
        for i in range(seconds, 0, -1):
            print(f"{i}...", end=' ', flush=True)
            time.sleep(1)
        print("\nKI läuft! Drücke ESC zum Beenden")

    def run(self):
        self.countdown(5)

        def on_press(key):
            if key == keyboard.Key.esc:
                self.running = False
                return False

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        while self.running:
            self.current_distance = 0
            self.current_actions = []
            planned_actions = self.create_variation()

            while self.is_player_alive() and self.running:
                self.current_distance += 1

                if self.current_distance in planned_actions:
                    self.jump()
                elif not self.base_actions and random.random() < 0.25:
                    self.jump()

                # Update Web-Dashboard
                live_status.update({
                    "run": self.run_count,
                    "distance": self.current_distance,
                    "max_distance": self.max_distance,
                    "current_actions": len(self.current_actions),
                    "status": "Alive"
                })

                time.sleep(0.008)

            self.run_count += 1
            live_status["status"] = "Gestorben"

            if self.current_distance > self.max_distance * 1.1:
                self.max_distance = self.current_distance
                self.base_actions = self.current_actions.copy()
                self.base_iteration += 1
                print(f"\n🔥 NEUE BASIS (Iteration {self.base_iteration}) 🔥")
                print(f"Länge: {len(self.base_actions)} | Rekord: {self.max_distance}")
                self.save_progress()

            print(f"\nVersuch {self.run_count}:")
            print(f"- Erreicht: {self.current_distance} | Beste: {self.max_distance}")
            print(f"- Basis-Länge: {len(self.base_actions)}")
            print(f"- Aktionsanzahl: {len(self.current_actions)}")

            if self.running:
                time.sleep(0.8)

        listener.stop()
        print("\nTraining beendet.")

# Starte Flask-Webserver im Hintergrund
def start_web_server():
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    threading.Thread(target=start_web_server, daemon=True).start()
    ai = GeometryDashAI("death_template.png")
    ai.run()

