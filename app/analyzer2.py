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
        input_variables=["qa_pairs"],
        template="""
        As an expert HR interviewer, provide a detailed, line-by-line analysis of the candidate's answer. Judge each line strictly on multiple metrics, providing scores and thorough reasoning for each score. 

        Questions and Answers:
        {qa_pairs}

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
    chain = LLMChain(llm=llm,prompt=prompt)
    analyzed_results = []
    for stage, item in results.items():
        qa_pairs = "\n\n".join([f"Question: {q}\nAnswer: {a}" for q, a in item.items()])
        analysis = chain.invoke({'qa_pairs': qa_pairs})
        print(analysis)
        analysis = str(analysis['text'].strip().strip('```json').strip('```'))
        print(analysis)
        time.sleep(2)
        try:
            analysis_json = json.loads(analysis)
            analyzed_results.append({
                "stage": stage,
                "analysis": analysis_json
            })
        except json.JSONDecodeError:
            print(f"Error decoding JSON for question: {stage}")
            print("Raw analysis:", analysis)

    return analyzed_results

