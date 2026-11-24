/**
 * AURA-FOG SMART TRAFFIC & ACCIDENT AI DASHBOARD
 * Core Frontend Engine: Live AI Vision Canvas, WebSockets, GIS Map, and Fog Telemetry
 */

// Application State
const state = {
  activeNodeId: 'FN-01',
  activeNodeName: 'Downtown Broadway & 5th Ave',
  nodes: [],
  vehicles: [],
  telemetry: null,
  activeIncident: null,
  cityKpis: null,
  wsFeed: null,
  wsCity: null,
  audioMuted: false,
  map: null,
  markers: {},
  throughputChart: null,
  particles: [] // Spark particles for collision animations
};

// Audio Synthesizer using Web Audio API
class AudioAlertSynth {
  constructor() {
    this.ctx = null;
    this.lastAlarmTime = 0;
  }

  init() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.ctx = new AudioContext();
      }
    }
  }

  playCollisionAlarm() {
    if (state.audioMuted) return;
    const now = Date.now();
    if (now - this.lastAlarmTime < 4000) return; // Prevent spamming
    this.lastAlarmTime = now;

    try {
      this.init();
      if (!this.ctx) return;
      if (this.ctx.state === 'suspended') {
        this.ctx.resume();
      }

      // Two-tone warning beep: 880Hz -> 659Hz
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';

      const t = this.ctx.currentTime;
      osc.frequency.setValueAtTime(880, t);
      osc.frequency.setValueAtTime(659, t + 0.15);
      osc.frequency.setValueAtTime(880, t + 0.3);
      osc.frequency.setValueAtTime(659, t + 0.45);

      gain.gain.setValueAtTime(0.12, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.65);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.7);
    } catch (e) {
      console.warn("Audio alert prevented by browser policy:", e);
    }
  }

  playDispatchChime() {
    if (state.audioMuted) return;
    try {
      this.init();
      if (!this.ctx) return;
      if (this.ctx.state === 'suspended') this.ctx.resume();

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';

      const t = this.ctx.currentTime;
      osc.frequency.setValueAtTime(523.25, t); // C5
      osc.frequency.exponentialRampToValueAtTime(783.99, t + 0.25); // G5

      gain.gain.setValueAtTime(0.15, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.45);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.5);
    } catch (e) {
      console.warn("Audio chime prevented:", e);
    }
  }
}

const audioSynth = new AudioAlertSynth();

// Initialize the Application on DOM load
window.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  initGISMap();
  initThroughputChart();
  setupEventListeners();
  connectCityWebSocket();
  connectLiveFeedWebSocket(state.activeNodeId);
  fetchInitialData();
});

// 1. GIS Map Setup with Leaflet
function initGISMap() {
  const mapEl = document.getElementById('cityMap');
  if (!mapEl) return;

  state.map = L.map('cityMap', {
    zoomControl: false,
    attributionControl: false
  }).setView([40.7140, -74.0040], 14);

  // High-contrast dark CartoDB tile layer
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(state.map);
}

function updateMapMarkers(nodes) {
  if (!state.map) return;

  nodes.forEach(node => {
    const isAlert = node.status === 'ALERT';
    const isCongested = node.status === 'CONGESTED';
    const isActive = node.node_id === state.activeNodeId;

    let markerColor = '#10b981'; // emerald
    if (isAlert) markerColor = '#f43f5e'; // rose
    else if (isCongested) markerColor = '#f59e0b'; // amber

    const iconHtml = `
      <div style="position:relative; width:24px; height:24px;">
        <div style="
          position:absolute; inset:0; border-radius:50%;
          background:${markerColor};
          box-shadow:0 0 ${isActive ? '15px' : '8px'} ${markerColor};
          border:2px solid ${isActive ? '#ffffff' : '#0f172a'};
          opacity:0.95;
          animation:${isAlert ? 'blink 0.8s infinite' : 'none'};
        "></div>
        <div style="
          position:absolute; top:-16px; left:-18px; width:60px; text-align:center;
          font-size:10px; font-weight:700; color:#f8fafc; font-family:monospace;
          text-shadow:0 1px 4px #000; pointer-events:none;
        ">${node.node_id}</div>
      </div>
    `;

    const customIcon = L.divIcon({
      className: 'fog-marker-icon',
      html: iconHtml,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    if (state.markers[node.node_id]) {
      state.markers[node.node_id].setIcon(customIcon);
    } else {
      const marker = L.marker([node.lat, node.lng], { icon: customIcon }).addTo(state.map);
      marker.on('click', () => switchActiveNode(node.node_id, node.name));
      state.markers[node.node_id] = marker;
    }
  });
}

// 2. Chart.js Traffic Throughput Setup
function initThroughputChart() {
  const ctx = document.getElementById('trafficThroughputChart').getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 120);
  gradient.addColorStop(0, 'rgba(6, 182, 212, 0.45)');
  gradient.addColorStop(1, 'rgba(6, 182, 212, 0.02)');

  state.throughputChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({ length: 12 }, (_, i) => `T-${12 - i}`),
      datasets: [{
        label: 'Vehicles / Cycle',
        data: [22, 25, 29, 34, 30, 26, 38, 42, 35, 31, 28, 33],
        borderColor: '#06b6d4',
        borderWidth: 2,
        backgroundColor: gradient,
        fill: true,
        tension: 0.35,
        pointRadius: 2,
        pointBackgroundColor: '#38bdf8'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          borderColor: 'rgba(56, 189, 248, 0.3)',
          borderWidth: 1,
          titleFont: { family: 'JetBrains Mono' },
          bodyFont: { family: 'Outfit' }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: { color: '#64748b', font: { size: 9, family: 'JetBrains Mono' } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: { color: '#64748b', font: { size: 9, family: 'JetBrains Mono' } },
          min: 10
        }
      }
    }
  });
}

function updateThroughputChart(data) {
  if (!state.throughputChart || !data || data.length === 0) return;
  state.throughputChart.data.labels = data.map((_, i) => `T-${data.length - 1 - i}`);
  state.throughputChart.data.datasets[0].data = data;
  state.throughputChart.update('none'); // Update without full redraw
}

// 3. WebSocket Real-time Connections with Serverless (Vercel) HTTP Polling Fallback
let livePollingTimer = null;
let cityPollingTimer = null;
let wsFailCount = 0;

function startHttpPollingFallback() {
  if (livePollingTimer) return;
  logToTerminal('Live feed connected via high-frequency edge sync.', 'log-info');
  
  livePollingTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/node/${state.activeNodeId}`);
      if (res.ok) {
        const data = await res.json();
        state.telemetry = data.telemetry;
        state.vehicles = data.vehicles;
        state.activeIncident = data.incident;

        renderTelemetry(data.telemetry);
        renderIncidentDesk(data.incident);
        drawIntersectionFrame(data.vehicles, data.telemetry, data.incident);
      }
    } catch (e) {
      // quiet retry
    }
  }, 90);

  if (!cityPollingTimer) {
    cityPollingTimer = setInterval(async () => {
      try {
        const [kpiRes, nodeRes] = await Promise.all([fetch('/api/kpis'), fetch('/api/nodes')]);
        if (kpiRes.ok && nodeRes.ok) {
          const kpis = await kpiRes.json();
          const nodes = await nodeRes.json();
          state.cityKpis = kpis;
          state.nodes = nodes;
          renderCityKpis(kpis);
          renderNodesList(nodes);
          updateMapMarkers(nodes);
        }
      } catch (e) {}
    }, 1500);
  }
}

function connectLiveFeedWebSocket(nodeId) {
  if (state.wsFeed) {
    state.wsFeed.close();
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const wsUrl = `${protocol}//${host}/ws/live-feed/${nodeId}`;

  try {
    state.wsFeed = new WebSocket(wsUrl);

    state.wsFeed.onopen = () => {
      wsFailCount = 0;
      if (livePollingTimer) {
        clearInterval(livePollingTimer);
        livePollingTimer = null;
      }
    };

    state.wsFeed.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        state.telemetry = data.telemetry;
        state.vehicles = data.vehicles;
        state.activeIncident = data.incident;

        renderTelemetry(data.telemetry);
        renderIncidentDesk(data.incident);
        drawIntersectionFrame(data.vehicles, data.telemetry, data.incident);
      } catch (e) {
        console.error("Error processing live frame data:", e);
      }
    };

    state.wsFeed.onerror = (err) => {
      wsFailCount++;
      if (wsFailCount >= 2) {
        startHttpPollingFallback();
      }
    };

    state.wsFeed.onclose = () => {
      wsFailCount++;
      if (wsFailCount >= 2) {
        startHttpPollingFallback();
      } else {
        setTimeout(() => {
          if (state.activeNodeId === nodeId) {
            connectLiveFeedWebSocket(nodeId);
          }
        }, 2000);
      }
    };
  } catch (err) {
    startHttpPollingFallback();
  }
}

function connectCityWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const wsUrl = `${protocol}//${host}/ws/city-telemetry`;

  try {
    state.wsCity = new WebSocket(wsUrl);

    state.wsCity.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        state.cityKpis = data.kpis;
        state.nodes = data.nodes;

        renderCityKpis(data.kpis);
        renderNodesList(data.nodes);
        updateMapMarkers(data.nodes);
      } catch (e) {
        console.error("Error processing city telemetry:", e);
      }
    };

    state.wsCity.onerror = () => {
      startHttpPollingFallback();
    };

    state.wsCity.onclose = () => {
      startHttpPollingFallback();
    };
  } catch (err) {
    startHttpPollingFallback();
  }
}

// 4. Initial REST Data Fetch
async function fetchInitialData() {
  try {
    const [nodesRes, kpisRes] = await Promise.all([
      fetch('/api/nodes'),
      fetch('/api/kpis')
    ]);
    const nodes = await nodesRes.json();
    const kpis = await kpisRes.json();

    state.nodes = nodes;
    state.cityKpis = kpis;

    renderCityKpis(kpis);
    renderNodesList(nodes);
    updateMapMarkers(nodes);
    logToTerminal(`System initialized: 5 Fog Nodes operational on decentralized mesh network.`, 'log-success');
  } catch (err) {
    console.error("Failed initial fetch:", err);
  }
}

// 5. Switching Active Fog Node
function switchActiveNode(nodeId, nodeName) {
  state.activeNodeId = nodeId;
  state.activeNodeName = nodeName;

  document.getElementById('activeNodeHeading').textContent = nodeName;
  document.getElementById('activeNodeBadge').textContent = nodeId;

  renderNodesList(state.nodes);
  updateMapMarkers(state.nodes);
  connectLiveFeedWebSocket(nodeId);

  // Center map smoothly on selected node
  const selectedNode = state.nodes.find(n => n.node_id === nodeId);
  if (selectedNode && state.map) {
    state.map.panTo([selectedNode.lat, selectedNode.lng]);
  }

  logToTerminal(`Switched active view to Fog Node ${nodeId} (${nodeName})`, 'log-info');
}

// 6. UI Renderers
function renderCityKpis(kpis) {
  if (!kpis) return;
  document.getElementById('kpiFogLatency').textContent = `${kpis.avg_fog_latency_ms} ms`;
  document.getElementById('kpiLatencyAdvantage').textContent = `${kpis.latency_reduction_pct}%`;
  document.getElementById('kpiBwSaved').textContent = `${kpis.bandwidth_saved_pct}%`;
  document.getElementById('kpiSavedGb').textContent = `${kpis.cumulative_bandwidth_saved_gb} GB`;
  document.getElementById('kpiVehicleCount').textContent = kpis.total_active_vehicles;

  const incidentEl = document.getElementById('kpiIncidentStatus');
  const incidentSub = document.getElementById('kpiIncidentSubtext');
  const incidentIcon = document.getElementById('kpiIncidentIcon');

  if (kpis.active_incidents && kpis.active_incidents.length > 0) {
    incidentEl.textContent = `${kpis.active_incidents.length} ALERT`;
    incidentEl.style.color = 'var(--accent-rose)';
    incidentSub.textContent = `Crash detected at ${kpis.active_incidents[0].location_name}`;
    incidentIcon.setAttribute('data-lucide', 'alert-octagon');
    incidentIcon.style.color = 'var(--accent-rose)';
  } else {
    incidentEl.textContent = 'NORMAL';
    incidentEl.style.color = 'var(--accent-emerald)';
    incidentSub.textContent = 'All Corridors Clear';
    incidentIcon.setAttribute('data-lucide', 'shield-check');
    incidentIcon.style.color = 'rgba(16,185,129,0.4)';
  }
  lucide.createIcons();
}

function renderNodesList(nodes) {
  const container = document.getElementById('fogNodesList');
  if (!container || !nodes) return;

  container.innerHTML = nodes.map(node => {
    const isActive = node.node_id === state.activeNodeId;
    const hasAlert = node.status === 'ALERT';
    let pillClass = 'status-online';
    if (hasAlert) pillClass = 'status-alert';
    else if (node.status === 'CONGESTED') pillClass = 'status-congested';

    return `
      <div class="node-list-item ${isActive ? 'active' : ''} ${hasAlert ? 'has-alert' : ''}" 
           onclick="switchActiveNode('${node.node_id}', '${node.name}')">
        <div>
          <div style="font-size:0.84rem; font-weight:700; color:${isActive ? 'var(--accent-cyan)' : '#f8fafc'};">
            ${node.node_id}
          </div>
          <div style="font-size:0.72rem; color:var(--text-secondary); max-width:160px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            ${node.name}
          </div>
        </div>
        <div style="text-align:right;">
          <span class="status-pill ${pillClass}">${node.status}</span>
          <div style="font-size:0.68rem; font-family:var(--font-mono); color:var(--text-muted); margin-top:2px;">
            ${node.vehicle_count} veh // ${node.inference_latency_ms}ms
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderTelemetry(telem) {
  if (!telem) return;

  // Stream stats
  document.getElementById('streamFps').textContent = telem.fps.toFixed(1);
  document.getElementById('streamAvgSpeed').textContent = `${telem.avg_speed_kmh} km/h`;
  document.getElementById('hudLatency').textContent = `${telem.inference_latency_ms}ms`;

  // Hardware load
  document.getElementById('nodeCpuLoad').textContent = `${telem.cpu_load_pct}%`;
  document.getElementById('nodeCpuBar').style.width = `${telem.cpu_load_pct}%`;
  document.getElementById('nodeMemLoad').textContent = `${telem.memory_load_pct}%`;
  document.getElementById('nodeMemBar').style.width = `${telem.memory_load_pct}%`;

  // Fog vs Cloud Benchmarks
  document.getElementById('bmFogLatency').textContent = `${telem.inference_latency_ms} ms`;
  document.getElementById('bmFogBar').style.width = `${Math.min(100, (telem.inference_latency_ms / 250) * 100)}%`;
  document.getElementById('bmCloudLatency').textContent = `${telem.cloud_latency_ms} ms`;
  document.getElementById('bmCloudBar').style.width = `${Math.min(100, (telem.cloud_latency_ms / 250) * 100)}%`;
  document.getElementById('bmBwReduced').textContent = `${telem.bandwidth_saved_pct}%`;

  // Traffic Signal UI update
  updateSignalControllerUI(telem.signal);

  // Update chart if throughput data present
  if (telem.historical_throughput) {
    updateThroughputChart(telem.historical_throughput);
  }
}

function updateSignalControllerUI(signal) {
  if (!signal) return;

  const phase = signal.current_phase;
  const timeRemaining = signal.time_remaining;

  const nsRed = document.getElementById('nsLightRed');
  const nsYellow = document.getElementById('nsLightYellow');
  const nsGreen = document.getElementById('nsLightGreen');

  const ewRed = document.getElementById('ewLightRed');
  const ewYellow = document.getElementById('ewLightYellow');
  const ewGreen = document.getElementById('ewLightGreen');

  // Reset classes
  [nsRed, nsYellow, nsGreen, ewRed, ewYellow, ewGreen].forEach(el => {
    el.className = 'signal-bulb';
  });

  const phaseLabel = document.getElementById('signalPhaseLabel');
  const timerLabel = document.getElementById('signalTimerCountdown');
  const greenWaveBanner = document.getElementById('greenWaveAlert');

  timerLabel.textContent = `${timeRemaining}s`;

  if (phase === 'EMERGENCY_CORRIDOR') {
    nsGreen.classList.add('green-active');
    ewRed.classList.add('red-active');
    phaseLabel.textContent = 'EMERGENCY GREEN WAVE';
    phaseLabel.style.color = '#10b981';
    greenWaveBanner.style.display = 'flex';
  } else {
    greenWaveBanner.style.display = 'none';

    if (phase === 'NS_GREEN') {
      nsGreen.classList.add('green-active');
      ewRed.classList.add('red-active');
      phaseLabel.textContent = 'NS GREEN CORRIDOR';
      phaseLabel.style.color = 'var(--accent-emerald)';
    } else if (phase === 'NS_YELLOW') {
      nsYellow.classList.add('yellow-active');
      ewRed.classList.add('red-active');
      phaseLabel.textContent = 'NS CAUTION YELLOW';
      phaseLabel.style.color = 'var(--accent-amber)';
    } else if (phase === 'EW_GREEN') {
      nsRed.classList.add('red-active');
      ewGreen.classList.add('green-active');
      phaseLabel.textContent = 'EW GREEN CORRIDOR';
      phaseLabel.style.color = 'var(--accent-emerald)';
    } else if (phase === 'EW_YELLOW') {
      nsRed.classList.add('red-active');
      ewYellow.classList.add('yellow-active');
      phaseLabel.textContent = 'EW CAUTION YELLOW';
      phaseLabel.style.color = 'var(--accent-amber)';
    }
  }
}

function renderIncidentDesk(incident) {
  const noIncident = document.getElementById('noIncidentPlaceholder');
  const activeCard = document.getElementById('activeIncidentCard');
  const canvasBanner = document.getElementById('accidentBanner');
  const countBadge = document.getElementById('incidentCountBadge');

  if (!incident || incident.status === 'RESOLVED') {
    noIncident.style.display = 'block';
    activeCard.style.display = 'none';
    canvasBanner.style.display = 'none';
    countBadge.textContent = '0 ACTIVE';
    countBadge.className = 'status-pill status-online';
    return;
  }

  // Crash active! Play sound alert
  audioSynth.playCollisionAlarm();

  noIncident.style.display = 'none';
  activeCard.style.display = 'block';
  canvasBanner.style.display = 'flex';

  countBadge.textContent = '1 CRASH';
  countBadge.className = 'status-pill status-alert';

  document.getElementById('incSeverityBadge').textContent = `${incident.severity} COLLISION`;
  document.getElementById('incSeverityBadge').className = incident.severity === 'CRITICAL' ? 'badge-critical' : 'badge-high';
  document.getElementById('incTimeBadge').textContent = incident.timestamp.split(' ')[1] || incident.timestamp;
  document.getElementById('incLocation').textContent = incident.location_name;
  document.getElementById('incSpeed').textContent = `${incident.impact_speed_kmh} km/h (Estimated)`;

  const vehicleNames = incident.vehicles_involved.map(v => `${v.id} (${v.type.toUpperCase()})`).join(' vs ');
  document.getElementById('incVehicles').textContent = vehicleNames;

  const recList = document.getElementById('incRecommendations');
  recList.innerHTML = incident.recommended_response.map(r => `<li>${r}</li>`).join('');

  document.getElementById('accidentBannerSub').textContent =
    `Impact speed: ${incident.impact_speed_kmh} km/h between ${vehicleNames}. Emergency units required.`;

  lucide.createIcons();
}

// 7. Live AI Vision Canvas Renderer (60 FPS Visual Feed)
function drawIntersectionFrame(vehicles, telemetry, incident) {
  const canvas = document.getElementById('visionCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  // Background Asphalt & Ground
  ctx.fillStyle = '#060913';
  ctx.fillRect(0, 0, W, H);

  // Concrete roadside curbs
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, W * 0.38, H * 0.38); // Top-left block
  ctx.fillRect(W * 0.62, 0, W * 0.38, H * 0.38); // Top-right block
  ctx.fillRect(0, H * 0.62, W * 0.38, H * 0.38); // Bottom-left block
  ctx.fillRect(W * 0.62, H * 0.62, W * 0.38, H * 0.38); // Bottom-right block

  // Road Surface (Cross intersection)
  ctx.fillStyle = '#141d2f';
  ctx.fillRect(W * 0.38, 0, W * 0.24, H); // Vertical Road (North-South)
  ctx.fillRect(0, H * 0.38, W, H * 0.24); // Horizontal Road (East-West)

  // Intersection Center Box
  ctx.fillStyle = '#17223b';
  ctx.fillRect(W * 0.38, H * 0.38, W * 0.24, H * 0.24);

  // Lane Dividers & Stop Lines
  ctx.strokeStyle = '#f8fafc';
  ctx.lineWidth = 2;

  // Stop lines (North, South, East, West)
  ctx.beginPath();
  // North approach stop line
  ctx.moveTo(W * 0.38, H * 0.38);
  ctx.lineTo(W * 0.50, H * 0.38);
  // South approach stop line
  ctx.moveTo(W * 0.50, H * 0.62);
  ctx.lineTo(W * 0.62, H * 0.62);
  // West approach stop line
  ctx.moveTo(W * 0.38, H * 0.50);
  ctx.lineTo(W * 0.38, H * 0.62);
  // East approach stop line
  ctx.moveTo(W * 0.62, H * 0.38);
  ctx.lineTo(W * 0.62, H * 0.50);
  ctx.stroke();

  // Dashed lane lines
  ctx.setLineDash([8, 8]);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';

  // North-South center divider (Yellow)
  ctx.beginPath();
  ctx.strokeStyle = '#fbbf24';
  ctx.moveTo(W * 0.50, 0);
  ctx.lineTo(W * 0.50, H * 0.38);
  ctx.moveTo(W * 0.50, H * 0.62);
  ctx.lineTo(W * 0.50, H);
  ctx.stroke();

  // East-West center divider (Yellow)
  ctx.beginPath();
  ctx.moveTo(0, H * 0.50);
  ctx.lineTo(W * 0.38, H * 0.50);
  ctx.moveTo(W * 0.62, H * 0.50);
  ctx.lineTo(W, H * 0.50);
  ctx.stroke();

  // Lane sub-dividers (white dashed)
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
  ctx.beginPath();
  // NS lanes
  ctx.moveTo(W * 0.44, 0); ctx.lineTo(W * 0.44, H * 0.38);
  ctx.moveTo(W * 0.56, H * 0.62); ctx.lineTo(W * 0.56, H);
  // EW lanes
  ctx.moveTo(0, H * 0.56); ctx.lineTo(W * 0.38, H * 0.56);
  ctx.moveTo(W * 0.62, H * 0.44); ctx.lineTo(W, H * 0.44);
  ctx.stroke();
  ctx.setLineDash([]); // Reset dash

  // Zebra Pedestrian Crossings
  drawZebraCrossing(ctx, W * 0.38, H * 0.34, W * 0.24, H * 0.035, 'horizontal');
  drawZebraCrossing(ctx, W * 0.38, H * 0.625, W * 0.24, H * 0.035, 'horizontal');
  drawZebraCrossing(ctx, W * 0.34, H * 0.38, W * 0.035, H * 0.24, 'vertical');
  drawZebraCrossing(ctx, W * 0.625, H * 0.38, W * 0.035, H * 0.24, 'vertical');

  // Traffic Light Indicator Dots at Intersections
  drawSignalDots(ctx, W, H, telemetry?.signal?.current_phase);

  // Render Vehicles & AI Bounding Boxes
  if (vehicles && vehicles.length > 0) {
    vehicles.forEach(v => {
      drawVehicle(ctx, v, W, H);
    });
  }

  // Render Collision Particle FX & Shockwaves if incident detected
  if (incident && incident.status !== 'RESOLVED') {
    drawCollisionFX(ctx, incident.collision_x * W, incident.collision_y * H);
  }
}

function drawZebraCrossing(ctx, x, y, w, h, orientation) {
  ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
  const stripes = 7;
  if (orientation === 'horizontal') {
    const step = w / stripes;
    for (let i = 0; i < stripes; i += 2) {
      ctx.fillRect(x + i * step, y, step * 0.8, h);
    }
  } else {
    const step = h / stripes;
    for (let i = 0; i < stripes; i += 2) {
      ctx.fillRect(x, y + i * step, w, step * 0.8);
    }
  }
}

function drawSignalDots(ctx, W, H, phase) {
  if (!phase) return;
  const isNsGreen = phase === 'NS_GREEN' || phase === 'EMERGENCY_CORRIDOR';
  const isNsYellow = phase === 'NS_YELLOW';
  const isEwGreen = phase === 'EW_GREEN';
  const isEwYellow = phase === 'EW_YELLOW';

  const nsColor = isNsGreen ? '#10b981' : (isNsYellow ? '#f59e0b' : '#ef4444');
  const ewColor = isEwGreen ? '#10b981' : (isEwYellow ? '#f59e0b' : '#ef4444');

  // North light post
  drawPulsingBeacon(ctx, W * 0.36, H * 0.36, nsColor);
  // South light post
  drawPulsingBeacon(ctx, W * 0.64, H * 0.64, nsColor);
  // West light post
  drawPulsingBeacon(ctx, W * 0.36, H * 0.64, ewColor);
  // East light post
  drawPulsingBeacon(ctx, W * 0.64, H * 0.36, ewColor);
}

function drawPulsingBeacon(ctx, x, y, color) {
  ctx.beginPath();
  ctx.arc(x, y, 6, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 10;
  ctx.fill();
  ctx.shadowBlur = 0; // Reset blur
}

function drawVehicle(ctx, v, W, H) {
  const cx = v.x * W;
  const cy = v.y * H;

  // Dimensions based on type
  let vw = 24;
  let vh = 42;
  let bodyColor = '#38bdf8';

  if (v.type === 'suv') {
    vw = 26; vh = 46; bodyColor = '#818cf8';
  } else if (v.type === 'truck') {
    vw = 30; vh = 68; bodyColor = '#f59e0b';
  } else if (v.type === 'bus') {
    vw = 32; vh = 80; bodyColor = '#a855f7';
  } else if (v.type === 'motorcycle') {
    vw = 14; vh = 28; bodyColor = '#34d399';
  } else if (v.type === 'ambulance') {
    vw = 28; vh = 56; bodyColor = '#ffffff';
  }

  // Direction rotation
  ctx.save();
  ctx.translate(cx, cy);

  let angle = 0;
  if (v.direction === 'N') angle = 0; // Moving down
  else if (v.direction === 'S') angle = Math.PI; // Moving up
  else if (v.direction === 'W') angle = -Math.PI / 2; // Moving right
  else if (v.direction === 'E') angle = Math.PI / 2; // Moving left

  ctx.rotate(angle);

  // Headlight illumination beam
  if (v.status !== 'collided') {
    const beamGrad = ctx.createRadialGradient(0, vh / 2, 2, 0, vh / 2 + 50, 40);
    beamGrad.addColorStop(0, 'rgba(255, 255, 200, 0.4)');
    beamGrad.addColorStop(1, 'rgba(255, 255, 200, 0)');
    ctx.fillStyle = beamGrad;
    ctx.beginPath();
    ctx.moveTo(-vw / 2, vh / 2);
    ctx.lineTo(-vw, vh / 2 + 50);
    ctx.lineTo(vw, vh / 2 + 50);
    ctx.lineTo(vw / 2, vh / 2);
    ctx.fill();
  }

  // Vehicle Body
  ctx.fillStyle = bodyColor;
  ctx.beginPath();
  ctx.roundRect(-vw / 2, -vh / 2, vw, vh, 4);
  ctx.fill();

  // Windshield & roof
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(-vw / 2 + 2, -vh / 4, vw - 4, vh / 2.5);

  // Red Taillights (glow brighter when braking/stopped)
  const isBraking = v.status === 'braking' || v.status === 'stopped' || v.status === 'collided';
  ctx.fillStyle = isBraking ? '#ef4444' : '#7f1d1d';
  if (isBraking) {
    ctx.shadowColor = '#ef4444';
    ctx.shadowBlur = 8;
  }
  ctx.fillRect(-vw / 2 + 2, -vh / 2 - 2, 4, 3);
  ctx.fillRect(vw / 2 - 6, -vh / 2 - 2, 4, 3);
  ctx.shadowBlur = 0;

  // Ambulance Strobe Lights
  if (v.type === 'ambulance') {
    const strobe = Math.floor(Date.now() / 150) % 2 === 0;
    ctx.fillStyle = strobe ? '#ef4444' : '#3b82f6';
    ctx.shadowColor = ctx.fillStyle;
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(0, 0, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  ctx.restore();

  // Edge AI Detection Bounding Box HUD (Overlay in screen coordinates)
  const bboxW = Math.max(vw, vh) + 14;
  const bboxH = Math.max(vw, vh) + 14;
  const bx = cx - bboxW / 2;
  const by = cy - bboxH / 2;

  const isCollision = v.status === 'collided';
  const boxColor = isCollision ? '#f43f5e' : (v.type === 'ambulance' ? '#10b981' : '#06b6d4');

  // Draw corner brackets
  ctx.strokeStyle = boxColor;
  ctx.lineWidth = 1.5;
  const cornerLen = 6;

  ctx.beginPath();
  // Top-left
  ctx.moveTo(bx, by + cornerLen); ctx.lineTo(bx, by); ctx.lineTo(bx + cornerLen, by);
  // Top-right
  ctx.moveTo(bx + bboxW - cornerLen, by); ctx.lineTo(bx + bboxW, by); ctx.lineTo(bx + bboxW, by + cornerLen);
  // Bottom-left
  ctx.moveTo(bx, by + bboxH - cornerLen); ctx.lineTo(bx, by + bboxH); ctx.lineTo(bx + cornerLen, by + bboxH);
  // Bottom-right
  ctx.moveTo(bx + bboxW - cornerLen, by + bboxH); ctx.lineTo(bx + bboxW, by + bboxH); ctx.lineTo(bx + bboxW, by + bboxH - cornerLen);
  ctx.stroke();

  // Label tag above box
  ctx.font = '9px JetBrains Mono, monospace';
  const labelText = `${v.id} ${Math.round(v.speed_kmh)}km/h`;
  const textWidth = ctx.measureText(labelText).width;

  ctx.fillStyle = 'rgba(6, 9, 19, 0.85)';
  ctx.fillRect(bx, by - 14, textWidth + 6, 12);
  ctx.fillStyle = boxColor;
  ctx.fillText(labelText, bx + 3, by - 5);
}

function drawCollisionFX(ctx, x, y) {
  // Pulsing shockwave ring
  const t = (Date.now() % 1200) / 1200;
  const radius = 20 + t * 40;
  ctx.strokeStyle = `rgba(244, 63, 94, ${1 - t})`;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.stroke();

  // Inner warning flash
  ctx.fillStyle = 'rgba(239, 68, 68, 0.4)';
  ctx.beginPath();
  ctx.arc(x, y, 16, 0, Math.PI * 2);
  ctx.fill();

  // Draw Hazard warning sign
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 14px Outfit, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('⚠ IMPACT', x, y - 26);
  ctx.textAlign = 'start';
}

// 8. Event Logging to Terminal Window
function logToTerminal(message, type = 'log-info') {
  const terminal = document.getElementById('terminalLog');
  if (!terminal) return;

  const timeStr = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.className = `terminal-entry ${type}`;
  entry.innerHTML = `<span style="color:#64748b;">[${timeStr}]</span> ${message}`;

  terminal.appendChild(entry);
  terminal.scrollTop = terminal.scrollHeight;

  // Keep last 40 logs
  while (terminal.children.length > 40) {
    terminal.removeChild(terminal.firstChild);
  }
}

// 9. Interactive Action Handlers & Buttons
function setupEventListeners() {
  // Trigger Collision Button
  document.getElementById('btnTriggerAccident').addEventListener('click', async () => {
    try {
      const res = await fetch(`/api/node/${state.activeNodeId}/trigger-accident`, { method: 'POST' });
      const data = await res.json();
      logToTerminal(`SIMULATION: Collision triggered on ${state.activeNodeId}. AI inference alert initiated.`, 'log-alert');
      audioSynth.playCollisionAlarm();
    } catch (e) {
      console.error("Collision trigger error:", e);
    }
  });

  // Trigger Ambulance Button
  document.getElementById('btnTriggerAmbulance').addEventListener('click', async () => {
    try {
      const res = await fetch(`/api/node/${state.activeNodeId}/trigger-ambulance`, { method: 'POST' });
      const data = await res.json();
      logToTerminal(`EMERGENCY: Ambulance dispatched. Fog Node executing Green Wave preemption.`, 'log-warn');
      audioSynth.playDispatchChime();
    } catch (e) {
      console.error("Ambulance trigger error:", e);
    }
  });

  // Clear Scene Button
  document.getElementById('btnClearScene').addEventListener('click', async () => {
    try {
      await fetch(`/api/node/${state.activeNodeId}/clear-accident`, { method: 'POST' });
      logToTerminal(`Intersection scene cleared on Fog Node ${state.activeNodeId}. Traffic flow normal.`, 'log-success');
    } catch (e) {
      console.error("Clear scene error:", e);
    }
  });

  // Dispatch EMS button from active accident card
  document.getElementById('btnDispatchEMS').addEventListener('click', async () => {
    if (!state.activeIncident) return;
    try {
      const res = await fetch(`/api/incidents/${state.activeIncident.id}/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responder_unit: "Priority Trauma EMS & Traffic Police" })
      });
      const data = await res.json();
      logToTerminal(`DISPATCH: ${data.message}`, 'log-success');
      audioSynth.playDispatchChime();
      alert(`Emergency Units Dispatched to ${state.activeIncident.location_name}! Estimated Arrival: 3.4 mins.`);
    } catch (e) {
      console.error("Dispatch error:", e);
    }
  });

  // Resolve Incident Button
  document.getElementById('btnResolveIncident').addEventListener('click', async () => {
    if (!state.activeIncident) return;
    try {
      await fetch(`/api/incidents/${state.activeIncident.id}/resolve`, { method: 'POST' });
      logToTerminal(`Incident ${state.activeIncident.id} resolved and archived.`, 'log-info');
    } catch (e) {
      console.error("Resolve error:", e);
    }
  });

  // Signal Overrides
  document.getElementById('btnOverrideNS').addEventListener('click', async () => {
    await fetch(`/api/node/${state.activeNodeId}/signal-override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phase: 'NS_GREEN', duration: 25 })
    });
    logToTerminal(`Manual override: NS_GREEN locked for 25s`, 'log-warn');
  });

  document.getElementById('btnOverrideEW').addEventListener('click', async () => {
    await fetch(`/api/node/${state.activeNodeId}/signal-override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phase: 'EW_GREEN', duration: 25 })
    });
    logToTerminal(`Manual override: EW_GREEN locked for 25s`, 'log-warn');
  });

  document.getElementById('btnResetAdaptive').addEventListener('click', async () => {
    await fetch(`/api/node/${state.activeNodeId}/signal-adaptive?enabled=true`, { method: 'POST' });
    logToTerminal(`Traffic signal restored to AI Adaptive Webster mode`, 'log-success');
  });

  // Architecture Modal dialog
  const modal = document.getElementById('fogModal');
  document.getElementById('btnInfoModal').addEventListener('click', () => {
    modal.style.display = 'flex';
  });
  document.getElementById('btnCloseModal').addEventListener('click', () => {
    modal.style.display = 'none';
  });
  document.getElementById('btnDismissModal').addEventListener('click', () => {
    modal.style.display = 'none';
  });

  // Click outside modal to close
  window.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
  });
}
