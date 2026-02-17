window.PTSS = window.PTSS || {};
window.PTSS.Editor = {
    instance: null,
    currentPath: '',

    init() {
        if (this.instance) return;
        this.instance = ace.edit("aceEditor");
        this.instance.setTheme("ace/theme/dracula");
        this.instance.getSession().setMode("ace/mode/python");
        this.instance.setFontSize(14);
        this.instance.setShowPrintMargin(false);
    },

    async open(path) {
        const config = window.PTSS.config;
        if (!config.hostId) return;

        const modal = document.getElementById('editorModal');
        const titleEl = document.getElementById('editorFileName');
        const pathEl = document.getElementById('editorFilePath');

        this.currentPath = path;
        titleEl.innerText = path.split('/').pop();
        pathEl.innerText = path;

        modal.style.display = 'flex';
        this.init();
        this.instance.setValue("Loading...", -1);
        this.instance.setReadOnly(true);

        const ext = path.split('.').pop();
        if (ext === 'js') this.instance.getSession().setMode("ace/mode/javascript");
        else if (ext === 'sh') this.instance.getSession().setMode("ace/mode/sh");
        else if (ext === 'py') this.instance.getSession().setMode("ace/mode/python");
        else this.instance.getSession().setMode("ace/mode/text");

        try {
            const resp = await fetch(`/api/sftp/read_text/${config.hostId}?path=${encodeURIComponent(path)}`);
            const data = await resp.json();

            if (data.error) {
                alert('파일 읽기 실패: ' + data.error);
                this.close();
            } else {
                this.instance.setValue(data.content, -1);
                this.instance.setReadOnly(false);
            }
        } catch (e) {
            alert('로드 중 오류 발생');
            this.close();
        }
    },

    close() {
        document.getElementById('editorModal').style.display = 'none';
        this.currentPath = '';
    },

    async save() {
        const config = window.PTSS.config;
        if (!this.currentPath) return;

        const content = this.instance.getValue();
        try {
            const resp = await fetch(`/api/sftp/write_text/${config.hostId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: this.currentPath,
                    content: content
                })
            });

            const data = await resp.json();
            if (data.success) {
                alert('성공적으로 저장되었습니다.');
                this.close();
            } else {
                alert('저장 실패: ' + data.error);
            }
        } catch (e) {
            alert('저장 중 통신 오류');
        }
    }
};
