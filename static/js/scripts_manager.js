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
            editor.setValue("#!/bin/bash\n\n# " + window.I18N.write_script_here);
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

            if (!name) return alert(window.I18N.enter_script_name);

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
                alert(window.I18N.error_save);
            }
        },

        deleteScript: async function () {
            if (!currentScriptId) return;
            if (!confirm(window.I18N.confirm_delete)) return;

            try {
                const response = await fetch(`/api/scripts/delete/${currentScriptId}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                if (data.success) {
                    location.reload();
                }
            } catch (error) {
                alert(window.I18N.error_delete);
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
                alert(window.I18N.error_upload);
            }
        },

        execute: async function () {
            const hostId = document.getElementById('targetHost').value;
            if (!hostId) return alert(window.I18N.select_target_host_msg);
            if (!currentScriptId) return alert(window.I18N.first_save_or_load_script);

            const resultArea = document.getElementById('resultArea');
            const resultContent = document.getElementById('resultContent');

            resultArea.style.display = 'block';
            resultContent.innerText = window.I18N.executing_remote;

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
                resultContent.innerText = resultText || window.I18N.success_no_output;
            } catch (error) {
                resultContent.innerText = window.I18N.error_execution_comm;
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
