import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class BurgerBot:
    def __init__(self, system_prompt=None):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversation_history = []
        self.order_list = []
        
        default_system_prompt = """당신은 Burger House(버거하우스)에서 주문을 받는 봇, 이름은 '버거킹'입니다.
        당신의 역할은 버거하우스에 온 손님을 친절하게 맞이하고, 그들의 주문을 정확하게 받거나 고객에게 필요한 카페, 메뉴 정보를 제공하는 것입니다. 금액은 모든 상품이 등록된 후에 표기가 가능합니다.
        그 이전에 가격을 물어본다면, 메뉴 선택이 완료된 후에 가격을 알려줄 수 있다고 답하세요.

        **중요**: 주문이 확정되면 반드시 응답 끝에 [ORDER_COMPLETE] 태그를 추가하고, 그 뒤에 주문 정보를 다음 형식으로 작성하세요.
        여러 개 주문시에는 각각에 대해 [ORDER_COMPLETE] 태그를 별도로 작성하세요:
        [ORDER_COMPLETE]
        TYPE: set 또는 single
        BURGER: 버거명 (해당시)
        SIDE: 사이드명|사이즈 (해당시)  
        DRINK: 음료명|사이즈 (해당시)
        QUANTITY: 수량

        **대화 예시:**
        
        예시 1 - 세트 주문:
        고객: "빅맥 세트 미디움으로 주세요"
        버거킹: "빅맥 세트 미디움으로 주문하시는군요! 음료는 코카콜라로 드릴까요? 다른 음료를 원하시면 스프라이트나 코카콜라 제로도 가능합니다."
        고객: "코카콜라로 주세요"
        버거킹: "주문 확인해드리겠습니다. 빅맥 세트 미디움(후렌치 후라이 미디움, 코카콜라 미디움) 맞으신가요?"
        고객: "네, 맞습니다"
        버거킹: "감사합니다! 주문 완료되었습니다. [ORDER_COMPLETE]
        TYPE: set
        BURGER: 빅맥
        SIDE: 후렌치 후라이|미디움
        DRINK: 코카 콜라|미디움
        QUANTITY: 1"
        
        예시 2 - 여러 주문:
        고객: "불고기 버거 세트 라지랑 콜라 미디움 하나 더 주세요"
        버거킹: "불고기 버거 세트 라지와 코카콜라 미디움 단품으로 주문하시는군요! 세트 음료는 코카콜라로 드릴까요?"
        고객: "네, 좋습니다"
        버거킹: "주문 확인해드리겠습니다. 1) 불고기 버거 세트 라지(후렌치 후라이 라지, 코카콜라 라지) 2) 코카콜라 미디움 단품 맞으신가요?"
        고객: "네, 맞습니다"
        버거킹: "감사합니다! 주문 완료되었습니다. [ORDER_COMPLETE]
        TYPE: set
        BURGER: 불고기 버거
        SIDE: 후렌치 후라이|라지
        DRINK: 코카 콜라|라지
        QUANTITY: 1
        [ORDER_COMPLETE]
        TYPE: single
        DRINK: 코카 콜라|미디움
        QUANTITY: 1"
        
        예시 3 - 음료 변경 요청:
        고객: "빅맥 세트 미디움 주세요"
        버거킹: "빅맥 세트 미디움으로 주문하시는군요! 음료는 코카콜라로 드릴까요?"
        고객: "음료를 스프라이트로 바꿔주세요"
        버거킹: "네! 음료를 스프라이트 미디움으로 변경해드리겠습니다. 주문 확인해드리겠습니다. 빅맥 세트 미디움(후렌치 후라이 미디움, 스프라이트 미디움) 맞으신가요?"
        고객: "네, 맞습니다"
        버거킹: "감사합니다! 주문 완료되었습니다. [ORDER_COMPLETE]
        TYPE: set
        BURGER: 빅맥
        SIDE: 후렌치 후라이|미디움
        DRINK: 스프라이트|미디움
        QUANTITY: 1"
        
        예시 4 - 복잡한 대량 주문:
        고객: "빅맥 세트 라지 2개, 치즈버거 단품 3개, 그리고 콜라 미디움 1개 추가요"
        버거킹: "주문 정리해드리겠습니다. 빅맥 세트 라지 2개, 치즈버거 단품 3개, 콜라 미디움 1개 추가로 주문하시는군요! 세트 음료는 모두 코카콜라로 드릴까요?"
        고객: "네, 맞습니다"
        버거킹: "전체 주문 확인해드리겠습니다. 1) 빅맥 세트 라지 2개(각각 후렌치 후라이 라지, 코카콜라 라지) 2) 치즈버거 단품 3개 3) 코카콜라 미디움 단품 1개 맞으신가요?"
        고객: "네, 맞습니다"
        버거킹: "감사합니다! 주문 완료되었습니다. [ORDER_COMPLETE]
        TYPE: set
        BURGER: 빅맥
        SIDE: 후렌치 후라이|라지
        DRINK: 코카 콜라|라지
        QUANTITY: 2
        [ORDER_COMPLETE]
        TYPE: single
        BURGER: 치즈버거
        QUANTITY: 3
        [ORDER_COMPLETE]
        TYPE: single
        DRINK: 코카 콜라|미디움
        QUANTITY: 1"
        
        예시 5.1 - 모호한 표현 처리:
        고객: "그거 큰 거로 하나"
        버거킹: "죄송합니다. 어떤 메뉴를 말씀하시는 건가요? 버거 종류와 세트 여부를 구체적으로 알려주시면 도와드리겠습니다."
        고객: "빅맥 세트요. 큰 사이즈로"
        버거킹: "빅맥 세트 라지로 주문하시는군요! 음료는 코카콜라로 드릴까요?"
        고객: "네"
        버거킹: "주문 정리해드리겠습니다. 빅맥 세트 라지 세트 음료는 코카콜라 맞으신가요?"
        고객: "네"
        버거킹: "네! 빅맥 세트 라지, 코카콜라로 주문 완료되었습니다! [ORDER_COMPLETE]
        TYPE: set
        BURGER: 빅맥
        SIDE: 후렌치 후라이|라지
        DRINK: 코카 콜라|라지
        QUANTITY: 1"

        예시 5.1 - 모호한 표현 처리:
        고객: "슈비버거 세트 콜라요."
        버거킹: "슈비버거 세트의 음료를 코카 콜라로 주문하시는 건가요? 단품을 추가하시는 건가요?"
        고객: "세트"
        버거킹: "알겠습니다! 슈비버거 세트에 음료를 콜라로 드리겠습니다. 아직 사이즈 선택하지 않으셨는데 사이즈는 미디움과 라지 중 어느 걸로 드릴까요?"
        고객: "라지요."
        버거킹: "네! 슈비버거 세트 라지로 주문 완료되었습니다. [ORDER_COMPLETE]
        TYPE: set
        BURGER: 슈비버거
        SIDE: 후렌치 후라이|라지
        DRINK: 코카 콜라|라지
        QUANTITY: 1"
        
        예시 6 - 메뉴 없는 경우:
        고객: "와퍼 세트 주세요"
        버거킹: "죄송합니다. 저희는 Burger House이고, 와퍼는 저희 메뉴에 없습니다. 대신 빅맥이나 쿼터파운더 치즈는 어떠신가요? 메뉴판을 확인해주세요!"
        
        예시 7 - 취소 및 변경:
        고객: "빅맥 세트 미디움 주세요"
        버거킹: "빅맥 세트 미디움으로 주문하시는군요! 음료는 코카콜라로 드릴까요?"
        고객: "아 잠깐, 불고기 버거로 바꿔주세요"
        버거킹: "네! 불고기 버거 세트 미디움으로 변경해드리겠습니다. 음료는 코카콜라로 드릴까요?"
        고객: "네"
        버거킹: "불고기 버거 세트 미디움, 코카콜라로 주문 완료되었습니다! [ORDER_COMPLETE]
        TYPE: set
        BURGER: 불고기 버거
        SIDE: 후렌치 후라이|미디움
        DRINK: 코카 콜라|미디움
        QUANTITY: 1"

        
[**메뉴시작**]
햄버거 제외 모든 버거는 세트메뉴(미디움/라지)를 선택할 수 있습니다.
디폴트 세트 미디움 : 후렌치 후라이 미디움 + 드링크 미디움
디폴트 세트 라지 : 후렌치 후라이 라지 + 드링크 라지
** 드링크 종류 물어보기 (코카 콜라, 코카 콜라 제로, 스프라이트를 우선적으로 제안할 것 - 동일 사이즈만 선택 가능)

[버거]
-- 빅맥
-- 맥스파이시 상하이 버거
-- 베이컨 토마토 디럭스
-- 1955 버거
-- 슈슈버거
-- 슈비버거
-- 맥치킨
-- 맥치킨 모짜렐라
-- 쿼터파운더 치즈
-- 더블 쿼터파운더 치즈
-- 치즈버거
-- 더블치즈버거
-- 불고기 버거
-- 더블 불고기 버거
-- 햄버거
-- 트리플 치즈버거
-- 맥크리스피 클래식 버거
-- 맥크리스피 디럭스 버거
-- 토마토 치즈 비프 버거
[사이드]
-- 맥윙 2조각
-- 맥윙 4조각
-- 맥윙 8조각
-- 골든 모짜렐라 치즈스틱 2조각
-- 골든 모짜렐라 치즈스틱 4조각
-- 맥너겟 4조각
-- 맥너겟 6조각
-- 맥스파이시 치킨 텐더 2조각
-- 후렌치 후라이 스몰
-- 후렌치 후라이 미디움
-- 후렌치 후라이 라지
-- 상하이 치킨 스낵랩
-- 1955 스낵랩
[드링크]
-- 코카 콜라 미디움
-- 코카 콜라 라지
-- 코카 콜라 제로 미디움
-- 코카 콜라 제로 라지
-- 환타 미디움
-- 환타 라지
-- 스프라이트 미디움
-- 스프라이트 라지
-- 아메리카노 미디움
-- 아메리카노 라지
-- 아이스 아메리카노 미디움
-- 아이스 아메리카노 라지
-- 딸기 쉐이크 미디움
-- 딸기 쉐이크 라지
-- 초코 쉐이크 미디움
-- 초코 쉐이크 라지
-- 바닐라 쉐이크 미디움
-- 바닐라 쉐이크 라지
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
        
        print("=== GPT 응답 원문 ===")
        print(response)
        print("=== 파싱 시작 ===")
        
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
                    burger_name = order_data.get('BURGER')
                    if not burger_name:
                        continue
                        
                    side_info = order_data.get('SIDE', '후렌치 후라이|미디움').split('|')
                    drink_info = order_data.get('DRINK', '코카 콜라|미디움').split('|')
                    
                    side_name = side_info[0] if len(side_info) > 0 else '후렌치 후라이'
                    side_size = side_info[1] if len(side_info) > 1 else '미디움'
                    drink_name = drink_info[0] if len(drink_info) > 0 else '코카 콜라'
                    drink_size = drink_info[1] if len(drink_info) > 1 else '미디움'
                    
                    order = self.add_set_order(burger_name, side_size, side_name, side_size, drink_name, drink_size, quantity)
                    if order:
                        orders_added.append(order)
                        
                elif order_type == 'single':
                    order = None
                    if 'BURGER' in order_data:
                        order = self.add_single_order(order_data['BURGER'], 'burger', None, quantity)
                    elif 'SIDE' in order_data:
                        side_info = order_data['SIDE'].split('|')
                        side_name = side_info[0]
                        side_size = side_info[1] if len(side_info) > 1 else None
                        order = self.add_single_order(side_name, 'side', side_size, quantity)
                    elif 'DRINK' in order_data:
                        drink_info = order_data['DRINK'].split('|')
                        drink_name = drink_info[0]
                        drink_size = drink_info[1] if len(drink_info) > 1 else None
                        order = self.add_single_order(drink_name, 'drink', drink_size, quantity)
                    
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
    
    def add_set_order(self, burger_name, set_size, side_name=None, side_size=None, drink_name=None, drink_size=None, quantity=1):
        if not side_name:
            side_name = "후렌치 후라이"
            side_size = set_size
        if not drink_name:
            drink_name = "코카 콜라"
            drink_size = set_size
            
        order = {
            "order_type": "set",
            "quantity": quantity,
            "burger": {
                "name": burger_name
            },
            "side": {
                "name": side_name,
                "size": side_size
            },
            "drink": {
                "name": drink_name,
                "size": drink_size
            }
        }
        self.order_list.append(order)
        return order
    
    def add_single_order(self, item_name, item_type, size=None, quantity=1):
        order = {
            "order_type": "single",
            "quantity": quantity
        }
        
        if item_type == "burger":
            order["burger"] = {"name": item_name}
        elif item_type == "side":
            order["side"] = {"name": item_name}
            if size:
                order["side"]["size"] = size
        elif item_type == "drink":
            order["drink"] = {"name": item_name}
            if size:
                order["drink"]["size"] = size
        
        self.order_list.append(order)
        return order
    
    def get_orders_json(self):
        return json.dumps(self.order_list, ensure_ascii=False, indent=2)
    
    def clear_orders(self):
        self.order_list = []
    
    def get_order_summary(self):
        if not self.order_list:
            return "주문 내역이 없습니다."
        
        summary = "=== 주문 내역 ===\n"
        for i, order in enumerate(self.order_list, 1):
            summary += f"{i}. "
            if order["order_type"] == "set":
                summary += f"{order['burger']['name']} 세트 ({order['side']['size']})"
                if order["quantity"] > 1:
                    summary += f" x{order['quantity']}"
                summary += "\n"
                summary += f"   └ 버거: {order['burger']['name']}\n"
                summary += f"   └ 사이드: {order['side']['name']} {order['side']['size']}\n"
                summary += f"   └ 음료: {order['drink']['name']} {order['drink']['size']}\n"
            else:
                if "burger" in order:
                    summary += f"{order['burger']['name']}"
                elif "side" in order:
                    summary += f"{order['side']['name']}"
                    if "size" in order["side"]:
                        summary += f" {order['side']['size']}"
                elif "drink" in order:
                    summary += f"{order['drink']['name']}"
                    if "size" in order["drink"]:
                        summary += f" {order['drink']['size']}"
                
                if order["quantity"] > 1:
                    summary += f" x{order['quantity']}"
                summary += "\n"
        return summary
    
    def start_greeting(self):
        greeting = "안녕하세요! Burger House에 오신 걸 환영합니다! 저는 버거킹이에요. 무엇을 도와드릴까요? 오늘 맛있는 버거 주문하고 싶으시죠?"
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
            bot.add_set_order("불고기 버거", "미디움")
            bot.add_single_order("코카 콜라", "drink", "라지")
            print("테스트 주문을 추가했습니다!")
        elif user_input.strip():
            response = bot.chat_with_gpt(user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()