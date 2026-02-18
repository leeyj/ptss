/* 로그 뷰어 전용 코드 */

const LogViewer = (function () {
    let hostId, path, logViewMode;
    let tailInterval = null;
    let lastContent = "";

    return {
        init: function (config) {
            hostId = config.hostId;
            path = config.path;
            logViewMode = config.logViewMode;

            this.fetchLog();

            if (logViewMode === 'tail') {
                tailInterval = setInterval(() => this.fetchLog(), 3000);
            }

            window.onbeforeunload = () => {
                if (tailInterval) clearInterval(tailInterval);
            };

            console.log("Log Viewer Initialized - Mode:", logViewMode);
        },

        fetchLog: async function () {
            try {
                const resp = await fetch(`/api/sftp/view_log/${hostId}?path=${encodeURIComponent(path)}`);
                const data = await resp.json();
                const contentEl = document.getElementById('logContent');

                if (data.content) {
                    if (data.content !== lastContent) {
                        contentEl.innerText = data.content;
                        contentEl.scrollTop = contentEl.scrollHeight;
                        lastContent = data.content;
                    }
                } else {
                    contentEl.innerText = '로그 로드 실패: ' + (data.error || '알 수 없는 오류');
                }
            } catch (e) {
                document.getElementById('logContent').innerText = '데이터를 가져오는 중 오류가 발생했습니다.';
            }
        }
    };
})();
