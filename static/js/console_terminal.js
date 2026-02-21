window.PTSS = window.PTSS || {};
window.PTSS.Terminal = {
    tabs: {}, // { tabId: { term, fitAddon, element, btnElement } }
    activeTabId: null,
    tabCounter: 0,

    init() {
        this.createTab();

        // 리사이즈 이벤트
        window.addEventListener('resize', () => {
            if (this.activeTabId && this.tabs[this.activeTabId]) {
                this.tabs[this.activeTabId].fitAddon.fit();
                this.sendResize();
            }
        });

        // 소켓 이벤트 연결
        const socket = window.PTSS.socket;
        socket.on('terminal_output', (data) => this.handleOutput(data));

        // Guard 초기화
        if (window.PTSS.Guard) window.PTSS.Guard.init();
    },

    createTab() {
        const config = window.PTSS.config;
        const socket = window.PTSS.socket;

        this.tabCounter++;
        // 탭 ID를 고유하게 생성 (현재 시간 + 랜덤값 조합)하여 여러 창/팝업 간 충돌 방지
        const uniqueId = Math.random().toString(36).substring(2, 9);
        const tabId = `session-${Date.now()}-${uniqueId}`;

        // 1. 탭 버튼 생성
        const tabBtn = document.createElement('div');
        tabBtn.className = 'session-tab';
        tabBtn.id = `btn-${tabId}`;
        tabBtn.innerHTML = `
            <span>Terminal ${this.tabCounter}</span>
            <div class="tab-controls">
                <span class="log-btn" onclick="PTSS.Terminal.downloadLog('${tabId}', event)" title="Log">💾</span>
                <span class="popup-btn" onclick="PTSS.Session.openPopup(event)" title="Popup">↗️</span>
                <span class="close-btn" onclick="PTSS.Terminal.closeTab('${tabId}', event)">×</span>
            </div>
        `;
        tabBtn.onclick = () => this.activateTab(tabId);
        document.getElementById('session-tabs').appendChild(tabBtn);

        // 2. 터미널 컨테이너 생성
        const termContainer = document.createElement('div');
        termContainer.id = `term-${tabId}`;
        termContainer.className = 'terminal-instance';
        termContainer.style.width = '100%';
        termContainer.style.height = '100%';
        termContainer.style.display = 'none'; // 기본적으로 숨김
        document.getElementById('terminal-stack').appendChild(termContainer);

        // 안내 메시지 제거
        const placeholder = document.getElementById('terminal-placeholder');
        if (placeholder) placeholder.remove();

        // 3. xterm.js 초기화
        const settings = window.PTSS.Settings ? window.PTSS.Settings.config : {
            fontSize: 14,
            fontFamily: '"JetBrains Mono", monospace',
            theme: 'default'
        };
        const activeTheme = (window.PTSS.Settings && window.PTSS.Settings.themes)
            ? window.PTSS.Settings.themes[settings.theme]
            : { background: '#0f172a', foreground: '#f1f5f9', cursor: '#38bdf8' };

        const term = new Terminal({
            fontFamily: settings.fontFamily,
            fontSize: settings.fontSize,
            theme: activeTheme,
            convertEol: true,
            cursorBlink: true,
            allowProposedApi: true
        });

        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);

        // WebGL 가속 설정 확인 및 적용
        if (settings.useWebgl && typeof WebglAddon !== 'undefined') {
            try {
                const webglAddon = new WebglAddon.WebglAddon();
                webglAddon.onContextLoss(e => {
                    console.warn("WebGL context lost. Falling back to canvas renderer.");
                    webglAddon.dispose();
                });
                term.loadAddon(webglAddon);
                console.log("WebGL acceleration enabled for tab:", tabId);
            } catch (e) {
                console.warn("WebGL acceleration could not be initialized:", e);
            }
        }

        term.open(termContainer);

        // **중요: ResizeObserver 적용**
        // 컨테이너 크기가 변하거나 display가 block으로 바뀔 때 자동으로 fit 수행
        let resizeTimeout;
        const resizeObserver = new ResizeObserver(() => {
            try {
                if (termContainer.clientWidth > 0 && termContainer.clientHeight > 0) {
                    fitAddon.fit();

                    // 소켓으로 리사이즈 이벤트 전송 (디바운스 적용)
                    if (resizeTimeout) clearTimeout(resizeTimeout);
                    resizeTimeout = setTimeout(() => {
                        if (this.activeTabId === tabId) {
                            console.log(`[PTSS] Terminal Resized: ${term.cols}x${term.rows}`);
                            window.PTSS.socket.emit('terminal_resize', {
                                cols: term.cols,
                                rows: term.rows,
                                tab_id: tabId
                            });
                        }
                    }, 200);
                }
            } catch (e) { console.warn('Resize Error:', e); }
        });
        resizeObserver.observe(termContainer);

        // 4. 데이터 전송 및 히스토리 수집
        term.onData(data => {
            socket.emit('terminal_input', {
                data: data,
                tab_id: tabId
            });
        });

        term.onKey(e => {
            // Enter 키가 눌렸을 때 현재 줄의 명령어를 완성된 형태로 추출
            if (e.domEvent.key === 'Enter') {
                const buffer = term.buffer.active;
                const lineIndex = buffer.cursorY + buffer.baseY;
                const line = buffer.getLine(lineIndex).translateToString(true);

                // 프롬프트 이후의 명령어 본문 추출 시도
                // 보통 'user@host:~$ ' 또는 'root@host:~# ' 형태이므로 '$ '나 '# ' 이후를 자름
                let command = '';
                const lastDollar = line.lastIndexOf('$ ');
                const lastHash = line.lastIndexOf('# ');
                const markerIndex = Math.max(lastDollar, lastHash);

                if (markerIndex !== -1) {
                    command = line.substring(markerIndex + 2).trim();
                } else {
                    // 프롬프트 형식이 특이한 경우 등 (보수적으로 1자 이상일 때만 기록)
                    command = line.trim();
                    // 너무 짧거나 공백만 있는 경우는 무시 (실제 명령어가 아닐 확률 높음)
                }

                if (command.length > 1) {
                    socket.emit('terminal_command', {
                        command: command,
                        tab_id: tabId
                    });
                }
            }
        });

        if (term.textarea) {
            term.textarea.addEventListener('focus', () => termContainer.classList.add('focused'));
            term.textarea.addEventListener('blur', () => termContainer.classList.remove('focused'));
        }

        // 5. 관리 객체에 저장
        this.tabs[tabId] = {
            id: tabId,
            term: term,
            fitAddon: fitAddon,
            element: termContainer,
            btnElement: tabBtn,
            resizeObserver: resizeObserver // 옵저버 저장
        };

        // 6. 서버 연결 요청
        if (config.hostId) {
            socket.emit('terminal_connect', {
                host_id: config.hostId,
                tab_id: tabId
            });
        } else {
            term.write('\r\n\x1b[31m[ERROR] Host ID not found!\x1b[0m\r\n');
        }

        // 7. 활성화
        this.activateTab(tabId);
    },

    activateTab(tabId) {
        if (this.activeTabId === tabId) return;

        // 기존 탭 비활성화
        if (this.activeTabId && this.tabs[this.activeTabId]) {
            this.tabs[this.activeTabId].element.style.display = 'none';
            this.tabs[this.activeTabId].btnElement.classList.remove('active');
        }

        // 새 탭 활성화
        this.activeTabId = tabId;
        const tab = this.tabs[tabId];
        if (tab) {
            tab.element.style.display = 'block';
            tab.btnElement.classList.add('active');

            setTimeout(() => {
                tab.fitAddon.fit();
                tab.term.focus();
                this.sendResize();
            }, 50);
        }
    },

    closeTab(tabId, event) {
        if (event) event.stopPropagation();

        if (Object.keys(this.tabs).length <= 1) {
            alert(window.I18N.min_one_terminal);
            return;
        }

        if (!confirm(window.I18N.confirm_close_tab)) return;

        const tab = this.tabs[tabId];
        if (tab) {
            // 옵저버 해제
            if (tab.resizeObserver) {
                tab.resizeObserver.disconnect();
            }

            tab.btnElement.remove();
            tab.element.remove();
            tab.term.dispose();
            delete this.tabs[tabId];

            if (this.activeTabId === tabId) {
                const remainingIds = Object.keys(this.tabs);
                if (remainingIds.length > 0) {
                    this.activateTab(remainingIds[remainingIds.length - 1]);
                } else {
                    this.activeTabId = null;
                }
            }
        }
    },

    sendResize() {
        if (!this.activeTabId || !this.tabs[this.activeTabId]) return;
        const tab = this.tabs[this.activeTabId];
        window.PTSS.socket.emit('terminal_resize', {
            cols: tab.term.cols,
            rows: tab.term.rows,
            tab_id: this.activeTabId
        });
    },

    handleOutput(data) {
        const targetTabId = data.tab_id || this.activeTabId;
        const tab = this.tabs[targetTabId];

        if (tab) {
            tab.term.write(data.data);
        } else if (!data.tab_id && this.activeTabId) {
            this.tabs[this.activeTabId].term.write(data.data);
        }
    },

    downloadLog(tabId, event) {
        if (event) event.stopPropagation();
        const tab = this.tabs[tabId];
        if (!tab) return;

        // xterm.js 버퍼에서 텍스트 추출
        const buffer = tab.term.buffer.active;
        let logText = '';
        for (let i = 0; i < buffer.baseY + buffer.viewportY + tab.term.rows; i++) {
            const line = buffer.getLine(i);
            if (line) {
                logText += line.translateToString(true) + '\n';
            }
        }

        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);

        a.href = url;
        a.download = `terminal_log_${tabId}_${timestamp}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

window.PTSS.Guard = {
    pendingTabId: null,

    init() {
        console.log("[PTSS] Guard System Initialized");
        const socket = window.PTSS.socket;
        socket.on('command_guard_required', (data) => this.show(data));
    },

    show(data) {
        this.pendingTabId = data.tab_id;
        document.getElementById('restrictedCommandText').textContent = data.command;
        document.getElementById('commandGuardModal').style.display = 'flex';
    },

    confirm() {
        const socket = window.PTSS.socket;
        socket.emit('terminal_confirm_guard', { tab_id: this.pendingTabId });
        this.close();
    },

    cancel() {
        const socket = window.PTSS.socket;
        socket.emit('terminal_cancel_guard', { tab_id: this.pendingTabId });
        this.close();
    },

    close() {
        document.getElementById('commandGuardModal').style.display = 'none';
        this.pendingTabId = null;
        // 터미널 포커스 복구
        if (PTSS.Terminal.activeTabId && PTSS.Terminal.tabs[PTSS.Terminal.activeTabId]) {
            PTSS.Terminal.tabs[PTSS.Terminal.activeTabId].term.focus();
        }
    }
};
