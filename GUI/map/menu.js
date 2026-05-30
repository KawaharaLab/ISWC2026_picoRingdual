window.updateMenuUI = function updateMenuUI() {
    window.AppState.menuIds.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (idx === window.AppState.selectedMenuIdx) {
            el.classList.add('selected');
        } else {
            el.classList.remove('selected');
        }
    });
};

window.switchScreen = function switchScreen(screenName) {
    if (screenName === 'map') {
        document.getElementById('menu-screen').style.opacity = '0';
        setTimeout(() => {
            document.getElementById('menu-screen').classList.add('hidden');
            document.getElementById('map-screen').classList.add('visible');
            window.initMap();
        }, 500);
    } else {
        document.getElementById('map-screen').classList.remove('visible');
        document.getElementById('menu-screen').classList.remove('hidden');
        setTimeout(() => {
            document.getElementById('menu-screen').style.opacity = '1';
        }, 50);
    }
    window.AppState.currentScreen = screenName;
};
