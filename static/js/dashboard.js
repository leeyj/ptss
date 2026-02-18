/**
 * 대시보드 호스트 상태 및 실시간 데이터 관리
 */

const Dashboard = (function () {
    let socket;

    return {
        monitoredHosts: new Set(),

        init: function () {
            socket = io();
            this.setupListeners();
            console.log("Dashboard Module Initialized");
        },

        setupListeners: function () {
            // Stats update
            socket.on('server_stats', (data) => {
                // If I am not monitoring this host, maybe ignore? 
                // But if someone else is monitoring, I get broadcast? 
                // Actually server_stats is usually broadcast to everyone.
                // It's fine to update even if I didn't press the button, 
                // OR we can strictly enforce:
                if (this.monitoredHosts.has(data.host_id)) {
                    this.updateHostStats(data.host_id, data.stats);
                }
            });

            // Connection success (My request confirmed)
            socket.on('monitoring_started', (data) => {
                this.monitoredHosts.add(data.host_id);
                const btn = document.getElementById(`monitor-btn-${data.host_id}`);
                const icon = document.getElementById(`monitor-icon-${data.host_id}`);
                if (btn) btn.classList.remove('btn-outline');
                if (btn) btn.classList.add('btn-primary');
                if (icon) {
                    icon.innerText = '📡';
                    icon.classList.remove('spin');
                }
            });

            // Connection error
            socket.on('monitoring_error', (data) => {
                this.monitoredHosts.delete(data.host_id);
                const icon = document.getElementById(`monitor-icon-${data.host_id}`);
                if (icon) {
                    icon.innerText = '👁️';
                    icon.classList.remove('spin');
                }
                alert('Connection Failed: ' + data.message);
            });

            // Global status change
            socket.on('host_status_change', (data) => {
                if (data.status === 'offline') {
                    updateStatus(data.host_id, 'offline');
                    // Reset stats bars?
                    if (this.monitoredHosts.has(data.host_id)) {
                        // Maybe keep the last stats or clear them?
                    }
                } else {
                    updateStatus(data.host_id, 'online');
                }
            });
        },

        toggleMonitoring: function (hostId) {
            const icon = document.getElementById(`monitor-icon-${hostId}`);

            if (this.monitoredHosts.has(hostId)) {
                // Stop
                socket.emit('stop_monitoring', { host_id: hostId });
                this.monitoredHosts.delete(hostId);
                const btn = document.getElementById(`monitor-btn-${hostId}`);
                if (btn) btn.classList.remove('btn-primary');
                if (btn) btn.classList.add('btn-outline');
                icon.innerText = '👁️';

                // Clear UI
                updateStatus(hostId, 'offline'); // Should we? Or just stop updating?
            } else {
                // Start
                icon.innerText = '↻'; // Spinner icon
                icon.classList.add('spin');
                socket.emit('start_monitoring', { host_id: hostId });
            }
        },

        updateHostStats: function (id, stats) {
            // 상태 업데이트
            updateStatus(id, 'online');

            // CPU 업데이트
            const cpuVal = document.getElementById(`cpu-val-${id}`);
            const cpuBar = document.getElementById(`cpu-bar-${id}`);
            if (cpuVal && cpuBar) {
                cpuVal.innerText = stats.cpu + '%';
                cpuBar.style.width = stats.cpu + '%';
                // 임계치에 따른 색상 변경
                cpuBar.style.background = stats.cpu > 80 ? '#ef4444' : (stats.cpu > 50 ? '#f59e0b' : '#38bdf8');
            }

            // RAM 업데이트
            const ramVal = document.getElementById(`ram-val-${id}`);
            const ramBar = document.getElementById(`ram-bar-${id}`);
            if (ramVal && ramBar) {
                ramVal.innerText = stats.ram + '%';
                ramBar.style.width = stats.ram + '%';
                ramBar.style.background = stats.ram > 90 ? '#ef4444' : '#a855f7';
            }

            // Disk 업데이트
            const diskVal = document.getElementById(`disk-val-${id}`);
            const diskBar = document.getElementById(`disk-bar-${id}`);
            if (diskVal && diskBar) {
                diskVal.innerText = stats.disk + '%';
                diskBar.style.width = stats.disk + '%';
            }
        },

        deleteHost: async function (id, name) {
            if (!confirm(`'${name}' 호스트를 삭제하시겠습니까?`)) return;

            try {
                const response = await fetch(`/host/delete/${id}`, { method: 'POST' });
                if (response.ok) {
                    location.reload();
                } else {
                    alert('삭제 중 오류가 발생했습니다.');
                }
            } catch (error) {
                alert('통신 오류가 발생했습니다.');
            }
        },

        handleAddHost: async function (form) {
            const btn = document.getElementById('saveHostBtn');
            const originalText = btn.innerText;
            btn.innerText = '📡 연결 테스트 중...';
            btn.disabled = true;

            const formData = new FormData(form);
            try {
                const response = await fetch('/host/add', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.success) {
                    alert('✅ ' + data.message);
                    location.reload();
                } else {
                    alert('❌ ' + (data.error || '알 수 없는 오류가 발생했습니다.'));
                }
            } catch (error) {
                alert('❌ 서버와 통신 중 오류가 발생했습니다.');
            } finally {
                btn.innerText = originalText;
                btn.disabled = false;
            }
        }
    };
})();

// Global hooks
window.deleteHost = Dashboard.deleteHost;

document.addEventListener('DOMContentLoaded', () => {
    // 호스트 추가 폼 이벤트
    const addHostForm = document.getElementById('addHostForm');
    if (addHostForm) {
        addHostForm.addEventListener('submit', function (e) {
            e.preventDefault();
            Dashboard.handleAddHost(this);
        });
    }

    // 소켓 초기화 및 초기 세션 상태 설정
    Dashboard.init();

    // 서버 초기 상태 동기화 (optional)
    if (window.ACTIVE_HOSTS) {
        window.ACTIVE_HOSTS.forEach(id => {
            updateStatus(id, 'online');
            Dashboard.monitoredHosts.add(id);
            const icon = document.getElementById(`monitor-icon-${id}`);
            if (icon) icon.innerText = '📡';
        });
    }
});

function toggleMonitoring(hostId) {
    Dashboard.toggleMonitoring(hostId);
}
