window.onload = () => {
    const serialBtn = document.getElementById('serial-btn');
    const fullscreenBtn = document.getElementById('fullscreen-btn');

    if (serialBtn) {
        serialBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            window.connectSerial();
        });
    }

    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            window.toggleFullscreen();
        });
    }

    window.updateMenuUI();
};

let lastSpaceTime = 0;

window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    window.setMapKeyState(k, true);

    if (k === 'f') {
        window.toggleFullscreen();
    }

    if (window.AppState.currentScreen === 'menu') {
        if (k === 'arrowright') {
            window.AppState.selectedMenuIdx = (window.AppState.selectedMenuIdx + 1) % 3;
            window.updateMenuUI();
        } else if (k === 'arrowleft') {
            window.AppState.selectedMenuIdx = (window.AppState.selectedMenuIdx - 1 + 3) % 3;
            window.updateMenuUI();
        } else if (k === 'enter' && window.AppState.selectedMenuIdx === 1) {
            window.switchScreen('map');
        }
        return;
    }

    if (window.AppState.currentScreen === 'map') {
        if (k === 'backspace') {
            window.switchScreen('menu');
        } else if (k === ' ') {
            const now = Date.now();
            if (now - lastSpaceTime < 300) {
                window.startNavAnimation();
            } else {
                window.toggleMapControlMode();
            }
            lastSpaceTime = now;
        }
    }
});

window.addEventListener('keyup', (e) => {
    window.setMapKeyState(e.key.toLowerCase(), false);
});

window.onresize = () => {
    window.onMapResize();
};
