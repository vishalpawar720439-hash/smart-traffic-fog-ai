"""
Fog Node Edge Computing Module.
Represents a smart intersection edge node executing real-time AI inference,
local adaptive traffic signal actuation, and edge-to-cloud metadata telemetry aggregation.
"""
import time
import random
from typing import Dict, Any, Optional, List
from .models import FogNodeTelemetry, AccidentEvent, SignalState
from .ai_detector import EdgeAIDetector
from .traffic_controller import FogTrafficSignalController
from .simulation import IntersectionSimulator


class FogNode:
    def __init__(self, node_id: str, name: str, lat: float, lng: float):
        self.node_id = node_id
        self.name = name
        self.lat = lat
        self.lng = lng

        self.detector = EdgeAIDetector(node_id=node_id, location_name=name, gps=[lat, lng])
        self.controller = FogTrafficSignalController(node_id=node_id)
        self.simulator = IntersectionSimulator(node_id=node_id)

        self.active_incident: Optional[AccidentEvent] = None
        self.historical_throughput: List[int] = [random.randint(18, 42) for _ in range(12)]
        self.last_tick = time.time()
        self.throughput_counter = 0
        self.throughput_timer = time.time()

    def tick(self) -> FogNodeTelemetry:
        """
        Main execution loop for the fog node, running at ~10-20 Hz.
        Executes physics update, edge AI vision inference, collision detection,
        and adaptive signal phase adjustments.
        """
        now = time.time()
        dt = min(0.1, max(0.01, now - self.last_tick))
        self.last_tick = now

        # 1. Update Traffic Signal Controller
        signal_state = self.controller.update(dt, self.simulator.vehicles)

        # 2. Advance Vehicle Physics
        self.simulator.update_physics(dt, signal_state)

        # 3. Edge AI Vision Detection & Metrics
        avg_speed, congestion_level, congestion_pct = self.detector.evaluate_traffic_metrics(self.simulator.vehicles)
        inf_latency_ms, cloud_latency_ms, bw_saved_pct = self.detector.compute_edge_inference(self.simulator.vehicles)

        # 4. Check for Collisions / Accidents
        detected_collision = self.detector.check_for_collisions(self.simulator.vehicles)
        if detected_collision:
            self.active_incident = detected_collision

        # Update historical throughput every 10 seconds
        if now - self.throughput_timer > 10.0:
            self.throughput_timer = now
            new_throughput = len(self.simulator.vehicles) + random.randint(2, 6)
            self.historical_throughput.append(new_throughput)
            if len(self.historical_throughput) > 15:
                self.historical_throughput.pop(0)

        # Edge node hardware health simulation
        cpu_load = round(32.0 + len(self.simulator.vehicles) * 1.5 + random.uniform(-2.0, 3.0), 1)
        mem_load = round(44.0 + random.uniform(-1.0, 1.5), 1)

        node_status = "ALERT" if self.active_incident else ("CONGESTED" if congestion_pct > 75.0 else "ONLINE")

        telemetry = FogNodeTelemetry(
            node_id=self.node_id,
            name=self.name,
            lat=self.lat,
            lng=self.lng,
            status=node_status,
            vehicle_count=len(self.simulator.vehicles),
            congestion_level=congestion_level,
            congestion_pct=congestion_pct,
            avg_speed_kmh=avg_speed,
            inference_latency_ms=inf_latency_ms,
            cloud_latency_ms=cloud_latency_ms,
            fps=round(29.8 + random.uniform(-0.6, 0.4), 1),
            bandwidth_raw_mbps=round(34.2 + random.uniform(-1.0, 1.0), 1),
            bandwidth_fog_kbps=round(112.5 + len(self.simulator.vehicles) * 2.1, 1),
            bandwidth_saved_pct=bw_saved_pct,
            cpu_load_pct=min(98.0, cpu_load),
            memory_load_pct=min(95.0, mem_load),
            signal=signal_state,
            active_incident=self.active_incident,
            historical_throughput=self.historical_throughput
        )

        return telemetry

    def get_live_frame_data(self) -> Dict[str, Any]:
        """
        Returns real-time vehicle positions, bounding boxes, labels, and signal states
        for high-speed canvas visualization on frontend.
        """
        telemetry = self.tick()
        vehicles_data = [v.dict() for v in self.simulator.vehicles]
        return {
            "telemetry": telemetry.dict(),
            "vehicles": vehicles_data,
            "incident": self.active_incident.dict() if self.active_incident else None
        }

    def trigger_collision(self) -> bool:
        return self.simulator.trigger_collision()

    def trigger_ambulance(self):
        return self.simulator.trigger_ambulance()

    def clear_incident(self):
        self.active_incident = None
        self.simulator.clear_accidents()
