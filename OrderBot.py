import sqlite3
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def connect_database():
    try:
        conn = sqlite3.connect("C:\\data\\cafeDB.db")
        print("데이터베이스 연결 성공!")
        return conn
    except sqlite3.Error as e:
        print(f"데이터베이스 연결 실패: {e}")
        return None

def get_menu_data():
    sql_query = """
    SELECT
      T1.CAT_NM,
      T2.PROD_NM,
      T2.PROD_OPTIONS
    FROM PROD_CATEGORY AS T1
    INNER JOIN PROD_MENU AS T2
      ON T1.UID = T2.CAT_UID
    ORDER BY
      T1.UID,
      T2.PROD_NM;
    """
    
    conn = connect_database()
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            categorized_menu = {}
            for cat_name, prod_name, prod_options in rows:
                if cat_name not in categorized_menu:
                    categorized_menu[cat_name] = []
                
                option_text = ""
                if prod_options == 'B':
                    option_text = " (HOT/ICE)"
                elif prod_options == 'I' and cat_name not in ['콜드 브루', '프라푸치노', '블렌디드', '피지오']:
                    option_text = " (ICE)"
                elif prod_options == 'H':
                    option_text = " (HOT)"
                    
                categorized_menu[cat_name].append(f"{prod_name}{option_text}")
            
            print('[메뉴판 시작]')
            for category, items in categorized_menu.items():
                print(f'**{category}**')
                for item in items:
                    print(f'-- {item}')
                print('')
            print('[메뉴판 끝]')
            
        except sqlite3.Error as e:
            print(f"데이터베이스 오류가 발생했습니다: {e}")
        finally:
            conn.close()
            print("데이터베이스 연결 종료")

class OrderBot:
    def __init__(self, system_prompt=None):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversation_history = []
        
        default_system_prompt = """당신은 juno-cafe(주노 카페)에서 주문을 받는 봇, 이름은 '마크'입니다.
당신의 역할은 카페에 온 손님을 친절하고 상냥하게 맞이하고, 그들의 주문을 정확하게 받거나 고객에게 필요한 카페, 메뉴 정보를 제공하는 것입니다. 그 이외의 질문에는 "죄송합니다. 전 알바생이라 그건 답해드릴 수가 없어요."라고 단호하게 거절하며 대답하세요.

손님은 여러가지 언어로 주문할 수 있습니다. 당신은 손님과 동일한 언어로 대답해야 합니다. 손님이 한국어로 주문하면 한국어로, 일본어로 주문하면 일본어로, 영어로 주문하면 영어로 대답하세요. 당신이 주문을 받을 때 확인이 필요한 것은 4가지 입니다. 1. 음료 종류, 2. 사이즈(톨, 그란데, 벤티), 3. 아이스/핫 여부, 4. 추가 옵션 (ex. 시럽, 휘핑크림 등), 5. 테이크아웃 여부. 만약 고객이 주문을 할 떄 이 4가지 중 하나라도 빠뜨린다면, 당신은 그 부분을 물어봐야 합니다. 예를 들면, 고객이 "아메리카노 톨 사이즈 하나요."라고 말하면 당신은 아이스/핫 여부, 추가 옵션, 테이크아웃 여부를 순서대로 물어봐야 합니다. 이렇게 고객의 주문이 완성되면, 추가로 주문할 내용이 있는지 물어보세요. 만약 고객이 추가 주문이 없다고 하면, 주문을 마무리하면 됩니다.

주문이 완료되면, 고객의 주문내용을 확인하고, 주문이 완료되었다고 알려주세요."""
        
        self.set_system_prompt(system_prompt or default_system_prompt)
        
    def set_system_prompt(self, system_prompt):
        if system_prompt:
            self.conversation_history = [{"role": "system", "content": system_prompt}]
        else:
            self.conversation_history = []
    
    def add_system_prompt(self, prompt):
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history[0]["content"] = prompt
        else:
            self.conversation_history.insert(0, {"role": "system", "content": prompt})
        
    def chat_with_gpt(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.conversation_history,
            max_tokens=150,
            temperature=0.7
        )
        
        gpt_response = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": gpt_response})
        
        return gpt_response
    
    def clear_history(self):
        system_prompt = None
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            system_prompt = self.conversation_history[0]["content"]
        
        self.conversation_history = []
        if system_prompt:
            self.conversation_history = [{"role": "system", "content": system_prompt}]

def main():
    bot = OrderBot()
    print("OpenAI 챗봇을 시작합니다. (종료하려면 'exit' 입력)")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("챗봇을 종료합니다.")
            break
        if user_input.strip():
            response = bot.chat_with_gpt(user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()