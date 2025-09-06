// 전역 변수
let messageHistory = [];
let isTyping = false;
let messageId = 0;
let orderList = [];
let isOrderSidebarOpen = false;

// DOM 요소
const messagesContainer = document.getElementById('messagesContainer');
const messagesList = document.getElementById('messagesList');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const charCount = document.getElementById('charCount');
const errorToast = document.getElementById('errorToast');
const orderSidebar = document.getElementById('orderSidebar');
const orderSummary = document.getElementById('orderSummary');
const toggleOrderBtn = document.getElementById('toggleOrderBtn');
const closeOrderBtn = document.getElementById('closeOrderBtn');
const clearOrdersBtn = document.getElementById('clearOrdersBtn');
const finalizeOrderBtn = document.getElementById('finalizeOrderBtn');

// 로컬 스토리지 키
const STORAGE_KEY = 'claude-chat-history';
const ORDER_STORAGE_KEY = 'claude-orders';

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
    loadChatHistory();
    loadOrders();
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
    
    // 토스트 닫기
    errorToast.querySelector('.toast-close').addEventListener('click', hideErrorToast);
    
    // 주문 사이드바 이벤트
    toggleOrderBtn.addEventListener('click', toggleOrderSidebar);
    closeOrderBtn.addEventListener('click', closeOrderSidebar);
    clearOrdersBtn.addEventListener('click', clearOrders);
    finalizeOrderBtn.addEventListener('click', finalizeOrder);
    
    // 윈도우 리사이즈 이벤트
    window.addEventListener('resize', handleResize);
    
    // 모바일 키보드 대응
    if (window.innerWidth <= 768) {
        setupMobileKeyboardHandling();
    }
    
    // 포커스 트랩 설정
    setupFocusTrap();
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
            // Shift+Enter: 줄바꿈 (기본 동작 유지)
            return;
        } else {
            // Enter: 메시지 전송
            e.preventDefault();
            sendMessage();
        }
    }
    
    // Escape: 입력 취소
    if (e.key === 'Escape') {
        messageInput.blur();
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
    const maxHeight = 120; // CSS에서 설정한 max-height와 동일
    
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
    sendButton.disabled = !hasText || isTyping;
    
    if (hasText && !isTyping) {
        sendButton.setAttribute('aria-label', '메시지 전송');
    } else {
        sendButton.setAttribute('aria-label', '메시지를 입력하세요');
    }
}

// 글자 수 카운트 업데이트
function updateCharCount() {
    const currentLength = messageInput.value.length;
    const maxLength = parseInt(messageInput.getAttribute('maxlength'));
    charCount.textContent = `${currentLength} / ${maxLength}`;
    
    // 글자 수가 한계에 가까우면 색상 변경
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
    if (!text || isTyping) return;
    
    // 사용자 메시지 추가
    const userMessage = {
        id: messageId++,
        type: 'user',
        text: text,
        timestamp: new Date()
    };
    
    addMessage(userMessage);
    messageInput.value = '';
    adjustTextareaHeight();
    updateSendButton();
    updateCharCount();
    
    // 메시지 히스토리에 추가
    messageHistory.push(userMessage);
    saveChatHistory();
    
    // AI 응답 시뮬레이션
    await simulateAIResponse(text);
}

// 메시지 추가
function addMessage(message) {
    const messageElement = createMessageElement(message);
    messagesList.appendChild(messageElement);
    scrollToBottom();
    
    // 접근성을 위한 live region 업데이트
    announceMessage(message);
}

// 메시지 요소 생성
function createMessageElement(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.type}-message`;
    messageDiv.setAttribute('data-timestamp', formatTime(message.timestamp));
    messageDiv.setAttribute('role', 'article');
    messageDiv.setAttribute('aria-label', `${message.type === 'user' ? '사용자' : 'AI'} 메시지`);
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = `<div class="avatar-icon">${message.type === 'user' ? '👤' : '🍔'}</div>`;
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const text = document.createElement('div');
    text.className = 'message-text';
    text.textContent = message.text;
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = formatTime(message.timestamp);
    time.setAttribute('title', message.timestamp.toLocaleString());
    
    content.appendChild(text);
    content.appendChild(time);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    return messageDiv;
}

// AI 응답 시뮬레이션 (BurgerBot 통합)
async function simulateAIResponse(userText) {
    showTypingIndicator();
    isTyping = true;
    updateSendButton();
    
    try {
        // Flask /chat API 호출
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: userText,
                session_id: 'claude-chat-session',
                streaming: false
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // BurgerBot 응답 처리
        const aiResponseText = data.response;
        
        // 주문 정보가 있으면 업데이트
        if (data.orders && data.orders !== '[]') {
            try {
                const orders = JSON.parse(data.orders);
                if (orders.length > 0) {
                    // BurgerBot 주문을 로컬 형식으로 변환
                    const convertedOrders = orders.map(order => ({
                        id: Date.now() + Math.random(),
                        type: order.order_type,
                        burger: order.burger?.name || '',
                        side: order.side ? `${order.side.name} ${order.side.size || ''}`.trim() : '',
                        drink: order.drink ? `${order.drink.name} ${order.drink.size || ''}`.trim() : '',
                        quantity: order.quantity || 1
                    }));
                    
                    // 새 주문만 추가 (중복 방지)
                    const existingOrderIds = new Set(orderList.map(o => `${o.burger}-${o.side}-${o.drink}-${o.quantity}`));
                    const newOrders = convertedOrders.filter(order => 
                        !existingOrderIds.has(`${order.burger}-${order.side}-${order.drink}-${order.quantity}`)
                    );
                    
                    if (newOrders.length > 0) {
                        orderList.push(...newOrders);
                        saveOrders();
                        updateOrderDisplay();
                        updateOrderButton();
                    }
                }
            } catch (parseError) {
                console.warn('주문 파싱 오류:', parseError);
            }
        }
        
        const aiResponse = {
            id: messageId++,
            type: 'ai',
            text: aiResponseText,
            timestamp: new Date()
        };
        
        hideTypingIndicator();
        addMessage(aiResponse);
        
        // 메시지 히스토리에 추가
        messageHistory.push(aiResponse);
        saveChatHistory();
        
    } catch (error) {
        console.error('AI 응답 생성 오류:', error);
        
        // 에러 발생 시 폴백 응답
        const fallbackResponse = {
            id: messageId++,
            type: 'ai',
            text: '죄송합니다. 잠시 문제가 발생했어요. 다시 시도해주세요.',
            timestamp: new Date()
        };
        
        hideTypingIndicator();
        addMessage(fallbackResponse);
        messageHistory.push(fallbackResponse);
        saveChatHistory();
        
        showErrorToast();
    } finally {
        isTyping = false;
        updateSendButton();
    }
}

// 타이핑 인디케이터 표시
function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    scrollToBottom();
}

// 타이핑 인디케이터 숨김
function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// 에러 토스트 표시
function showErrorToast() {
    errorToast.style.display = 'block';
    
    // 3초 후 자동으로 숨김
    setTimeout(() => {
        hideErrorToast();
    }, 3000);
}

// 에러 토스트 숨김
function hideErrorToast() {
    errorToast.style.display = 'none';
}

// 시간 포맷팅
function formatTime(date) {
    return date.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// 메시지 하단으로 스크롤
function scrollToBottom() {
    requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

// 채팅 히스토리 저장
function saveChatHistory() {
    try {
        const historyData = messageHistory.map(msg => ({
            ...msg,
            timestamp: msg.timestamp.toISOString()
        }));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(historyData));
    } catch (error) {
        console.warn('채팅 히스토리 저장 실패:', error);
    }
}

// 채팅 히스토리 로드
function loadChatHistory() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return;
        
        const historyData = JSON.parse(stored);
        messageHistory = historyData.map(msg => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
        }));
        
        // 환영 메시지 제거 (히스토리가 있는 경우)
        if (messageHistory.length > 0) {
            const welcomeMessage = messagesList.querySelector('.message');
            if (welcomeMessage) {
                welcomeMessage.remove();
            }
        }
        
        // 히스토리 메시지 표시
        messageHistory.forEach(message => {
            addMessage(message);
        });
        
        // 최신 메시지 ID 설정
        if (messageHistory.length > 0) {
            messageId = Math.max(...messageHistory.map(msg => msg.id)) + 1;
        }
        
    } catch (error) {
        console.warn('채팅 히스토리 로드 실패:', error);
    }
}

// 히스토리 초기화 (개발용)
function clearChatHistory() {
    localStorage.removeItem(STORAGE_KEY);
    messageHistory = [];
    messagesList.innerHTML = '';
    
    // 환영 메시지 다시 추가
    const welcomeMessage = {
        id: messageId++,
        type: 'ai',
        text: '안녕하세요! 저는 Claude입니다. 무엇을 도와드릴까요?',
        timestamp: new Date()
    };
    addMessage(welcomeMessage);
}

// 접근성 메시지 알림
function announceMessage(message) {
    const announcement = document.createElement('div');
    announcement.className = 'sr-only';
    announcement.setAttribute('aria-live', 'polite');
    announcement.textContent = `${message.type === 'user' ? '사용자' : 'AI'}가 메시지를 보냈습니다: ${message.text}`;
    
    document.body.appendChild(announcement);
    
    // 알림 후 제거
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

// 포커스 트랩 설정
function setupFocusTrap() {
    const focusableElements = [
        messageInput,
        sendButton,
        errorToast.querySelector('.toast-close')
    ];
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            const activeElement = document.activeElement;
            const currentIndex = focusableElements.indexOf(activeElement);
            
            if (e.shiftKey) {
                // Shift+Tab: 이전 요소로 포커스
                if (currentIndex <= 0) {
                    e.preventDefault();
                    focusableElements[focusableElements.length - 1].focus();
                }
            } else {
                // Tab: 다음 요소로 포커스
                if (currentIndex >= focusableElements.length - 1) {
                    e.preventDefault();
                    focusableElements[0].focus();
                }
            }
        }
    });
}

// 모바일 키보드 처리
function setupMobileKeyboardHandling() {
    let initialViewportHeight = window.innerHeight;
    
    function handleViewportChange() {
        const currentHeight = window.innerHeight;
        const heightDiff = initialViewportHeight - currentHeight;
        
        // 키보드가 올라온 경우
        if (heightDiff > 100) {
            document.body.classList.add('keyboard-visible');
            // 메시지를 키보드 위로 스크롤
            setTimeout(() => scrollToBottom(), 100);
        } else {
            document.body.classList.remove('keyboard-visible');
        }
    }
    
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            initialViewportHeight = window.innerHeight;
            handleViewportChange();
        }, 500);
    });
    
    // 입력 필드 포커스/블러 이벤트
    messageInput.addEventListener('focus', () => {
        setTimeout(handleViewportChange, 300);
    });
    
    messageInput.addEventListener('blur', () => {
        setTimeout(handleViewportChange, 300);
    });
}

// 윈도우 리사이즈 처리
function handleResize() {
    adjustTextareaHeight();
    scrollToBottom();
}

// 주문 사이드바 토글
function toggleOrderSidebar() {
    if (isOrderSidebarOpen) {
        closeOrderSidebar();
    } else {
        openOrderSidebar();
    }
}

// 주문 사이드바 열기
function openOrderSidebar() {
    isOrderSidebarOpen = true;
    orderSidebar.classList.add('open');
    messagesContainer.classList.add('with-sidebar');
    toggleOrderBtn.textContent = '📋 주문닫기';
    
    // 접근성을 위한 포커스 이동
    setTimeout(() => {
        closeOrderBtn.focus();
    }, 300);
}

// 주문 사이드바 닫기
function closeOrderSidebar() {
    isOrderSidebarOpen = false;
    orderSidebar.classList.remove('open');
    messagesContainer.classList.remove('with-sidebar');
    toggleOrderBtn.textContent = '📋 주문보기';
    toggleOrderBtn.focus();
}

// 주문 내역 표시 업데이트
function updateOrderDisplay() {
    if (orderList.length === 0) {
        orderSummary.innerHTML = '<div style="text-align: center; color: #6c757d; margin-top: 50px;">주문 내역이 없습니다.</div>';
        finalizeOrderBtn.disabled = true;
        return;
    }
    
    let orderHtml = '';
    orderList.forEach((order, index) => {
        orderHtml += createOrderItemHTML(order, index);
    });
    
    orderSummary.innerHTML = orderHtml;
    finalizeOrderBtn.disabled = false;
}

// 주문 아이템 HTML 생성
function createOrderItemHTML(order, index) {
    if (order.type === 'set') {
        return `
            <div class="order-item" data-order-id="${order.id}">
                <div class="order-item-header">
                    <span class="order-item-title">${order.burger} 세트</span>
                    <span class="order-item-quantity">x${order.quantity}</span>
                </div>
                <div class="order-item-details">
                    <div class="detail-line">🍔 버거: ${order.burger}</div>
                    <div class="detail-line">🍟 사이드: ${order.side}</div>
                    <div class="detail-line">🥤 음료: ${order.drink}</div>
                </div>
            </div>
        `;
    } else {
        return `
            <div class="order-item" data-order-id="${order.id}">
                <div class="order-item-header">
                    <span class="order-item-title">${order.name}</span>
                    <span class="order-item-quantity">x${order.quantity}</span>
                </div>
            </div>
        `;
    }
}

// 주문 초기화
function clearOrders() {
    if (orderList.length === 0) return;
    
    if (confirm('모든 주문 내역을 삭제하시겠습니까?')) {
        orderList = [];
        saveOrders();
        updateOrderDisplay();
        updateOrderButton();
        
        // 피드백 메시지
        const clearMessage = {
            id: messageId++,
            type: 'ai',
            text: '주문 내역이 모두 삭제되었습니다. 새로운 주문을 시작해보세요!',
            timestamp: new Date()
        };
        addMessage(clearMessage);
        messageHistory.push(clearMessage);
        saveChatHistory();
    }
}

// 주문 완료
function finalizeOrder() {
    if (orderList.length === 0) return;
    
    const orderCount = orderList.length;
    const finalizeMessage = {
        id: messageId++,
        type: 'ai',
        text: `총 ${orderCount}개의 주문이 완료되었습니다! 곧 준비해드릴게요. 감사합니다! 🎉`,
        timestamp: new Date()
    };
    
    addMessage(finalizeMessage);
    messageHistory.push(finalizeMessage);
    saveChatHistory();
    
    // 주문 완료 후 초기화
    orderList = [];
    saveOrders();
    updateOrderDisplay();
    updateOrderButton();
    
    // 사이드바 자동 닫기
    setTimeout(() => {
        closeOrderSidebar();
    }, 2000);
}

// 주문 버튼 상태 업데이트
function updateOrderButton() {
    const orderCount = orderList.length;
    if (orderCount > 0) {
        toggleOrderBtn.textContent = `📋 주문보기 (${orderCount})`;
        toggleOrderBtn.style.background = 'rgba(255, 255, 255, 0.3)';
        toggleOrderBtn.style.borderColor = 'rgba(255, 255, 255, 0.5)';
    } else {
        toggleOrderBtn.textContent = '📋 주문보기';
        toggleOrderBtn.style.background = 'rgba(255, 255, 255, 0.2)';
        toggleOrderBtn.style.borderColor = 'rgba(255, 255, 255, 0.3)';
    }
}

// 주문 저장
function saveOrders() {
    try {
        localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(orderList));
    } catch (error) {
        console.warn('주문 저장 실패:', error);
    }
}

// 주문 로드
function loadOrders() {
    try {
        const stored = localStorage.getItem(ORDER_STORAGE_KEY);
        if (stored) {
            orderList = JSON.parse(stored);
            updateOrderDisplay();
            updateOrderButton();
        }
    } catch (error) {
        console.warn('주문 로드 실패:', error);
        orderList = [];
    }
}

// 가상 스크롤링 (성능 최적화 - 메시지가 많을 때)
function enableVirtualScrolling() {
    if (messageHistory.length < 100) return; // 메시지가 적으면 비활성화
    
    // 가상 스크롤링 구현
    // 화면에 보이는 메시지만 DOM에 유지
    const ITEM_HEIGHT = 80; // 평균 메시지 높이
    const BUFFER_SIZE = 5; // 위아래 버퍼
    
    let startIndex = 0;
    let endIndex = Math.ceil(messagesContainer.clientHeight / ITEM_HEIGHT) + BUFFER_SIZE;
    
    function updateVisibleMessages() {
        const scrollTop = messagesContainer.scrollTop;
        const newStartIndex = Math.max(0, Math.floor(scrollTop / ITEM_HEIGHT) - BUFFER_SIZE);
        const newEndIndex = Math.min(
            messageHistory.length,
            newStartIndex + Math.ceil(messagesContainer.clientHeight / ITEM_HEIGHT) + BUFFER_SIZE * 2
        );
        
        if (newStartIndex !== startIndex || newEndIndex !== endIndex) {
            startIndex = newStartIndex;
            endIndex = newEndIndex;
            renderVisibleMessages();
        }
    }
    
    function renderVisibleMessages() {
        // DOM 업데이트 로직
        messagesList.innerHTML = '';
        
        // 상단 스페이서
        if (startIndex > 0) {
            const topSpacer = document.createElement('div');
            topSpacer.style.height = `${startIndex * ITEM_HEIGHT}px`;
            messagesList.appendChild(topSpacer);
        }
        
        // 보이는 메시지들
        for (let i = startIndex; i < endIndex; i++) {
            if (messageHistory[i]) {
                const messageElement = createMessageElement(messageHistory[i]);
                messagesList.appendChild(messageElement);
            }
        }
        
        // 하단 스페이서
        if (endIndex < messageHistory.length) {
            const bottomSpacer = document.createElement('div');
            bottomSpacer.style.height = `${(messageHistory.length - endIndex) * ITEM_HEIGHT}px`;
            messagesList.appendChild(bottomSpacer);
        }
    }
    
    messagesContainer.addEventListener('scroll', updateVisibleMessages);
}

// 전역 함수로 노출 (개발/디버깅용)
window.clearChatHistory = clearChatHistory;
window.enableVirtualScrolling = enableVirtualScrolling;
window.clearOrders = clearOrders;
window.addTestOrder = () => {
    const testOrder = {
        id: Date.now(),
        type: 'set',
        burger: '테스트 버거',
        side: '후렌치 후라이 미디움',
        drink: '코카 콜라 미디움',
        quantity: 1
    };
    orderList.push(testOrder);
    saveOrders();
    updateOrderDisplay();
    updateOrderButton();
};

// CSS에 스크린 리더 전용 스타일 추가
const srOnlyStyle = document.createElement('style');
srOnlyStyle.textContent = `
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
    
    body.keyboard-visible {
        /* 모바일 키보드 대응 스타일 */
    }
`;
document.head.appendChild(srOnlyStyle);