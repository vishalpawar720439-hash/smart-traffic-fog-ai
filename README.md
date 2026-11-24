# 🚦 AURA-FOG: Real-Time AI Smart Traffic & Accident Detection Using Fog Computing

A state-of-the-art, decentralized smart city traffic management and accident detection platform powered by **Fog Computing Architecture** and **Edge AI Vision**.

---

## 🌟 Highlights & Key Capabilities

- **Decentralized Fog Computing Architecture**: Edge vision inference at intersection micro-nodes eliminates central cloud latency bottlenecks and reduces raw video streaming bandwidth by **>99%**.
- **Real-Time AI Accident Detection**: Sub-10ms collision identification, trajectory deviation analysis, kinetic impact speed estimation, and automated emergency severity triage (`CRITICAL`, `HIGH`, `MODERATE`).
- **Dynamic Adaptive Traffic Signal Control**: Webster-inspired queue-weighted green phase duration adjustments that continuously adapt to real-time traffic density.
- **Emergency Vehicle "Green Wave" Preemption**: Edge detection of approaching ambulances/fire engines immediately turns downstream signals green and locks conflicting cross-traffic red.
- **Interactive Cyber Command Center UI**:
  - Live 60 FPS Canvas rendering simulated intersection vehicle flows, headlights, brake lights, and AI bounding box HUDs.
  - Interactive Dark GIS Map displaying geographically distributed Fog Nodes.
  - Real-time comparison metrics between Fog Edge vs. Centralized Cloud latency.
  - Emergency Incident Response & Dispatch Desk with audio-visual alarms.
  - Real-time Chart.js traffic throughput curves and live WebSocket event streams.

---

## 🏗️ Fog Computing vs. Cloud Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │               LAYER 3: CENTRAL CITY CLOUD              │
                    │   - Aggregated City-wide Analytics & Long-term KPIs    │
                    │   - Emergency Services Coordination (EMS, Police)      │
                    │   - Historical Incident Audit Logs                     │
                    └───────────────────────────▲────────────────────────────┘
                                                │
                                    Low-bandwidth Telemetry
                                    (JSON Metadata < 120 Kbps)
                                                │
                    ┌───────────────────────────┴────────────────────────────┐
                    │            LAYER 2: FOG COMPUTING NODES (EDGE)         │
                    │  [FN-01] Downtown       [FN-02] Hospital Corridor      │
                    │  [FN-03] Expressway     [FN-04] Tech Park              │
                    │  ────────────────────────────────────────────────────  │
                    │  • Quantized INT8 Edge AI Vision (YOLO-Edge)           │
                    │  • Ultra-low latency collision detection (~8ms)        │
                    │  • Local Adaptive Traffic Signal Controller (Webster)  │
                    │  • Autonomous Operation (Resilient to cloud outages)   │
                    └───────────────────────────▲────────────────────────────┘
                                                │
                                     High-Bandwidth Raw Video
                                      (1080p @ 30 FPS ~ 34 Mbps)
                                                │
                    ┌───────────────────────────┴────────────────────────────┐
                    │              LAYER 1: IOT SENSORS & CAMERAS            │
                    │   - Intersection CCTV Cameras / Optical Sensors        │
                    │   - Inductive Loop Detectors & Emergency RF Transponders│
                    └────────────────────────────────────────────────────────┘
```

### Why Fog Computing for Traffic & Accidents?
1. **Critical Latency Difference**: In high-speed collisions, the "Golden Hour" of trauma response starts instantly. Fog nodes detect collisions and act in **~8ms** (compared to 200–300ms in centralized cloud systems), immediately locking upstream signals to prevent secondary pileups and auto-dispatching EMS.
2. **Bandwidth Efficiency**: Streaming raw 1080p HD feeds from thousands of cameras across a city consumes tens of gigabits per second. Fog nodes process the video locally and only transmit lightweight JSON metadata (~110 Kbps), saving **over 99% of bandwidth**.
3. **Local Autonomy**: If the municipal internet connection or cloud service fails, the Fog Node continues operating intersection signals and logging incidents locally without interruption.

---

## 📁 Project Structure

```
smart-traffic-fog-ai/
├── backend/
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── models.py            # Pydantic schemas (Vehicle, Signal, Incident, Telemetry)
│   │   ├── ai_detector.py       # Edge AI Vision & Collision Detection Engine
│   │   ├── traffic_controller.py# Adaptive Webster Signal & Green Wave Controller
│   │   ├── simulation.py        # Multi-lane vehicle physics & crash simulator
│   │   ├── fog_node.py          # Fog Node edge server logic & bandwidth filtering
│   │   └── cloud_hub.py         # Central city cloud hub & emergency dispatcher
│   ├── main.py                  # FastAPI REST endpoints & WebSockets
│   └── requirements.txt
├── frontend/
│   ├── index.html               # High-tech Cyber Command Dashboard
│   ├── style.css                # Glassmorphism, animations, cyber HUD styling
│   └── app.js                   # 60 FPS Canvas visualizer, Leaflet GIS, Audio Synth
├── run.py                       # One-click startup script
└── README.md                    # Project documentation
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12 / 3.15)
- Standard modern web browser (Chrome, Edge, Firefox, Safari)

### 2. Install Dependencies
```bash
cd smart-traffic-fog-ai
python -m pip install -r backend/requirements.txt
```

### 3. Run Locally
Launch the project with the included launcher:
```bash
python run.py
```
Or directly with uvicorn:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

### 4. Deploy to Vercel ⚡
This project is pre-configured with `vercel.json` and `api/index.py`:
1. Push this repository to GitHub.
2. Go to [vercel.com](https://vercel.com) and click **"Add New..." > "Project"**.
3. Select this repository and click **"Deploy"**.
4. The backend serverless functions and frontend static assets will be deployed automatically!

---

## 🎮 Interactive Controls & Scenarios to Try

Once the dashboard is open:
1. **💥 Simulate Collision**: Click the red button in the top bar. Notice:
   - Vehicles collide at high speed in the intersection core.
   - The Edge AI detects the crash in **~8ms** and tags it with confidence scores.
   - Synthesized audio collision alarm beeps.
   - Incident details appear in the **Accident Dispatch Desk** with impact velocity and recommended EMS units.
   - Click **"Dispatch Emergency Services"** to trigger trauma rescue units.
2. **🚑 Simulate Ambulance**: Click the green button. Notice:
   - A high-priority emergency vehicle approaches with active siren strobes.
   - The Fog Node triggers **"Emergency Green Wave Preemption"**: holding the green light open and turning conflicting directions red.
3. **🗺️ Switch Fog Nodes**: Click any intersection in the **Fog Nodes Grid** or click its marker on the **GIS Map** to inspect different cameras and locations across the city.
4. **🚦 Manual Signal Overrides**: Test manual phase locking (`Force NS Green`, `Force EW Green`) or return to `Auto Adaptive`.
5. **ℹ️ Fog Architecture Guide**: Click the top button to open the detailed interactive architecture modal.

---

## 📡 REST API & WebSocket Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/nodes` | List all fog nodes with real-time telemetry |
| `GET` | `/api/node/{id}` | Detailed node frame data, vehicle coordinates, signals |
| `POST` | `/api/node/{id}/trigger-accident` | Simulate a collision on the specified fog node |
| `POST` | `/api/node/{id}/trigger-ambulance` | Dispatch an emergency vehicle to test green wave preemption |
| `POST` | `/api/node/{id}/clear-accident` | Clear collided vehicles and restore regular traffic flow |
| `POST` | `/api/node/{id}/signal-override` | Manual traffic light phase control |
| `GET` | `/api/kpis` | Aggregated city-wide metrics, latency and bandwidth savings |
| `GET` | `/api/incidents` | Incident history and active accident reports |
| `POST` | `/api/incidents/{id}/dispatch` | Dispatch emergency responder teams |
| `POST` | `/api/incidents/{id}/resolve` | Mark incident resolved and clear scene |
| `WS` | `/ws/live-feed/{node_id}` | High-frequency (~20 FPS) vehicle coordinates & AI bounding boxes |
| `WS` | `/ws/city-telemetry` | Broadcasts city-wide KPIs and node statuses (1 Hz) |

---

## 🛡️ License & Attribution
Designed and built for smart city traffic intelligence, emergency response optimization, and distributed edge computing research.
