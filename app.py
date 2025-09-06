# -*- coding: utf-8 -*-
import os
import sys
from flask import Flask, render_template, request, jsonify
import json
from BurgerBot import BurgerBot

# Windows에서 UTF-8 출력 설정
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

# 글로벌 봇 인스턴스 관리를 위한 딕셔너리
# - 각 세션 ID별로 별도의 BurgerBot 인스턴스를 저장
# - 사용자가 브라우저를 새로고침해도 대화 히스토리와 주문 내역이 유지됨
# - 서버가 재시작되면 모든 세션 데이터가 초기화됨
bot_instances = {}

def get_bot_instance(session_id):
    """
    세션 ID에 해당하는 봇 인스턴스를 반환
    
    Args:
        session_id (str): 클라이언트에서 전송한 세션 식별자
        
    Returns:
        BurgerBot: 해당 세션의 봇 인스턴스
        
    동작:
        - 새 세션 ID인 경우: 새 BurgerBot 인스턴스 생성 및 인사말 시작
        - 기존 세션 ID인 경우: 저장된 인스턴스 반환 (대화 히스토리 유지)
    """
    if session_id not in bot_instances:
        bot_instances[session_id] = BurgerBot()
        bot_instances[session_id].start_greeting()
    return bot_instances[session_id]


@app.route('/')
def claude_chat():
    #return render_template('claude-chat.html')
    return render_template('claude-chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    채팅 메시지를 처리하는 메인 엔드포인트
    
    요청 데이터:
        - message: 사용자 입력 메시지
        - session_id: 세션 식별자 (기본값: 'default')
        - streaming: 스트리밍 모드 사용 여부 (기본값: True)
    
    동작:
        1. 세션 ID로 기존 봇 인스턴스를 가져오거나 새로 생성
        2. 스트리밍/논스트리밍 모드에 따라 응답 처리
        3. 대화 히스토리는 봇 인스턴스에 자동으로 누적됨
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')  # 세션별 대화 구분
        use_streaming = data.get('streaming', True)
        
        if not user_message.strip():
            return jsonify({'error': '메시지를 입력해주세요.'}), 400
        
        # 세션 ID로 봇 인스턴스 가져오기 (대화 히스토리 유지)
        # - 같은 세션 ID면 이전 대화를 이어감
        # - 다른 세션 ID면 새로운 대화 시작
        bot = get_bot_instance(session_id)
        
        if use_streaming:
            def generate():
                try:
                    for chunk in bot.chat_with_gpt(user_message):
                        if chunk:
                            yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                    
                    # 주문 정보 전송
                    yield f"data: {json.dumps({'orders': bot.get_orders_json(), 'order_summary': bot.get_order_summary(), 'complete': True}, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    print(f"Streaming error: {e}")
                    # 스트리밍 실패 시 non-streaming으로 폴백
                    try:
                        response = bot.chat_with_gpt_non_streaming(user_message)
                        yield f"data: {json.dumps({'chunk': response, 'complete': True, 'orders': bot.get_orders_json(), 'order_summary': bot.get_order_summary()}, ensure_ascii=False)}\n\n"
                    except Exception as fallback_error:
                        yield f"data: {json.dumps({'error': f'오류가 발생했습니다: {str(fallback_error)}'}, ensure_ascii=False)}\n\n"
            
            return app.response_class(generate(), mimetype='text/plain; charset=utf-8')
        else:
            # Non-streaming 모드
            bot_response = bot.chat_with_gpt_non_streaming(user_message)
            return jsonify({
                'response': bot_response,
                'orders': bot.get_orders_json(),
                'order_summary': bot.get_order_summary()
            })
        
    except Exception as e:
        return jsonify({'error': f'오류가 발생했습니다: {str(e)}'}), 500

@app.route('/orders/<session_id>')
def get_orders(session_id):
    try:
        if session_id in bot_instances:
            bot = bot_instances[session_id]
            return jsonify({
                'orders': bot.get_orders_json(),
                'order_summary': bot.get_order_summary()
            })
        else:
            return jsonify({
                'orders': '[]',
                'order_summary': '주문 내역이 없습니다.'
            })
    except Exception as e:
        return jsonify({'error': f'주문 조회 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/clear_orders/<session_id>', methods=['POST'])
def clear_orders(session_id):
    try:
        if session_id in bot_instances:
            bot = bot_instances[session_id]
            bot.clear_orders()
            return jsonify({'message': '주문 내역을 초기화했습니다.'})
        else:
            return jsonify({'message': '주문 내역이 없습니다.'})
    except Exception as e:
        return jsonify({'error': f'주문 초기화 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/new_session', methods=['POST'])
def new_session():
    """
    새로운 채팅 세션을 시작하는 엔드포인트
    
    동작:
        1. 기존 세션 데이터 완전 삭제 (대화 히스토리 + 주문 내역)
        2. 새로운 BurgerBot 인스턴스 생성
        3. 초기 인사말 반환
        
    사용 시나리오:
        - 사용자가 "새 대화" 버튼을 클릭했을 때
        - 완전히 새로운 주문을 시작하고 싶을 때
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        
        # 기존 세션 데이터 완전 삭제하고 새 세션 생성
        # 이전 대화 히스토리와 주문 내역이 모두 초기화됨
        bot_instances[session_id] = BurgerBot()
        greeting = bot_instances[session_id].start_greeting()
        
        return jsonify({
            'message': '새 세션이 시작되었습니다.',
            'greeting': greeting
        })
    except Exception as e:
        return jsonify({'error': f'세션 생성 중 오류가 발생했습니다: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)