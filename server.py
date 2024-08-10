import os
import sys
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from interviewer import *
import io
from PyPDF2 import PdfReader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from analyzer import *
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()


@app.get('/')
async def root():
    return {"data":"HELLO WORLD"}


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
                interview = False
                if interview_task:
                    await interview_task
                print("interview Concluded")
            elif data['type'] == 'get_analysis':
                analyzed_result = analyze_answer(results)
                await websocket.send_json({"type":"analysis","result":analyzed_result})
    
    except WebSocketDisconnect:
        print("WebSocket disconnected")


async def conduct_interview(interview_bot, websocket):
    for stage in interview_bot.stages:
        print(f"\n--- {stage} STAGE ---")
        
        interview_bot.message_history = ChatMessageHistory()
        if stage == "TECHNICAL":
            prompt = PROMPTS[stage].format(skills=interview_bot.cv_parts[stage], job_description=interview_bot.job_description)
        else:
            prompt = PROMPTS[stage].format(variable=interview_bot.cv_parts[stage])

        while True:
            response = interview_bot.get_ai_response(prompt, "Ask your question or exit the interview")
            
            next_phase = response.find("move to next phase")
            if next_phase != -1:
                response = response[:next_phase]
                move_to_new_phase = True
            else:
                move_to_new_phase = False
            if response:
                if "exit" in response or "interview concluded" in response:
                    break

            print("Interviewer:", response)
            #interview_bot.text_to_speech(response)
            await websocket.send_json({'type': 'interview_question', 'question': response})

            print("Please speak your answer...")
            answer = await websocket.receive_json()
            answer = answer.get('answer', '')

            print("You:", answer)
            if answer:
                if "exit" in answer:
                    return

            interview_bot.message_history.add_user_message(answer)

            if move_to_new_phase:
                break
            interview_bot.result[response] = answer
            
    print("\nInterview concluded. Thank you for your time!")
    await websocket.send_json({'type': 'interview_end', 'message': 'Interview completed'}) 
    return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)