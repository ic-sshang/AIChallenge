import json
import sys
import os
# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from system_prompt import system_prompt 
from config import OPENAI_KEY, IC_OpenAI_URL
import requests

def message_gpt(user_prompt, model_type):
    if not user_prompt or not model_type:
        return "❌ All fields are required."

    try:
        headers = {
            'api-key': OPENAI_KEY,
            'Content-Type': 'application/json'
        }
        payload =json.dumps({
            "messages": [
                {
                "role": "system",
                "content": system_prompt
                },
                {
                "role": "user",
                "content": user_prompt
                }
            ]
        })
        response = requests.request(
        "POST", IC_OpenAI_URL, 
        headers= headers,
        data= payload
        )
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ Error: {str(e)}"
    

if __name__ == "__main__":
    message_gpt("Create a user story for a login feature", "gpt-4o-mini")
    

