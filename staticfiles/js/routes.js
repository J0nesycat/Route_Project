document.addEventListener("DOMContentLoaded", () => {
    mapboxgl.accessToken = window.mapbox_token;

    const map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/streets-v11',
        center: [35.004569, 31.904589],
        zoom: 8
    });

    const colors = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4", "#46f0f0"];
    let markers = [];

    function clearMarkers() {
        markers.forEach(m => m.remove());
        markers = [];
    }

    function clearRoutes() {
        const layers = map.getStyle().layers || [];
        layers.forEach(layer => {
            if (layer.id.startsWith("route-")) {
                if (map.getLayer(layer.id)) map.removeLayer(layer.id);
                if (map.getSource(layer.id)) map.removeSource(layer.id);
            }
        });
    }

    function loadRoutesForDate(date) {
        fetch(`/route_data/?date=${date}`)
            .then(response => response.json())
            .then(data => {
                const { depot, routes } = data;
                const routeList = document.getElementById("route-list");
                const noRoutesMsg = document.getElementById("no-routes-msg");

                routeList.innerHTML = "";
                clearMarkers();
                clearRoutes();

                if (!routes || routes.length === 0) {
                    noRoutesMsg.style.display = "block";
                    return;
                }

                noRoutesMsg.style.display = "none";

                routes.forEach((route, index) => {
                    const color = colors[index % colors.length];
                    const coords = route.points.map(p => [p.lon, p.lat]);

                    const cityNames = route.points.map(p => p.name).slice(1).join(" ← ");
                    const li = document.createElement("li");
                    li.innerHTML = `🚛 ${route.driver}: <strong>${depot.name}</strong> ← ${cityNames}`;
                    routeList.appendChild(li);

                    const routeId = `route-${route.driver.replace(/\s+/g, '-').toLowerCase()}`;
                    const directionsUrl = `https://api.mapbox.com/directions/v5/mapbox/driving/${coords.map(c => c.join(',')).join(';')}?geometries=geojson&access_token=${window.mapbox_token}`;

                    fetch(directionsUrl)
                        .then(res => res.json())
                        .then(data => {
                            const geometry = data.routes[0].geometry;

                            map.addSource(routeId, {
                                type: "geojson",
                                data: {
                                    type: "Feature",
                                    geometry: geometry
                                }
                            });

                            map.addLayer({
                                id: routeId,
                                type: "line",
                                source: routeId,
                                layout: {
                                    "line-join": "round",
                                    "line-cap": "round"
                                },
                                paint: {
                                    "line-color": color,
                                    "line-width": 4
                                }
                            });
                        })
                        .catch(err => console.error("❌ Directions API error:", err));

                    // Depot marker
                    const depotMarker = new mapboxgl.Marker({ color: "green" })
                        .setLngLat([depot.lon, depot.lat])
                        .setPopup(new mapboxgl.Popup().setText(`Depot: ${depot.name}`))
                        .addTo(map);
                    markers.push(depotMarker);

                    // Stop markers
                    coords.slice(1).forEach((coord, i) => {
                        const marker = new mapboxgl.Marker({ color: "blue" })
                            .setLngLat(coord)
                            .setPopup(new mapboxgl.Popup().setText(`Stop ${i + 1} - ${route.driver}`))
                            .addTo(map);
                        markers.push(marker);
                    });
                });
            })
            .catch(err => console.error("❌ Load error:", err));
    }

    // Sync selected date from URL to dropdown
    const urlParams = new URLSearchParams(window.location.search);
    const selectedFromURL = urlParams.get("selected_date");
    const dropdown = document.getElementById("summary_date");

    if (selectedFromURL && dropdown) {
        dropdown.value = selectedFromURL;
        loadRoutesForDate(selectedFromURL);
    }

    // Load existing route manually
    document.getElementById("load-button").addEventListener("click", () => {
        const date = dropdown.value;
        loadRoutesForDate(date);
    });

    // Show loader on form submit
    const form = document.getElementById("route-form");
    form.addEventListener("submit", () => {
        const overlay = document.getElementById("loading-overlay");
        if (overlay) {
            overlay.style.display = "flex";
        }
    });
});
