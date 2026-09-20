import tkinter as tk
from tkinter import scrolledtext
import threading
import time
speaking = False
import subprocess
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import ollama
import os
import webbrowser
import urllib.parse
import openwakeword
from openwakeword.model import Model
import numpy as np
import queue
import time



# =========================
# ARU VOICE
# =========================

VOICE_MODEL = "en_US-lessac-medium"


def speak(text):
    global speaking

    try:
        speaking = True
        update_status("🔊 Speaking...")

        wav_file = "aru_voice.wav"

        subprocess.run(
            [
                "python",
                "-m",
                "piper",
                "-m",
                VOICE_MODEL,
                "-f",
                wav_file
            ],
            input=text,
            text=True,
            check=True
        )

        audio, sample_rate = sf.read(wav_file)

        sd.play(audio, sample_rate)
        sd.wait()

        if os.path.exists(wav_file):
            os.remove(wav_file)

    except Exception as e:
        print("Voice Error:", repr(e))

    finally:
        speaking = False
        update_status("🎤 Listening...")


# =========================
# ARU AI
# =========================

def ask_ai(question):
    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Aru, a friendly female desktop AI assistant. "
                        "Speak naturally and briefly. "
                        "Use simple English or Hinglish depending on the user. "
                        "Be warm, helpful and casual."
                    )
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        return response["message"]["content"]

    except Exception as e:
        print("AI Error:", repr(e))
        return "Sorry, my local AI brain is not responding right now."


# =========================
# MICROPHONE
# =========================

def listen():

    try:
        duration = 5
        sample_rate = 16000
        filename = "aru_mic.wav"

        update_status("🎤 Listening... Speak now")

        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32"
        )

        sd.wait()

        sf.write(filename, audio, sample_rate)

        recognizer = sr.Recognizer()

        with sr.AudioFile(filename) as source:
            recorded_audio = recognizer.record(source)

        update_status("🔄 Understanding...")

        text = recognizer.recognize_google(recorded_audio)

        if os.path.exists(filename):
            os.remove(filename)

        return text

    except sr.UnknownValueError:
        return ""

    except Exception as e:
        print("Microphone Error:", repr(e))
        return ""
    
def continuous_listening():
    while True:
        try:
            if speaking:
                continue

            duration = 5
            sample_rate = 16000
            filename = "aru_mic.wav"

            update_status("🎤 Listening...")

            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32"
            )

            sd.wait()

            sf.write(filename, audio, sample_rate)

            recognizer = sr.Recognizer()

            with sr.AudioFile(filename) as source:
                recorded_audio = recognizer.record(source)

            if os.path.exists(filename):
                os.remove(filename)

            try:
                text = recognizer.recognize_google(recorded_audio)

                if not text.strip():
                    continue

                # Wake word check
                words = text.strip().lower().split()

                if not words or words[0] != "aru":
                    update_status("🎤 Listening...")
                    continue

                # Remove "Aru"
                command = text.strip()[3:].strip()

                if command:
                    process_message(command)

            except sr.UnknownValueError:
                continue

        except Exception as e:
            print("Listening Error:", repr(e))

            if os.path.exists(filename):
                os.remove(filename)

            update_status("🎤 Ready")

# =========================
# MESSAGE PROCESSING
# =========================

def understand_command(text):
    command_prompt = f"""
You are Aru's command parser.

Understand the user's English or Hinglish command.

Return ONLY one of these formats:

OPEN_YOUTUBE
OPEN_GOOGLE
SEARCH_YOUTUBE: query
SEARCH_GOOGLE: query
OPEN_APP: app_name
CHAT

Rules:
- "open YouTube", "YouTube kholo", "YouTube open karo" → OPEN_YOUTUBE
- "open Google", "Google kholo", "Google open karo" → OPEN_GOOGLE
- Normal conversation → CHAT

User command:
{text}
"""

    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "user",
                    "content": command_prompt
                }
            ]
        )

        return response["message"]["content"].strip()

    except Exception as e:
        print("Command Parser Error:", repr(e))
        return "CHAT"

    
def process_message(text):

    if not text:
        update_status("🎤 Ready")
        return

    command = text.lower()

    action = understand_command(text)
    print("ACTION:", repr(action))
    action = action.strip().upper()
   
   

    if action == "OPEN_YOUTUBE":
        os.startfile("https://www.youtube.com")
        add_message("Aru 🌸", "Opening YouTube...")
        speak("Opening YouTube")
        return

    if action == "OPEN_GOOGLE":
        os.startfile("https://www.google.com")
        add_message("Aru 🌸", "Opening Google...")
        speak("Opening Google")
        return

    if action.startswith("SEARCH_YOUTUBE:"):
        query = action.split(":", 1)[1].strip()

        if query:
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
            os.startfile(url)

            add_message("Aru 🌸", f"Searching YouTube for {query}")
            speak(f"Searching YouTube for {query}")

        return

   

    if action.startswith("SEARCH_GOOGLE:"):
        query = action.split(":", 1)[1].strip()

        if query:
            url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
            os.startfile(url)

            add_message(
                "Aru 🌸",
                f"Searching Google for {query}"
            )

            speak(f"Searching Google for {query}")

        return

    if action.startswith("OPEN_APP:"):
        app = action.split(":", 1)[1].strip().lower()

        apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe"
        }

        if app in apps:
            subprocess.Popen(apps[app])

            add_message(
                "Aru 🌸",
                f"Opening {app}..."
            )

            speak(f"Opening {app}")
        else:
            speak(f"I don't know how to open {app} yet.")

        return

   
    
    add_message("You", text)

    update_status("🧠 Thinking...")

    answer = ask_ai(text)

    add_message("Aru 🌸", answer)

    update_status("🔊 Speaking...")

    speak(answer)

    update_status("🎤 Ready")
   

# =========================
# SEND TEXT
# =========================

def send_message():

    text = entry.get().strip()

    if not text:
        return

    entry.delete(0, tk.END)

    threading.Thread(
        target=process_message,
        args=(text,),
        daemon=True
    ).start()


# =========================
# MICROPHONE BUTTON
# =========================
def wake_word_listener():
    openwakeword.utils.download_models()

    wake_model = Model(wakeword_models=["alexa"])
    audio_queue = queue.Queue()

    print("🎤 Aru is listening for Alexa...")
    
    cooldown_until = 0

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(indata.copy())

    with sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype="int16",
        blocksize=1280,
        callback=audio_callback
    ):
        while True:

            audio = audio_queue.get()
            samples = np.squeeze(audio)

            current_time = time.time()

            # Don't listen while Aru is speaking
            if speaking:
               continue

            # Ignore wake-word detection during cooldown
            if current_time < cooldown_until:
               continue

            prediction = wake_model.predict(samples)
            score = prediction.get("alexa", 0)

            if score > 0.3:

                print("🌸 Wake word detected!")

                # Immediately start cooldown
                cooldown_until = time.time() + 15

                update_status("🗣️ Listening for command...")

                command_audio = []
                start_time = time.time()

                # Collect command audio
                while time.time() - start_time < 3:
                    chunk = audio_queue.get()
                    command_audio.append(chunk.copy())

                if not command_audio:
                    update_status("🎤 Listening...")
                    continue

                audio_data = np.concatenate(
                    command_audio,
                    axis=0
                )

                recognizer = sr.Recognizer()

                recognizer_audio = sr.AudioData(
                    audio_data.tobytes(),
                    16000,
                    2
                )

                try:
                    text = recognizer.recognize_google(
                        recognizer_audio
                    )

                    print("RECOGNIZED:", repr(text))

                    command = text.strip()

                    # Remove Alexa if Google included it
                    if command.lower().startswith("alexa"):
                        command = command[5:].strip()

                    print("📝 Command:", command)

                    if command:
                       print("🚀 PROCESSING COMMAND:", repr(command))
                       process_message(command)

                except sr.UnknownValueError:
                    print("❌ Couldn't understand command")

                except Exception as e:
                    print(
                        "Recognition Error:",
                        repr(e)
                    )

                # Remove old microphone audio
                while not audio_queue.empty():
                    try:
                        audio_queue.get_nowait()
                    except queue.Empty:
                        break

                update_status("🎤 Listening...")


def microphone():
    def voice_thread():
        update_status("🎤 Listening...")

        text = listen()

        if not text:
            update_status("🎤 Ready")
            return

        command = text.strip()
        lower_command = command.lower()
        print("RECOGNIZED:", repr(command))

        # Wake word must be at the beginning
        wake_word = None

        if lower_command.startswith("aru"):
           wake_word = "aru"
        elif lower_command.startswith("are you"):
          wake_word = "are you"
        elif lower_command.startswith("a ru"):
          wake_word = "a ru"
        elif lower_command.startswith("aroo"):
          wake_word = "aroo"

        if wake_word:
           command = command[len(wake_word):].strip()

           if command:
              process_message(command)
           else:
              update_status("🎤 Ready")
        else:
          # Ignore everything without the wake word
          update_status("🎤 Ready")

    threading.Thread(
        target=voice_thread,
        daemon=True
    ).start()

# =========================
# GUI FUNCTIONS
# =========================

def add_message(sender, message):

    def update():

        chat.config(state="normal")

        chat.insert(
            tk.END,
            f"{sender}: {message}\n\n"
        )

        chat.config(state="disabled")
        chat.see(tk.END)

    root.after(0, update)


def update_status(text):

    root.after(
        0,
        lambda: status.config(text=text)
    )


# =========================
# GUI
# =========================

root = tk.Tk()

root.title("Aru 🌸")
root.geometry("650x750")
root.minsize(550, 650)


title = tk.Label(
    root,
    text="🌸 ARU",
    font=("Segoe UI", 30, "bold")
)

title.pack(pady=(25, 2))


subtitle = tk.Label(
    root,
    text="Your friendly AI desktop assistant",
    font=("Segoe UI", 11)
)

subtitle.pack()


status = tk.Label(
    root,
    text="🎤 Ready",
    font=("Segoe UI", 10)
)

status.pack(pady=8)


chat = scrolledtext.ScrolledText(
    root,
    wrap=tk.WORD,
    font=("Segoe UI", 11),
    state="disabled"
)

chat.pack(
    padx=25,
    pady=15,
    fill="both",
    expand=True
)


# =========================
# INPUT
# =========================

input_frame = tk.Frame(root)

input_frame.pack(
    padx=25,
    pady=(0, 25),
    fill="x"
)


entry = tk.Entry(
    input_frame,
    font=("Segoe UI", 12)
)

entry.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=10
)


mic_button = tk.Button(
    input_frame,
    text="🎤",
    font=("Segoe UI", 14),
    command=microphone
)

mic_button.pack(
    side="left",
    padx=8,
    ipadx=8,
    ipady=3
)


send_button = tk.Button(
    input_frame,
    text="Send",
    font=("Segoe UI", 11, "bold"),
    command=send_message
)

send_button.pack(
    side="right",
    ipadx=15,
    ipady=5
)


entry.bind(
    "<Return>",
    lambda event: send_message()
)

entry.focus_set()


# =========================
# START MESSAGE
# =========================

add_message(
    "Aru 🌸",
    "Hi! I'm Aru. You can type or press 🎤 and talk to me."
)

threading.Thread(
    target=wake_word_listener,
    daemon=True
).start()

root.mainloop()

