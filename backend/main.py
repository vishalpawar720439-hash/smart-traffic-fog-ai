"""
FastAPI Server & Real-time WebSocket Gateway for Smart Traffic & Fog Computing.
"""
import os
import asyncio
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .engine import CloudCityHub

app = FastAPI(
    title="Real-Time AI Smart Traffic & Accident Detection Fog Computing System",
    description="Decentralized fog computing architecture for edge AI vision, accident detection, and adaptive traffic management.",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Central City Hub managing all fog nodes
city_hub = CloudCityHub()

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


# Request models
class SignalOverrideRequest(BaseModel):
    phase: str  # 'NS_GREEN', 'EW_GREEN', 'NS_YELLOW', 'EW_YELLOW'
    duration: int = 25


class DispatchRequest(BaseModel):
    responder_unit: str = "Level-1 Trauma EMS & Traffic Police"


# REST Endpoints
@app.get("/api/nodes")
async def get_all_nodes():
    """Returns telemetry and status for all active fog nodes in the city."""
    return city_hub.get_all_nodes_summary()


@app.get("/api/node/{node_id}")
async def get_node_details(node_id: str):
    """Returns detailed real-time data for a specific fog node."""
    node = city_hub.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fog Node not found")
    return node.get_live_frame_data()


@app.post("/api/node/{node_id}/trigger-accident")
async def trigger_accident(node_id: str):
    """Simulates a vehicular collision at the target fog node."""
    node = city_hub.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fog Node not found")
    node.trigger_collision()
    # Force a tick so AI detector classifies the crash immediately
    frame_data = node.get_live_frame_data()
    return {
        "success": True,
        "message": f"Collision simulated on Fog Node {node_id} ({node.name}). Edge AI analysis active.",
        "incident": frame_data.get("incident")
    }


@app.post("/api/node/{node_id}/trigger-ambulance")
async def trigger_ambulance(node_id: str):
    """Spawns an emergency vehicle to test Fog Node Green Wave preemption."""
    node = city_hub.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fog Node not found")
    ev = node.trigger_ambulance()
    return {
        "success": True,
        "message": f"Emergency ambulance dispatched through Fog Node {node_id}. Green Wave preemption triggered.",
        "vehicle": ev.dict() if hasattr(ev, 'dict') else str(ev)
    }


@app.post("/api/node/{node_id}/clear-accident")
async def clear_accident(node_id: str):
    """Clears accidents from the specified fog node."""
    node = city_hub.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fog Node not found")
    node.clear_incident()
    return {"success": True, "message": f"Accidents cleared on node {node_id}"}


@app.post("/api/node/{node_id}/signal-override")
async def override_signal(node_id: str, req: SignalOverrideRequest):
    """Allows manual traffic light phase override."""
    node = city_hub.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fog Node not found")
    node.controller.manual_override(req.phase, req.duration)
    return {"success": True, "message": f"Phase override set to {req.phase} for {req.duration}s"}


@app.post("/api/node/{node_id}/signal-adaptive")
async def set_signal_adaptive(node_id: str, enabled: bool = True):
    """Toggles adaptive AI signal control on the fog node."""
    node = city_hub.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Fog Node not found")
    node.controller.set_adaptive(enabled)
    return {"success": True, "adaptive": enabled}


@app.get("/api/kpis")
async def get_city_kpis():
    """Returns city-wide aggregated KPIs and Fog vs Cloud performance metrics."""
    return city_hub.get_city_kpis()


@app.get("/api/incidents")
async def get_incidents():
    """Returns full incident audit log."""
    return {
        "active_incidents": [n.active_incident.dict() for n in city_hub.nodes.values() if n.active_incident],
        "history": [i.dict() for i in city_hub.incident_history]
    }


@app.post("/api/incidents/{incident_id}/dispatch")
async def dispatch_incident(incident_id: str, req: DispatchRequest = DispatchRequest()):
    """Dispatches emergency response units to the incident."""
    res = city_hub.dispatch_incident(incident_id, req.responder_unit)
    return res


@app.post("/api/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str):
    """Marks an incident as resolved and clears the intersection."""
    res = city_hub.resolve_incident(incident_id)
    return res


# WebSockets for Ultra-low-latency Real-time Data
@app.websocket("/ws/live-feed/{node_id}")
async def websocket_live_feed(websocket: WebSocket, node_id: str):
    """
    Streams high-frequency vehicle bounding boxes, trajectories, collision telemetry,
    and signal states directly to the live vision canvas on the dashboard.
    """
    await websocket.accept()
    node = city_hub.get_node(node_id)
    if not node:
        await websocket.close(code=1008, reason="Fog Node not found")
        return

    try:
        while True:
            frame_data = node.get_live_frame_data()
            await websocket.send_json(frame_data)
            # ~20 FPS live telemetry stream (50ms interval)
            await asyncio.sleep(0.05)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass


@app.websocket("/ws/city-telemetry")
async def websocket_city_telemetry(websocket: WebSocket):
    """
    Streams city-wide aggregated KPIs, fog vs cloud latency stats, and multi-node status updates.
    """
    await websocket.accept()
    try:
        while True:
            kpis = city_hub.get_city_kpis()
            nodes_summary = city_hub.get_all_nodes_summary()
            await websocket.send_json({
                "kpis": kpis,
                "nodes": nodes_summary
            })
            await asyncio.sleep(1.0)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass


# Static files mount
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Frontend index.html not found"})
