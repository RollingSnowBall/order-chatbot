// 전역 변수
let sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
let isProcessing = false;
let messageId = 0;

// DOM 요소
const messagesContainer = document.getElementById('messagesContainer');
const messagesList = document.getElementById('messagesList');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const charCount = document.getElementById('charCount');
const errorToast = document.getElementById('errorToast');
const orderSidebar = document.getElementById('orderSidebar');
const orderToggleBtn = document.getElementById('orderToggleBtn');
const closeSidebar = document.getElementById('closeSidebar');
const mobileOverlay = document.getElementById('mobileOverlay');
const orderSummary = document.getElementById('orderSummary');
const clearOrdersBtn = document.getElementById('clearOrdersBtn');

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
    initializeSession();
});

// 채팅 초기화
function initializeChat() {
    adjustTextareaHeight();
    updateSendButton();
    updateCharCount();
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 메시지 입력 이벤트
    messageInput.addEventListener('input', handleInput);
    messageInput.addEventListener('keydown', handleKeyDown);
    messageInput.addEventListener('paste', handlePaste);
    
    // 전송 버튼
    sendButton.addEventListener('click', sendMessage);
    
    // 주문 사이드바 관련
    orderToggleBtn.addEventListener('click', toggleOrderSidebar);
    closeSidebar.addEventListener('click', closeOrderSidebar);
    mobileOverlay.addEventListener('click', closeOrderSidebar);
    clearOrdersBtn.addEventListener('click', clearOrders);
    
    // 토스트 닫기
    errorToast.querySelector('.toast-close').addEventListener('click', hideErrorToast);
    
    // 윈도우 리사이즈 이벤트
    window.addEventListener('resize', handleResize);
    
    // ESC 키로 사이드바 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeOrderSidebar();
        }
    });
    
    // 모바일 키보드 대응
    if (window.innerWidth <= 768) {
        setupMobileKeyboardHandling();
    }
}

// 세션 초기화
async function initializeSession() {
    try {
        const response = await fetch('/new_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        console.log('세션 초기화:', data);
        updateOrderDisplay();
    } catch (error) {
        console.error('세션 초기화 오류:', error);
    }
}

// 입력 처리
function handleInput() {
    adjustTextareaHeight();
    updateSendButton();
    updateCharCount();
}

// 키 입력 처리
function handleKeyDown(e) {
    if (e.key === 'Enter') {
        if (e.shiftKey) {
            return; // Shift+Enter: 줄바꿈
        } else {
            e.preventDefault();
            sendMessage(); // Enter: 메시지 전송
        }
    }
    
    if (e.key === 'Escape') {
        messageInput.blur();
        closeOrderSidebar();
    }
}

// 붙여넣기 처리
function handlePaste(e) {
    setTimeout(() => {
        adjustTextareaHeight();
        updateCharCount();
    }, 0);
}

// 텍스트 영역 높이 자동 조정
function adjustTextareaHeight() {
    messageInput.style.height = 'auto';
    const scrollHeight = messageInput.scrollHeight;
    const maxHeight = 120;
    
    if (scrollHeight <= maxHeight) {
        messageInput.style.height = scrollHeight + 'px';
        messageInput.style.overflowY = 'hidden';
    } else {
        messageInput.style.height = maxHeight + 'px';
        messageInput.style.overflowY = 'auto';
    }
}

// 전송 버튼 상태 업데이트
function updateSendButton() {
    const hasText = messageInput.value.trim().length > 0;
    sendButton.disabled = !hasText || isProcessing;
}

// 글자 수 카운트 업데이트
function updateCharCount() {
    const currentLength = messageInput.value.length;
    const maxLength = parseInt(messageInput.getAttribute('maxlength'));
    charCount.textContent = `${currentLength} / ${maxLength}`;
    
    if (currentLength > maxLength * 0.9) {
        charCount.style.color = '#dc3545';
    } else if (currentLength > maxLength * 0.8) {
        charCount.style.color = '#ffc107';
    } else {
        charCount.style.color = '#6c757d';
    }
}

// 메시지 전송
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isProcessing) return;
    
    // UI 업데이트
    isProcessing = true;
    updateSendButton();
    addUserMessage(text);
    messageInput.value = '';
    adjustTextareaHeight();
    updateCharCount();
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
                message: text,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error('네트워크 응답이 올바르지 않습니다.');
        }
        
        hideTypingIndicator();
        messagesList.appendChild(botMessageDiv);
        scrollToBottom();
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();
            
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
                        console.error('JSON 파싱 오류:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('메시지 전송 오류:', error);
        hideTypingIndicator();
        addBotMessage('죄송합니다. 서버 연결에 문제가 발생했습니다.');
        showErrorToast();
    } finally {
        isProcessing = false;
        updateSendButton();
        messageInput.focus();
    }
}

// 사용자 메시지 추가
function addUserMessage(text) {
    const message = {
        id: messageId++,
        type: 'user',
        text: text,
        timestamp: new Date()
    };
    
    const messageElement = createMessageElement(message);
    messagesList.appendChild(messageElement);
    scrollToBottom();
}

// 봇 메시지 추가
function addBotMessage(text) {
    const message = {
        id: messageId++,
        type: 'ai',
        text: text,
        timestamp: new Date()
    };
    
    const messageElement = createMessageElement(message);
    messagesList.appendChild(messageElement);
    scrollToBottom();
}

// 메시지 요소 생성
function createMessageElement(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.type}-message`;
    messageDiv.setAttribute('data-timestamp', formatTime(message.timestamp));
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    const avatarIcon = document.createElement('div');
    avatarIcon.className = 'avatar-icon';
    
    if (message.type === 'user') {
        avatarIcon.textContent = '👤';
    } else {
        avatarIcon.textContent = '🤖';
    }
    
    avatar.appendChild(avatarIcon);
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const text = document.createElement('div');
    text.className = 'message-text';
    text.textContent = message.text;
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = formatTime(message.timestamp);
    
    content.appendChild(text);
    content.appendChild(time);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    return messageDiv;
}

// 봇 메시지 요소 생성 (스트리밍용)
function createBotMessageElement() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ai-message';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<div class="avatar-icon">🤖</div>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const text = document.createElement('div');
    text.className = 'message-text';
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = formatTime(new Date());
    
    content.appendChild(text);
    content.appendChild(time);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    return messageDiv;
}

// 시간 포맷팅
function formatTime(date) {
    return date.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// 타이핑 인디케이터 표시/숨기기
function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    scrollToBottom();
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// 메시지 하단으로 스크롤
function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

// 주문 사이드바 토글
function toggleOrderSidebar() {
    if (window.innerWidth <= 768) {
        orderSidebar.classList.toggle('active');
        mobileOverlay.classList.toggle('active');
        
        if (orderSidebar.classList.contains('active')) {
            updateOrderDisplay();
        }
    }
}

// 주문 사이드바 닫기
function closeOrderSidebar() {
    orderSidebar.classList.remove('active');
    mobileOverlay.classList.remove('active');
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
    } catch (error) {
        console.error('주문 내역 업데이트 오류:', error);
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
        console.error('주문 초기화 오류:', error);
        addBotMessage('주문 초기화 중 오류가 발생했습니다.');
    }
}

// 에러 토스트 표시/숨김
function showErrorToast() {
    errorToast.style.display = 'block';
    setTimeout(() => {
        hideErrorToast();
    }, 3000);
}

function hideErrorToast() {
    errorToast.style.display = 'none';
}

// 윈도우 리사이즈 처리
function handleResize() {
    adjustTextareaHeight();
    scrollToBottom();
    
    // 데스크톱으로 전환 시 사이드바 상태 리셋
    if (window.innerWidth > 768) {
        closeOrderSidebar();
    }
}

// 모바일 키보드 처리
function setupMobileKeyboardHandling() {
    let initialViewportHeight = window.innerHeight;
    
    function handleViewportChange() {
        const currentHeight = window.innerHeight;
        const heightDiff = initialViewportHeight - currentHeight;
        const inputContainer = document.querySelector('.input-container');
        
        if (heightDiff > 100) {
            document.body.classList.add('keyboard-visible');
            // 모바일에서는 키보드 위로 입력창 이동
            if (window.innerWidth <= 768) {
                inputContainer.style.bottom = (heightDiff - 20) + 'px';
            }
            setTimeout(() => scrollToBottom(), 100);
        } else {
            document.body.classList.remove('keyboard-visible');
            if (window.innerWidth <= 768) {
                inputContainer.style.bottom = '0px';
            }
        }
    }
    
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            initialViewportHeight = window.innerHeight;
            handleViewportChange();
        }, 500);
    });
    
    messageInput.addEventListener('focus', () => {
        if (window.innerWidth <= 768) {
            setTimeout(handleViewportChange, 300);
        }
    });
    
    messageInput.addEventListener('blur', () => {
        if (window.innerWidth <= 768) {
            setTimeout(handleViewportChange, 300);
        }
    });
}

// 페이지 로드 완료 후 입력 필드에 포커스
window.addEventListener('load', function() {
    if (window.innerWidth > 768) {
        messageInput.focus();
    }
});

// 개발용 함수들
window.clearAllMessages = function() {
    const messages = messagesList.querySelectorAll('.message:not(:first-child)');
    messages.forEach(msg => msg.remove());
};

window.showDebugInfo = function() {
    console.log('Session ID:', sessionId);
    console.log('Messages count:', messagesList.children.length);
    console.log('Is processing:', isProcessing);
};