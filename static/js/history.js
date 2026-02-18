/**
 * 활동 히스토리 페이지 전용 스크립트
 */

function applyFilters() {
    const url = new URL(window.location.href);
    const userId = document.getElementById('userFilter').value;
    const hostId = document.getElementById('hostFilter').value;
    const actionType = document.getElementById('actionFilter').value;
    const search = document.getElementById('searchInput').value;

    url.searchParams.set('page', '1');
    if (userId) url.searchParams.set('user_id', userId); else url.searchParams.delete('user_id');
    if (hostId) url.searchParams.set('host_id', hostId); else url.searchParams.delete('host_id');
    if (actionType) url.searchParams.set('action_type', actionType); else url.searchParams.delete('action_type');
    if (search) url.searchParams.set('q', search); else url.searchParams.delete('q');

    window.location.href = url.toString();
}

function changePerPage(val) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', '1');
    url.searchParams.set('per_page', val);
    window.location.href = url.toString();
}

// 엔터 키 검색 지원
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') applyFilters();
        });
    }
});
