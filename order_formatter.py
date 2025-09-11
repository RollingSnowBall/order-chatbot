# -*- coding: utf-8 -*-
import json
import os
from typing import Dict, List, Any

class OrderFormatter:
    def __init__(self, rules_file_path=None):
        """
        주문 포맷터 초기화
        
        Args:
            rules_file_path: 룰셋 JSON 파일 경로 (기본값: config/order_format_rules.json)
        """
        if rules_file_path is None:
            rules_file_path = os.path.join(os.path.dirname(__file__), "config", "order_format_rules.json")
        
        self.rules = self._load_rules(rules_file_path)
    
    def _load_rules(self, file_path: str) -> Dict:
        """룰셋 JSON 파일을 로드합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"❌ 룰셋 파일 로드 실패: {e}")
            return self._get_default_rules()
    
    def _get_default_rules(self) -> Dict:
        """기본 룰셋을 반환합니다 (백업용)."""
        return {
            "order_formats": {},
            "suffix_rules": {},
            "conditional_items": {},
            "summary_header": "=== 주문 내역 ===",
            "empty_order_message": "주문 내역이 없습니다."
        }
    
    def format_order_summary(self, order_list: List[Dict]) -> str:
        """
        주문 리스트를 포맷팅된 요약으로 변환합니다.
        
        Args:
            order_list: 주문 데이터 리스트
            
        Returns:
            포맷팅된 주문 요약 문자열
        """
        if not order_list:
            return self.rules.get("empty_order_message", "주문 내역이 없습니다.")
        
        summary = self.rules.get("summary_header", "=== 주문 내역 ===") + "\n"
        
        for i, order in enumerate(order_list, 1):
            order_text = self._format_single_order(order, i)
            summary += order_text + "\n"
        
        return summary.strip()
    
    def _format_single_order(self, order: Dict, order_number: int) -> str:
        """단일 주문을 포맷팅합니다."""
        order_type = order.get("order_type")
        
        if order_type == "set":
            return self._format_set_order(order, order_number)
        elif order_type == "single":
            return self._format_single_item_order(order, order_number)
        else:
            return f"{order_number}. 알 수 없는 주문 타입"
    
    def _format_set_order(self, order: Dict, order_number: int) -> str:
        """세트 주문을 포맷팅합니다."""
        set_type = order.get("set_type", "burger_set")
        format_rules = self.rules.get("order_formats", {}).get("set", {}).get(set_type)
        
        if not format_rules:
            return f"{order_number}. 알 수 없는 세트 타입: {set_type}"
        
        # 변수 추출
        variables = self._extract_variables_from_order(order, order_number)
        
        # 헤더 포맷팅
        header = self._format_template(format_rules.get("header", ""), variables)
        
        # 아이템 포맷팅
        items = []
        for item_template in format_rules.get("items", []):
            # 토핑 처리 - 각 토핑을 별도 라인으로
            if "토핑" in item_template and variables.get("toppings"):
                toppings_list = variables["toppings"]
                if isinstance(toppings_list, list):
                    for topping_id in toppings_list:
                        topping_line = f"      + 토핑: 메뉴ID {topping_id}"
                        items.append(topping_line)
                else:
                    # 단일 토핑인 경우
                    topping_line = f"      + 토핑: 메뉴ID {toppings_list}"
                    items.append(topping_line)
            # 조건부 아이템 체크 (토핑이 아닌 경우)
            elif self._should_include_item(item_template, variables):
                formatted_item = self._format_template(item_template, variables)
                if formatted_item.strip():  # 빈 문자열이 아닌 경우만 추가
                    items.append(formatted_item)
        
        # 결합
        result = header
        if items:
            result += "\n" + "\n".join(items)
        
        return result
    
    def _format_single_item_order(self, order: Dict, order_number: int) -> str:
        """단품 주문을 포맷팅합니다."""
        # 주문에서 아이템 타입 찾기
        item_type = None
        for key in ["burger", "chicken", "side", "drink", "sauce"]:
            if key in order:
                item_type = key
                break
        
        if not item_type:
            return f"{order_number}. 알 수 없는 단품 주문"
        
        format_rules = self.rules.get("order_formats", {}).get("single", {}).get(item_type)
        
        if not format_rules:
            return f"{order_number}. 알 수 없는 단품 타입: {item_type}"
        
        # 변수 추출
        variables = self._extract_variables_from_order(order, order_number)
        
        # 헤더 포맷팅 (토핑 접미사 제거)
        header_template = format_rules.get("header", "")
        header = header_template.replace("{toppings_suffix}", "").format(**variables)
        
        # 버거 단품의 경우 토핑을 별도 라인으로 추가
        result = header
        if item_type == "burger" and variables.get("toppings"):
            toppings_list = variables["toppings"]
            if isinstance(toppings_list, list):
                for topping_id in toppings_list:
                    result += f"\n      + 토핑: 메뉴ID {topping_id}"
            else:
                result += f"\n      + 토핑: 메뉴ID {toppings_list}"
        
        return result
    
    def _extract_variables_from_order(self, order: Dict, order_number: int) -> Dict:
        """주문에서 템플릿 변수를 추출합니다."""
        variables = {
            "order_number": order_number,
            "quantity": order.get("quantity", 1)
        }
        
        # 수량 접미사
        if variables["quantity"] > 1:
            variables["quantity_suffix"] = f" x{variables['quantity']}"
        else:
            variables["quantity_suffix"] = ""
        
        # 각 아이템에서 ID 추출
        if "burger" in order:
            variables["burger_id"] = order["burger"].get("menu_id")
            toppings = order["burger"].get("toppings")
            if toppings:
                variables["toppings"] = toppings
                variables["toppings_suffix"] = f" + 토핑: {toppings}"
            else:
                variables["toppings"] = None
                variables["toppings_suffix"] = ""
        
        if "chicken" in order:
            variables["chicken_id"] = order["chicken"].get("menu_id")
        
        if "side" in order:
            variables["side_id"] = order["side"].get("menu_id")
        
        if "drink" in order:
            variables["drink_id"] = order["drink"].get("menu_id")
        
        if "sauce" in order:
            variables["sauce_id"] = order["sauce"].get("menu_id")
            variables["sauce_quantity"] = order["sauce"].get("quantity", 1)
        
        return variables
    
    def _format_template(self, template: str, variables: Dict) -> str:
        """템플릿 문자열에 변수를 적용합니다."""
        try:
            return template.format(**variables)
        except KeyError as e:
            # 누락된 변수가 있으면 그 부분을 빈 문자열로 처리
            return template
    
    def _should_include_item(self, item_template: str, variables: Dict) -> bool:
        """조건부 아이템을 포함할지 결정합니다."""
        # 토핑 관련 조건 체크
        if "토핑" in item_template and variables.get("toppings") is None:
            return False
        
        # 사이드 관련 조건 체크  
        if "사이드" in item_template and variables.get("side_id") is None:
            return False
        
        return True