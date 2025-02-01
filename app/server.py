import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.interviewer import *
from app.analyzer import *
from app.utils import *
from app.prompts import evaluate_code
import asyncio
import logging
import json
import websockets
import re
import random
from dotenv import load_dotenv
# from google.cloud import speech
# from google.oauth2 import service_account
# import queue
# import base64
# from pydub import AudioSegment

load_dotenv()



# # Audio recording parameters
# RATE = 48000
# CHUNK = int(RATE / 10)  # 100ms

# class AudioStream:
#     """Handles audio stream from websocket and prepares it for speech recognition."""
    
#     def __init__(self, rate=RATE, chunk=CHUNK):
#         self._rate = rate
#         self._chunk = chunk
#         self._buff = queue.Queue()
#         self.closed = True

#     def __enter__(self):
#         self.closed = False
#         return self

#     def __exit__(self, type, value, traceback):
#         """Closes the stream."""
#         self.closed = True
#         self._buff.put(None)

#     def add_data(self, data):
#         """Add audio data to the buffer."""
#         self._buff.put(data)

#     def generator(self):
#         """Generates audio chunks from the stream of audio data."""
#         while not self.closed:
#             chunk = self._buff.get()
#             if chunk is None:
#                 return
#             data = [chunk]

#             # Consume buffered data
#             while True:
#                 try:
#                     chunk = self._buff.get(block=False)
#                     if chunk is None:
#                         return
#                     data.append(chunk)
#                 except queue.Empty:
#                     break

#             yield b"".join(data)


# def listen_print_loop(responses):
#     """Process speech recognition responses and return transcribed text."""
#     transcript = ""
#     num_chars_printed = 0
    
#     for response in responses:
#         if not response.results:
#             continue

#         result = response.results[0]
#         if not result.alternatives:
#             continue

#         transcript = result.alternatives[0].transcript
#         overwrite_chars = " " * (num_chars_printed - len(transcript))

#         if not result.is_final:
#             print(transcript + overwrite_chars + "\r", end="", flush=True)
#             num_chars_printed = len(transcript)
#         else:
#             print(transcript + overwrite_chars)
#             if re.search(r"\b(exit|quit)\b", transcript, re.I):
#                 print("Exiting..")
#                 return transcript
#             num_chars_printed = 0

#     return transcript

# async def process_audio(client, audio_data, content_type):
#     """Process audio with proper configuration based on content type."""
#     try:
#         # Decode base64 audio data
#         audio_content = base64.b64decode(audio_data)
#         print("decoding the audio data ....")
#         # Configure recognition based on content type
#         if 'webm' in content_type.lower():

#             print("configuring the recognition based on content type....")

#             config = speech.RecognitionConfig(
#                 encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
#                 sample_rate_hertz=48000,  # WebM typically uses 48kHz
#                 language_code="en-US",
#                 enable_automatic_punctuation=True,
#                 audio_channel_count=1,  # Mono audio
#             )
#         else:
#             raise ValueError(f"Unsupported content type: {content_type}")

#         # Create recognition audio input
#         print("creating recognition audio input....")
#         audio = speech.RecognitionAudio(content=audio_content)
        
#         # Perform synchronous recognition
#         print("debugg   123344")
#         response = client.recognize(config=config, audio=audio)
#         print("response from google api--> ",response.results)
#         # Process results
#         transcript = ""
#         for result in response.results:
#             transcript += result.alternatives[0].transcript
        
#         return transcript

#     except Exception as e:
#         print(f"Error processing audio: {str(e)}")
#         raise

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
app = FastAPI()
genai.configure(api_key=GOOGLE_API_KEY)
@app.get('/')
async def root():
    return {"data":"HELLO WORLD"}
logging.basicConfig(level=logging.INFO)
# State management
class InterviewState:
    def __init__(self):
        self.cv_text = ""
        self.job_description = ""
        self.interview_bot = None
        self.results = {"INTRODUCTION":{},"PROJECT":{},"CODING":{},"TECHNICAL":{},"OUTRO":{}}
        self.stop_interview = asyncio.Event()



# # WebSocket endpoint
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     state = InterviewState()
#     llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)

#     async def handle_interview():
#         if state.interview_bot:
#             try:
#                 await state.interview_bot.conduct_interview(websocket)
#             except asyncio.CancelledError:
#                 logging.info("Interview task cancelled")
#             except Exception as e:
#                 logging.error(f"Error during interview: {e}")
#             finally:
#                 state.interview_bot = None

#     try:
#         while True:
#             data = await websocket.receive_json()
#             logging.info(f"Received data: {data}")
#             await handle_event(data, websocket, state, llm, handle_interview)

#     except WebSocketDisconnect:
#         logging.info("WebSocket disconnected")
#     except Exception as e:
#         logging.error(f"Unexpected error: {e}")
#     finally:
#         if state.interview_bot:
#             state.interview_bot.stop_interview.set()
#             state.interview_bot = None

async def handle_event(data, websocket, state, llm, handle_interview):
    if data['type'] == 'upload_cv':
        await handle_upload_cv(data, websocket, state)
    elif data['type'] == 'analyze_jd':
        await handle_analyze_jd(data, websocket, state)
    elif data['type'] == 'start_interview':
        await handle_start_interview(websocket, state, handle_interview)
    elif data['type'] == 'answer':
        await handle_answer(data, state)
    elif data['type'] == 'coding':
        await handle_coding(data, websocket, state, llm)
    elif data['type'] == 'end_interview':
        await handle_end_interview(websocket, state)
    elif data['type'] == 'get_analysis':
        await handle_get_analysis(websocket, state, llm)
    elif data['type'] == 'get_summary_analysis':
        await handle_summary_analysis(websocket, state, llm)
    elif data['type'] == 'test_coding_question':
        try:
            print("CODING INTERVIEW IS HERE")
            q1 = random.choice(["Q1. Print Hello World", "Q2. Print Hello Anish", "Q3. Print Hello Duniya"])
            await websocket.send_json({'type': 'test_coding_question', 'message': q1})
            #await asyncio.wait_for(self.coding_event.wait(), timeout=1000)  # 5-minute timeout
            #self.coding_event.clear()
        except asyncio.TimeoutError:
            await websocket.send_json({'type': 'coding_timeout', 'message': 'Coding question timed out'})
        except Exception as e:
            await websocket.send_json({'type': 'coding_error', 'message': f'Error in coding stage: {str(e)}'})
    elif data['type']=='HELLO':
        await websocket.send_json({'type': 'greeting_from_ws', 'message': 'Client connected successfully'})

# async def handle_speech_to_text(data,websocket):
#     try:
#             try:
#                 # Initialize speech client and configs
#                 credentials_path ='C:\\VsCode\\yuhi\\speech_to_text\\credential.json'
#                 credentials = service_account.Credentials.from_service_account_file(
#                     credentials_path,
#                     scopes=["https://www.googleapis.com/auth/cloud-platform"]
#                 )
#                 client = speech.SpeechClient(credentials=credentials)
#                 print("WebSocket connection established")
        
#                 while True:
#                     try:
#                         # Wait for a message using standard websockets receive
#                         # message = await websocket.receive()                        
#                         # Try to parse as JSON
#                         try:
#                             if isinstance(data, str):
#                                 data = json.loads(data)  # Convert JSON string to a dictionary
#                                 print("Data successfully parsed into a dictionary.")
                            
#                             print(f"Received message type: {data.get('type')}")
                            
#                             audio_data = data.get('audioData')   
#                             print("audio data received....",audio_data)                          
#                             content_type = data.get('contentType')
                                
#                             if audio_data:
#                                     print(f"Processing audio with content type: {content_type}")
#                                     # Process the audio
#                                     transcript = await process_audio(client, audio_data, content_type)
                                    
#                                     print(f"Transcripted text : {transcript}")
#                                     # Send result back to client
#                                     response = json.dumps({
#                                         'type': 'transcription_result',
#                                         'result': transcript,
#                                         'status': 'success'
#                                     })
#                                     await websocket.send(response)
#                             else:
#                                     await websocket.send(json.dumps({
#                                         'type': 'error',
#                                         'message': 'No audio data received'
#                                     }))    
                            
                                
#                         except json.JSONDecodeError as e:
#                             print(f"Failed to parse message as JSON: {str(e)}")
#                             await websocket.send(json.dumps({
#                                 'type': 'error',
#                                 'message': 'Invalid JSON message received'
#                             }))
                        
#                     except Exception as e:
#                         print(f"Processing error: {str(e)}")
#                         await websocket.send(json.dumps({
#                             'type': 'error',
#                             'message': f'Error processing audio: {str(e)}'
#                         }))

#             except websockets.exceptions.ConnectionClosed:
#                 print("WebSocket connection closed")
#             except Exception as e:
#                 print(f"Error: {str(e)}")
#                 try:
#                     await websocket.send(json.dumps({
#                         'type': 'error',
#                         'message': str(e)
#                     }))
#                 except:
#                     pass
#         # elif data['action']=="stop":
#         #     pass
#     except Exception as e:
#         await websocket.send_json({'type': 'speech_to_text_error', 'message': f'Error in speech to text: {str(e)}'})


async def handle_summary_analysis(websocket, state, llm):
    analyzed_result = summary_results(state.results, llm)
    await websocket.send_json({"type": "analysis", "result": analyzed_result})


# Handlers for specific events
async def handle_upload_cv(data, websocket, state):
    print("UPLOADING CV")
    state.cv_text = await get_cv(data, websocket)
    await websocket.send_json({'type': 'cv_uploaded', 'message': 'CV data received', 'cv_text': state.cv_text})
    return
async def handle_analyze_jd(data, websocket, state):
    state.job_description = await get_job_description(data, websocket)
    await websocket.send_json({'type': 'jd_analyzed', 'message': "Received JD Successfully", 'job_description': state.job_description})

async def handle_start_interview(websocket, state, handle_interview):
    if not state.interview_bot:
        state.interview_bot = InterviewBot(state.cv_text, state.job_description, state.results)
        asyncio.create_task(handle_interview())
        await websocket.send_json({"type": "interview_started", "message": "Interview started"})

async def handle_answer(data, state):
    if state.interview_bot:
        state.interview_bot.current_answer = data['answer']
        state.interview_bot.answer_event.set()

async def handle_coding(data, websocket, state, llm):
    try:
        if state.interview_bot:
            resp = ""
            # Simulate the coding session
            code = data.get("code")
            ques = data.get("ques")
            print(code,ques)
            if code:
                print(code,ques)
                resp = evaluate_code(llm,ques,code)
                print(code,ques)
                print(resp)
                await websocket.send_json({"type": "code_evaluation", "result": resp})
                if resp:
                    if resp["RESULT"]==True:
                        state.interview_bot.coding_event.set()
    except Exception as e:
        await websocket.send_json({"type": "code_evaluation", "result": resp})
        print(e)

async def handle_end_interview(websocket, state):
    if state.interview_bot:
        state.interview_bot.stop_interview.set()
        await asyncio.sleep(0.1)  # Allow time for interview task to react
        state.interview_bot.stop_interview.clear()
        await websocket.send_json({"type": "interview_end", "message": "Interview ended"})
    logging.info("Interview concluded")


async def handle_get_analysis(websocket, state, llm):
    analyzed_result = analyze_results(state.results, llm)
    await websocket.send_json({"type": "analysis", "result": analyzed_result})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        cv_text = ""
        job_description = ""
        interview_bot = None
        results = {}
        stop_interview = asyncio.Event()
        llm= ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
        async def handle_interview():
            nonlocal interview_bot
            try:
                await interview_bot.conduct_interview(websocket)
            except asyncio.CancelledError:
                print("Interview task cancelled")
            finally:
                interview_bot = None

        while True:
            data = await websocket.receive_json()
            if data['type'] == 'upload_cv':
                cv_text = await get_cv(data, websocket)  
            elif data['type'] == 'analyze_jd':
                job_description = await get_job_description(data, websocket)
            elif data['type'] == 'start_interview':
                if not interview_bot:
                    interview_bot = InterviewBot(cv_text, job_description, results)
                    asyncio.create_task(handle_interview())
            elif data['type'] == 'answer':
                if interview_bot:
                    interview_bot.current_answer = data['answer']
                    interview_bot.answer_event.set()
            elif data['type'] == 'coding':
                if interview_bot:
                    interview_bot.coding_event.set()
            elif data['type'] == 'end_interview':
                if interview_bot:
                    interview_bot.stop_interview.set()
                    await asyncio.sleep(0.1)  # Give a moment for the interview task to react
                    interview_bot.stop_interview.clear()
                print("Interview Concluded")
            elif data['type'] == 'get_analysis':
                analyzed_result = analyze_results(results,llm)
                await websocket.send_json({"type": "analysis", "result": analyzed_result})
    except WebSocketDisconnect:
        print("WebSocket disconnected")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app,port=8000)