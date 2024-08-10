<<<<<<< HEAD
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from interviewer import *
from analyzer import *
from utils import *
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()


@app.get('/')
async def root():
    return {"data":"HELLO WORLD"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        cv_text = ""
        job_description = ""
        interview = True
        while True:
            data = await websocket.receive_json()
            
            if data['type'] == 'upload_cv':
                cv_text = await get_cv(data,websocket)
                            
            elif data['type'] == 'analyze_jd':
                job_description = await get_job_description(data,websocket)
                            
            elif data['type'] == 'start_interview':
                results = {}
                interview_bot = InterviewBot(cv_text, job_description, results)
                interview_task = await conduct_interview(interview_bot, websocket)
            elif data['type'] == 'end_interview':
                if interview_task:
                    await interview_task
                print("interview Concluded")
            elif data['type'] == 'get_analysis':
                analyzed_result = analyze_answer(results)
                await websocket.send_json({"type":"analysis","result":analyzed_result})
    
    except WebSocketDisconnect:
        print("WebSocket disconnected")

if __name__ == "__main__":
    import uvicorn
=======
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from interviewer import *
from analyzer import *
from utils import *
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()


@app.get('/')
async def root():
    return {"data":"HELLO WORLD"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        cv_text = ""
        job_description = ""
        interview = True
        while True:
            data = await websocket.receive_json()
            
            if data['type'] == 'upload_cv':
                cv_text = await get_cv(data,websocket)
                            
            elif data['type'] == 'analyze_jd':
                job_description = await get_job_description(data,websocket)
                            
            elif data['type'] == 'start_interview':
                results = {}
                interview_bot = InterviewBot(cv_text, job_description, results)
                interview_task = await conduct_interview(interview_bot, websocket)
            elif data['type'] == 'end_interview':
                if interview_task:
                    await interview_task
                print("interview Concluded")
            elif data['type'] == 'get_analysis':
                analyzed_result = analyze_answer(results)
                await websocket.send_json({"type":"analysis","result":analyzed_result})
    
    except WebSocketDisconnect:
        print("WebSocket disconnected")

if __name__ == "__main__":
    import uvicorn
>>>>>>> 43c2e9a9b6a447ba662af1949e3ae197dd2a3592
    uvicorn.run(app, host="0.0.0.0", port=8000)