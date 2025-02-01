import json
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import time
def analyze_results(results, llm = None):
    prompt = PromptTemplate(
        input_variables=["question", "answer"],
        template="""
        As an expert HR interviewer, provide a detailed, line-by-line analysis of the candidate's answer. Judge each line strictly on multiple metrics, providing scores and thorough reasoning for each score. 

        Question: {question}
        Candidate's Answer: {answer}

        For each line of the answer, provide the following:
        1. Relevance Score (0-10): How relevant is this line to the question asked?
        2. Clarity Score (0-10): How clear and understandable is this line?
        3. Depth Score (0-10): How in-depth or detailed is this line?
        4. Professionalism Score (0-10): How professional is the language and content?
        5. Technical Accuracy Score (0-10): How technically accurate is the information provided? (If applicable)

        For each score, provide a detailed reasoning explaining why that specific score was given. Be strict and thorough in your analysis.

        After analyzing each line, provide:
        1. Overall Score (0-10): An overall assessment of the entire answer.
        2. Strengths: What were the strongest aspects of the answer?
        3. Areas for Improvement: What specific areas could the candidate improve upon?
        4. Suggestions: Provide actionable suggestions for how the candidate could have answered more effectively.

        Format your response as a JSON object starting and trailing with '```json' and '```' with the following structure:
        {{
            "line_analysis": [
                {{
                    "line": "Text of the line",
                    "relevance": {{"score": 0, "reasoning": ""}},
                    "clarity": {{"score": 0, "reasoning": ""}},
                    "depth": {{"score": 0, "reasoning": ""}},
                    "professionalism": {{"score": 0, "reasoning": ""}},
                    "technical_accuracy": {{"score": 0, "reasoning": ""}}
                }}
            ],
            "overall_assessment": {{
                "overall_score": 0,
                "strengths": [],
                "areas_for_improvement": [],
                "suggestions": []
            }}
        }}
        """
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    analyzed_results = []
    for question,answer in results.items():
        analysis = chain.invoke({'question':question, 'answer':answer})
        print(analysis)
        analysis = str(analysis['text'].strip().strip('```json').strip('```'))
        print(analysis)
        time.sleep(1)
        try:
            analysis_json = json.loads(analysis)
            analyzed_results.append({
                "question": question,
                "answer": answer,
                "analysis": analysis_json
            })
        except json.JSONDecodeError:
            print(f"Error decoding JSON for question: {question}")
            print("Raw analysis:", analysis)

    return analyzed_results

def summary_results(results,llm):
    prompt = PromptTemplate(
        input_variables=["qa_pairs"],
        template="""
        As an Expert HR professional, critically evaluate the candidate's interview responses using multiple metrics. Provide scores and thorough reasoning for each score, maintaining a high standard of objectivity and thoroughness in your assessment.

        Questions and Answers:
        {qa_pairs}

        For each question-answer pair, provide the following analysis:

        1. Response Summary (2-3 sentences summarizing the candidate's response based on metric like Relevance, Depth,Clarity,Technical Accuracy)

        After analyzing all responses, provide:

        2. Comprehensive Evaluation:
        a) Overall Candidate Score (0-10): An aggregate assessment of all responses.
        b) Key Strengths: Top 3-5 positive aspects of the candidate's responses.
        c) Primary Areas for Improvement: Top 3-5 aspects where the candidate could enhance their performance.
        d) Recommendations: 3-5 actionable suggestions for how the candidate could improve their interview performance.
        Format your response as a JSON object, enclosed by triple backticks and "json", with the following structure:

        ```json
        {{
            "response_analysis": [
            {{
                "question_number": 1,
                "response_summary": "",
            }}
            ],
            "comprehensive_evaluation": {{
            "overall_candidate_score": {{"score": 0, "justification": ""}},
            "key_strengths": [],
            "areas_for_improvement": [],
            "recommendations": []
            }},
        }}
        """
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    analyzed_results = {}
    for stage, item in results.items():
        if item:
            qa_pairs = "\n\n".join([f"Question: {q}\nAnswer: {a}" for q, a in item.items()])
            analysis = chain.invoke({'qa_pairs': qa_pairs})
            analysis_text = analysis['text'].strip()
            time.sleep(2)
            try:
                analysis_json = json.loads(analysis_text)
                analyzed_results[stage] = analysis_json
            except json.JSONDecodeError:
                print(f"Error decoding JSON for question: {stage}")
                print("Raw analysis:", analysis_text)
    
    print(analyzed_results)
    with open("data.json", "w") as f:
        json.dump(analyzed_results, f, indent=2)
    return analyzed_results

from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os

llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3,api_key="AIzaSyAY8U8Asc0ccXyF2_EI2ctM1K6f422fUbY")
if __name__ == "__main__":
    result = {
    "INTRODUCTION": {
        "Interview Question": "Tell me about yourself.",
        "Expected Answer": "I am a [Your Profession] with [Number] years of experience in [Industry]. I am passionate about [Your Interests] and enjoy working on [Your Projects]. I am particularly interested in this opportunity because [Reason for Interest]."
    },
    "PROJECT": {
        "Interview Question": "Can you describe a challenging project you've worked on?",
        "Expected Answer": "One of the most challenging projects I worked on was [Project Name]. The project involved [Project Description]. I faced [Challenges] but was able to overcome them by [Solutions]. The project was successful because [Positive Outcomes]."
    },
    "TECHNICAL": {
        "Interview Question": "What are your technical skills and experience?",
        "Expected Answer": "I have strong technical skills in [Technical Skills]. I have experience with [Technologies or Tools]. I have worked on projects involving [Projects or Applications]."
    },
    "OUTRO": {
        "Interview Question": "Do you have any questions for us?",
        "Expected Answer": "Yes, I have a few questions. First, could you tell me more about the team I would be working with? Second, what is the company's vision for the future? Finally, what are the opportunities for growth and development within the company?"
    }
}
    summary_results(result,llm)
