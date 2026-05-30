(function mapModule() {
    let map;
    let isNavigating = false;
    let controlMode = 'pan';
    let velLat = 0;
    let velLng = 0;
    let currentNavLatLng = null;

    const friction = 0.94;
    const impulse = 0.000001;
    const manualRoute = [
        [35.715852, 139.763745],
        [35.716118, 139.763853],
        [35.716326, 139.763888],
        [35.716363, 139.764260]
    ];
    const keys = {};

    function updateModeBadge() {
        const modeBadge = document.getElementById('mode-badge');
        if (modeBadge) {
            modeBadge.innerText = `MODE // ${controlMode}`;
        }
    }

    function calculateBearing(lat1, lon1, lat2, lon2) {
        const dLon = ((lon2 - lon1) * Math.PI) / 180;
        const y = Math.sin(dLon) * Math.cos((lat2 * Math.PI) / 180);
        const x =
            Math.cos((lat1 * Math.PI) / 180) * Math.sin((lat2 * Math.PI) / 180) -
            Math.sin((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.cos(dLon);
        return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
    }

    function updateRouteDisplay() {
        if (!map) return;

        const routePath = document.getElementById('route-path');
        const points = manualRoute.map((latlng) => map.latLngToContainerPoint(L.latLng(latlng)));
        routePath.setAttribute('d', `M ${points.map((p) => `${p.x},${p.y}`).join(' L ')}`);

        if (isNavigating && currentNavLatLng) {
            const navIcon = document.getElementById('nav-icon');
            const point = map.latLngToContainerPoint(currentNavLatLng);
            navIcon.style.left = `${point.x - 16}px`;
            navIcon.style.top = `${point.y - 16}px`;
        }
    }

    function setupMapLoop() {
        function loop() {
            if (window.AppState.currentScreen === 'map' && map) {
                if (controlMode === 'pan') {
                    if (keys.w) velLat += impulse;
                    if (keys.s) velLat -= impulse;
                    if (keys.a) velLng -= impulse;
                    if (keys.d) velLng += impulse;

                    if (Math.abs(velLat) > 1e-8 || Math.abs(velLng) > 1e-8) {
                        const center = map.getCenter();
                        map.setView([center.lat + velLat, center.lng + velLng], map.getZoom(), {
                            animate: false
                        });
                    }
                    velLat *= friction;
                    velLng *= friction;
                } else if (controlMode === 'zoom') {
                    if (keys.w) map.zoomIn(0.3);
                    if (keys.s) map.zoomOut(0.3);
                }

                updateRouteDisplay();
            }
            requestAnimationFrame(loop);
        }

        loop();
    }

    window.initMap = function initMap() {
        if (map) {
            setTimeout(() => {
                map.invalidateSize();
                updateRouteDisplay();
            }, 100);
            return;
        }

        map = L.map('map', {
            zoomControl: false,
            attributionControl: false,
            maxZoom: 22,
            zoomSnap: 0,
            inertia: false
        }).setView(manualRoute[0], 20);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxNativeZoom: 19,
            maxZoom: 22
        }).addTo(map);

        map.on('move zoom', updateRouteDisplay);
        setupMapLoop();
    };

    window.startNavAnimation = function startNavAnimation() {
        if (isNavigating) return;

        isNavigating = true;
        document.getElementById('route-path').classList.add('path-visible');
        const navIcon = document.getElementById('nav-icon');
        navIcon.style.display = 'block';
        document.getElementById('status-val').innerText = 'NAVIGATING';

        let currentIdx = 0;
        let subProgress = 0;
        const speed = 0.001;

        function animate() {
            if (window.AppState.currentScreen !== 'map') {
                isNavigating = false;
                navIcon.style.display = 'none';
                return;
            }

            if (currentIdx < manualRoute.length - 1) {
                const p1 = manualRoute[currentIdx];
                const p2 = manualRoute[currentIdx + 1];

                const lat = p1[0] + (p2[0] - p1[0]) * subProgress;
                const lng = p1[1] + (p2[1] - p1[1]) * subProgress;
                currentNavLatLng = L.latLng(lat, lng);

                const bearing = calculateBearing(p1[0], p1[1], p2[0], p2[1]);
                navIcon.style.transform = `rotate(${bearing}deg)`;

                updateRouteDisplay();
                subProgress += speed;

                if (subProgress >= 1) {
                    subProgress = 0;
                    currentIdx += 1;
                }
                requestAnimationFrame(animate);
            } else {
                document.getElementById('status-val').innerText = 'ARRIVED';
                isNavigating = false;
            }
        }

        animate();
    };

    window.toggleMapControlMode = function toggleMapControlMode() {
        controlMode = controlMode === 'pan' ? 'zoom' : 'pan';
        updateModeBadge();
    };

    window.setMapKeyState = function setMapKeyState(key, pressed) {
        keys[key] = pressed;
    };

    window.onMapResize = function onMapResize() {
        if (!map) return;
        map.invalidateSize();
        updateRouteDisplay();
    };
})();
