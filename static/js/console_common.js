// PTSS 네임스페이스 정의
window.PTSS = window.PTSS || {};

// 1. 전역 설정 가져오기
window.PTSS.config = window.CONFIG || {};

// 2. 소켓 초기화 (전역 공유)
window.PTSS.socket = io({
    transports: ['websocket'],
    reconnectionAttempts: 5
});

// 소켓 연결 기본 로그
window.PTSS.socket.on('connect', () => {
    console.log('[PTSS] Socket connected. SID:', window.PTSS.socket.id);
});

window.PTSS.socket.on('disconnect', () => {
    console.log('[PTSS] Socket disconnected');
});

window.PTSS.socket.on('connect_error', (err) => {
    console.error('[PTSS] Connection Error:', err);
});
