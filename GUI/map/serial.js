(function serialModule() {
    let activeHandId = 'RIGHT';
    let ports = {
        RIGHT: { port: null, connected: false, lastBtnState: false, lastLeft: false, lastRight: false, pressStartTime: 0, longPressTriggered: false },
        LEFT: { port: null, connected: false, lastBtnState: false, lastLeft: false, lastRight: false, pressStartTime: 0, longPressTriggered: false }
    };

    window.updateSerialLog = function (msg, hand = '') {
        // 既存のマップ内ログ（もしあれば）
        const logEl = document.getElementById('serial-log');
        if (logEl) logEl.innerText = `SERIAL: ${hand ? '['+hand+'] ' : ''}${msg}`;

        // --- 追加：デバッグコンソールへの出力 ---
        const debugConsole = document.getElementById('debug-serial-console');
        if (debugConsole) {
            const newLog = document.createElement('div');
            newLog.innerText = `${new Date().toLocaleTimeString().split(' ')[0]} ${hand ? '['+hand+']' : ''} ${msg}`;
            debugConsole.appendChild(newLog);

            // 古いログを消して最新5行に保つ
            while (debugConsole.childNodes.length > 5) {
                debugConsole.removeChild(debugConsole.firstChild);
            }
        }
        console.log(`[SERIAL DEBUG] ${hand}: ${msg}`);
    };

    function handleSerialData(line, handId) {
        if (!line.startsWith("IMU:")) return;
        try {
            const dataStr = line.split(":")[1];
            const data = dataStr.split(",");
            const gpio = parseInt(data[4]);
            const hand = ports[handId];
            const now = Date.now();

            // --- 1. ボタン判定（決定・モード切替・長押しナビ） ---
            const isBtnDown = !!(gpio & 0x10);

            if (isBtnDown) {
                if (!hand.lastBtnState) {
                    hand.pressStartTime = now;
                    hand.longPressTriggered = false;
                } else {
                    const duration = now - hand.pressStartTime;
                    // 【長押し】ナビ開始（マップ画面時のみ）
                    if (duration > 1000 && !hand.longPressTriggered) {
                        hand.longPressTriggered = true;
                        if (window.AppState.currentScreen === 'map' && window.startNavAnimation) {
                            window.startNavAnimation();
                        }
                    }
                }
            } else if (hand.lastBtnState) {
                // 【離した瞬間】
                const duration = now - hand.pressStartTime;
                if (!hand.longPressTriggered) {
                    // 短押しの処理
                    if (window.AppState.currentScreen === 'menu') {
                        // メニュー画面なら：現在選んでいるものを決定
                        const selectedId = window.AppState.menuIds[window.AppState.selectedMenuIdx];
                        if (selectedId === 'menu-map') window.switchScreen('map');
                        // 他の画面(video等)があればここに追加
                    } else {
                        // マップ画面なら：パン/ズーム切替
                        if (activeHandId !== handId) {
                            activeHandId = handId;
                        } else if (window.toggleMapControlMode) {
                            window.toggleMapControlMode();
                        }
                    }
                }
            }
            hand.lastBtnState = isBtnDown;

            // --- 2. 左右移動判定（メニュー選択 or マップ移動） ---
            const moveLeft = !!(gpio & 0x01);
            const moveRight = !!(gpio & 0x02);
            // 上下も取得（マップ用）
            const moveUp = !!(gpio & 0x04);
            const moveDown = !!(gpio & 0x08);

            if (activeHandId === handId) {
                if (window.AppState.currentScreen === 'menu') {
                    // メニュー操作：a/dが押された瞬間にインデックスを移動
                    if (moveLeft && !hand.lastLeft) {
                        window.AppState.selectedMenuIdx = (window.AppState.selectedMenuIdx - 1 + window.AppState.menuIds.length) % window.AppState.menuIds.length;
                        window.updateMenuUI();
                    }
                    if (moveRight && !hand.lastRight) {
                        window.AppState.selectedMenuIdx = (window.AppState.selectedMenuIdx + 1) % window.AppState.menuIds.length;
                        window.updateMenuUI();
                    }
                } else if (window.AppState.currentScreen === 'map' && window.setMapKeyState) {
                    // マップ操作
                    window.setMapKeyState('a', moveLeft);
                    window.setMapKeyState('d', moveRight);
                    window.setMapKeyState('w', moveUp);
                    window.setMapKeyState('s', moveDown);
                }
            }
            // 押しっぱなし防止用に状態保存
            hand.lastLeft = moveLeft;
            hand.lastRight = moveRight;

        } catch (e) { console.error(e); }
    }

    async function readLoop(handId) {
        const port = ports[handId].port;
        // Readerを直接取得し、デコーダーを介さずにチェックします
        const reader = port.readable.getReader();
        const decoder = new TextDecoder();

        try {
            window.updateSerialLog("READ LOOP STARTED", handId);
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    window.updateSerialLog("READER DONE", handId);
                    break;
                }
                
                // 1. 生のデータが届いた瞬間、何バイト届いたか表示
                // これすら出ない場合は、接続自体が物理的に切れています
                const chunk = decoder.decode(value);
                // window.updateSerialLog(`RAW: ${chunk.length} chars`, handId); 

                buffer += chunk;
                let lines = buffer.split(/\r?\n/); // \r\n と \n 両方に対応
                buffer = lines.pop();

                for (let line of lines) {
                    const cleanLine = line.trim();
                    if (cleanLine) {
                        // 2. 解析直前の文字列をコンソールに出す
                        window.updateSerialLog(`RCV: ${cleanLine.substring(0, 20)}...`, handId);
                        handleSerialData(cleanLine, handId);
                    }
                }
            }
        } catch (e) {
            window.updateSerialLog(`READ ERROR: ${e.message}`, handId);
            console.error(e);
        } finally {
            reader.releaseLock();
        }
    }

    function checkAllConnected() {
        if (ports.LEFT.connected && ports.RIGHT.connected) {
            const gate = document.getElementById('connection-gate');
            const status = document.getElementById('gate-status');
            const menu = document.getElementById('menu-screen');
            
            status.innerText = "ALL SYSTEMS ONLINE. BOOTING...";
            status.style.color = "#00ff88";
            
            setTimeout(() => {
                gate.style.opacity = "0";
                setTimeout(() => {
                    gate.classList.replace('visible', 'hidden');
                    if (menu) menu.classList.replace('hidden', 'visible');
                    if (window.AppState) window.AppState.currentScreen = 'menu';
                }, 500);
            }, 1000);
        }
    }

    window.connectSerial = async function (handId) {
        try {
            const port = await navigator.serial.requestPort();
            await port.open({ baudRate: 115200 });
            ports[handId].port = port;
            ports[handId].connected = true;

            const btn = document.getElementById(`gate-btn-${handId.toLowerCase()}`);
            if (btn) {
                btn.innerText = `${handId} READY`;
                btn.style.borderColor = "#00ff88";
                btn.style.color = "#00ff88";
            }

            readLoop(handId);
            checkAllConnected();
        } catch (error) {
            console.error(error);
        }
    };
})();