# -*- coding: utf-8 -*-
import os
import sys
import json
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

# Windows에서 UTF-8 출력 설정
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

class BurgerBot:
    def __init__(self, system_prompt=None):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversation_history = []
        self.order_list = []
        self.db_connection = None
        self.connect_to_local_db()

        menu_section = self.get_menuinfo_query()
        order_form = self.get_order_form()
        sample_data = self.get_few_shot()
        
        default_system_prompt = f"""당신은 Burger House(버거하우스)에서 주문을 받는 봇, 이름은 '버거하우스'입니다.
        당신의 역할은 버거하우스에 온 손님을 친절하게 맞이하고, 그들의 주문을 정확하게 받거나 고객에게 필요한 카페, 메뉴 정보를 제공하는 것입니다. 금액은 모든 상품이 등록된 후에 표기가 가능합니다.
        그 이전에 가격을 물어본다면, 메뉴 선택이 완료된 후에 가격을 알려줄 수 있다고 답하세요.

        [**주문서 양식**]
        {order_form}
        [**주문서 양식끝**]
        
        [**대화 예시 시작**]
        {sample_data}
        [**대화 예시 끝**]
        
        [**메뉴시작**]

            - 메뉴 정보 양식
            [카테고리]
            메뉴ID:메뉴

            예)
            [버거]
            1:한우불고기버거
            2:더블 한우불고기 버거

            [드링크]
            15:펩시 콜라

        {menu_section}
        [**메뉴끝**]"""
        
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
        
    def parse_orders_from_response(self, response):
        if "[ORDER_COMPLETE]" not in response:
            return []
        
        orders_added = []
        
        # 모든 [ORDER_COMPLETE] 섹션을 찾기
        parts = response.split("[ORDER_COMPLETE]")
        
        for i in range(1, len(parts)):  # 첫 번째는 일반 텍스트이므로 제외
            try:
                order_section = parts[i].strip()
                lines = [line.strip() for line in order_section.split('\n') if line.strip()]
                
                order_data = {}
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        order_data[key.strip()] = value.strip()
                
                order_type = order_data.get('TYPE')
                if not order_type:
                    continue
                    
                quantity = int(order_data.get('QUANTITY', 1))
                
                if order_type == 'set':
                    set_type = order_data.get('SET_TYPE', 'burger_set')
                    order = None
                    
                    if set_type == 'burger_set':
                        burger_id = order_data.get('BURGER')
                        if not burger_id:
                            continue
                        
                        # 토핑 처리
                        burger_toppings = None
                        if 'TOPPINGS' in order_data:
                            toppings_str = order_data['TOPPINGS']
                            burger_toppings = [int(t.strip()) for t in toppings_str.split(',') if t.strip().isdigit()]
                        
                        # 사이드 처리
                        side_id = int(order_data.get('SIDE', 10))
                        
                        # 음료 처리
                        drink_id = int(order_data.get('DRINK', 15))
                        
                        order = self.add_burger_set_order(int(burger_id), side_id, drink_id, quantity, burger_toppings)
                        
                    elif set_type == 'burger_combo':
                        burger_id = order_data.get('BURGER')
                        if not burger_id:
                            continue
                        
                        # 토핑 처리
                        burger_toppings = None
                        if 'TOPPINGS' in order_data:
                            toppings_str = order_data['TOPPINGS']
                            burger_toppings = [int(t.strip()) for t in toppings_str.split(',') if t.strip().isdigit()]
                        
                        drink_id = int(order_data.get('DRINK', 15))
                        order = self.add_burger_combo_order(int(burger_id), drink_id, quantity, burger_toppings)
                        
                    elif set_type == 'chicken_full_pack':
                        chicken_id = order_data.get('CHICKEN')
                        if not chicken_id:
                            continue
                        sauce_id = int(order_data.get('SAUCE', 40))
                        order = self.add_chicken_full_pack_order(int(chicken_id), sauce_id, quantity)
                        
                    elif set_type == 'chicken_half_pack':
                        chicken_id = order_data.get('CHICKEN')
                        if not chicken_id:
                            continue
                        sauce_id = int(order_data.get('SAUCE', 40))
                        order = self.add_chicken_half_pack_order(int(chicken_id), sauce_id, quantity)
                    
                    if order:
                        orders_added.append(order)
                        
                elif order_type == 'single':
                    order = None
                    if 'BURGER' in order_data:
                        # 토핑 처리
                        toppings = None
                        if 'TOPPINGS' in order_data:
                            toppings_str = order_data['TOPPINGS']
                            toppings = [int(t.strip()) for t in toppings_str.split(',') if t.strip().isdigit()]
                        order = self.add_single_order(int(order_data['BURGER']), 'burger', None, quantity, toppings)
                    elif 'CHICKEN' in order_data:
                        order = self.add_single_order(int(order_data['CHICKEN']), 'chicken', None, quantity)
                    elif 'SIDE' in order_data:
                        side_id = int(order_data['SIDE'])
                        order = self.add_single_order(side_id, 'side', quantity)
                    elif 'DRINK' in order_data:
                        drink_id = int(order_data['DRINK'])
                        order = self.add_single_order(drink_id, 'drink', None, quantity)
                    elif 'SAUCE' in order_data:
                        sauce_id = int(order_data['SAUCE'])
                        order = self.add_single_order(sauce_id, 'sauce', None, quantity)
                    
                    if order:
                        orders_added.append(order)
                        
            except Exception as e:
                print(f"주문 파싱 중 오류: {e}")
                continue
        
        return orders_added
    
    def chat_with_gpt(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.conversation_history,
            max_tokens=200,
            temperature=0.7,
            stream=True
        )
        
        full_response = ""
        
        # 먼저 전체 응답을 수집
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
        
        # 대화 기록에 추가
        self.conversation_history.append({"role": "assistant", "content": full_response})
        
        # 주문 파싱 및 자동 등록 (전체 응답으로)
        parsed_orders = self.parse_orders_from_response(full_response)
        if parsed_orders:
            print(f"✅ {len(parsed_orders)}개의 주문이 자동으로 등록되었습니다!")
        
        # 사용자에게 보여줄 부분만 스트리밍 (ORDER_COMPLETE 태그 제거)
        display_response = full_response.split("[ORDER_COMPLETE]")[0].strip()
        
        # 단어 단위로 스트리밍 효과 생성 (더 자연스러움)
        import time
        words = display_response.split(' ')
        for i, word in enumerate(words):
            if i == 0:
                yield word
            else:
                yield ' ' + word
            # 약간의 지연으로 타이핑 효과
            time.sleep(0.05)
    
    def chat_with_gpt_non_streaming(self, user_input):
        """Non-streaming version for compatibility"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.conversation_history,
            max_tokens=200,
            temperature=0.7
        )
        
        gpt_response = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": gpt_response})
        
        # 주문 파싱 및 자동 등록
        parsed_orders = self.parse_orders_from_response(gpt_response)
        if parsed_orders:
            print(f"✅ {len(parsed_orders)}개의 주문이 자동으로 등록되었습니다!")
        
        # [ORDER_COMPLETE] 태그 제거한 응답 반환
        display_response = gpt_response.split("[ORDER_COMPLETE]")[0].strip()
        return display_response
    
    def clear_history(self):
        system_prompt = None
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            system_prompt = self.conversation_history[0]["content"]
        
        self.conversation_history = []
        if system_prompt:
            self.conversation_history = [{"role": "system", "content": system_prompt}]
    
    def add_burger_set_order(self, burger_id, side_id=None, drink_id=None, quantity=1, burger_toppings=None):
        """버거 세트 주문 (버거 + 사이드 + 음료)"""
        if not side_id:
            side_id = 10  # 기본 후렌치 후라이
        if not drink_id:
            drink_id = 15  # 기본 코카 콜라
            
        burger_data = {"menu_id": burger_id}
        if burger_toppings:
            burger_data["toppings"] = burger_toppings
            
        order = {
            "order_type": "set",
            "set_type": "burger_set",
            "quantity": quantity,
            "burger": burger_data,
            "side": {
                "menu_id": side_id
            },
            "drink": {
                "menu_id": drink_id
            }
        }
        self.order_list.append(order)
        return order
    
    def add_burger_combo_order(self, burger_id, drink_id=None, quantity=1, burger_toppings=None):
        """버거 콤보 주문 (버거 + 음료)"""
        if not drink_id:
            drink_id = 15  # 기본 코카 콜라
            
        burger_data = {"menu_id": burger_id}
        if burger_toppings:
            burger_data["toppings"] = burger_toppings
            
        order = {
            "order_type": "set",
            "set_type": "burger_combo",
            "quantity": quantity,
            "burger": burger_data,
            "drink": {
                "menu_id": drink_id
            }
        }
        self.order_list.append(order)
        return order
    
    def add_chicken_full_pack_order(self, chicken_id, sauce_id=None, quantity=1):
        """치킨 풀팩 주문 (치킨 + 소스 2개)"""
        if not sauce_id:
            sauce_id = 40  # 기본 치킨 소스
            
        order = {
            "order_type": "set",
            "set_type": "chicken_full_pack",
            "quantity": quantity,
            "chicken": {
                "menu_id": chicken_id
            },
            "sauce": {
                "menu_id": sauce_id,
                "quantity": 2
            }
        }
        self.order_list.append(order)
        return order
    
    def add_chicken_half_pack_order(self, chicken_id, sauce_id=None, quantity=1):
        """치킨 하프팩 주문 (치킨 + 소스 1개)"""
        if not sauce_id:
            sauce_id = 40  # 기본 치킨 소스
            
        order = {
            "order_type": "set",
            "set_type": "chicken_half_pack",
            "quantity": quantity,
            "chicken": {
                "menu_id": chicken_id
            },
            "sauce": {
                "menu_id": sauce_id,
                "quantity": 1
            }
        }
        self.order_list.append(order)
        return order
    
    def add_single_order(self, item_id, item_type, quantity=1, toppings=None):
        """단품 주문"""
        order = {
            "order_type": "single",
            "quantity": quantity
        }
        
        if item_type == "burger":
            burger_data = {"menu_id": item_id}
            if toppings:
                burger_data["toppings"] = toppings
            order["burger"] = burger_data
        elif item_type == "chicken":
            order["chicken"] = {"menu_id": item_id}
        elif item_type == "side":
            order["side"] = {"menu_id": item_id}
        elif item_type == "drink":
            order["drink"] = {"menu_id": item_id}
        elif item_type == "sauce":
            order["sauce"] = {"menu_id": item_id}
        
        self.order_list.append(order)
        return order
    
    def get_orders_json(self):
        return json.dumps(self.order_list, ensure_ascii=False, indent=2)
    
    def clear_orders(self):
        self.order_list = []
    
    def connect_to_local_db(self):
        """로컬 데이터베이스에 연결하는 함수"""
        try:
            # C:\data\BurgerDB.db 경로 설정
            db_directory = r"C:\data"
            db_path = os.path.join(db_directory, "BurgerDB.db")
            
            # 디렉토리가 없으면 생성
            if not os.path.exists(db_directory):
                os.makedirs(db_directory)
                print(f"✅ 디렉토리 생성: {db_directory}")
            
            # SQLite 데이터베이스 연결
            self.db_connection = sqlite3.connect(db_path)
            self.db_connection.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            
            print(f"✅ SQLite 데이터베이스 연결 성공! (경로: {db_path})")
            return True
            
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            return False
    
    def get_order_form(self):
        """주문서 양식을 반환하는 함수"""
        try:
            # PROMPT\ORDER_FORM 파일 읽기
            order_form_path = os.path.join(os.path.dirname(__file__), "PROMPT", "ORDER_FORM.txt")
            
            with open(order_form_path, 'r', encoding='utf-8') as file:
                order_form_content = file.read()
            
            return order_form_content
            
        except Exception as e:
            print(f"❌ 주문서 양식 파일 읽기 실패: {e}")
            return "주문서 양식을 불러올 수 없습니다."
        
    def get_few_shot(self):
        """주문서 양식을 반환하는 함수"""
        try:
            # PROMPT\FEW_SHOT 파일 읽기
            order_form_path = os.path.join(os.path.dirname(__file__), "PROMPT", "FEW_SHOT.txt")
            
            with open(order_form_path, 'r', encoding='utf-8') as file:
                few_shot_content = file.read()
            
            return few_shot_content
            
        except Exception as e:
            print(f"❌ 주문서 양식 파일 읽기 실패: {e}")
            return "주문서 양식을 불러올 수 없습니다."

    def get_menuinfo_query(self):
        """메뉴 정보를 가져와서 system prompt에 넣을 데이터베이스 쿼리 함수"""
        query = """
        SELECT 
            A.MENU_ID,
            B.CATEGORY_NAME,
            A.MENU_NAME
        FROM MENU A, MenuCategory B
        WHERE 1=1
        AND A.CATEGORY_ID = B.CATEGORY_ID
        ORDER BY B.CATEGORY_NAME, A.MENU_ID
        """
        
        try:
            if not self.db_connection:
                print("❌ 데이터베이스 연결이 없습니다.")
                return None
            
            cursor = self.db_connection.cursor()
            cursor.execute(query)
            
            results = cursor.fetchall()
            
            # [CATEGORY_NAME]\nMENU_ID:MENU_NAME 형태로 포맷팅
            formatted_result = ""
            current_category = ""
            
            for row in results:
                category = row['CATEGORY_NAME']
                menu_id = row['MENU_ID']
                menu_name = row['MENU_NAME']
                
                # 카테고리가 바뀌면 새로운 카테고리 헤더 추가
                if category != current_category:
                    if formatted_result:  # 첫 번째가 아니면 줄바꿈 추가
                        formatted_result += "\n"
                    formatted_result += f"[{category}]\n"
                    current_category = category
                
                formatted_result += f"{menu_id}:{menu_name}\n"
            
            return formatted_result.strip()
                
        except Exception as e:
            print(f"❌ 메뉴 정보 쿼리 실행 실패: {e}")
            return None
    
    def get_order_summary(self):
        if not self.order_list:
            return "주문 내역이 없습니다."
        
        summary = "=== 주문 내역 ===\n"
        for i, order in enumerate(self.order_list, 1):
            summary += f"{i}. "
            if order["order_type"] == "set":
                set_type = order.get("set_type", "burger_set")
                if set_type == "burger_set":
                    summary += f"버거 세트 (메뉴ID: {order['burger']['menu_id']})"
                    if order["quantity"] > 1:
                        summary += f" x{order['quantity']}"
                    summary += "\n"
                    summary += f"   └ 버거: 메뉴ID {order['burger']['menu_id']}\n"
                    if "toppings" in order["burger"]:
                        summary += f"      + 토핑: {order['burger']['toppings']}\n"
                    if "side" in order:
                        summary += f"   └ 사이드: 메뉴ID {order['side']['menu_id']}\n"
                    summary += f"   └ 음료: 메뉴ID {order['drink']['menu_id']}\n"
                elif set_type == "burger_combo":
                    summary += f"버거 콤보 (메뉴ID: {order['burger']['menu_id']})"
                    if order["quantity"] > 1:
                        summary += f" x{order['quantity']}"
                    summary += "\n"
                    summary += f"   └ 버거: 메뉴ID {order['burger']['menu_id']}\n"
                    if "toppings" in order["burger"]:
                        summary += f"      + 토핑: {order['burger']['toppings']}\n"
                    summary += f"   └ 음료: 메뉴ID {order['drink']['menu_id']}\n"
                elif set_type == "chicken_full_pack":
                    summary += f"치킨 풀팩 (메뉴ID: {order['chicken']['menu_id']})"
                    if order["quantity"] > 1:
                        summary += f" x{order['quantity']}"
                    summary += "\n"
                    summary += f"   └ 치킨: 메뉴ID {order['chicken']['menu_id']}\n"
                    summary += f"   └ 소스: 메뉴ID {order['sauce']['menu_id']} x{order['sauce']['quantity']}\n"
                elif set_type == "chicken_half_pack":
                    summary += f"치킨 하프팩 (메뉴ID: {order['chicken']['menu_id']})"
                    if order["quantity"] > 1:
                        summary += f" x{order['quantity']}"
                    summary += "\n"
                    summary += f"   └ 치킨: 메뉴ID {order['chicken']['menu_id']}\n"
                    summary += f"   └ 소스: 메뉴ID {order['sauce']['menu_id']} x{order['sauce']['quantity']}\n"
            else:
                if "burger" in order:
                    summary += f"버거 단품 (메뉴ID: {order['burger']['menu_id']})"
                    if "toppings" in order["burger"]:
                        summary += f" + 토핑: {order['burger']['toppings']}"
                elif "chicken" in order:
                    summary += f"치킨 단품 (메뉴ID: {order['chicken']['menu_id']})"
                elif "side" in order:
                    summary += f"사이드 (메뉴ID: {order['side']['menu_id']})"
                elif "drink" in order:
                    summary += f"음료 (메뉴ID: {order['drink']['menu_id']})"
                elif "sauce" in order:
                    summary += f"소스 (메뉴ID: {order['sauce']['menu_id']})"
                
                if order["quantity"] > 1:
                    summary += f" x{order['quantity']}"
                summary += "\n"
        return summary
    
    def start_greeting(self):
        greeting = "안녕하세요! Burger House에 오신 걸 환영합니다! 저는 버거하우스이에요. 무엇을 도와드릴까요? 오늘 맛있는 버거 주문하고 싶으시죠?"
        print(f"Bot: {greeting}")
        self.conversation_history.append({"role": "assistant", "content": greeting})
        return greeting

def main():
    bot = BurgerBot()
    print("=== Burger House 주문 시스템 ===")
    
    bot.start_greeting()
    print("(종료: 'exit', 주문확인: 'orders', JSON보기: 'json', 주문초기화: 'clear')")
    print("테스트 주문 추가: 'test'")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("주문 시스템을 종료합니다. 감사합니다!")
            break
        elif user_input.lower() == "orders":
            print(bot.get_order_summary())
        elif user_input.lower() == "json":
            print("=== 주문 JSON ===")
            print(bot.get_orders_json())
        elif user_input.lower() == "clear":
            bot.clear_orders()
            print("주문 내역을 초기화했습니다.")
        elif user_input.lower() == "test":
            # 테스트용 주문 추가 (예시와 같은 주문)
            bot.add_burger_set_order(2)  # 불고기 버거 (ID: 2)
            bot.add_single_order(15, "drink")  # 코카 콜라 (ID: 15)
            print("테스트 주문을 추가했습니다!")
        elif user_input.strip():
            response = bot.chat_with_gpt_non_streaming(user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()