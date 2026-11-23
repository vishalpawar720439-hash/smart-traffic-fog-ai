"""
Local Adaptive Traffic Signal Controller running on Fog Nodes.
Calculates dynamic green light durations based on real-time vehicle queue lengths
and executes instant Emergency Green Wave preemption upon AI detection of emergency vehicles.
"""
from typing import List, Optional
from .models import SignalState, Vehicle


class FogTrafficSignalController:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state = SignalState()
        self.yellow_duration = 4
        self.min_green = 12
        self.max_green = 45
        self.cycle_timer = float(self.state.time_remaining)
        self.last_update = 0.0

    def update(self, dt: float, vehicles: List[Vehicle]) -> SignalState:
        """
        Updates the signal cycle based on elapsed time dt and dynamic vehicle queues.
        """
        # Check for emergency vehicles approaching
        emergency_vehicles = [v for v in vehicles if v.type == 'ambulance' and v.status != 'collided']
        if emergency_vehicles:
            first_ev = emergency_vehicles[0]
            self.state.emergency_override = True
            self.state.current_phase = 'EMERGENCY_CORRIDOR'
            self.state.emergency_direction = first_ev.direction
            self.state.time_remaining = 30  # Hold corridor open
            return self.state

        # If emergency was cleared, resume adaptive operation
        if self.state.emergency_override and not emergency_vehicles:
            self.state.emergency_override = False
            self.state.current_phase = 'NS_YELLOW'
            self.cycle_timer = float(self.yellow_duration)
            self.state.emergency_direction = None

        # Decrement timer
        self.cycle_timer -= dt
        self.state.time_remaining = max(1, int(round(self.cycle_timer)))

        if self.cycle_timer <= 0:
            self._transition_phase(vehicles)

        return self.state

    def _calculate_optimal_green(self, direction_vehicles: int, opposing_vehicles: int) -> int:
        """
        Webster-inspired adaptive green time computation.
        Allocates proportional green time based on edge-detected queue volume.
        """
        total = direction_vehicles + opposing_vehicles
        if total == 0:
            return 20
        ratio = direction_vehicles / max(total, 1)
        target = int(self.min_green + ratio * (self.max_green - self.min_green))
        return max(self.min_green, min(self.max_green, target))

    def _transition_phase(self, vehicles: List[Vehicle]):
        """
        Switches phases between NS and EW with adaptive duration calculation.
        """
        ns_vehicles = sum(1 for v in vehicles if v.direction in ['N', 'S'])
        ew_vehicles = sum(1 for v in vehicles if v.direction in ['E', 'W'])

        if self.state.current_phase == 'NS_GREEN':
            self.state.current_phase = 'NS_YELLOW'
            self.cycle_timer = float(self.yellow_duration)
        elif self.state.current_phase == 'NS_YELLOW':
            self.state.current_phase = 'EW_GREEN'
            duration = self._calculate_optimal_green(ew_vehicles, ns_vehicles)
            self.state.ew_green_duration = duration
            self.cycle_timer = float(duration)
        elif self.state.current_phase == 'EW_GREEN':
            self.state.current_phase = 'EW_YELLOW'
            self.cycle_timer = float(self.yellow_duration)
        elif self.state.current_phase == 'EW_YELLOW':
            self.state.current_phase = 'NS_GREEN'
            duration = self._calculate_optimal_green(ns_vehicles, ew_vehicles)
            self.state.ns_green_duration = duration
            self.cycle_timer = float(duration)
        else:
            self.state.current_phase = 'NS_GREEN'
            self.cycle_timer = 20.0

    def manual_override(self, phase: str, duration: int = 30):
        """Allows manual signal lock from central traffic command."""
        self.state.is_adaptive = False
        self.state.current_phase = phase
        self.cycle_timer = float(duration)
        self.state.time_remaining = duration

    def set_adaptive(self, enabled: bool):
        self.state.is_adaptive = enabled
