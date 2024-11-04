import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import random
import asyncio
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from interviewer import InterviewBot
from analyzer import summary_results, analyze_results
from utils import get_cv, get_job_description
from prompts import evaluate_code

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
app = FastAPI()

@app.get('/')
async def root():
    return {"data": "HELLO WORLD"}

logging.basicConfig(level=logging.INFO)

class InterviewState:
    def __init__(self):
        self.cv_text = ""
        self.job_description = ""
        self.interview_bot = None
        self.results = {"INTRODUCTION":{}, "PROJECT":{}, "CODING":{}, "TECHNICAL":{}, "OUTRO":{}}
        self.stop_interview = asyncio.Event()
        self.interview_task = None  # Add this to track the interview task

    async def cleanup(self):
        if self.interview_bot:
            self.interview_bot.stop_interview.set()
            if self.interview_task:
                try:
                    self.interview_task.cancel()
                    await asyncio.wait_for(self.interview_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            self.interview_bot = None
            self.interview_task = None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state = InterviewState()
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, api_key=GOOGLE_API_KEY)

    async def handle_interview():
        if state.interview_bot:
            try:
                await state.interview_bot.conduct_interview(websocket)
            except asyncio.CancelledError:
                logging.info("Interview task cancelled")
            except Exception as e:
                logging.error(f"Error during interview: {e}")
            finally:
                await state.cleanup()

    try:
        while True:
            data = await websocket.receive_json()
            logging.info(f"Received data: {data}")
            await handle_event(data, websocket, state, llm, handle_interview)

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
        await state.cleanup()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await state.cleanup()
    finally:
        await state.cleanup()

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
        await handle_test_coding_question(websocket)

async def handle_start_interview(websocket, state, handle_interview):
    if not state.interview_bot:
        state.interview_bot = InterviewBot(state.cv_text, state.job_description, state.results)
        state.interview_task = asyncio.create_task(handle_interview())
        await websocket.send_json({"type": "interview_started", "message": "Interview started"})

async def handle_end_interview(websocket, state):
    await state.cleanup()
    await websocket.send_json({"type": "interview_end", "message": "Interview ended"})
    logging.info("Interview concluded")

async def handle_test_coding_question(websocket):
    try:
        q1 = random.choice(["Q1. Print Hello World", "Q2. Print Hello Anish", "Q3. Print Hello Duniya"])
        await websocket.send_json({'type': 'test_coding_question', 'message': q1})
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

# async def handle_start_interview(websocket, state, handle_interview):
#     if not state.interview_bot:
#         state.interview_bot = InterviewBot(state.cv_text, state.job_description, state.results)
#         asyncio.create_task(handle_interview())
#         await websocket.send_json({"type": "interview_started", "message": "Interview started"})

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

# async def handle_end_interview(websocket, state):
#     if state.interview_bot:
#         state.interview_bot.stop_interview.set()
#         await asyncio.sleep(0.1)  # Allow time for interview task to react
#         state.interview_bot.stop_interview.clear()
#         await websocket.send_json({"type": "interview_end", "message": "Interview ended"})
#     logging.info("Interview concluded")


async def handle_get_analysis(websocket, state, llm):
    analyzed_result = analyze_results(state.results, llm)
    await websocket.send_json({"type": "analysis", "result": analyzed_result})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,port=8000)