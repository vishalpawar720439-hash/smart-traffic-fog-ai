"""
Edge AI Vision & Accident Detection Engine for Fog Computing Nodes.
Simulates high-speed quantized Edge AI inference (YOLO-Edge INT8) for vehicle tracking,
anomaly classification, optical-flow speed estimation, and collision physics detection.
"""
import math
import random
import time
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from .models import Vehicle, AccidentEvent


class EdgeAIDetector:
    def __init__(self, node_id: str, location_name: str, gps: List[float]):
        self.node_id = node_id
        self.location_name = location_name
        self.gps = gps
        self.last_detection_time = time.time()
        # Simulated Edge hardware specs (e.g., NVIDIA Jetson Orin / Intel OpenVINO Fog Edge Box)
        self.quantized_model = "YOLO-Edge-V8n-Quantized-INT8"
        self.target_fps = 30.0

    def compute_edge_inference(self, vehicles: List[Vehicle]) -> Tuple[float, float, float]:
        """
        Calculates edge inference latency, bandwidth saved, and edge CPU load.
        Fog nodes process the video locally in ~5-10ms, while transmitting raw video
        to central cloud incurs 180-280ms network round-trip.
        """
        # Baseline edge inference latency with micro jitter
        base_latency = 6.8 + (len(vehicles) * 0.15)
        inference_latency_ms = round(base_latency + random.uniform(-0.4, 0.6), 2)
        cloud_latency_ms = round(210.0 + random.uniform(-15.0, 30.0), 1)

        # Raw HD stream bandwidth (1080p @ 30fps) is ~25-40 Mbps
        raw_mbps = round(32.0 + random.uniform(-2.0, 3.0), 1)
        # Fog Node filters video locally and only sends telemetry JSON (metadata) ~80-140 Kbps
        fog_kbps = round(95.0 + (len(vehicles) * 1.8) + random.uniform(-5.0, 5.0), 1)
        bandwidth_saved_pct = round((1.0 - (fog_kbps / (raw_mbps * 1000.0))) * 100.0, 2)

        return inference_latency_ms, cloud_latency_ms, bandwidth_saved_pct

    def evaluate_traffic_metrics(self, vehicles: List[Vehicle]) -> Tuple[float, str, float]:
        """
        Computes average speed, congestion percentage, and qualitative level.
        """
        if not vehicles:
            return 50.0, "LOW", 10.0

        moving_speeds = [v.speed_kmh for v in vehicles if v.status != 'collided']
        avg_speed = sum(moving_speeds) / len(moving_speeds) if moving_speeds else 0.0

        # Congestion heuristic: vehicle count + ratio of stopped/slow vehicles
        slow_vehicles = sum(1 for v in vehicles if v.speed_kmh < 15.0)
        density_factor = min(len(vehicles) / 25.0, 1.0) * 60.0
        slow_factor = (slow_vehicles / max(len(vehicles), 1)) * 40.0
        congestion_pct = min(100.0, round(density_factor + slow_factor, 1))

        if congestion_pct < 30.0:
            level = "LOW"
        elif congestion_pct < 65.0:
            level = "MODERATE"
        elif congestion_pct < 85.0:
            level = "HEAVY"
        else:
            level = "GRIDLOCK"

        return round(avg_speed, 1), level, congestion_pct

    def check_for_collisions(self, vehicles: List[Vehicle]) -> Optional[AccidentEvent]:
        """
        Edge AI Collision Detection:
        Examines spatial overlap, sudden deceleration, and velocity differential
        between pairs of vehicles in adjacent/opposing lanes or intersection crossing zones.
        """
        n = len(vehicles)
        for i in range(n):
            v1 = vehicles[i]
            if v1.status == 'collided':
                continue

            for j in range(i + 1, n):
                v2 = vehicles[j]
                if v2.status == 'collided':
                    continue

                # Distance calculation between normalized center coordinates
                dx = v1.x - v2.x
                dy = v1.y - v2.y
                distance = math.sqrt(dx * dx + dy * dy)

                # Collision threshold (based on vehicle bounding box proximity in intersection)
                threshold = 0.065

                # Check if vehicles are colliding or about to strike
                if distance < threshold:
                    # Check relative approach speed
                    rel_speed = abs(v1.speed_kmh - v2.speed_kmh) + (v1.speed_kmh + v2.speed_kmh) * 0.4

                    if rel_speed > 18.0 or (v1.status == 'braking' and v2.status == 'braking'):
                        # Mark vehicles as collided
                        v1.status = 'collided'
                        v2.status = 'collided'
                        v1.speed_kmh = 0.0
                        v2.speed_kmh = 0.0

                        # Determine accident severity based on impact kinetic energy approximation
                        impact_speed = max(v1.speed_kmh, v2.speed_kmh, rel_speed)
                        is_heavy = v1.type in ['truck', 'bus'] or v2.type in ['truck', 'bus']

                        if impact_speed > 55.0 or (impact_speed > 40.0 and is_heavy):
                            severity = "CRITICAL"
                            recommended = [
                                "Level-1 Trauma Ambulance (EMS Dispatch)",
                                "Heavy Rescue / Fire & Hazard Unit",
                                "Rapid Police Interceptor (Lane Closure)",
                                "Automated Upstream Green Wave Divert"
                            ]
                        elif impact_speed > 30.0 or is_heavy:
                            severity = "HIGH"
                            recommended = [
                                "Advanced Life Support Ambulance",
                                "Traffic Incident Management Patrol",
                                "Towing & Clearing Unit"
                            ]
                        else:
                            severity = "MODERATE"
                            recommended = [
                                "Paramedic Assessment Unit",
                                "Local Traffic Police (Fender Bender Clearance)"
                            ]

                        inf_ms, cloud_ms, _ = self.compute_edge_inference(vehicles)

                        event = AccidentEvent(
                            id=f"ACC-{int(time.time() * 1000) % 1000000}",
                            node_id=self.node_id,
                            location_name=self.location_name,
                            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            severity=severity,
                            gps=self.gps,
                            vehicles_involved=[
                                {"id": v1.id, "type": v1.type, "lane": v1.lane, "role": "Primary Impact"},
                                {"id": v2.id, "type": v2.type, "lane": v2.lane, "role": "Secondary Impact"}
                            ],
                            impact_speed_kmh=round(impact_speed, 1),
                            collision_x=(v1.x + v2.x) / 2.0,
                            collision_y=(v1.y + v2.y) / 2.0,
                            confidence=round(random.uniform(0.92, 0.98), 2),
                            status="DETECTED",
                            recommended_response=recommended,
                            fog_latency_ms=inf_ms,
                            cloud_estimated_latency_ms=cloud_ms
                        )
                        return event

        return None
