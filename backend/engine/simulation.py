"""
Multi-lane Vehicle Physics & Traffic Intersection Simulator.
Simulates realistic vehicle motion, car-following models, lane discipline,
traffic signal compliance, and triggered accident/emergency events.
"""
import random
import time
from typing import List, Dict, Optional
from .models import Vehicle, SignalState


VEHICLE_PROFILES = [
    {"type": "car", "length": 0.05, "width": 0.03, "max_speed": 62.0, "weight": 60},
    {"type": "suv", "length": 0.06, "width": 0.032, "max_speed": 55.0, "weight": 20},
    {"type": "truck", "length": 0.09, "width": 0.038, "max_speed": 44.0, "weight": 10},
    {"type": "bus", "length": 0.10, "width": 0.038, "max_speed": 40.0, "weight": 6},
    {"type": "motorcycle", "length": 0.035, "width": 0.02, "max_speed": 68.0, "weight": 4},
]


class IntersectionSimulator:
    def __init__(self, node_id: str, max_vehicles: int = 18):
        self.node_id = node_id
        self.max_vehicles = max_vehicles
        self.vehicles: List[Vehicle] = []
        self.vehicle_seq = 100
        self.accident_in_progress = False

        # Pre-seed intersection with initial moving vehicles
        for _ in range(8):
            self.spawn_vehicle()

    def _get_random_profile(self) -> Dict:
        types = [p["type"] for p in VEHICLE_PROFILES]
        weights = [p["weight"] for p in VEHICLE_PROFILES]
        chosen_type = random.choices(types, weights=weights, k=1)[0]
        return next(p for p in VEHICLE_PROFILES if p["type"] == chosen_type)

    def spawn_vehicle(self, force_type: Optional[str] = None, force_dir: Optional[str] = None) -> Optional[Vehicle]:
        """
        Spawns a new vehicle at one of the 4 approaches (North, South, East, West).
        """
        if len(self.vehicles) >= self.max_vehicles and force_type != 'ambulance':
            return None

        self.vehicle_seq += 1
        direction = force_dir or random.choice(['N', 'S', 'E', 'W'])
        profile = next((p for p in VEHICLE_PROFILES if p["type"] == force_type), None) if force_type else self._get_random_profile()
        v_type = force_type or profile["type"]
        base_speed = 75.0 if v_type == 'ambulance' else profile["max_speed"] * random.uniform(0.75, 1.05)

        # Coordinates configuration:
        # Canvas space: 0.0 to 1.0. Intersection center is at (0.5, 0.5)
        # N: moves South (y: 0.0 -> 1.0), lane 0 (x=0.45) or lane 1 (x=0.48)
        # S: moves North (y: 1.0 -> 0.0), lane 0 (x=0.52) or lane 1 (x=0.55)
        # W: moves East (x: 0.0 -> 1.0), lane 0 (y=0.52) or lane 1 (y=0.55)
        # E: moves West (x: 1.0 -> 0.0), lane 0 (y=0.45) or lane 1 (y=0.48)
        lane = random.choice([0, 1])

        if direction == 'N':
            x = 0.45 if lane == 0 else 0.48
            y = random.uniform(-0.1, -0.02)
            vx = 0.0
            vy = (base_speed / 3600.0) * 1.5
        elif direction == 'S':
            x = 0.52 if lane == 0 else 0.55
            y = random.uniform(1.02, 1.1)
            vx = 0.0
            vy = -(base_speed / 3600.0) * 1.5
        elif direction == 'W':
            x = random.uniform(-0.1, -0.02)
            y = 0.52 if lane == 0 else 0.55
            vx = (base_speed / 3600.0) * 1.5
            vy = 0.0
        else:  # 'E'
            x = random.uniform(1.02, 1.1)
            y = 0.45 if lane == 0 else 0.48
            vx = -(base_speed / 3600.0) * 1.5
            vy = 0.0

        vehicle = Vehicle(
            id=f"{v_type.upper()}-{self.vehicle_seq}",
            type=v_type,
            x=round(x, 4),
            y=round(y, 4),
            vx=vx,
            vy=vy,
            speed_kmh=round(base_speed, 1),
            lane=lane,
            direction=direction,
            status='emergency' if v_type == 'ambulance' else 'normal',
            confidence=round(random.uniform(0.93, 0.99), 2),
            bbox=[round(x - 0.02, 3), round(y - 0.02, 3), 0.04, 0.04]
        )
        self.vehicles.append(vehicle)
        return vehicle

    def update_physics(self, dt: float, signal_state: SignalState):
        """
        Advances vehicle physics: handles stop lines, green wave preemption,
        car following deceleration, and removing vehicles that leave intersection view.
        """
        # Define stop line coordinates
        stop_line_n = 0.38  # N going South stops before y=0.38
        stop_line_s = 0.62  # S going North stops before y=0.62
        stop_line_w = 0.38  # W going East stops before x=0.38
        stop_line_e = 0.62  # E going West stops before x=0.62

        active_vehicles = []

        for v in self.vehicles:
            if v.status == 'collided':
                active_vehicles.append(v)
                continue

            # Determine whether vehicle faces a red light
            is_red = False
            phase = signal_state.current_phase

            if phase == 'EMERGENCY_CORRIDOR':
                # Only emergency direction and vehicles already past stop line proceed
                if v.direction != signal_state.emergency_direction and v.type != 'ambulance':
                    is_red = True
            elif 'NS' in phase:
                if 'EW' in v.direction or v.direction in ['E', 'W']:
                    is_red = True
                elif phase == 'NS_YELLOW':
                    # Yellow light caution
                    is_red = False
            elif 'EW' in phase:
                if 'NS' in v.direction or v.direction in ['N', 'S']:
                    is_red = True
                elif phase == 'EW_YELLOW':
                    is_red = False

            # Check if vehicle should stop at red signal
            should_stop_at_signal = False
            if is_red and v.type != 'ambulance':
                if v.direction == 'N' and 0.25 <= v.y <= stop_line_n:
                    should_stop_at_signal = True
                elif v.direction == 'S' and stop_line_s <= v.y <= 0.75:
                    should_stop_at_signal = True
                elif v.direction == 'W' and 0.25 <= v.x <= stop_line_w:
                    should_stop_at_signal = True
                elif v.direction == 'E' and stop_line_e <= v.x <= 0.75:
                    should_stop_at_signal = True

            # Car-following logic: check vehicle ahead in same lane & direction
            vehicle_ahead_dist = 999.0
            for other in self.vehicles:
                if other.id == v.id or other.direction != v.direction or other.lane != v.lane:
                    continue
                # Ahead in movement direction
                if v.direction == 'N' and other.y > v.y:
                    vehicle_ahead_dist = min(vehicle_ahead_dist, other.y - v.y)
                elif v.direction == 'S' and other.y < v.y:
                    vehicle_ahead_dist = min(vehicle_ahead_dist, v.y - other.y)
                elif v.direction == 'W' and other.x > v.x:
                    vehicle_ahead_dist = min(vehicle_ahead_dist, other.x - v.x)
                elif v.direction == 'E' and other.x < v.x:
                    vehicle_ahead_dist = min(vehicle_ahead_dist, v.x - other.x)

            # Apply deceleration if red light or obstacle/vehicle ahead
            min_gap = 0.075
            if should_stop_at_signal or vehicle_ahead_dist < min_gap:
                v.speed_kmh = max(0.0, v.speed_kmh - 80.0 * dt)
                v.status = 'stopped' if v.speed_kmh <= 1.0 else 'braking'
            else:
                target_speed = 75.0 if v.type == 'ambulance' else 52.0
                v.speed_kmh = min(target_speed, v.speed_kmh + 30.0 * dt)
                v.status = 'emergency' if v.type == 'ambulance' else 'normal'

            # Move vehicle
            displacement = (v.speed_kmh / 3600.0) * dt * 2.2
            if v.direction == 'N':
                v.y += displacement
            elif v.direction == 'S':
                v.y -= displacement
            elif v.direction == 'W':
                v.x += displacement
            elif v.direction == 'E':
                v.x -= displacement

            # Update bounding box coordinates for frontend visualization
            v.bbox = [round(v.x - 0.02, 3), round(v.y - 0.02, 3), 0.04, 0.04]

            # Keep vehicles that are within bounds
            if -0.2 <= v.x <= 1.2 and -0.2 <= v.y <= 1.2:
                active_vehicles.append(v)

        self.vehicles = active_vehicles

        # Replenish vehicles if below threshold
        if len(self.vehicles) < 10 and not self.accident_in_progress:
            self.spawn_vehicle()

    def trigger_collision(self) -> bool:
        """
        Forces an accident scenario by picking two crossing or adjacent vehicles
        and placing them on an unavoidable high-speed collision course at the center.
        """
        # Find or spawn two candidate vehicles
        candidates = [v for v in self.vehicles if v.status != 'collided']
        if len(candidates) < 2:
            self.spawn_vehicle(force_type='car', force_dir='N')
            self.spawn_vehicle(force_type='truck', force_dir='W')
            candidates = self.vehicles

        v1 = candidates[0]
        v2 = candidates[1]

        # Stage collision at intersection core
        v1.x = 0.48
        v1.y = 0.49
        v1.speed_kmh = 58.0
        v1.status = 'braking'

        v2.x = 0.51
        v2.y = 0.50
        v2.speed_kmh = 64.0
        v2.status = 'braking'

        self.accident_in_progress = True
        return True

    def trigger_ambulance(self) -> Vehicle:
        """Spawns an emergency ambulance to trigger Green Wave corridor."""
        ev = self.spawn_vehicle(force_type='ambulance', force_dir='S')
        if not ev:
            # Force spawn
            self.vehicle_seq += 1
            ev = Vehicle(
                id=f"AMBULANCE-{self.vehicle_seq}",
                type='ambulance',
                x=0.52,
                y=1.05,
                vx=0.0,
                vy=-0.03,
                speed_kmh=80.0,
                lane=0,
                direction='S',
                status='emergency',
                confidence=0.99,
                bbox=[0.50, 1.03, 0.04, 0.04]
            )
            self.vehicles.append(ev)
        return ev

    def clear_accidents(self):
        """Clears crashed vehicles and resets status."""
        self.vehicles = [v for v in self.vehicles if v.status != 'collided']
        self.accident_in_progress = False
