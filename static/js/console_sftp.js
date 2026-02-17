window.PTSS = window.PTSS || {};
window.PTSS.SFTP = {
    currentFileList: [],
    showPermissions: false,

    // SFTP 목록 로드
    async load(path = '.') {
        const config = window.PTSS.config;
        if (!config.hostId) return;

        const fileListEl = document.getElementById('fileList');
        const currentPathDisplay = document.getElementById('currentPath');

        if (fileListEl) fileListEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">불러오는 중...</div>';
        if (currentPathDisplay) currentPathDisplay.innerText = path;

        try {
            const response = await fetch(`/api/sftp/list/${config.hostId}?path=${path}`);
            const data = await response.json();

            if (data.files) {
                this.currentFileList = data.files;
                this.sort();
            } else {
                if (fileListEl) fileListEl.innerHTML = `<div style="padding: 20px; color: var(--danger);">Error: ${data.error}</div>`;
            }
        } catch (e) {
            console.error('SFTP Load Error:', e);
            if (fileListEl) fileListEl.innerHTML = '<div style="padding: 20px; color: var(--danger);">로드 실패</div>';
        }
    },

    // 파일 정렬 (설정값 or 옵션)
    sort() {
        const sortSelect = document.getElementById('sortSelect');
        const config = window.PTSS.config;
        const sortBy = sortSelect ? sortSelect.value : (config.sftpSortBy || 'name');

        let sorted = [...this.currentFileList];

        if (sortBy === 'name') {
            sorted.sort((a, b) => a.filename.localeCompare(b.filename));
        } else if (sortBy === 'type') {
            sorted.sort((a, b) => (b.is_dir ? 1 : 0) - (a.is_dir ? 1 : 0));
        } else if (sortBy === 'date') {
            sorted.sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
        }

        this.render(sorted);
    },

    // 렌더링
    render(files) {
        const fileListEl = document.getElementById('fileList');
        const pathEl = document.getElementById('currentPath');
        if (!fileListEl || !pathEl) return;

        const path = pathEl.innerText;
        fileListEl.innerHTML = '';

        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.padding = '8px 12px';
            item.style.borderBottom = '1px solid rgba(255,255,255,0.03)';

            // 작업 아이콘
            let actions = `<div style="display: flex; gap: 10px; width: 60px; justify-content: flex-end;">`;
            if (!file.is_dir) {
                actions += `
                    <span title="수정" onclick="PTSS.Editor.open('${path}/${file.filename}')" style="cursor:pointer; font-size: 1rem; opacity: 0.7;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">✏️</span>
                    <span title="다운로드" onclick="PTSS.SFTP.download('${path}/${file.filename}')" style="cursor:pointer; font-size: 1rem; opacity: 0.7;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">📥</span>
                    <span title="로그 보기" onclick="PTSS.SFTP.viewLog('${path}/${file.filename}')" style="cursor:pointer; font-size: 1rem; opacity: 0.7;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">🔍</span>
                `;
            }
            actions += `</div>`;

            // 클릭 액션 (디렉토리 이동)
            const clickAction = file.is_dir
                ? `PTSS.SFTP.syncAndLoad('${path}/${file.filename}')`
                : '';

            // 권한 표시
            let permBadgeColor = 'var(--text-muted)';
            let permBg = 'rgba(255,255,255,0.05)';
            let octColor = 'var(--accent-color)';
            let octBg = 'rgba(56, 189, 248, 0.1)';

            const oct = file.mode_oct;
            const othersPerm = parseInt(oct[2]);
            const groupPerm = parseInt(oct[1]);

            if (othersPerm > 0 || oct === '777' || oct === '666') {
                octColor = '#fff';
                octBg = 'var(--danger)';
                permBadgeColor = 'var(--danger)';
                permBg = 'rgba(239, 68, 68, 0.1)';
            } else if (groupPerm > 4) {
                octColor = '#fff';
                octBg = 'var(--warning)';
                permBadgeColor = 'var(--warning)';
                permBg = 'rgba(245, 158, 11, 0.1)';
            }

            const permText = this.showPermissions
                ? `<div style="width: 155px; display: flex; justify-content: center; gap: 6px;">
                    <span title="숫자 권한" style="font-size:0.75rem; color:${octColor}; font-family:'JetBrains Mono'; background:${octBg}; padding:2px 5px; border-radius:4px; font-weight:bold;">${file.mode_oct}</span>
                    <span title="기호 권한" style="font-size:0.75rem; color:${permBadgeColor}; font-family:'JetBrains Mono'; background:${permBg}; padding:2px 5px; border-radius:4px;">${file.mode}</span>
                   </div>`
                : '';

            const dateText = `<div style="width: 120px; font-size:0.75rem; color:var(--text-muted); text-align: right; white-space:nowrap;">${file.date_str || ''}</div>`;

            item.innerHTML = `
                <span class="file-icon" style="font-size: 1.1rem; width: 24px; text-align: center; margin-right: 8px;">${file.is_dir ? '📁' : '📄'}</span>
                <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; cursor: pointer;" onclick="${clickAction}">${file.filename}</span>
                <div style="display: flex; align-items: center; gap: 15px;">
                    ${dateText}
                    ${permText}
                    ${actions}
                </div>
            `;
            fileListEl.appendChild(item);
        });
    },

    togglePerms() {
        this.showPermissions = !this.showPermissions;

        // 버튼 스타일 업데이트
        const btn = document.getElementById('btnTogglePerms');
        if (btn) {
            if (this.showPermissions) btn.classList.add('active');
            else btn.classList.remove('active');
        }

        this.sort();
    },

    syncAndLoad(newPath) {
        // 활성 터미널 탭이 있으면 거기서도 cd 명령 실행
        if (window.PTSS.Terminal && window.PTSS.Terminal.activeTabId) {
            window.PTSS.socket.emit('terminal_input', {
                data: `cd "${newPath}"\n`,
                tab_id: window.PTSS.Terminal.activeTabId
            });
        }
        this.load(newPath);
    },

    upload() {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.onchange = async () => {
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            const pathEl = document.getElementById('currentPath');
            const currentPath = pathEl ? pathEl.innerText : '.';
            formData.append('path', currentPath);

            try {
                const config = window.PTSS.config;
                const resp = await fetch(`/api/sftp/upload/${config.hostId}`, {
                    method: 'POST',
                    body: formData
                });
                if (resp.ok) {
                    alert('업로드 성공');
                    this.load(currentPath);
                } else {
                    const data = await resp.json();
                    alert('업로드 실패: ' + data.error);
                }
            } catch (e) { alert('업로드 중 오류 발생'); }
        };
        fileInput.click();
    },

    download(remotePath) {
        const config = window.PTSS.config;
        window.location.href = `/api/sftp/download/${config.hostId}?path=${remotePath}`;
    },

    viewLog(remotePath) {
        const config = window.PTSS.config;
        const width = 900;
        const height = 700;
        const left = (window.screen.width / 2) - (width / 2);
        const top = (window.screen.height / 2) - (height / 2);

        window.open(
            `/log_view/${config.hostId}?path=${remotePath}`,
            `log_${Date.now()}`,
            `width=${width},height=${height},left=${left},top=${top},menubar=no,toolbar=no,location=no,status=no,scrollbars=yes`
        );
    }
};
