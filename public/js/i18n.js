// i18n.js
(function (global) {
    'use strict';

    const i18n = {
        translations: {},

        /**
         * 获取用户浏览器当前语言
         */
        getBrowserLanguage() {
            const lang = navigator.language || navigator.userLanguage;
            return lang.split('-')[0];
        },

        /**
         * 将元素内容赋值给tr属性值
         */
        setTr() {
            document.querySelectorAll('[tr]').forEach(el => {
                const textContent = el.textContent?.trim() || '';
                if (textContent) el.setAttribute('tr', textContent);
            });
        },

        /**
         * 将元素内容设置为tr属性值
         */
        applyTr() {
            document.querySelectorAll('[tr]').forEach(el => {
                const trValue = el.getAttribute('tr')?.trim();
                if (trValue) el.textContent = trValue;
            });
        },

        /**
         * 加载翻译文件
         */
        load(url) {
            if (!url || typeof url !== 'string') {
                return Promise.reject(new Error('Invalid URL provided to i18n.load()'));
            }

            return fetch(url)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to load translations: ${response.status} ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (typeof data !== 'object' || data === null) {
                        throw new Error('Translation data must be a valid JSON object');
                    }
                    this.translations = data;
                })
                .catch(error => {
                    console.error('i18n.load() error:', error);
                    throw error;
                });
        },

        /**
         * 应用翻译
         */
        apply() {
            if (!this.translations || Object.keys(this.translations).length === 0) return;
            document.querySelectorAll('[tr]').forEach(el => {
                const originalText = el.getAttribute('tr')?.trim() || '';
                if (!originalText) return;
                const translated = this.tr(originalText);
                if (translated !== originalText) el.textContent = translated;
            });
        },

        /**
         * 翻译单个文本
         */
        tr(key) {
            if (typeof key !== 'string') return String(key || '');
            return this.translations[key?.trim()] || key;
        }
    };

    // 挂载到全局对象
    global.i18n = i18n;

    // 模块化导出
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = i18n;
    }
    if (typeof define === 'function' && define.amd) {
        define(() => i18n);
    }
})(typeof window !== 'undefined' ? window : globalThis || this);