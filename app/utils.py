
# import os
# from dotenv import load_dotenv
# from pypdf import PdfReader
# load_dotenv()
# import sys
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from fastapi import WebSocket
# import io

# async def get_cv(data,websocket:WebSocket):
#     pdf_file = io.BytesIO(bytearray(data['cv_data']))
#     reader = PdfReader(pdf_file)
#     pdf_text = ""
#     for page in reader.pages:
#         pdf_text += page.extract_text()
#    #print(pdf_text)
#     await websocket.send_json({'type': 'cv_uploaded', 'message': 'CV data received', 'cv_text': pdf_text})
#     return pdf_text

# async def get_job_description(data,websocket:WebSocket):
#     job_description = data['job_description']
#    #print(job_description)
#     await websocket.send_json({'type': 'jd_analyzed', 'message': "Received JD Successfully", 'job_description': job_description})
#     return job_description

# def read_cv(cv_path):
#     with open(cv_path, 'rb') as file:
#         reader = PdfReader(file)
#         return ' '.join(page.extract_text() for page in reader.pages)
    
# import json

# def save_analysis_results(results):
#     with open('interview_analysis.json', 'w') as f:
#         json.dump(results, f, indent=2)
#    #print("Analysis results saved to 'interview_analysis.json'")



# from fastapi import WebSocket
# import io
# from pypdf import PdfReader

# async def get_cv(data,websocket:WebSocket):
#     pdf_file = io.BytesIO(bytearray(data['cv_data']))
#     reader = PdfReader(pdf_file)
#     pdf_text = ""
#     for page in reader.pages:
#         pdf_text += page.extract_text()
#    #print(pdf_text)
#     return pdf_text

# async def get_job_description(data,websocket:WebSocket):
#     job_description = data['job_description']
#    #print(job_description)
    
#     return job_description

# def read_cv(cv_path):
#     with open(cv_path, 'rb') as file:
#         reader = PdfReader(file)
#         return ' '.join(page.extract_text() for page in reader.pages)
    
# import json

# def save_analysis_results(results):
#     with open('interview_analysis.json', 'w') as f:
#         json.dump(results, f, indent=2)
#    #print("Analysis results saved to 'interview_analysis.json'")

