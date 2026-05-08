/* SafeRoute AI — Frontend Application */
const API = 'http://localhost:8000';

// ── State ──
let routeMap, schoolMap;
let routeLayers = [], schoolMarkers = [];

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  initMaps();
  checkHealth();
  bindEvents();
  initNavScroll();
});

// ── Maps ──
function initMaps() {
  const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
  const attr = '&copy; OpenStreetMap';

  routeMap = L.map('route-map').setView([16.772, 79.171], 11);
  L.tileLayer(tileUrl, { attribution: attr }).addTo(routeMap);

  schoolMap = L.map('school-map').setView([16.772, 79.171], 10);
  L.tileLayer(tileUrl, { attribution: attr }).addTo(schoolMap);

  // Fix map rendering in hidden/scrolled containers
  setTimeout(() => { routeMap.invalidateSize(); schoolMap.invalidateSize(); }, 500);
}

// ── Health Check ──
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    const d = await r.json();
    const dot = document.querySelector('.status-dot');
    const txt = document.querySelector('.status-text');
    if (d.status === 'healthy') {
      dot.classList.add('online');
      txt.textContent = `Online · ${d.schools_loaded} schools`;
      document.getElementById('stat-schools').textContent = d.schools_loaded;
    }
  } catch {
    document.querySelector('.status-text').textContent = 'Offline';
    showToast('Backend not reachable. Start the server on port 8000.', 'error');
  }
}

// ── Events ──
function bindEvents() {
  document.getElementById('route-form').addEventListener('submit', handleRouteAnalyze);
  document.getElementById('school-form').addEventListener('submit', handleSchoolSearch);
  document.getElementById('village-form').addEventListener('submit', handleVillageReport);
  document.getElementById('school-analysis-form').addEventListener('submit', handleSchoolAnalysis);

  // Radio cards
  document.querySelectorAll('.radio-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.radio-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      card.querySelector('input').checked = true;
    });
  });

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');
    });
  });

  // Mobile nav
  document.getElementById('mobile-toggle').addEventListener('click', () => {
    const links = document.querySelector('.nav-links');
    links.style.display = links.style.display === 'flex' ? 'none' : 'flex';
  });
}

function initNavScroll() {
  const sections = ['hero', 'route-analyzer', 'school-finder', 'lawmaker'];
  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY + 200;
    sections.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      const link = document.querySelector(`.nav-link[data-section="${id}"]`);
      if (!link) return;
      if (scrollY >= el.offsetTop && scrollY < el.offsetTop + el.offsetHeight) {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
      }
    });
    document.getElementById('navbar').style.boxShadow = window.scrollY > 50 ? '0 4px 30px rgba(0,0,0,0.3)' : 'none';
  });
}

// ── Route Analyzer ──
async function handleRouteAnalyze(e) {
  e.preventDefault();
  const btn = document.getElementById('analyze-btn');
  setLoading(btn, true);
  try {
    const body = {
      origin_lat: parseFloat(document.getElementById('origin-lat').value),
      origin_lon: parseFloat(document.getElementById('origin-lon').value),
      travel_time: document.querySelector('input[name="travel-time"]:checked').value,
    };
    const r = await fetch(`${API}/api/routes/analyze`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Request failed');
    const data = await r.json();
    renderRouteResults(data, body);
    showToast(`Analyzed ${data.schools_found} schools, ${data.routes_per_school.length * 3} routes`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderRouteResults(data, origin) {
  const results = document.getElementById('route-results');
  const best = data.best_route;
  results.classList.remove('hidden');

  // Best route hero card
  document.getElementById('best-route-card').innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px">
      <div>
        <span class="section-tag">🏆 Safest Route Found</span>
        <h3>${best.school_name}</h3>
        <p class="meta">${best.explanation}</p>
        ${best.women_safety_warning ? `<div class="safety-warning">${best.women_safety_warning}</div>` : ''}
      </div>
      <div style="text-align:center">
        ${scoreBadge(best.safety_score, true)}
        <div style="margin-top:8px;font-size:0.8rem;color:var(--text-muted)">${best.distance_km} km · ${data.travel_time}</div>
      </div>
    </div>
    ${best.shap_contributions ? renderShapBars(best.shap_contributions) : ''}
  `;

  // Per-school cards
  const grid = document.getElementById('school-routes-grid');
  grid.innerHTML = data.routes_per_school.map(s => `
    <div class="route-card">
      <div class="card-header">
        <div>
          <div class="card-title">${s.school_name}</div>
          <div class="card-subtitle">${s.distance_km} km away</div>
        </div>
        ${scoreBadge(s.best_route.safety_score)}
      </div>
      <div class="detail-row"><span class="detail-label">Best Route</span><span class="detail-value">${s.best_route.route_id.slice(0, 8)}</span></div>
      <div class="detail-row"><span class="detail-label">Distance</span><span class="detail-value">${s.best_route.distance_km} km</span></div>
      <div class="detail-row"><span class="detail-label">Confidence</span><span class="detail-value">${pct(s.best_route.confidence)}</span></div>
      <div class="detail-row"><span class="detail-label">Alt. Score</span><span class="detail-value">${pct(s.alternative_route.safety_score)}</span></div>
      <p style="margin-top:12px;font-size:0.8rem;color:var(--text-secondary)">${s.best_route.explanation}</p>
      ${s.best_route.women_safety_warning ? `<div class="safety-warning" style="margin-top:8px">${s.best_route.women_safety_warning}</div>` : ''}
    </div>
  `).join('');

  // Draw on map
  routeLayers.forEach(l => routeMap.removeLayer(l));
  routeLayers = [];

  const originMarker = L.marker([origin.origin_lat, origin.origin_lon], {
    icon: L.divIcon({ className: '', html: '<div style="width:14px;height:14px;background:#6366f1;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.4)"></div>', iconSize: [14, 14], iconAnchor: [7, 7] })
  }).addTo(routeMap).bindPopup('Your Location');
  routeLayers.push(originMarker);

  const bounds = L.latLngBounds([[origin.origin_lat, origin.origin_lon]]);

  data.routes_per_school.forEach(s => {
    const feat = s.best_route.geojson_feature;
    if (!feat || !feat.geometry) return;
    const coords = feat.geometry.coordinates.map(c => [c[1], c[0]]);
    const score = s.best_route.safety_score;
    const color = score >= 0.65 ? '#22c55e' : score >= 0.45 ? '#f59e0b' : '#ef4444';
    const line = L.polyline(coords, { color, weight: 4, opacity: 0.8 }).addTo(routeMap);
    line.bindPopup(`<b>${s.school_name}</b><br>Safety: ${pct(score)}`);
    routeLayers.push(line);
    coords.forEach(c => bounds.extend(c));
  });

  data.schools.forEach(s => {
    const m = L.marker([s.lat, s.lon], {
      icon: L.divIcon({ className: '', html: '<div style="width:12px;height:12px;background:#22c55e;border:2px solid #fff;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>', iconSize: [12, 12], iconAnchor: [6, 6] })
    }).addTo(routeMap).bindPopup(`<b>${s.name}</b><br>${s.type} · ${s.grades}<br>${s.students} students`);
    routeLayers.push(m);
    bounds.extend([s.lat, s.lon]);
  });

  routeMap.fitBounds(bounds, { padding: [40, 40] });
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderShapBars(shap) {
  const maxVal = Math.max(...Object.values(shap), 0.01);
  const labels = { road_quality: 'Road Quality', terrain_safety: 'Terrain', weather_safety: 'Weather', crime_safety: 'Crime Safety', population_density: 'Pop. Density', public_transport: 'Transit' };
  const colors = { road_quality: '#3b82f6', terrain_safety: '#22c55e', weather_safety: '#06b6d4', crime_safety: '#ef4444', population_density: '#f59e0b', public_transport: '#8b5cf6' };
  return `<div style="margin-top:20px"><h4 style="font-size:0.85rem;color:var(--text-muted);margin-bottom:12px">Safety Factor Contributions</h4>
    ${Object.entries(shap).map(([k, v]) => `
      <div style="margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px">
          <span style="color:var(--text-secondary)">${labels[k] || k}</span><span style="font-weight:600">${(v * 100).toFixed(1)}%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${(v / maxVal) * 100}%;background:${colors[k] || '#6366f1'}"></div></div>
      </div>
    `).join('')}</div>`;
}

// ── School Finder ──
async function handleSchoolSearch(e) {
  e.preventDefault();
  const btn = document.getElementById('search-btn');
  setLoading(btn, true);
  try {
    const lat = document.getElementById('school-lat').value;
    const lon = document.getElementById('school-lon').value;
    const radius = document.getElementById('search-radius').value;
    const r = await fetch(`${API}/api/schools/boundary?lat=${lat}&lon=${lon}&radius_km=${radius}`);
    if (!r.ok) throw new Error('Request failed');
    const data = await r.json();
    renderSchoolResults(data, { lat: parseFloat(lat), lon: parseFloat(lon), radius: parseFloat(radius) });
    showToast(`Found ${data.features.length} schools`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderSchoolResults(data, query) {
  document.getElementById('school-count-badge').textContent = `${data.features.length} schools`;
  const results = document.getElementById('school-results');
  results.classList.remove('hidden');

  const grid = document.getElementById('school-cards-grid');
  grid.innerHTML = data.features.map(f => {
    const p = f.properties;
    const needScore = p.need_score || 0;
    return `
    <div class="school-card">
      <div class="card-header">
        <div>
          <div class="card-title">${p.name}</div>
          <div class="card-subtitle">${p.type} · ${p.grades} · ${p.medium}</div>
        </div>
        ${scoreBadge(1 - needScore)}
      </div>
      <div class="detail-row"><span class="detail-label">Students</span><span class="detail-value">${p.students}</span></div>
      <div class="detail-row"><span class="detail-label">Distance</span><span class="detail-value">${p.distance_km} km</span></div>
      <div class="detail-row"><span class="detail-label">Need Score</span><span class="detail-value">${(needScore * 100).toFixed(1)}%</span></div>
      <div class="detail-row"><span class="detail-label">Facilities</span><span class="detail-value">${(p.facilities || []).join(', ') || 'N/A'}</span></div>
    </div>`;
  }).join('');

  // Map
  schoolMarkers.forEach(m => schoolMap.removeLayer(m));
  schoolMarkers = [];
  const bounds = L.latLngBounds();

  // Search area circle
  const circle = L.circle([query.lat, query.lon], { radius: query.radius * 1000, color: '#6366f1', fillColor: '#6366f1', fillOpacity: 0.05, weight: 1 }).addTo(schoolMap);
  schoolMarkers.push(circle);
  bounds.extend(circle.getBounds());

  data.features.forEach(f => {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const need = p.need_score || 0;
    const color = need > 0.6 ? '#ef4444' : need > 0.4 ? '#f59e0b' : '#22c55e';
    const m = L.circleMarker([lat, lon], { radius: 8, fillColor: color, fillOpacity: 0.8, color: '#fff', weight: 2 })
      .addTo(schoolMap)
      .bindPopup(`<b>${p.name}</b><br>${p.type} · ${p.students} students<br>Need: ${(need * 100).toFixed(1)}%`);
    schoolMarkers.push(m);
    bounds.extend([lat, lon]);
  });

  schoolMap.fitBounds(bounds, { padding: [30, 30] });
}

// ── Village Report ──
async function handleVillageReport(e) {
  e.preventDefault();
  const btn = document.getElementById('village-btn');
  setLoading(btn, true);
  try {
    const name = document.getElementById('village-name').value;
    const r = await fetch(`${API}/api/lawmaker/village-report?village_name=${encodeURIComponent(name)}`);
    if (!r.ok) { const d = await r.json(); throw new Error(d.detail || 'Not found'); }
    const data = await r.json();
    renderVillageReport(data);
    showToast(`Report for ${data.village} generated`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderVillageReport(data) {
  const results = document.getElementById('village-results');
  results.classList.remove('hidden');
  const s = data.summary;

  results.innerHTML = `
    <div class="village-summary">
      <div class="summary-card"><div class="value">${s.total_schools}</div><div class="label">Total Schools</div></div>
      <div class="summary-card"><div class="value">${s.total_students_served}</div><div class="label">Students Served</div></div>
      <div class="summary-card"><div class="value">${s.government_schools}</div><div class="label">Govt Schools</div></div>
      <div class="summary-card"><div class="value">${(s.avg_need_score * 100).toFixed(0)}%</div><div class="label">Avg Need Score</div></div>
      <div class="summary-card"><div class="value">${s.high_need_schools}</div><div class="label">High Need</div></div>
    </div>

    <div class="analysis-section">
      <h4>🏫 Schools Ranked by Need</h4>
      <div class="results-grid">
        ${data.schools_ranked_by_need.map(school => `
          <div class="report-card" style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-md);padding:24px">
            <div class="card-header">
              <div>
                <div class="card-title">${school.school_name}</div>
                <div class="card-subtitle">${school.school_id}</div>
              </div>
              ${scoreBadge(1 - school.need_score)}
            </div>
            <div style="margin:12px 0">
              ${school.top_issues.map(i => `<span class="issue-tag ${i.severity}">${i.issue} · ${i.metric}</span>`).join(' ')}
            </div>
            <div style="margin-top:12px">
              <div style="font-size:0.78rem;font-weight:600;color:var(--text-muted);margin-bottom:8px">INTERVENTIONS</div>
              ${school.interventions.map(iv => `<div class="intervention-item">• ${iv}</div>`).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="analysis-section">
      <h4>🎯 Top Recommended Interventions</h4>
      ${data.recommended_interventions.map((iv, i) => `
        <div class="intervention-item"><strong>${i + 1}.</strong> ${iv}</div>
      `).join('')}
    </div>

    <div style="text-align:right;margin-top:16px;font-size:0.75rem;color:var(--text-muted)">
      Confidence: ${pct(data.confidence_score)} · Generated: ${new Date(data.generated_at).toLocaleString()}
    </div>
  `;
}

// ── School Analysis ──
async function handleSchoolAnalysis(e) {
  e.preventDefault();
  const btn = document.getElementById('school-analysis-btn');
  setLoading(btn, true);
  try {
    const schoolId = document.getElementById('school-id-select').value;
    const r = await fetch(`${API}/api/lawmaker/school-analysis`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ school_id: schoolId }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Failed');
    const data = await r.json();
    renderSchoolAnalysis(data);
    showToast(`Analysis for ${data.school_name} complete`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}

function renderSchoolAnalysis(data) {
  const results = document.getElementById('school-analysis-results');
  results.classList.remove('hidden');
  const need = data.need_assessment;

  results.innerHTML = `
    <div class="result-hero-card">
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px">
        <div>
          <span class="section-tag">📊 School Analysis</span>
          <h3>${data.school_name}</h3>
          <p class="meta">Location: ${data.location.lat}, ${data.location.lon}</p>
        </div>
        <div style="text-align:center">
          ${scoreBadge(1 - need.need_score, true)}
          <div style="margin-top:6px;font-size:0.75rem;color:var(--text-muted)">Need: ${pct(need.need_score)}</div>
        </div>
      </div>
    </div>

    <div class="village-summary">
      <div class="summary-card"><div class="value">${pct(need.crime_risk)}</div><div class="label">Crime Risk</div></div>
      <div class="summary-card"><div class="value">${pct(need.pop_density)}</div><div class="label">Pop Density</div></div>
      <div class="summary-card"><div class="value">${pct(need.weather_risk)}</div><div class="label">Weather Risk</div></div>
      <div class="summary-card"><div class="value">${need.n_facilities}/6</div><div class="label">Facilities</div></div>
      <div class="summary-card"><div class="value">${need.students}</div><div class="label">Students</div></div>
    </div>

    <div class="analysis-section">
      <h4>🛣️ Route Problems (${data.route_problems.total_routes_analysed} routes analyzed)</h4>
      ${data.route_problems.summary.length ? data.route_problems.summary.map(rp => `
        <div class="fix-card">
          <div class="detail-row"><span class="detail-label">Time</span><span class="detail-value">${rp.travel_time}</span></div>
          <div class="detail-row"><span class="detail-label">Safety</span><span class="detail-value">${pct(rp.overall_safety)}</span></div>
          <div class="detail-row"><span class="detail-label">Problem Segments</span><span class="detail-value">${rp.n_problem_segments}</span></div>
          <p style="font-size:0.8rem;color:var(--text-secondary);margin-top:8px">${rp.explanation}</p>
        </div>
      `).join('') : '<p style="color:var(--text-muted)">No significant route problems detected.</p>'}
    </div>

    <div class="analysis-section">
      <h4>⛰️ Terrain Issues</h4>
      ${data.terrain_issues.map(t => `
        <div class="fix-card">
          <div class="fix-text">${t.issue}</div>
          <span class="issue-tag ${t.severity}">${t.severity}</span>
          <p style="font-size:0.78rem;color:var(--text-muted);margin-top:6px">${t.impact}</p>
        </div>
      `).join('')}
    </div>

    <div class="analysis-section">
      <h4>🌦️ Seasonal Weather Patterns</h4>
      <div class="weather-grid">
        ${data.weather_patterns.map(w => `
          <div class="weather-card">
            <div class="season">${w.season}</div>
            <div class="detail-row"><span class="detail-label">Morning Risk</span><span class="detail-value">${(w.morning_risk * 100).toFixed(0)}%</span></div>
            <div class="detail-row"><span class="detail-label">Evening Risk</span><span class="detail-value">${(w.evening_risk * 100).toFixed(0)}%</span></div>
            <div class="concern">${w.concern}</div>
          </div>
        `).join('')}
      </div>
    </div>

    ${data.crime_hotspots.length ? `
    <div class="analysis-section">
      <h4>🔴 Crime Hotspots Nearby</h4>
      <div class="results-grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr))">
        ${data.crime_hotspots.map(h => `
          <div class="fix-card">
            <span class="issue-tag ${h.severity === 'high' ? 'critical' : 'high'}">${h.severity}</span>
            <div class="detail-row"><span class="detail-label">Risk</span><span class="detail-value">${pct(h.crime_risk)}</span></div>
            <div style="font-size:0.72rem;color:var(--text-muted)">${h.lat}, ${h.lon}</div>
          </div>
        `).join('')}
      </div>
    </div>` : ''}

    <div class="analysis-section">
      <h4>🔧 Suggested Fixes</h4>
      ${data.suggested_fixes.map(f => `
        <div class="fix-card">
          <div class="fix-text">${f.fix}</div>
          <div class="fix-meta">
            <span class="issue-tag ${f.priority === 'immediate' ? 'critical' : f.priority === 'high' ? 'high' : 'moderate'}">${f.priority}</span>
            ${f.cost_tier ? `<span class="badge">Cost: ${f.cost_tier}</span>` : ''}
          </div>
        </div>
      `).join('')}
    </div>

    <div style="text-align:right;font-size:0.75rem;color:var(--text-muted)">
      Confidence: ${pct(data.confidence_score)} · ${new Date(data.generated_at).toLocaleString()}
    </div>
  `;
}

// ── Helpers ──
function scoreBadge(score, large) {
  const cls = score >= 0.65 ? 'safe' : score >= 0.45 ? 'moderate' : 'risky';
  const label = score >= 0.65 ? 'Safe' : score >= 0.45 ? 'Moderate' : 'Risky';
  const sz = large ? 'font-size:1.3rem;padding:10px 22px' : '';
  return `<span class="score-badge ${cls}" style="${sz}">${(score * 100).toFixed(0)}% ${label}</span>`;
}

function pct(v) { return (v * 100).toFixed(1) + '%'; }

function setLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.originalText;
  }
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4000);
}

function setLocation(lat, lon, name) {
  document.getElementById('origin-lat').value = lat;
  document.getElementById('origin-lon').value = lon;
  showToast(`Location set: ${name}`, 'info');
}

function setVillage(name) {
  document.getElementById('village-name').value = name;
}
