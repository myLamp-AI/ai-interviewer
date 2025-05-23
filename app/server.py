# /app/server.py
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.interviewer import *
from app.analyzer import *
from app.utils import *
from app.prompts import evaluate_code
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import uvicorn
from app.recruiter_socket import sio_app

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the Socket.IO app
app.mount("/recruiter", sio_app)

logging.basicConfig(level=logging.INFO)


@app.get('/')
async def root():
    return {"data": "HELLO WORLD"}


class InterviewState:
    def __init__(self):
        self.cv_text = ""
        self.job_description = ""
        self.interview_bot = None
        self.results = {
            "INTRODUCTION": {"conversation": [], "analysis": {}},
            "PROJECT": {"conversation": [], "analysis": {}},
            "CODING": {"conversation": [], "analysis": {}},
            "TECHNICAL": {"conversation": [], "analysis": {}},
            "OUTRO": {"conversation": [], "analysis": {}}
        }
        self.stop_interview = asyncio.Event()


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state = InterviewState()
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", temperature=0.3)

    async def handle_interview():
        if state.interview_bot:
            try:
                await state.interview_bot.conduct_interview(websocket)
            except asyncio.CancelledError:
                logging.info("Interview task cancelled")
            except Exception as e:
                logging.error(f"Error during interview: {e}")
            finally:
                if hasattr(state.interview_bot, 'last_question') and state.interview_bot.last_question:
                    current_stage = state.interview_bot.current_stage
                    if "conversation" not in state.results[current_stage]:
                        state.results[current_stage]["conversation"] = []

                    state.results[current_stage]["conversation"].append({
                        "interviewer": state.interview_bot.last_question,
                        "you": ""  # Empty string for unanswered question
                    })
                state.interview_bot = None

    try:
        while True:
            data = await websocket.receive_json()
            # logging.info(f"Received data: {data}")
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
    if data['type'] == 'start_interview':
        await handle_start_interview(data, websocket, state, handle_interview)
    elif data['type'] == 'answer':
        await handle_answer(data, state)
    elif data['type'] == 'coding':
        await handle_coding(data, websocket, state, llm)
    elif data['type'] == 'end_interview':
        await handle_end_interview(websocket, state)
    elif data['type'] == 'get_analysis':
        await handle_get_analysis(data, websocket, state, llm)
    elif data['type'] == 'test_coding_question':
        try:
           # print("CODING INTERVIEW IS HERE")
            q1 = random.choice(
                ["Q1.#print Hello World", "Q2.#print Hello Anish", "Q3.#print Hello Duniya"])
            await websocket.send_json({'type': 'test_coding_question', 'message': q1})
            # await asyncio.wait_for(self.coding_event.wait(), timeout=1000)  # 5-minute timeout
            # self.coding_event.clear()
        except asyncio.TimeoutError:
            await websocket.send_json({'type': 'coding_timeout', 'message': 'Coding question timed out'})
        except Exception as e:
            await websocket.send_json({'type': 'coding_error', 'message': f'Error in coding stage: {str(e)}'})


async def handle_start_interview(data, websocket, state, handle_interview):
    if not state.interview_bot:
        state.interview_bot = InterviewBot(
            data["cv_text"], data["job_description"], state.results)
        asyncio.create_task(handle_interview())
        await websocket.send_json({"type": "interview_started", "message": "Interview started"})


async def handle_answer(data, state):
    if state.interview_bot:
        state.interview_bot.current_answer = data['answer']
        state.interview_bot.answer_event.set()
        state.interview_bot.last_question = None


async def handle_coding(data, websocket, state, llm):
    try:
        if state.interview_bot:
            resp = ""
            # Simulate the coding session
            code = data.get("code")
            ques = data.get("ques")
           # print(code,ques)
            if code:
               # print(code,ques)
                resp = evaluate_code(llm, ques, code)
               # print(code,ques)
               # print(resp)
                await websocket.send_json({"type": "code_evaluation", "result": resp})
                if resp:
                    if resp["RESULT"] == True:
                        state.interview_bot.coding_event.set()
    except Exception as e:
        await websocket.send_json({"type": "code_evaluation", "result": resp})
       # print(e)



async def handle_end_interview(websocket, state):
    if state.interview_bot:
        # If there's an active last question that wasn't answered, store it
        if hasattr(state.interview_bot, 'last_question') and state.interview_bot.last_question:
            current_stage = state.interview_bot.current_stage

            # Ensure the section exists in results
            if current_stage not in state.results:
                state.results[current_stage] = {}

            # Ensure the conversation array exists
            if "conversation" not in state.results[current_stage]:
                state.results[current_stage]["conversation"] = []

            # Add the unanswered question to the conversation
            state.results[current_stage]["conversation"].append({
                "interviewer": state.interview_bot.last_question,
                "you": ""  # Empty string for unanswered question
            })

        state.interview_bot.stop_interview.set()
        await asyncio.sleep(0.1)  # Allow time for interview task to react
        state.interview_bot.stop_interview.clear()
        await websocket.send_json({"type": "interview_end", "message": "Interview ended"})
    logging.info("Interview concluded")


async def handle_get_analysis(data, websocket, state, llm):
    analyzed_result = analyze_results(state.results, llm, data["rubrics"])
    await websocket.send_json({"type": "analysis", "result": analyzed_result})


@app.post("/generate_rubrics")
async def generateRubrics(body: dict):
    """
    Generate rubrics based on the provided data.
    """
    try:
        # Extract data from the request body
        data = body.get("job_description")
        # print("DATA_JD",data)
        if not data:
            return {"error": "No data provided"}

        # Process the data and generate rubrics
        rubrics = generate_rubrics(data)

        return {"rubrics": rubrics}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, port=5000, reload=True)
