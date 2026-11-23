"""
Central Cloud Management Hub & Aggregator.
Coordinates distributed Fog Nodes across the city grid, aggregates telemetry,
manages city-wide emergency dispatch operations, and computes cumulative KPIs.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .fog_node import FogNode
from .models import AccidentEvent


class CloudCityHub:
    def __init__(self):
        # 5 Fog Nodes placed at strategic smart city intersection coordinates
        self.nodes: Dict[str, FogNode] = {
            "FN-01": FogNode("FN-01", "Downtown Broadway & 5th Ave", 40.7128, -74.0060),
            "FN-02": FogNode("FN-02", "Metro Hospital Emergency Corridor", 40.7180, -74.0020),
            "FN-03": FogNode("FN-03", "North Expressway Interchange 14", 40.7250, -74.0110),
            "FN-04": FogNode("FN-04", "Tech Park Blvd & Ring Rd", 40.7100, -73.9950),
            "FN-05": FogNode("FN-05", "Harbor Port Cargo Gateway", 40.7040, -74.0150)
        }
        self.incident_history: List[AccidentEvent] = []
        self.cumulative_bandwidth_saved_gb: float = 142.8
        self.start_time = datetime.now()

    def get_node(self, node_id: str) -> Optional[FogNode]:
        return self.nodes.get(node_id)

    def get_all_nodes_summary(self) -> List[Dict[str, Any]]:
        summaries = []
        for node in self.nodes.values():
            telem = node.tick()
            summaries.append(telem.dict())
        return summaries

    def get_city_kpis(self) -> Dict[str, Any]:
        """
        Computes aggregated real-time metrics across all fog nodes.
        """
        all_nodes_telem = [node.tick() for node in self.nodes.values()]

        total_vehicles = sum(t.vehicle_count for t in all_nodes_telem)
        avg_speed = round(sum(t.avg_speed_kmh for t in all_nodes_telem) / max(len(all_nodes_telem), 1), 1)
        avg_fog_latency = round(sum(t.inference_latency_ms for t in all_nodes_telem) / max(len(all_nodes_telem), 1), 1)
        avg_cloud_latency = round(sum(t.cloud_latency_ms for t in all_nodes_telem) / max(len(all_nodes_telem), 1), 1)
        avg_bw_saved = round(sum(t.bandwidth_saved_pct for t in all_nodes_telem) / max(len(all_nodes_telem), 1), 1)

        active_incidents = []
        for node in self.nodes.values():
            if node.active_incident:
                active_incidents.append(node.active_incident.dict())
                # Ensure added to history if not present
                if not any(inc.id == node.active_incident.id for inc in self.incident_history):
                    self.incident_history.insert(0, node.active_incident)

        return {
            "total_nodes": len(self.nodes),
            "online_nodes": sum(1 for t in all_nodes_telem if t.status != "OFFLINE"),
            "alert_nodes": sum(1 for t in all_nodes_telem if t.status == "ALERT"),
            "total_active_vehicles": total_vehicles,
            "city_avg_speed_kmh": avg_speed,
            "avg_fog_latency_ms": avg_fog_latency,
            "avg_cloud_latency_ms": avg_cloud_latency,
            "latency_reduction_pct": round((1.0 - (avg_fog_latency / avg_cloud_latency)) * 100.0, 1),
            "bandwidth_saved_pct": avg_bw_saved,
            "cumulative_bandwidth_saved_gb": round(self.cumulative_bandwidth_saved_gb + (total_vehicles * 0.05), 1),
            "active_incidents": active_incidents,
            "total_incidents_recorded": len(self.incident_history),
            "cloud_connection": "SYNCHRONIZED",
            "uptime_hours": round((datetime.now() - self.start_time).total_seconds() / 3600.0, 2)
        }

    def dispatch_incident(self, incident_id: str, responder_unit: str = "Automated EMS & Traffic Rescue") -> Dict[str, Any]:
        """
        Dispatches emergency personnel to an active accident location.
        """
        for inc in self.incident_history:
            if inc.id == incident_id:
                inc.status = "DISPATCHED"
                break

        for node in self.nodes.values():
            if node.active_incident and node.active_incident.id == incident_id:
                node.active_incident.status = "DISPATCHED"
                return {
                    "success": True,
                    "message": f"Units [{responder_unit}] dispatched to {node.name}. ETA: 3.4 minutes.",
                    "incident": node.active_incident.dict()
                }

        return {"success": False, "message": "Incident not found or already resolved."}

    def resolve_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Resolves incident, clears wreckage, and restores normal signal cycle.
        """
        for inc in self.incident_history:
            if inc.id == incident_id:
                inc.status = "RESOLVED"
                inc.cleared_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for node in self.nodes.values():
            if node.active_incident and node.active_incident.id == incident_id:
                node.clear_incident()
                return {"success": True, "message": f"Incident {incident_id} cleared. Traffic flow restored."}

        return {"success": True, "message": "Incident marked as resolved."}
