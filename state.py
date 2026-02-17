from collections import deque

# 전역 상태 관리 모듈
ssh_sessions = {}  # (user_id, host_id) -> manager
monitoring_sessions = {}  # host_id -> manager
active_shells = {}  # (user_id, host_id, tab_id) -> shell
active_sids = {}  # (user_id, host_id, tab_id) -> current_sid
session_backlogs = {}  # (user_id, host_id, tab_id) -> deque
sid_to_info = {}  # sid -> (user_id, host_id, tab_id)
shell_threads = {}  # 하위 호환 매핑용
sid_to_host = {}  # SID - HostID 매핑
input_buffers = {}  # 전역 버퍼 관리
