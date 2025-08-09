from openai import OpenAI
import os
from dotenv import load_dotenv

print ("Loading environment variables...")

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "너는 요리 전문가야."},
        {"role": "user", "content": "토마토와 파스타로 레시피 알려줘."}
    ]
)

print(response.choices[0].message.content)