import os
import sys
import asyncio
from dotenv import load_dotenv
from interviewer import *
from flask import Flask
from flask_socketio import SocketIO, emit
import threading
import io
from waitress import serve
from PyPDF2 import PdfReader
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

pdf_text = ""
job_description = ""

@socketio.on('upload_cv')
def handle_cv_upload(data):
    cv_data = data['cv_data']
    # Convert the binary file data to an in-memory file-like object
    pdf_file = io.BytesIO(bytearray(cv_data))

    # Extract text from the in-memory PDF
    reader = PdfReader(pdf_file)
    pdf_text = ""
    for page in reader.pages:
        pdf_text += page.extract_text()
    print(pdf_text)
    emit('cv_uploaded', {'message': 'CV data received', 'cv_text':pdf_text})


@socketio.on('analyze_jd')
def handle_jd_analysis(data):
    job_description = data['job_description']
    print(job_description)
    emit('jd_analyzed', {'message': "Receive JD Successfully","job_description":job_description})

@socketio.on('start_interview')
def start_interview(data):
    results = {}
    print("PDF- ", data['pdf_text'])
    print("data- ", data['job_description'])
    interview_bot = InterviewBot(data['pdf_text'],data['job_description'], results)
    interview_bot.conduct_interview()

if __name__ == "__main__":
    socketio.run(app, debug=True)
    