/**
 * Google Maps 実装（ref.html をベースに本アプリへ統合）
 * - libraries=geometry（経路補間・方位）
 * - Polyline（グロー + 点線）と Marker（矢印）でルート表示
 * - PAN: setCenter + 速度は visualScale で除算（ref と同様）
 * - ZOOM: map.setZoom ではなく #zoom-layer の CSS transform: scale（ref と同様）
 */
(function mapModule() {
    const GOOGLE_MAPS_API_KEY = 'YourAPIKey';

    let map;
    let navMarker;
    const routePolylines = [];
    let dottedPolyline = null;
    let routeAnimationOffset = 0;
    let pathCoords = [];
    let isNavigating = false;
    let controlMode = 'pan';

    let velLat = 0;
    let velLng = 0;
    let visualScale = 2.5
    ;

    const friction = 0.94;
    const impulse = 0.0000015;
    const scaleSpeed = 0.02;

    /** ref.html の rawPoints と同一（キャンパスグリッド用サンプル経路） */
    const rawPoints = [
        { lat: 35.715972, lng: 139.763627 },
        { lat: 35.715981, lng: 139.763718 },
        { lat: 35.716314, lng: 139.764013 },
        { lat: 35.716341, lng: 139.764225 },
        { lat: 35.716438, lng: 139.76422 }
    ];

    const keys = {};
    let mapsLoadPromise = null;
    let mapLoopStarted = false;

    function loadGoogleMaps() {
        if (window.google && window.google.maps && window.google.maps.Map) {
            return Promise.resolve();
        }
        if (mapsLoadPromise) {
            return mapsLoadPromise;
        }
        mapsLoadPromise = new Promise((resolve, reject) => {
            const cbName = '__googleMapsJsApiCallback_mapWeb';
            window[cbName] = function onGoogleMapsReady() {
                resolve();
                try {
                    delete window[cbName];
                } catch (e) {
                    window[cbName] = undefined;
                }
            };
            const script = document.createElement('script');
            script.async = true;
            script.defer = true;
            script.onerror = () => reject(new Error('Failed to load Google Maps JavaScript API'));
            script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(
                GOOGLE_MAPS_API_KEY
            )}&loading=async&libraries=geometry&language=en&region=JP&callback=${cbName}`;
            document.head.appendChild(script);
        });
        return mapsLoadPromise;
    }

    function updateModeBadge() {
        const modeBadge = document.getElementById('mode-badge');
        if (modeBadge) {
            modeBadge.innerText = `MODE: ${controlMode.toUpperCase()}`;
            if (controlMode === 'zoom') {
                modeBadge.classList.add('mode-zoom');
            } else {
                modeBadge.classList.remove('mode-zoom');
            }
        }
    }

    function syncZoomLayerTransform() {
        const layer = document.getElementById('zoom-layer');
        if (layer) {
            layer.style.transform = `scale(${visualScale})`;
        }
    }

    function buildRouteGraphics() {
        const glowPoly = new google.maps.Polyline({
            path: pathCoords,
            strokeColor: '#008cff',
            strokeOpacity: 0.25,
            strokeWeight: 8,
            visible: false,
            map
        });
        routePolylines.push(glowPoly);

        const lineSymbol = {
            path: google.maps.SymbolPath.CIRCLE,
            fillOpacity: 1,
            scale: 3,
            fillColor: '#008cff',
            strokeWeight: 0
        };

        const dottedPoly = new google.maps.Polyline({
            path: pathCoords,
            strokeOpacity: 0,
            visible: false,
            icons: [
                {
                    icon: lineSymbol,
                    offset: '0',
                    repeat: '15px'
                }
            ],
            map
        });
        routePolylines.push(dottedPoly);
        dottedPolyline = dottedPoly;

        const arrowSvg = {
            path: 'M16 4 L28 28 L16 22 L4 28 Z',
            fillColor: '#008cff',
            fillOpacity: 1,
            strokeWeight: 2,
            strokeColor: '#ffffff',
            rotation: 0,
            scale: 1,
            anchor: new google.maps.Point(16, 16)
        };

        navMarker = new google.maps.Marker({
            position: pathCoords[0],
            map,
            icon: arrowSvg,
            visible: false,
            zIndex: 100
        });
    }

    function setupMapLoop() {
        if (mapLoopStarted) return;
        mapLoopStarted = true;

        function loop() {
            if (window.AppState.currentScreen === 'map' && map) {
                if (controlMode === 'pan') {
                    if (keys.w) velLat += impulse / visualScale;
                    if (keys.s) velLat -= impulse / visualScale;
                    if (keys.a) velLng -= impulse / visualScale;
                    if (keys.d) velLng += impulse / visualScale;

                    if (Math.abs(velLat) > 1e-10 || Math.abs(velLng) > 1e-10) {
                        const center = map.getCenter();
                        map.setCenter({
                            lat: center.lat() + velLat,
                            lng: center.lng() + velLng
                        });
                    }
                    velLat *= friction;
                    velLng *= friction;
                } else if (controlMode === 'zoom') {
                    if (keys.w) visualScale *= 1 + scaleSpeed;
                    if (keys.s) visualScale /= 1 + scaleSpeed;
                    visualScale = Math.max(1.0, Math.min(visualScale, 15));
                    syncZoomLayerTransform();
                }

                // ルートの点線を流れるようにアニメーション
                if (dottedPolyline) {
                    routeAnimationOffset = (routeAnimationOffset + 0.8) % 60;
                    const icons = dottedPolyline.get('icons') || [];
                    if (icons.length > 0) {
                        icons[0] = {
                            ...icons[0],
                            offset: `${routeAnimationOffset}px`
                        };
                        dottedPolyline.set('icons', icons);
                    }
                }
            }
            requestAnimationFrame(loop);
        }

        loop();
    }

    window.initMap = async function initMap() {
        try {
            await loadGoogleMaps();
        } catch (err) {
            console.error(err);
            return;
        }

        if (map) {
            setTimeout(() => {
                google.maps.event.trigger(map, 'resize');
            }, 100);
            return;
        }

        const startPoint = rawPoints[0];
        const mapOptions = {
            center: { lat: startPoint.lat, lng: startPoint.lng },
            zoom: 19,
            minZoom: 3,
            maxZoom: 22,
            disableDefaultUI: true,
            gestureHandling: 'none',
            clickableIcons: false,
            keyboardShortcuts: false,
            draggable: false,
            scrollwheel: false,
            disableDoubleClickZoom: true,
            mapTypeId: 'roadmap'
        };

        map = new google.maps.Map(document.getElementById('map'), mapOptions);
        pathCoords = rawPoints.map((p) => new google.maps.LatLng(p.lat, p.lng));

        buildRouteGraphics();
        syncZoomLayerTransform();
        updateModeBadge();

        google.maps.event.addListenerOnce(map, 'idle', () => {
            setupMapLoop();
        });
    };

    window.startNavAnimation = function startNavAnimation() {
        if (isNavigating || !map || !navMarker) return;

        isNavigating = true;
        routePolylines.forEach((p) => p.setVisible(true));
        navMarker.setVisible(true);

        const statusVal = document.getElementById('status-val');
        if (statusVal) statusVal.innerText = 'NAVIGATING';

        let step = 0;
        const totalSteps = 1000;

        function animate() {
            if (window.AppState.currentScreen !== 'map') {
                isNavigating = false;
                navMarker.setVisible(false);
                routePolylines.forEach((p) => p.setVisible(false));
                return;
            }

            if (step >= totalSteps) {
                isNavigating = false;
                if (statusVal) statusVal.innerText = 'ARRIVED';
                return;
            }

            const fraction = step / totalSteps;
            const pathLength = google.maps.geometry.spherical.computeLength(pathCoords);
            const distanceAtStep = pathLength * fraction;

            let currentDistance = 0;
            let targetLatLng = pathCoords[0];
            let heading = 0;

            for (let i = 0; i < pathCoords.length - 1; i += 1) {
                const segmentDist = google.maps.geometry.spherical.computeDistanceBetween(
                    pathCoords[i],
                    pathCoords[i + 1]
                );
                if (currentDistance + segmentDist >= distanceAtStep) {
                    const segmentFraction = (distanceAtStep - currentDistance) / segmentDist;
                    targetLatLng = google.maps.geometry.spherical.interpolate(
                        pathCoords[i],
                        pathCoords[i + 1],
                        segmentFraction
                    );
                    heading = google.maps.geometry.spherical.computeHeading(pathCoords[i], pathCoords[i + 1]);
                    break;
                }
                currentDistance += segmentDist;
            }

            navMarker.setPosition(targetLatLng);
            const icon = navMarker.getIcon();
            if (typeof icon === 'object' && icon !== null) {
                icon.rotation = heading;
                navMarker.setIcon(icon);
            }

            step += 0.2;
            requestAnimationFrame(animate);
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
        google.maps.event.trigger(map, 'resize');
    };
})();
