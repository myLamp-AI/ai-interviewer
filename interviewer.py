import os
import re
import sys
from dotenv import load_dotenv
from utils import*
from prompts import *
from analyzer import *
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
#from RealtimeTTS import TextToAudioStream, GTTSEngine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# engine = GTTSEngine()  # replace with your TTS engine
# stream = TextToAudioStream(engine)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class InterviewBot:
    def __init__(self, cv_text, job_description,results):
        
        self.stages = ["INTRODUCTION", "PROJECT", "TECHNICAL", "OUTRO"]
        self.message_history = ChatMessageHistory()
        self.result = results
        # Initialize Google Generative AI
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
        self.cv_parts = get_resume_in_parts(self.model, cv_text)
        self.job_description = get_summarized_jd(self.model, job_description)
        # Initialize TTS engine
        # self.stream = stream
        
        # Initialize STT recognizer
        

    @staticmethod
    def clean_text(text):
        text = text.lower()
        text = re.sub(r"[^a-z0-9',!?-]", " ", text)
        return text

    # def text_to_speech(self, text):
    #     self.stream.feed(text)
    #     self.stream.play()

    # def speech_to_text(self):
    #     transcriber = AudioTranscriber()
    #     transcription = transcriber.run()
    #     return transcription

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

    # def conduct_interview_inside(self):
    #     for stage in self.stages:
    #         print(f"\n--- {stage} STAGE ---")
            
    #         self.message_history = ChatMessageHistory()
    #         if stage == "TECHNICAL":
    #             prompt = PROMPTS[stage].format(skills=self.cv_parts[stage], job_description=self.job_description)
    #         else:
    #             prompt = PROMPTS[stage].format(variable=self.cv_parts[stage])

    #         while True:
    #             response = self.get_ai_response(prompt, "Ask your question or exit the interview")
                
    #             next_phase = response.find("move to next phase")
    #             if next_phase != -1:
    #                 response = response[:next_phase]
    #                 move_to_new_phase = True
    #             else:
    #                 move_to_new_phase = False
    #             if response:
    #                 if "exit" in response or "interview concluded" in response:
    #                     break

    #             print("Interviewer:", response)
    #             self.text_to_speech(response)

    #             print("Please speak your answer...")
    #             answer = self.speech_to_text()
    #             print("You:", answer)
    #             if answer:
    #                 if "exit" in answer:
    #                     return

    #             self.message_history.add_user_message(answer)

    #             if move_to_new_phase:
    #                 break
    #             self.result[response] = answer
    #     print("\nInterview concluded. Thank you for your time!")

# Usage
if __name__ == "__main__":
    cv_path = "sample_cv_2.pdf"
    cv_text =  read_cv(cv_path)
    job_description = "Data Science and ML"
    model = ChatGoogleGenerativeAI(model="gemini-pro",temperature=0.3,max_output_tokens=2048)
    results = {}
    bot = InterviewBot(cv_text, job_description,results)
    bot.conduct_interview()
    analyzed_results = analyze_results({"introduce yourself":"I am anish kumar from uganda, i won't answer you"},model)
    save_analysis_results(analyzed_results)

