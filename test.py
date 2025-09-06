from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class SimpleChatBot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversation_history = []
        
    def chat(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=self.conversation_history,
            max_completion_tokens=300,
            temperature=1
        )
        
        bot_response = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": bot_response})
        
        return bot_response

def main():
    bot = SimpleChatBot()
    print("=== Simple ChatBot ===")
    print("종료하려면 'exit' 입력")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("챗봇을 종료합니다.")
            break
        elif user_input.strip():
            response = bot.chat(user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()