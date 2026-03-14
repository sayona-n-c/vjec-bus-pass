// ═══════════════════════════════════════════════
//  VML College Bus Pass App – Main JS
// ═══════════════════════════════════════════════

// ── Alert Auto-dismiss ──
document.querySelectorAll('.alert').forEach(el => {
    el.addEventListener('click', () => el.remove());
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 0.4s'; }, 4500);
    setTimeout(() => el.remove(), 5000);
});

// ── Active nav link highlight ──
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href && (href === currentPath || (currentPath.startsWith(href) && href !== '/'))) {
        link.classList.add('active');
    }
});

// ── Fade-up animation on scroll ──
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.card, .stat-card, .route-card, .bus-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(16px)';
    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    observer.observe(el);
});

// ── Button loading state ──
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
        const btn = form.querySelector('[type="submit"]');
        if (btn && !btn.dataset.noLoad) {
            btn.disabled = true;
            const original = btn.innerHTML;
            btn.innerHTML = '<span class="spinner"></span> Please wait…';
            // Re-enable after 10s as a fallback
            setTimeout(() => { btn.disabled = false; btn.innerHTML = original; }, 10000);
        }
    });
});

// ── Occupancy bar colour ──
document.querySelectorAll('.occupancy-fill, .seat-bar-fill').forEach(bar => {
    const pct = parseInt(bar.dataset.pct || bar.style.width || '0');
    bar.classList.remove('low', 'mid', 'high', 'low', 'medium');
    if (pct < 50) { bar.classList.add('low'); }
    else if (pct < 85) { bar.classList.add('mid', 'medium'); }
    else { bar.classList.add('high'); }
});

// ── Live clock (shown if element #live-clock exists) ──
const clockEl = document.getElementById('live-clock');
if (clockEl) {
    const tick = () => {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };
    tick();
    setInterval(tick, 1000);
}

// ── GPS Map polling (runs only on map page) ──
if (typeof L !== 'undefined' && document.getElementById('bus-map')) {
    const map = L.map('bus-map').setView([11.0168, 76.9558], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    const busIcon = L.divIcon({
        html: '<div style="font-size:1.6rem;line-height:1">🚌</div>',
        className: '',
        iconSize: [32, 32],
        iconAnchor: [16, 16],
    });

    const markers = {};

    const fetchBusLocations = () => {
        fetch('/api/bus-locations/')
            .then(r => r.json())
            .then(data => {
                data.buses.forEach(b => {
                    const latlng = [b.lat, b.lng];
                    if (markers[b.bus_id]) {
                        markers[b.bus_id].setLatLng(latlng);
                        markers[b.bus_id].setPopupContent(
                            `<strong>Bus ${b.bus_number}</strong><br>Route: ${b.route}<br>Speed: ${b.speed} km/h<br>Updated: ${b.updated}`
                        );
                    } else {
                        markers[b.bus_id] = L.marker(latlng, { icon: busIcon })
                            .addTo(map)
                            .bindPopup(`<strong>Bus ${b.bus_number}</strong><br>Route: ${b.route}<br>Speed: ${b.speed} km/h<br>Updated: ${b.updated}`);
                    }
                });
            })
            .catch(() => { });
    };

    fetchBusLocations();
    setInterval(fetchBusLocations, 15000);  // refresh every 15s
}

// ── QR Scan (admin scanner page) ──
const scanInput = document.getElementById('qr-scan-input');
if (scanInput) {
    scanInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const qrData = scanInput.value.trim();
            if (!qrData) return;
            const resultEl = document.getElementById('scan-result');
            resultEl.innerHTML = '<span class="spinner"></span> Scanning…';
            fetch('/api/scan-qr/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                body: JSON.stringify({ qr_data: qrData }),
            })
                .then(r => r.json())
                .then(data => {
                    resultEl.innerHTML = data.success
                        ? `<div class="alert alert-success">✅ ${data.message} — Seats left: ${data.available_seats}</div>`
                        : `<div class="alert alert-error">❌ ${data.error}</div>`;
                    scanInput.value = '';
                    scanInput.focus();
                })
                .catch(() => {
                    resultEl.innerHTML = '<div class="alert alert-error">❌ Connection error</div>';
                });
        }
    });
}

// ── CSRF helper ──
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

// ── Print pass button ──
document.querySelectorAll('[data-action="print-pass"]').forEach(btn => {
    btn.addEventListener('click', () => window.print());
});
