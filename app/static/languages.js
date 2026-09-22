// URL paths are public links; UI language identifiers follow BCP 47 (ko).
const LanguageRoutes = (() => {
    const paths = {zh:'zh', ko:'kr', en:'en', ja:'ja', fr:'fr', es:'es', ru:'ru', vi:'vi', mn:'mn', ar:'ar', th:'th', id:'id'};
    const fromPath = () => Object.keys(paths).find(language => '/' + paths[language] === location.pathname.replace(/\/$/, ''));
    function initialLanguage() {
        const explicit = fromPath();
        if (explicit) return explicit;
        let saved;
        try { saved = localStorage.getItem('ui-language'); } catch (_) {}
        if (paths[saved]) return saved;
        for (const locale of navigator.languages || [navigator.language || '']) {
            const language = locale.toLowerCase().replace('_', '-').split('-')[0];
            if (paths[language]) return language;
        }
        return 'zh';
    }
    function remember(language) {
        if (!paths[language]) return;
        try { localStorage.setItem('ui-language', language); } catch (_) {}
        document.cookie = `ui-language=${language}; Path=/; Max-Age=31536000; SameSite=Lax` + (location.protocol === 'https:' ? '; Secure' : '');
    }
    function navigate(language) {
        if (!paths[language]) return;
        history.pushState(null, '', '/' + paths[language] + location.search + location.hash);
        remember(language);
    }
    return {fromPath, initialLanguage, remember, navigate};
})();
