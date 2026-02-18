/**
 * 자동화 스크립트 도구 관리 모듈
 */

const ScriptManager = (function () {
    let editor;
    let currentScriptId = null;
    let scripts = [];

    return {
        init: function (initialScripts) {
            scripts = initialScripts;

            // Ace Editor 초기화
            editor = ace.edit("editor");
            editor.setTheme("ace/theme/tomorrow_night_eighties");
            editor.session.setMode("ace/mode/sh");
            editor.setOptions({
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: true,
                showPrintMargin: false
            });

            console.log("Script Manager Initialized");
        },

        newScript: function () {
            currentScriptId = null;
            document.getElementById('scriptName').value = '';
            editor.setValue("#!/bin/bash\n\n# 여기에 스크립트를 작성하세요.");
            document.querySelectorAll('.script-item').forEach(el => el.classList.remove('active'));
        },

        loadScript: function (id) {
            const script = scripts.find(s => s.id === id);
            if (script) {
                currentScriptId = id;
                document.getElementById('scriptName').value = script.name;
                editor.setValue(script.content);
                editor.clearSelection();

                document.querySelectorAll('.script-item').forEach(el => el.classList.remove('active'));
                const activeEl = document.getElementById(`script-${id}`);
                if (activeEl) activeEl.classList.add('active');
            }
        },

        saveScript: async function () {
            const name = document.getElementById('scriptName').value;
            const content = editor.getValue();

            if (!name) return alert('스크립트 이름을 입력하세요.');

            try {
                const response = await fetch('/api/scripts/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: currentScriptId, name, content })
                });
                const data = await response.json();
                if (data.success) {
                    location.reload();
                }
            } catch (error) {
                alert('저장 중 오류가 발생했습니다.');
            }
        },

        deleteScript: async function () {
            if (!currentScriptId) return;
            if (!confirm('정말 삭제하시겠습니까?')) return;

            try {
                const response = await fetch(`/api/scripts/delete/${currentScriptId}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                if (data.success) {
                    location.reload();
                }
            } catch (error) {
                alert('삭제 중 오류가 발생했습니다.');
            }
        },

        uploadFile: async function () {
            const fileInput = document.getElementById('scriptUpload');
            if (fileInput.files.length === 0) return;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const response = await fetch('/api/scripts/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.error);
                }
            } catch (error) {
                alert('업로드 중 오류가 발생했습니다.');
            }
        },

        execute: async function () {
            const hostId = document.getElementById('targetHost').value;
            if (!hostId) return alert('대상 호스트를 선택하세요.');
            if (!currentScriptId) return alert('먼저 스크립트를 저장하거나 로드하세요.');

            const resultArea = document.getElementById('resultArea');
            const resultContent = document.getElementById('resultContent');

            resultArea.style.display = 'block';
            resultContent.innerText = '📡 원격 서버로 전송 및 실행 중...';

            try {
                const response = await fetch('/api/scripts/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ script_id: currentScriptId, host_id: hostId })
                });
                const data = await response.json();

                let resultText = data.output || '';
                if (data.error) {
                    resultText += '\n[ERROR]\n' + data.error;
                }
                resultContent.innerText = resultText || '성공 (출력 없음)';
            } catch (error) {
                resultContent.innerText = '❌ 실행 중 통신 오류가 발생했습니다.';
            }
        },

        closeResult: function () {
            document.getElementById('resultArea').style.display = 'none';
        }
    };
})();

// Global functions for HTML onclick handlers
window.newScript = ScriptManager.newScript;
window.loadScript = ScriptManager.loadScript;
window.saveScript = ScriptManager.saveScript;
window.deleteScript = ScriptManager.deleteScript;
window.uploadScriptFile = ScriptManager.uploadFile;
window.executeScript = ScriptManager.execute;
window.closeResult = ScriptManager.closeResult;
