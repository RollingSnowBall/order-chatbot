// 전역 변수
let sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
let isProcessing = false;
let typingIndicatorElement = null;

// DOM 요소
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const orderSummary = document.getElementById('orderSummary');
const clearOrdersBtn = document.getElementById('clearOrdersBtn');
const toggleOrdersBtn = document.getElementById('toggleOrdersBtn');
const mobileOrderToggle = document.getElementById('mobileOrderToggle');
const headerOrderBtn = document.getElementById('headerOrderBtn');
const sidebar = document.querySelector('.sidebar');

// 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', function() {
    // 전송 버튼 클릭
    sendButton.addEventListener('click', sendMessage);
    
    // 엔터키로 메시지 전송
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 주문 초기화 버튼
    clearOrdersBtn.addEventListener('click', clearOrders);
    
    // 주문 접기/펼치기 버튼
    toggleOrdersBtn.addEventListener('click', toggleOrderSummary);
    
    // 모바일 주문 토글 (하단 플로팅 버튼)
    mobileOrderToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
        updateMobileToggleText();
    });
    
    // 헤더 주문 버튼 (상단 헤더)
    headerOrderBtn.addEventListener('click', function() {
        sidebar.classList.toggle('active');
        updateMobileToggleText();
    });
    
    // 사이드바 외부 클릭 시 닫기 (모바일)
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && 
            sidebar.classList.contains('active') && 
            !sidebar.querySelector('.order-section').contains(e.target) && 
            !mobileOrderToggle.contains(e.target) &&
            !headerOrderBtn.contains(e.target)) {
            closeMobileOrderPanel();
        }
    });
    
    // ESC 키로 주문 패널 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && window.innerWidth <= 768 && sidebar.classList.contains('active')) {
            closeMobileOrderPanel();
        }
    });
    
    // 초기 세션 생성
    initializeSession();
});

// 초기 세션 생성
function initializeSession() {
    fetch('/new_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            session_id: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Session initialized:', data);
        updateOrderDisplay();
    })
    .catch(error => {
        console.error('Error initializing session:', error);
    });
}

// 메시지 전송
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isProcessing) return;
    
    // UI 업데이트
    isProcessing = true;
    updateSendButton();
    addUserMessage(message);
    messageInput.value = '';
    showTypingIndicator();
    
    // 스트리밍 봇 메시지 준비
    const botMessageDiv = createBotMessageElement();
    const botTextDiv = botMessageDiv.querySelector('.message-text');
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        hideTypingIndicator();
        chatMessages.appendChild(botMessageDiv);
        scrollToBottom();
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // 마지막 불완전한 라인 보관
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        
                        if (data.error) {
                            botTextDiv.textContent = '죄송합니다. 오류가 발생했습니다: ' + data.error;
                            break;
                        }
                        
                        if (data.chunk) {
                            botTextDiv.textContent += data.chunk;
                            scrollToBottom();
                        }
                        
                        if (data.complete) {
                            updateOrderDisplay(data.order_summary);
                        }
                        
                    } catch (e) {
                        console.error('JSON parsing error:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        addBotMessage('죄송합니다. 서버 연결에 문제가 발생했습니다.');
    } finally {
        isProcessing = false;
        updateSendButton();
        messageInput.focus();
    }
}

// 사용자 메시지 추가
function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">👤</div>
            <div class="message-text">${escapeHtml(text)}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// 봇 메시지 추가
function addBotMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">🤖</div>
            <div class="message-text">${escapeHtml(text)}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// 봇 메시지 요소 생성 (스트리밍용)
function createBotMessageElement() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">🤖</div>
            <div class="message-text streaming-text"></div>
        </div>
    `;
    return messageDiv;
}

// HTML 이스케이프
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 채팅 영역 스크롤
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 전송 버튼 상태 업데이트
function updateSendButton() {
    sendButton.disabled = isProcessing;
    sendButton.textContent = isProcessing ? '전송중...' : '전송';
}

// 타이핑 인디케이터 표시/숨기기
function showTypingIndicator() {
    // 기존 타이핑 인디케이터가 있다면 제거
    if (typingIndicatorElement) {
        typingIndicatorElement.remove();
    }
    
    // 새로운 타이핑 인디케이터 생성
    typingIndicatorElement = document.createElement('div');
    typingIndicatorElement.className = 'typing-indicator';
    typingIndicatorElement.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">🤖</div>
            <div class="message-text">
                <div class="typing-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
        </div>
    `;
    
    // 채팅 메시지의 맨 끝에 추가
    chatMessages.appendChild(typingIndicatorElement);
    scrollToBottom();
}

function hideTypingIndicator() {
    if (typingIndicatorElement) {
        typingIndicatorElement.remove();
        typingIndicatorElement = null;
    }
}

// 주문 내역 업데이트
async function updateOrderDisplay(orderSummaryText = null) {
    try {
        if (orderSummaryText) {
            orderSummary.textContent = orderSummaryText;
        } else {
            const response = await fetch(`/orders/${sessionId}`);
            const data = await response.json();
            
            if (data.error) {
                orderSummary.textContent = '주문 조회 중 오류가 발생했습니다.';
            } else {
                orderSummary.textContent = data.order_summary;
            }
        }
        
        // 주문 내역이 있을 때 모바일 알림
        if (window.innerWidth <= 768 && orderSummary.textContent !== '주문 내역이 없습니다.') {
            animateMobileOrderToggle();
        }
        
    } catch (error) {
        console.error('Error updating order display:', error);
        orderSummary.textContent = '주문 조회 중 오류가 발생했습니다.';
    }
}

// 주문 초기화
async function clearOrders() {
    try {
        const response = await fetch(`/clear_orders/${sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            addBotMessage('주문 초기화 중 오류가 발생했습니다: ' + data.error);
        } else {
            addBotMessage('주문 내역을 초기화했습니다.');
            updateOrderDisplay();
        }
        
    } catch (error) {
        console.error('Error clearing orders:', error);
        addBotMessage('주문 초기화 중 오류가 발생했습니다.');
    }
}

// 주문 요약 접기/펼치기
function toggleOrderSummary() {
    const isCollapsed = orderSummary.style.display === 'none';
    orderSummary.style.display = isCollapsed ? 'block' : 'none';
    toggleOrdersBtn.textContent = isCollapsed ? '주문 접기' : '주문 펼치기';
}

// 모바일 주문 패널 닫기
function closeMobileOrderPanel() {
    const orderSection = sidebar.querySelector('.order-section');
    if (orderSection) {
        orderSection.style.animation = 'slideDownOut 0.3s ease-out';
        setTimeout(() => {
            sidebar.classList.remove('active');
            orderSection.style.animation = '';
            updateMobileToggleText();
        }, 300);
    } else {
        sidebar.classList.remove('active');
        updateMobileToggleText();
    }
}

// 모바일 토글 버튼 텍스트 업데이트
function updateMobileToggleText() {
    const isActive = sidebar.classList.contains('active');
    mobileOrderToggle.innerHTML = isActive ? '✕' : '📋';
}

// 모바일 주문 토글 애니메이션
function animateMobileOrderToggle() {
    if (window.innerWidth <= 768 && !sidebar.classList.contains('active')) {
        mobileOrderToggle.style.transform = 'scale(1.2)';
        mobileOrderToggle.style.background = '#c0392b';
        
        setTimeout(() => {
            mobileOrderToggle.style.transform = 'scale(1)';
            mobileOrderToggle.style.background = '#e74c3c';
        }, 200);
    }
}

// 화면 크기 변경 감지
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        sidebar.classList.remove('active');
        updateMobileToggleText();
    }
});

// 페이지 로드 완료 후 입력 필드에 포커스
window.addEventListener('load', function() {
    if (window.innerWidth > 768) {
        messageInput.focus();
    }
});

// 모바일 키보드 대응
let initialViewportHeight = window.innerHeight;

function handleViewportChange() {
    if (window.innerWidth <= 768) {
        const currentHeight = window.innerHeight;
        const heightDiff = initialViewportHeight - currentHeight;
        const inputContainer = document.querySelector('.chat-input-container');
        
        // 키보드가 올라온 경우 (화면 높이가 100px 이상 줄어든 경우)
        if (heightDiff > 100) {
            document.body.classList.add('keyboard-visible');
            // 입력창을 키보드 바로 위로 이동
            inputContainer.style.bottom = (heightDiff - 20) + 'px';
            // 채팅 영역 패딩 조정
            chatMessages.style.paddingBottom = (heightDiff + 80) + 'px';
            setTimeout(() => scrollToBottom(), 100);
        } else {
            document.body.classList.remove('keyboard-visible');
            // 입력창을 다시 화면 하단으로
            inputContainer.style.bottom = '0px';
            chatMessages.style.paddingBottom = '100px';
        }
    }
}

// 화면 크기 변화 감지 (키보드 up/down)
window.addEventListener('resize', handleViewportChange);
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        initialViewportHeight = window.innerHeight;
        handleViewportChange();
    }, 500);
});

// 입력 필드 포커스/블러 이벤트
messageInput.addEventListener('focus', function() {
    if (window.innerWidth <= 768) {
        setTimeout(() => {
            handleViewportChange();
            scrollToBottom();
        }, 300);
    }
});

messageInput.addEventListener('blur', function() {
    if (window.innerWidth <= 768) {
        setTimeout(() => {
            handleViewportChange();
        }, 300);
    }
});