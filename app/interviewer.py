import os
import re
import sys
from dotenv import load_dotenv
from app.utils import*
from app.prompts import *
from app.analyzer import *
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import asyncio
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import random
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

async def start_coding_phase():
    pass
    



async def conduct_interview(interview_bot, websocket,stop_interview):
    for stage in interview_bot.stages:
        print(f"\n--- {stage} STAGE ---")
        
        interview_bot.message_history = ChatMessageHistory()
        if stage == "TECHNICAL":
            prompt = PROMPTS[stage].format(skills=interview_bot.cv_parts[stage], job_description=interview_bot.job_description)
        else:
            prompt = PROMPTS[stage].format(variable=interview_bot.cv_parts[stage])

        while not stop_interview.is_set():
            if stop_interview.is_set():
                return
            response = interview_bot.get_ai_response(prompt, "Ask your question or exit the interview")
            
            next_phase = response.find("move to next phase")
            coding_phase = response.find("coding phase")
            if next_phase != -1:
                response = response[:next_phase]
                move_to_new_phase = True
            elif coding_phase != -1:
                pass
            else:
                move_to_new_phase = False
            if response:
                if "exit" in response or "interview concluded" in response:
                    break

            print("Interviewer:", response)
            #interview_bot.text_to_speech(response)
            await websocket.send_json({'type': 'interview_question', 'question': response})

            print("Please speak your answer...")
            answer_data = await websocket.receive_json()
            answer = answer_data.get('answer', '')
            print("You:", answer)
            if answer:
                if "exit" in answer:
                    return

            interview_bot.message_history.add_user_message(answer)

            if move_to_new_phase:
                break
            if coding_phase:
                await websocket.send_json({"type":"start_coding",'message':'Starting Coding related Questions'})
                await start_coding_phase()
                break
            interview_bot.result[response] = answer
            await asyncio.sleep(0.1)
            
    print("\nInterview concluded. Thank you for your time!")
    await websocket.send_json({'type': 'interview_end', 'message': 'Interview completed'}) 
    return



class InterviewBot:
    def __init__(self, cv_text, job_description,results):
        #self.stages = ["CODING", "TECHNICAL", "OUTRO"]
        self.stages = ["INTRODUCTION", "PROJECT", "CODING", "TECHNICAL", "OUTRO"]
        self.message_history = ChatMessageHistory()
        self.result = results
        # Initialize Google Generative AIs
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
        self.cv_parts = get_resume_in_parts(self.model, cv_text)
        self.job_description = get_summarized_jd(self.model, job_description)
        self.answer_event = asyncio.Event()
        self.current_answer = None
        self.stop_interview = asyncio.Event()
        self.coding_event = asyncio.Event()
        # Initialize TTS engine
        # self.stream = stream
        
        # Initialize STT recognizer
        

    @staticmethod
    def clean_text(text):
        text = text.lower()
        text = re.sub(r"[^a-z0-9',!?-]", " ", text)
        return text

    def get_ai_response(self, prompt, input_text):
        chain = ChatPromptTemplate.from_messages([
            ("human", prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]) | self.model

        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: self.message_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        response = chain_with_history.invoke(
            {"input": input_text},
            {"configurable": {"session_id": "interview_session"}}
        )

        return self.clean_text(response.content)
    
    async def start_coding_stage(self,websocket):
        print("CODING INTERVIEW IS HERE")
        q1 = random.choice(["Print Hello World","Print Hello Anish","Print Hello Duniya"])
        await websocket.send_json({'type': 'coding_question', 'message': q1})
        print(self.coding_event.is_set())
        await self.coding_event.wait()
        self.coding_event.clear()
        return
    
    async def conduct_interview(self, websocket):
        for stage in self.stages:
            print(f"\n--- {stage} STAGE ---")
            try:
                self.message_history = ChatMessageHistory()
                if stage == "TECHNICAL":
                    prompt = PROMPTS[stage].format(skills=self.cv_parts[stage], job_description=self.job_description)
                elif stage == "CODING":
                    print("I AM HERE")
                    for i in range(2):
                        await self.start_coding_stage(websocket=websocket)
                    continue
                else:
                    prompt = PROMPTS[stage].format(variable=self.cv_parts[stage])

                while True:
                    if self.stop_interview.is_set():
                        return
                    response = self.get_ai_response(prompt, "Ask your question or exit the interview")
                    
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
                    #self.text_to_speech(response)
                    await websocket.send_json({'type': 'interview_question', 'question': response})

                    print("Please speak your answer...")
                    await self.answer_event.wait()
                    answer = self.current_answer
                    self.current_answer = None
                    self.answer_event.clear()
                    #answer = answer_data.get('answer', '')
                    print("You:", answer)
                    if answer:
                        if "exit" in answer:
                            return

                    self.message_history.add_user_message(answer)

                    if move_to_new_phase:
                        break
                    self.result[response] = answer
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(e)
                await websocket.send_json({'type': 'interview_end', 'message': 'Interview completed Because of not a good job description'})
                break 
                
        print("\nInterview concluded. Thank you for your time!")
        await websocket.send_json({'type': 'interview_end', 'message': 'Interview completed'}) 
        return

