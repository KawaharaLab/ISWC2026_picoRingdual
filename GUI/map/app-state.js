window.AppState = {
    currentScreen: 'menu',
    selectedMenuIdx: 0,
    menuIds: ['menu-video', 'menu-map', 'menu-pdf']
};

window.toggleFullscreen = function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch((err) => {
            if (window.updateSerialLog) {
                window.updateSerialLog(`FS ERR: ${err.message}`);
            }
        });
        return;
    }
    document.exitFullscreen();
};
