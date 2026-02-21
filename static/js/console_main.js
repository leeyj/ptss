window.PTSS = window.PTSS || {};

// ==========================================
// 1. Session & UI Logic
// ==========================================

window.PTSS.Session = {
    async terminate() {
        if (!confirm(window.I18N.confirm_terminate)) return;
        try {
            const config = window.PTSS.config;
            const resp = await fetch(`/api/disconnect/${config.hostId}`, { method: 'POST' });
            if (resp.ok) window.location.href = window.PTSS_BASE_URL || '/';
        } catch (e) { alert(window.I18N.error_terminate); }
    },

    openPopup(event) {
        if (event) event.stopPropagation();
        const url = new URL(window.location.href);
        url.searchParams.set('popup', 'true');
        const width = 1200;
        const height = 800;
        const left = (window.screen.width / 2) - (width / 2);
        const top = (window.screen.height / 2) - (height / 2);

        window.open(
            url.toString(),
            `ptss_popup_${Date.now()}`,
            `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes`
        );
    }
};

window.PTSS.UI = {
    switchView(view) {
        const termStackEl = document.getElementById('terminal-stack');
        const sftpEl = document.getElementById('sftpPanel');
        const snippetEl = document.getElementById('snippetPanel');
        const tabManager = document.querySelector('.session-tab-bar');

        // 뷰 탭 활성화 UI
        const tabs = document.querySelectorAll('.tab');
        if (tabs) tabs.forEach(t => t.classList.remove('active'));
        document.getElementById(`tab-${view}`).classList.add('active');

        if (view === 'terminal') {
            termStackEl.style.flex = '2';
            termStackEl.style.display = 'block';
            sftpEl.style.display = 'none';
            snippetEl.style.display = 'none';
            if (tabManager) tabManager.style.display = 'flex';
        } else if (view === 'sftp') {
            termStackEl.style.display = 'none';
            sftpEl.style.display = 'flex';
            sftpEl.style.flex = '1';
            snippetEl.style.display = 'none';
            if (tabManager) tabManager.style.display = 'none';
            PTSS.SFTP.load();
        } else if (view === 'snippet') {
            termStackEl.style.display = 'none';
            sftpEl.style.display = 'none';
            snippetEl.style.display = 'flex';
            snippetEl.style.flex = '1';
            if (tabManager) tabManager.style.display = 'none';
            PTSS.Snippet.load();
        } else if (view === 'combined') {
            termStackEl.style.display = 'block';
            termStackEl.style.flex = '1.2';
            sftpEl.style.display = 'flex';
            sftpEl.style.flex = '0.8';
            snippetEl.style.display = 'flex';
            snippetEl.style.flex = '0.6';
            if (tabManager) tabManager.style.display = 'flex';
            PTSS.SFTP.load();
            PTSS.Snippet.load();
        }

        // 리사이즈 트리거
        setTimeout(() => {
            if (PTSS.Terminal.activeTabId && PTSS.Terminal.tabs[PTSS.Terminal.activeTabId]) {
                PTSS.Terminal.tabs[PTSS.Terminal.activeTabId].fitAddon.fit();
                PTSS.Terminal.sendResize();
            }
        }, 100);
    }
};

// ==========================================
// 2. Initialization
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[PTSS] Initializing modules...');

    // 팝업 모드 체크
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('popup') === 'true') {
        document.body.classList.add('popup-mode');
        const newWinBtn = document.querySelector('button[title="별도 창으로 열기"]');
        if (newWinBtn) newWinBtn.style.display = 'none';
    }

    // 터미널 초기화 (탭 생성 포함)
    PTSS.Terminal.init();

    // 스니펫 초기 로드
    PTSS.Snippet.load();

    // Container Resize Handler
    const container = document.getElementById('resizableContainer');
    const handle = document.getElementById('resizeHandle');
    let isResizing = false;

    if (handle) {
        handle.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'ns-resize';
            e.preventDefault();
        });
    }

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const newHeight = e.clientY - container.offsetTop;
        if (newHeight > 200) {
            container.style.height = `${newHeight}px`;
            if (PTSS.Terminal.activeTabId) {
                PTSS.Terminal.tabs[PTSS.Terminal.activeTabId].fitAddon.fit();
                PTSS.Terminal.sendResize();
            }
        }
    });

    document.addEventListener('mouseup', () => {
        isResizing = false;
        document.body.style.cursor = 'default';
    });
});
