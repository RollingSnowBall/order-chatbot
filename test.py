from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.responses.create(
    model="gpt-5-nano-2025-08-07",  # 또는 사용 가능한 다른 모델 (예: gpt-4o)
    reasoning={"effort": "low"},
    instructions="Talk like a pirate.",
    input="Are semicolons optional in JavaScript?",
)

print(response.output_text)

