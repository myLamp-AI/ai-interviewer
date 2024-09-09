import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from interviewer import *
from analyzer import *
from utils import *
from prompts import evaluate_code
import asyncio
import logging
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
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



# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state = InterviewState()
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)

    async def handle_interview():
        if state.interview_bot:
            try:
                await state.interview_bot.conduct_interview(websocket)
            except asyncio.CancelledError:
                logging.info("Interview task cancelled")
            except Exception as e:
                logging.error(f"Error during interview: {e}")
            finally:
                state.interview_bot = None

    try:
        while True:
            data = await websocket.receive_json()
            logging.info(f"Received data: {data}")
            await handle_event(data, websocket, state, llm, handle_interview)

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if state.interview_bot:
            state.interview_bot.stop_interview.set()
            state.interview_bot = None

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
        
        

async def handle_summary_analysis(websocket, state, llm):
    analyzed_result = summary_results(state.results, llm)
    await websocket.send_json({"type": "analysis", "result": analyzed_result})

# Handlers for specific events
async def handle_upload_cv(data, websocket, state):
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
                    if resp["RESULT"] == True:
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

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         cv_text = ""
#         job_description = ""
#         interview_bot = None
#         results = {}
#         stop_interview = asyncio.Event()
#         llm= ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
#         async def handle_interview():
#             nonlocal interview_bot
#             try:
#                 await interview_bot.conduct_interview(websocket)
#             except asyncio.CancelledError:
#                 print("Interview task cancelled")
#             finally:
#                 interview_bot = None

#         while True:
#             data = await websocket.receive_json()
#             if data['type'] == 'upload_cv':
#                 cv_text = await get_cv(data, websocket)  
#             elif data['type'] == 'analyze_jd':
#                 job_description = await get_job_description(data, websocket)
#             elif data['type'] == 'start_interview':
#                 if not interview_bot:
#                     interview_bot = InterviewBot(cv_text, job_description, results)
#                     asyncio.create_task(handle_interview())
#             elif data['type'] == 'answer':
#                 if interview_bot:
#                     interview_bot.current_answer = data['answer']
#                     interview_bot.answer_event.set()
#             elif data['type'] == 'coding':
#                 if interview_bot:
#                     interview_bot.coding_event.set()
#             elif data['type'] == 'end_interview':
#                 if interview_bot:
#                     interview_bot.stop_interview.set()
#                     await asyncio.sleep(0.1)  # Give a moment for the interview task to react
#                     interview_bot.stop_interview.clear()
#                 print("Interview Concluded")
#             elif data['type'] == 'get_analysis':
#                 analyzed_result = analyze_results(results,llm)
#                 await websocket.send_json({"type": "analysis", "result": analyzed_result})
#     except WebSocketDisconnect:
#         print("WebSocket disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)