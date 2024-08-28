import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from interviewer import *
from analyzer import *
from utils import *
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
app = FastAPI()
genai.configure(api_key=GOOGLE_API_KEY)
@app.get('/')
async def root():
    return {"data":"HELLO WORLD"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)