# -*- coding: utf-8 -*-
import os
import sys
import json
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
from order_formatter import OrderFormatter

# Windows에서 UTF-8 출력 설정
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

class BurgerBotV2:
    def __init__(self, system_prompt=None):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversation_history = []
        self.order_list = []
        self.db_connection = None
        self.order_formatter = OrderFormatter()
        self.connect_to_local_db()

        # Function Calling 도구 정의
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_menu_info",
                    "description": "메뉴 정보를 조회합니다. 카테고리별 조회, 검색, 특정 메뉴 조회가 가능합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["get_categories", "search", "get_by_id", "get_by_category"],
                                "description": "수행할 작업 유형"
                            },
                            "query": {
                                "type": "string",
                                "description": "검색할 키워드 (action이 'search'일 때 필요)"
                            },
                            "menu_id": {
                                "type": "integer",
                                "description": "조회할 메뉴 ID (action이 'get_by_id'일 때 필요)"
                            },
                            "category": {
                                "type": "string",
                                "description": "조회할 카테고리명 (action이 'get_by_category'일 때 필요)"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]

        # 간소화된 시스템 프롬프트 (메뉴 정보 제거)
        order_form = self.get_order_form()
        sample_data = self.get_few_shot()
        
        default_system_prompt = f"""당신은 Burger House(버거하우스)에서 주문을 받는 봇, 이름은 '버거하우스'입니다.
        당신의 역할은 버거하우스에 온 손님을 친절하게 맞이하고, 그들의 주문을 정확하게 받거나 고객에게 필요한 카페, 메뉴 정보를 제공하는 것입니다.
        
        메뉴 정보가 필요할 때는 get_menu_info 함수를 사용하여 데이터베이스에서 조회하세요.
        - 카테고리 목록 조회: get_menu_info(action="get_categories")
        - 메뉴 검색: get_menu_info(action="search", query="검색어")
        - 특정 메뉴 조회: get_menu_info(action="get_by_id", menu_id=메뉴ID)
        - 카테고리별 메뉴 조회: get_menu_info(action="get_by_category", category="카테고리명")
        
        금액은 모든 상품이 등록된 후에 표기가 가능합니다. 그 이전에 가격을 물어본다면, 메뉴 선택이 완료된 후에 가격을 알려줄 수 있다고 답하세요.

        [**주문서 양식**]
        {order_form}
        [**주문서 양식끝**]
        
        [**대화 예시 시작**]
        {sample_data}
        [**대화 예시 끝**]
        """
        
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

    # Function Calling 구현 메서드들
    def get_menu_info(self, action, **kwargs):
        """메뉴 정보 조회 통합 함수 - GPT가 호출"""
        try:
            if action == "get_categories":
                return self._get_categories()
            elif action == "search":
                query = kwargs.get('query')
                if not query:
                    return "검색어가 필요합니다."
                return self._search_menu(query)
            elif action == "get_by_id":
                menu_id = kwargs.get('menu_id')
                if not menu_id:
                    return "메뉴 ID가 필요합니다."
                return self._get_menu_by_id(menu_id)
            elif action == "get_by_category":
                category = kwargs.get('category')
                if not category:
                    return "카테고리명이 필요합니다."
                return self._get_menu_by_category(category)
            else:
                return f"지원하지 않는 작업입니다: {action}"
                
        except Exception as e:
            return f"메뉴 정보 조회 중 오류가 발생했습니다: {e}"

    def _get_categories(self):
        """카테고리 목록 조회"""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT MENU_ID, MENU_NAME FROM Menu ORDER BY MENU_ID")
        results = cursor.fetchall()
        
        categories = []
        for row in results:
            categories.append({
                "menu_id": row["MENU_ID"],
                "menu_name": row["MENU_NAME"]
            })
        
        return {
            "action": "get_categories",
            "result": categories,
            "message": f"{len(categories)}개의 카테고리를 찾았습니다."
        }

    def _search_menu(self, query):
        """메뉴 검색"""
        cursor = self.db_connection.cursor()
        search_query = """
        SELECT A.MENU_ID, B.CATEGORY_NAME, A.MENU_NAME, A.PRICE
        FROM MENU A, MenuCategory B
        WHERE A.CATEGORY_ID = B.CATEGORY_ID 
        AND A.MENU_NAME LIKE ?
        ORDER BY B.CATEGORY_NAME, A.MENU_ID
        """
        
        cursor.execute(search_query, (f"%{query}%",))
        results = cursor.fetchall()
        
        menus = []
        for row in results:
            menus.append({
                "menu_id": row["MENU_ID"],
                "category": row["CATEGORY_NAME"],
                "name": row["MENU_NAME"],
                "price": row["PRICE"] if "PRICE" in row.keys() else "가격 정보 없음"
            })
        
        return {
            "action": "search",
            "query": query,
            "result": menus,
            "message": f"'{query}' 검색 결과 {len(menus)}개의 메뉴를 찾았습니다."
        }

    def _get_menu_by_id(self, menu_id):
        """특정 메뉴 ID로 조회"""
        cursor = self.db_connection.cursor()
        query = """
        SELECT A.MENU_ID, B.CATEGORY_NAME, A.MENU_NAME, A.PRICE
        FROM MENU A, MenuCategory B
        WHERE A.CATEGORY_ID = B.CATEGORY_ID 
        AND A.MENU_ID = ?
        """
        
        cursor.execute(query, (menu_id,))
        result = cursor.fetchone()
        
        if result:
            menu = {
                "menu_id": result["MENU_ID"],
                "category": result["CATEGORY_NAME"],
                "name": result["MENU_NAME"],
                "price": result["PRICE"] if "PRICE" in result.keys() else "가격 정보 없음"
            }
            return {
                "action": "get_by_id",
                "menu_id": menu_id,
                "result": menu,
                "message": f"메뉴 ID {menu_id}의 정보를 찾았습니다."
            }
        else:
            return {
                "action": "get_by_id",
                "menu_id": menu_id,
                "result": None,
                "message": f"메뉴 ID {menu_id}를 찾을 수 없습니다."
            }

    def _get_menu_by_category(self, category):
        """카테고리별 메뉴 조회"""
        cursor = self.db_connection.cursor()
        query = """
        SELECT A.MENU_ID, B.CATEGORY_NAME, A.MENU_NAME, A.PRICE
        FROM MENU A, MenuCategory B
        WHERE A.CATEGORY_ID = B.CATEGORY_ID 
        AND B.CATEGORY_NAME = ?
        ORDER BY A.MENU_ID
        """
        
        cursor.execute(query, (category,))
        results = cursor.fetchall()
        
        menus = []
        for row in results:
            menus.append({
                "menu_id": row["MENU_ID"],
                "category": row["CATEGORY_NAME"],
                "name": row["MENU_NAME"],
                "price": row["PRICE"] if "PRICE" in row.keys() else "가격 정보 없음"
            })
        
        return {
            "action": "get_by_category",
            "category": category,
            "result": menus,
            "message": f"'{category}' 카테고리에서 {len(menus)}개의 메뉴를 찾았습니다."
        }

    def _handle_function_calls(self, assistant_message):
        """GPT의 Function Call 요청 처리"""
        # assistant 메시지를 대화 기록에 추가 (tool_calls 포함)
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in assistant_message.tool_calls
            ]
        })
        
        # 각 tool call에 대해 결과 생성
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # 함수명에 따라 실제 메서드 호출
            if function_name == "get_menu_info":
                result = self.get_menu_info(**function_args)
            else:
                result = f"알 수 없는 함수: {function_name}"
            
            # 결과를 GPT에게 다시 전달
            self.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        # GPT가 function 결과를 받고 최종 응답 생성
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.conversation_history
        )
        
        final_response = response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": final_response
        })
        
        return final_response

    def chat_with_gpt_non_streaming(self, user_input):
        """Function Calling 지원 비스트리밍 채팅"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.conversation_history,
            tools=self.tools,
            tool_choice="auto"
        )
        
        # Function call이 있는지 확인
        if response.choices[0].message.tool_calls:
            gpt_response = self._handle_function_calls(response.choices[0].message)
        else:
            # 일반 응답 처리
            gpt_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": gpt_response})
        
        # 기존 주문 파싱 로직
        parsed_orders = self.parse_orders_from_response(gpt_response)
        if parsed_orders:
            print(f"✅ {len(parsed_orders)}개의 주문이 자동으로 등록되었습니다!")
        
        # [ORDER_COMPLETE] 태그 제거한 응답 반환
        display_response = gpt_response.split("[ORDER_COMPLETE]")[0].strip()
        return display_response

    def chat_with_gpt(self, user_input):
        """Function Calling 지원 스트리밍 채팅"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 먼저 non-streaming으로 function call 확인
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.conversation_history,
            tools=self.tools,
            tool_choice="auto"
        )
        
        # Function call이 있으면 처리
        if response.choices[0].message.tool_calls:
            full_response = self._handle_function_calls(response.choices[0].message)
        else:
            # Function call이 없으면 streaming으로 응답
            stream_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.conversation_history,
                max_tokens=200,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            for chunk in stream_response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
            
            # 대화 기록에 추가
            self.conversation_history.append({"role": "assistant", "content": full_response})
        
        # 주문 파싱 및 자동 등록
        parsed_orders = self.parse_orders_from_response(full_response)
        if parsed_orders:
            print(f"✅ {len(parsed_orders)}개의 주문이 자동으로 등록되었습니다!")
        
        # 사용자에게 보여줄 부분만 스트리밍
        display_response = full_response.split("[ORDER_COMPLETE]")[0].strip()
        
        # 단어 단위로 스트리밍 효과 생성
        import time
        words = display_response.split(' ')
        for i, word in enumerate(words):
            if i == 0:
                yield word
            else:
                yield ' ' + word
            time.sleep(0.05)

    # 기존 BurgerBot 메서드들 그대로 유지
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
                        order = self.add_single_order(int(order_data['BURGER']), 'burger', quantity, toppings)
                    elif 'CHICKEN' in order_data:
                        order = self.add_single_order(int(order_data['CHICKEN']), 'chicken', quantity)
                    elif 'SIDE' in order_data:
                        side_id = int(order_data['SIDE'])
                        order = self.add_single_order(side_id, 'side', quantity)
                    elif 'DRINK' in order_data:
                        drink_id = int(order_data['DRINK'])
                        order = self.add_single_order(drink_id, 'drink', quantity)
                    elif 'SAUCE' in order_data:
                        sauce_id = int(order_data['SAUCE'])
                        order = self.add_single_order(sauce_id, 'sauce', quantity)
                    
                    if order:
                        orders_added.append(order)
                        
            except Exception as e:
                print(f"주문 파싱 중 오류: {e}")
                continue
        
        return orders_added
    
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
        """Few-shot 예시를 반환하는 함수"""
        try:
            # PROMPT\FEW_SHOT 파일 읽기
            few_shot_path = os.path.join(os.path.dirname(__file__), "PROMPT", "FEW_SHOT.txt")
            
            with open(few_shot_path, 'r', encoding='utf-8') as file:
                few_shot_content = file.read()
            
            return few_shot_content
            
        except Exception as e:
            print(f"❌ Few-shot 예시 파일 읽기 실패: {e}")
            return "대화 예시를 불러올 수 없습니다."
    
    def get_order_summary(self):
        return self.order_formatter.format_order_summary(self.order_list)
    
    def start_greeting(self):
        greeting = "안녕하세요! Burger House에 오신 걸 환영합니다! 저는 버거하우스이에요. 무엇을 도와드릴까요? 오늘 맛있는 버거 주문하고 싶으시죠?"
        print(f"Bot: {greeting}")
        self.conversation_history.append({"role": "assistant", "content": greeting})
        return greeting

def main():
    bot = BurgerBotV2()
    print("=== Burger House 주문 시스템 V2 (Function Calling 지원) ===")
    
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