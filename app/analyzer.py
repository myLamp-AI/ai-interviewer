# /app/analyzer.py
import json
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import time

from dotenv import load_dotenv
load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.3,api_key=os.getenv("GOOGLE_API_KEY"))


def analyze_results(results, llm=None,  rubrics=None):
    if not rubrics:
        raise ValueError("Rubrics must be provided for evaluation")
    
    # Convert rubrics to a string format for the prompt
    rubrics_text = json.dumps(rubrics, indent=2)
    
    # First prompt for section-specific analysis
    section_prompt = PromptTemplate(
        input_variables=["conversation", "rubrics", "section","max_score"],
        template="""
        As an expert HR interviewer, provide a comprehensive analysis of the candidate's answers for the {section} section using both line-by-line evaluation and specific rubric criteria.
        
        Conversation:
        {conversation}
        
        Evaluation Rubrics:
        {rubrics}
        
        PART 1 - LINE-BY-LINE ANALYSIS:
        Analyze each line of the candidate's answers individually with these metrics:
        1. Relevance Score (0-10): How relevant is this line to the question asked?
        2. Clarity Score (0-10): How clear and understandable is this line?
        3. Depth Score (0-10): How in-depth or detailed is this line?
        4. Professionalism Score (0-10): How professional is the language and content?
        5. Technical Accuracy Score (0-10): How technically accurate is the information provided?
        
        PART 2 - OVERALL ASSESSMENT:
        1. Overall Score: Calculate a weighted average based on parameter weightages
        2. Strengths: The strongest aspects of the candidate's answers
        3. Areas for Improvement: Specific areas where the candidate could improve
        4. Suggestions: Actionable suggestions for improvement

        PART 3 - WEIGHTED SCORE
        1. Calculate a weighted score (only integer value) for each section based on overall performance and rubric weightages.
        2. The maximum weightage for section is {max_score} and the minimum is 0.
        3. The overall score should be a percentage of the maximum possible score.
        
        - Total score for all sections is 100. mean sum for weighted score of all section should be within or equal to 100.
        Format your response as a JSON object with the following structure:
        ```json
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
            }},
            "weighted_score": {{
                "score": 0,
                "max_score": {max_score},
                "percentage": 0.0
            }}
        }}
        ```
        """
    )
    
    # Second prompt for parameter evaluation across all sections
    parameter_prompt = PromptTemplate(
        input_variables=["all_conversations", "rubrics"],
        template="""
        As an expert HR interviewer, evaluate the candidate's performance across the entire interview based on specific rubric parameters.
        
        Complete Interview Conversations:
        {all_conversations}
        
        Evaluation Rubrics:
        {rubrics}
        
        RUBRIC-BASED EVALUATION:
        For each parameter in the provided rubrics, evaluate:
        1. Score (0-10): How well the candidate's answers across the entire interview satisfy this parameter
        2. Evidence: Specific parts of the candidate's answers that demonstrate competency in this area
        3. Analysis: Detailed reasoning for the score, considering the parameter's description and weightage
        
        Format your response as a JSON object with the following structure:
        ```json
        {{
            "parameter_evaluation": [
                {{
                    "parameter": "Parameter Name",
                    "score": 0,
                    "evidence": "Evidence from answers",
                    "analysis": "Detailed analysis",
                    "weightage": 0
                }}
            ]
        }}
        ```
        """
    )
    
    section_chain = LLMChain(llm=llm, prompt=section_prompt)
    parameter_chain = LLMChain(llm=llm, prompt=parameter_prompt)
    
    formatted_results = []
    all_conversations_text = ""
    
    # Process all sections, even if they have no conversation data
    all_sections = ["INTRODUCTION", "PROJECT", "CODING", "TECHNICAL", "OUTRO"]
    sections_score={"INTRODUCTION": 10, "PROJECT": 30, "CODING": 20, "TECHNICAL": 30, "OUTRO": 10}
    for section in all_sections:
        section_data = results.get(section, {})
        max_score = sections_score.get(section, 0)
        # Initialize conversation array if it doesn't exist
        if "conversation" not in section_data:
            section_data["conversation"] = []
        
        # Format the conversation for the prompt
        conversation_text = f"===== {section} SECTION =====\n"
        
        # Skip empty sections for analysis but still include them in results
        if not section_data["conversation"]:
            section_result = {
                "section": section,
                "conversation": [],
                "analysis": {
                    "line_analysis": [],
                    "overall_assessment": {
                        "overall_score": 0,
                        "strengths": [],
                        "areas_for_improvement": [],
                        "suggestions": []
                    },
                    "weighted_score": {
                        "score": 0,
                        "max_score": max_score,
                        "percentage": 0.0
                    }
                }
            }
            formatted_results.append(section_result)
            continue
            
        for exchange in section_data["conversation"]:
            conversation_text += f"Interviewer: {exchange['interviewer']}\n"
            conversation_text += f"Candidate: {exchange.get('you', '')}\n\n"
        
        # Add to consolidated conversations for parameter evaluation
        all_conversations_text += conversation_text + "\n"
        
        
        # Get analysis for this section only if it has content
        try:
            analysis = section_chain.invoke({
                'conversation': conversation_text, 
                'rubrics': rubrics_text,
                'section': section,
                'max_score': max_score
            })
            
            # Extract the JSON content
            analysis_text = str(analysis['text'].strip())
            json_match = re.search(r'```json\s*(.*?)\s*```', analysis_text, re.DOTALL)
            
            section_result = {
                "section": section,
                "conversation": section_data["conversation"]
            }
            
            if json_match:
                json_content = json_match.group(1)
                try:
                    analysis_json = json.loads(json_content)
                    section_result["analysis"] = analysis_json
                except json.JSONDecodeError:
                    print(f"Error decoding JSON for section: {section}")
                    section_result["analysis"] = {
                        "line_analysis": [],
                        "overall_assessment": {
                            "overall_score": 0,
                            "strengths": [],
                            "areas_for_improvement": ["Unable to analyze due to parsing error"],
                            "suggestions": []
                        },
                        "weighted_score": {
                            "score": 0,
                            "max_score": max_score,
                            "percentage": 0.0
                        }
                    }
            else:
                print(f"No JSON found in response for section: {section}")
                section_result["analysis"] = {
                    "line_analysis": [],
                    "overall_assessment": {
                        "overall_score": 0,
                        "strengths": [],
                        "areas_for_improvement": ["Unable to analyze - no valid response"],
                        "suggestions": []
                    },
                    "weighted_score": {
                        "score": 0,
                        "max_score": max_score,
                        "percentage": 0.0
                    }
                }
                
            formatted_results.append(section_result)
        except Exception as e:
            print(f"Error analyzing section {section}: {str(e)}")
            formatted_results.append({
                "section": section,
                "conversation": section_data["conversation"],
                "analysis": {
                    "line_analysis": [],
                    "overall_assessment": {
                        "overall_score": 0,
                        "strengths": [],
                        "areas_for_improvement": [f"Analysis error: {str(e)}"],
                        "suggestions": []
                    },
                    "weighted_score": {
                        "score": 0,
                        "max_score": sections_score.get(section, 0),
                        "percentage": 0.0
                    }
                }
            })
    
    # Add conclusion section (copy of OUTRO)
    outro_data = results.get("OUTRO", {})
    if "conversation" in outro_data:
        formatted_results.append({
            "section": "CONCLUSION",
            "conversation": outro_data["conversation"]
        })
    else:
        formatted_results.append({
            "section": "CONCLUSION",
            "conversation": []
        })
    
    # Now get parameter evaluation based on all conversations
    # Only attempt parameter evaluation if we have some conversation data
    if all_conversations_text.strip():
        try:
            parameter_analysis = parameter_chain.invoke({
                'all_conversations': all_conversations_text,
                'rubrics': rubrics_text
            })
            
            # Extract the JSON content for parameter evaluation
            parameter_text = str(parameter_analysis['text'].strip())
            parameter_json_match = re.search(r'```json\s*(.*?)\s*```', parameter_text, re.DOTALL)
            
            if parameter_json_match:
                parameter_json_content = parameter_json_match.group(1)
                try:
                    parameter_json = json.loads(parameter_json_content)
                    formatted_results.append(parameter_json)
                except json.JSONDecodeError:
                    print("Error decoding JSON for parameter evaluation")
                    formatted_results.append({
                        "parameter_evaluation": [
                            {
                                "parameter": "Error",
                                "score": 0,
                                "evidence": "Failed to parse parameter evaluation",
                                "analysis": "JSON decoding error",
                                "weightage": 0
                            }
                        ]
                    })
            else:
                print("No JSON found in response for parameter evaluation")
                formatted_results.append({
                    "parameter_evaluation": [
                        {
                            "parameter": "Error",
                            "score": 0,
                            "evidence": "No parameter evaluation generated",
                            "analysis": "JSON not found in response",
                            "weightage": 0
                        }
                    ]
                })
        except Exception as e:
            print(f"Error in parameter evaluation: {str(e)}")
            formatted_results.append({
                "parameter_evaluation": [
                    {
                        "parameter": "Error",
                        "score": 0,
                        "evidence": f"Error during evaluation: {str(e)}",
                        "analysis": "Exception occurred",
                        "weightage": 0
                    }
                ]
            })
    else:
        # If there's no conversation data at all, provide an empty parameter evaluation
        formatted_results.append({
            "parameter_evaluation": []
        })
    
    return formatted_results




def generate_rubrics(jobDescription):
    prompt = PromptTemplate(
    input_variables=["jobDescription"],
    template="""
        You are an experienced HR professional and hiring expert. Based on the job description provided below, your task is to create a JSON-formatted rubric for evaluating resumes. This rubric will be used to assess candidates across multiple dimensions.

        Job Description:
        {jobDescription}

        ## Instructions
        1. **Analyze the job description** and identify the following:
        - **Technical skills** (e.g., Python, React, API Integration)
        - **Soft skills** (e.g., communication, problem-solving, teamwork)
        - **Experience level** (e.g., years of experience, project complexity)
        - **Educational background** (e.g., specific degrees, majors)
        - **Certifications** (e.g., AWS Certified Developer)

        2. **Extract the job title** and include it as the `job_title` field in the output.

        3. **Create a list of evaluation criteria**, where each criterion includes:
        - `parameter`: The specific skill or requirement (e.g., Python, Communication, Bachelor's Degree)
        - `description`: A brief explanation (20-30 words) of why the parameter is important for the role
        - `weightage`: A number from 1 to 5 indicating the importance of this parameter (5 = most important)

        4. Use **exact names** for technologies or tools (e.g., use “JavaScript” not “web development”).

        ## Output Format
        Strictly follow the format below. The output must begin and end with triple backticks.

        ```json
        {{
        "job_title": "Extracted job title here",
        "evaluation_criteria": [
            {{
            "parameter": "Skill or requirement name",
            "description": "Why this parameter is essential for the role (20–30 words).",
            "weightage": 1 // Integer value between 1 and 5
            }},
            ...
        ]
        }}```
    
    Generate a JSON-based rubric system for evaluating resumes based on a given job description. 
    """
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    analysis = chain.invoke({'jobDescription': jobDescription})
    analysis = str(analysis['text'].strip().strip('```json').strip('```'))
    time.sleep(1)
    try:
        analysis_json = json.loads(analysis)
    except json.JSONDecodeError:
       print(f"Error decoding JSON for job description")
       #print("Raw analysis:", analysis)

    return analysis_json



