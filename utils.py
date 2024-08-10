# import pyaudio
# import threading
# import speech_recognition as sr
# import time
import os
from dotenv import load_dotenv
# from gtts import gTTS
# from io import BytesIO
# from pydub import AudioSegment
# from pydub.playback import play
# import queue
from PyPDF2 import PdfReader
load_dotenv()
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import WebSocket
import io
from PyPDF2 import PdfReader

async def get_cv(data,websocket:WebSocket):
    pdf_file = io.BytesIO(bytearray(data['cv_data']))
    reader = PdfReader(pdf_file)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text()
    print(pdf_text)
    await websocket.send_json({'type': 'cv_uploaded', 'message': 'CV data received', 'cv_text': pdf_text})
    return pdf_text

async def get_job_description(data,websocket:WebSocket):
    job_description = data['job_description']
    print(job_description)
    await websocket.send_json({'type': 'jd_analyzed', 'message': "Received JD Successfully", 'job_description': job_description})
    return job_description

def read_cv(cv_path):
    with open(cv_path, 'rb') as file:
        reader = PdfReader(file)
        return ' '.join(page.extract_text() for page in reader.pages)
    
import json

def save_analysis_results(results):
    with open('interview_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Analysis results saved to 'interview_analysis.json'")




# # Constants
# CHUNK = 1024
# FORMAT = pyaudio.paInt16
# CHANNELS = 1
# RATE = 16000
# RECORD_SECONDS = 5
# SLEEP_COMMAND = "sleep"
# QUIT_COMMAND = "quit"

# API_KEY = os.getenv("GOOGLE_API_KEY")

# def play_audio(text, lang="hi"):
#     mp3_fp = BytesIO()
#     tts = gTTS(text, lang=lang)
#     tts.write_to_fp(mp3_fp)
#     mp3_fp.seek(0)
#     audio = AudioSegment.from_mp3(mp3_fp)
#     play(audio)

# class AudioTranscriber:
#     def __init__(self):
#         self.recognizer = sr.Recognizer()
#         self.audio_queue = queue.Queue()
#         self.is_recording = True
#         self.transcription = ""
#         self.is_exiting = False
#         self.silence_count = 0
#         self.max_silence_count = 1

#     def transcribe_audio(self):
#         while True:
#             audio = self.audio_queue.get()
#             if audio is None:
#                 break
#             try:
#                 text = self.recognizer.recognize_google(audio)
#                 self.transcription += text + " "
#                 print(text, end=" ")
#                 self.silence_count = 0
#                 if SLEEP_COMMAND in text.lower():
#                     self.is_recording = False
#                 elif QUIT_COMMAND in text.lower():
#                     self.is_recording = False
#                     self.is_exiting = True
#                     print("Thank you for your response.")
#                     return
#             except sr.UnknownValueError:
#                 self.silence_count += 1
#                 if self.silence_count >= self.max_silence_count:
#                     self.is_recording = False
#             except sr.RequestError as e:
#                 print(f"Could not request results from Google Speech Recognition service; {e}")

#     def record_audio(self):
#         p = pyaudio.PyAudio()
#         stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

#         print("Recording Started...")
#         while self.is_recording:
#             frames = []
#             for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
#                 data = stream.read(CHUNK)
#                 frames.append(data)

#             audio_data = sr.AudioData(b''.join(frames), RATE, 2)
#             self.audio_queue.put(audio_data)

#         stream.stop_stream()
#         stream.close()
#         p.terminate()
#         self.audio_queue.put(None)

#     def run(self):
#         transcription_thread = threading.Thread(target=self.transcribe_audio)
#         recording_thread = threading.Thread(target=self.record_audio)
        
#         transcription_thread.start()
#         recording_thread.start()

#         while self.is_recording:
#             time.sleep(0.1)

#         recording_thread.join()
#         transcription_thread.join()
#         print("\nRecording Stopped...")
#         return self.transcription if self.transcription else None


