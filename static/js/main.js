// 메인 레이아웃 및 공통 스크립트

// 호스트 인증 방식 토글 함수 (전역 사용)
function toggleAuthFields(val) {
    const passwordField = document.getElementById('passwordField');
    const keyField = document.getElementById('keyField');
    if (passwordField) passwordField.style.display = val === 'password' ? 'block' : 'none';
    if (keyField) keyField.style.display = val === 'key' ? 'block' : 'none';
}

// 상태 업데이트 함수 (대시보드 등에서 사용)
function updateStatus(id, status) {
    const el = document.getElementById(`status-${id}`);
    if (!el) return;
    el.innerText = status.toUpperCase();
    el.className = `status-badge ${status}`;
}

// 사이드바 토글 기능
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    sidebar.classList.toggle('collapsed');
    const isCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebar_collapsed', isCollapsed);
}

// 초기 사이드바 상태 복원
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
        }
    }
});
