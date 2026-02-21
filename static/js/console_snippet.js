window.PTSS = window.PTSS || {};

window.PTSS.Snippet = {
    snippets: [],

    async load() {
        try {
            const response = await fetch('/api/snippets');
            this.snippets = await response.json();
            this.render();
        } catch (e) {
            console.error('Failed to load snippets:', e);
            document.getElementById('snippetList').innerHTML = `<div style="padding:10px; color:var(--danger);">${window.I18N.failed}</div>`;
        }
    },

    render() {
        const listEl = document.getElementById('snippetList');
        if (!listEl) return;

        if (this.snippets.length === 0) {
            listEl.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-muted);">${window.I18N.no_snippets}</div>`;
            return;
        }

        // 카테고리별 그룹화
        const groups = {};
        this.snippets.forEach(s => {
            const cat = s.category || window.I18N.default_category;
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(s);
        });

        let html = '';
        Object.keys(groups).sort().forEach(cat => {
            html += `<div class="snippet-category">${cat}</div>`;
            groups[cat].forEach(s => {
                html += `
                    <div class="snippet-item" onclick="PTSS.Snippet.use(${s.id})">
                        <div class="snippet-name">
                            <div style="font-weight:600;">${s.name}</div>
                            <div class="snippet-content">${s.command}</div>
                        </div>
                        <div class="snippet-actions" onclick="event.stopPropagation()">
                            <span onclick="PTSS.Snippet.openEditor(${s.id})" title="수정" style="cursor:pointer; opacity:0.7;">✏️</span>
                            <span onclick="PTSS.Snippet.delete(${s.id})" title="삭제" style="cursor:pointer; opacity:0.7;">🗑️</span>
                        </div>
                    </div>
                `;
            });
        });
        listEl.innerHTML = html;
    },

    use(id) {
        const snippet = this.snippets.find(s => s.id === id);
        if (!snippet) return;

        if (window.PTSS.Terminal && window.PTSS.Terminal.activeTabId) {
            const tab = window.PTSS.Terminal.tabs[window.PTSS.Terminal.activeTabId];
            if (tab && tab.term) {
                // 터미널에 명령어 입력 (엔터 포함)
                // xterm.js의 onData 핸들러를 통해 소켓으로 전송되도록 함
                tab.term.focus();

                // 명령어를 소켓으로 직접 전송 (터미널 버퍼에 쓰는 것보다 정확)
                window.PTSS.socket.emit('terminal_input', {
                    data: snippet.command + '\n',
                    tab_id: window.PTSS.Terminal.activeTabId
                });

                // 히스토리 기록을 위해 terminal_command 이벤트도 별도로 전송
                window.PTSS.socket.emit('terminal_command', {
                    command: snippet.command,
                    tab_id: window.PTSS.Terminal.activeTabId
                });
            }
        }
    },

    openEditor(id = null) {
        const modal = document.getElementById('snippetModal');
        const title = document.getElementById('snippetModalTitle');
        const sid = document.getElementById('snippetId');
        const scat = document.getElementById('snippetCategory');
        const sname = document.getElementById('snippetName');
        const scmd = document.getElementById('snippetCommand');

        if (id) {
            const s = this.snippets.find(x => x.id === id);
            title.innerText = window.I18N.edit_snippet;
            sid.value = s.id;
            scat.value = s.category;
            sname.value = s.name;
            scmd.value = s.command;
        } else {
            title.innerText = window.I18N.add_snippet;
            sid.value = '';
            scat.value = window.I18N.default_category;
            sname.value = '';
            scmd.value = '';
        }
        modal.style.display = 'flex';
    },

    closeEditor() {
        document.getElementById('snippetModal').style.display = 'none';
    },

    async save() {
        const id = document.getElementById('snippetId').value;
        const category = document.getElementById('snippetCategory').value || '일반';
        const name = document.getElementById('snippetName').value;
        const command = document.getElementById('snippetCommand').value;

        if (!name || !command) {
            alert(window.I18N.input_all_fields);
            return;
        }

        try {
            const response = await fetch('/api/snippets/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id ? parseInt(id) : null, category, name, command })
            });
            const res = await response.json();
            if (res.success) {
                this.closeEditor();
                this.load();
            }
        } catch (e) {
            alert(window.I18N.error_save);
        }
    },

    async delete(id) {
        if (!confirm(window.I18N.confirm_delete)) return;
        try {
            const response = await fetch(`/api/snippets/delete/${id}`, { method: 'DELETE' });
            const res = await response.json();
            if (res.success) this.load();
        } catch (e) {
            alert(window.I18N.error_delete);
        }
    }
};
