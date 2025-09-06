# -*- coding: utf-8 -*-
import os
import sys
from flask import Flask, render_template, request, jsonify, Response, stream_template
import json
from datetime import datetime
import threading
import time
from BurgerBot import BurgerBot

# 환경 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# 세션 관리
sessions = {}
session_lock = threading.Lock()

class BurgerChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.burger_bot = BurgerBot()
        self.order_items = []
        self.order_summary = ""
        self.created_at = datetime.now()
        
    def get_chat_response(self, message):
        try:
            # BurgerBot으로부터 응답 받기
            response = self.burger_bot.chat_streaming(message)
            
            # 주문 정보 업데이트
            if hasattr(self.burger_bot, 'order_items'):
                self.order_items = self.burger_bot.order_items
            
            if hasattr(self.burger_bot, 'order_summary'):
                self.order_summary = self.burger_bot.order_summary
            
            return response, self.order_summary
        except Exception as e:
            print(f"BurgerBot 오류: {e}")
            return "죄송합니다. 잠시 후 다시 시도해주세요.", self.order_summary

def get_or_create_session(session_id):
    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = BurgerChatSession(session_id)
        return sessions[session_id]

@app.route('/')
def index():
    return render_template('claude-burger.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not message.strip():
            return jsonify({'error': '메시지가 비어있습니다.'}), 400
        
        session = get_or_create_session(session_id)
        
        def generate_response():
            try:
                response_text, order_summary = session.get_chat_response(message)
                
                # 스트리밍 형태로 응답 전송
                words = response_text.split()
                current_text = ""
                
                for i, word in enumerate(words):
                    current_text += word + " "
                    
                    # [ORDER_COMPLETE] 태그 필터링
                    if "[ORDER_COMPLETE]" not in current_text:
                        chunk_data = {
                            'chunk': word + " ",
                            'complete': False
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    
                    # 자연스러운 속도로 전송
                    time.sleep(0.05)
                
                # 완료 신호
                final_data = {
                    'chunk': '',
                    'complete': True,
                    'order_summary': order_summary if order_summary else '주문 내역이 없습니다.'
                }
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error_data = {
                    'error': f'서버 오류: {str(e)}',
                    'complete': True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return Response(
            generate_response(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except Exception as e:
        print(f"채팅 오류: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

@app.route('/orders/<session_id>')
def get_orders(session_id):
    try:
        session = get_or_create_session(session_id)
        return jsonify({
            'order_summary': session.order_summary if session.order_summary else '주문 내역이 없습니다.',
            'order_items': session.order_items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear_orders/<session_id>', methods=['POST'])
def clear_orders(session_id):
    try:
        session = get_or_create_session(session_id)
        session.order_items = []
        session.order_summary = ""
        # BurgerBot 주문 초기화
        if hasattr(session.burger_bot, 'order_items'):
            session.burger_bot.order_items = []
        if hasattr(session.burger_bot, 'order_summary'):
            session.burger_bot.order_summary = ""
            
        return jsonify({'message': '주문 내역이 초기화되었습니다.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/new_session', methods=['POST'])
def new_session():
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        session = get_or_create_session(session_id)
        
        return jsonify({
            'message': '세션이 생성되었습니다.',
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 세션 정리 (메모리 관리)
def cleanup_old_sessions():
    while True:
        try:
            with session_lock:
                current_time = datetime.now()
                sessions_to_remove = []
                
                for session_id, session in sessions.items():
                    # 1시간 이상 된 세션 제거
                    if (current_time - session.created_at).seconds > 3600:
                        sessions_to_remove.append(session_id)
                
                for session_id in sessions_to_remove:
                    del sessions[session_id]
                    print(f"세션 {session_id} 정리됨")
                    
        except Exception as e:
            print(f"세션 정리 오류: {e}")
            
        time.sleep(1800)  # 30분마다 정리

# 백그라운드 세션 정리 스레드
cleanup_thread = threading.Thread(target=cleanup_old_sessions, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    print("Claude 스타일 버거 주문 봇 서버 시작...")
    print("http://localhost:5000 에서 확인하세요")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)