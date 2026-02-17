window.PTSS = window.PTSS || {};

window.PTSS.Settings = {
    config: {
        theme: 'default',
        fontSize: 14,
        fontFamily: '"JetBrains Mono", monospace'
    },

    themes: {
        default: {
            background: '#0f172a',
            foreground: '#f1f5f9',
            cursor: '#38bdf8',
            selectionBackground: 'rgba(56, 189, 248, 0.3)'
        },
        monokai: {
            background: '#272822',
            foreground: '#f8f8f2',
            cursor: '#f8f8f2',
            selectionBackground: 'rgba(255, 255, 255, 0.3)'
        },
        dracula: {
            background: '#282a36',
            foreground: '#f8f8f2',
            cursor: '#f8f8f2',
            selectionBackground: 'rgba(68, 71, 90, 0.5)'
        },
        solarized: {
            background: '#002b36',
            foreground: '#839496',
            cursor: '#93a1a1',
            selectionBackground: 'rgba(7, 54, 66, 0.5)'
        },
        onedark: {
            background: '#282c34',
            foreground: '#abb2bf',
            cursor: '#528bff',
            selectionBackground: 'rgba(171, 178, 191, 0.3)'
        }
    },

    init() {
        const saved = localStorage.getItem('ptss_terminal_settings');
        if (saved) {
            try {
                this.config = JSON.parse(saved);
            } catch (e) {
                console.error('Failed to parse settings:', e);
            }
        }
        this.updateUI();
        // 콘솔 페이지가 아니더라도 초기화 시점에 한 번 적용 (전역 변수용)
        this.applyToAll();
    },

    open() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'flex';
            this.updateUI();
        }
    },

    close() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    updateUI() {
        // UI 요소가 존재하는지 확인 (설정 페이지 또는 콘솔 모달)
        const fontSizeInput = document.getElementById('settingFontSize');
        const fontFamilySelect = document.getElementById('settingFontFamily');

        if (fontSizeInput) fontSizeInput.value = this.config.fontSize;
        if (fontFamilySelect) fontFamilySelect.value = this.config.fontFamily;

        // Highlight selected theme
        document.querySelectorAll('.theme-item').forEach(el => {
            if (el.dataset.theme === this.config.theme) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });
    },

    setTheme(themeName) {
        this.config.theme = themeName;
        this.updateUI();
        this.applyToAll();
        this.saveToStorage();
    },

    setFontSize(size) {
        this.config.fontSize = parseInt(size);
        this.applyToAll();
        this.saveToStorage();
    },

    setFontFamily(family) {
        this.config.fontFamily = family;
        this.applyToAll();
        this.saveToStorage();
    },

    applyToAll() {
        const theme = this.themes[this.config.theme] || this.themes.default;
        const options = {
            theme: theme,
            fontSize: this.config.fontSize,
            fontFamily: this.config.fontFamily
        };

        if (window.PTSS.Terminal && window.PTSS.Terminal.tabs) {
            Object.values(window.PTSS.Terminal.tabs).forEach(tab => {
                if (tab.term) {
                    // xterm.js 옵션 설정 방식 변경 (options.set 대신 직접 할당 또는 대량 설정)
                    try {
                        tab.term.options.theme = options.theme;
                        tab.term.options.fontSize = options.fontSize;
                        tab.term.options.fontFamily = options.fontFamily;
                    } catch (e) {
                        tab.term.setOption('theme', options.theme);
                        tab.term.setOption('fontSize', options.fontSize);
                        tab.term.setOption('fontFamily', options.fontFamily);
                    }

                    // Trigger fit to ensure consistency
                    setTimeout(() => {
                        if (tab.fitAddon) tab.fitAddon.fit();
                    }, 50);
                }
            });
        }
    },

    saveToStorage() {
        localStorage.setItem('ptss_terminal_settings', JSON.stringify(this.config));
    },

    save() {
        this.saveToStorage();
        this.close();
    }
};

// Initialize settings on load
document.addEventListener('DOMContentLoaded', () => {
    PTSS.Settings.init();
});
