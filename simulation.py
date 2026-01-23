"""
Hedonistic Tamagotchi - MVP Simulation
A physiological simulation to find optimal pleasure states.
"""

import copy
import multiprocessing as mp
from dataclasses import dataclass, field
from typing import Optional

from events import make_events, apply_decay
from human import Human

# =============================================================================
# SIMULATION
# =============================================================================

class Simulation:
    """
    Runs a sequence of events on a Human over time.
    """

    def __init__(self, time_step: float = 0.1):
        """
        time_step: simulation granularity in hours (0.1 = 6 minutes)
        """
        self.time_step = time_step
        self.events = make_events()

    def run(
        self,
        event_sequence: list[str],
        initial_state: Optional[Human] = None,
        max_hours: float = 10.0,
        verbose: bool = False
    ) -> dict:
        """
        Run a sequence of events and return results.

        Returns dict with:
            - total_pleasure: cumulative pleasure score
            - avg_pleasure: average pleasure per time step
            - final_state: Human state at end
            - timeline: list of (time, pleasure, event) tuples
            - viable: whether human remained viable throughout
        """
        human = copy.deepcopy(initial_state) if initial_state else Human()

        current_time = 0.0
        event_index = 0
        total_pleasure = 0.0
        time_steps = 0
        timeline = []
        viable = True

        while current_time < max_hours and viable:
            # Try to apply next event if available
            current_event = None
            if event_index < len(event_sequence):
                event_name = event_sequence[event_index]
                if event_name in self.events:
                    event = self.events[event_name]
                    if event.can_apply(human):
                        event.apply(human)
                        current_time += event.duration
                        current_event = event_name
                        event_index += 1
                    else:
                        # Can't apply this event, skip it
                        event_index += 1
                        continue
                else:
                    event_index += 1
                    continue

            # Apply decay for this time step
            apply_decay(human, self.time_step)
            human.clamp_values()

            # Check viability
            if not human.is_viable():
                viable = False
                break

            # Record pleasure
            pleasure = human.pleasure_score()
            total_pleasure += pleasure * self.time_step
            time_steps += 1

            if verbose:
                print(f"t={current_time:.2f}h | {current_event or 'decay':<20} | "
                      f"pleasure={pleasure:.1f} | {human}")

            timeline.append((current_time, pleasure, current_event))

            # Advance time if no event was applied
            if current_event is None:
                current_time += self.time_step

        avg_pleasure = total_pleasure / max(current_time, 0.01)

        return {
            'total_pleasure': total_pleasure,
            'avg_pleasure': avg_pleasure,
            'final_state': human,
            'timeline': timeline,
            'viable': viable,
            'hours_simulated': current_time
        }

    def get_event_names(self) -> list[str]:
        """Return list of all available event names."""
        return list(self.events.keys())

if __name__ == "__main__":
    # Example usage
    sim = Simulation(time_step=0.1)
    event_sequence = [
        'eat_meal',
        'take_nap'
    ]
    print(sim.run(event_sequence, verbose=True))