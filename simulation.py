"""
Hedonistic Tamagotchi - MVP Simulation
A physiological simulation to find optimal pleasure states.
"""

import copy
from typing import Optional

from events import make_events, apply_decay, apply_event
from human import Human


# =============================================================================
# EMOJI MAPPING
# =============================================================================

def physiology_to_emoji(human: Human) -> str:
    """
    Map the human's physiological state to an emoji representation.
    Returns an emoji that best represents the overall state.
    """
    pleasure = human.pleasure_score()

    # Check critical states first
    if not human.is_viable():
        return "💀"  # Dead/incapacitated

    if human.sleepiness > 80:
        return "😴"  # About to fall asleep

    if human.hunger > 80:
        return "🥺"  # Starving

    if human.energy < 20:
        return "😫"  # Exhausted

    # Check high anxiety
    if human.anxiety > 70:
        return "😰"  # Very anxious

    # Check high absorption (flow/trance states)
    if human.absorption > 80:
        return "🌀"  # Deep trance/flow

    # Check arousal states
    if human.arousal > 80:
        return "🥵"  # Very aroused

    if human.arousal > 50:
        return "😏"  # Aroused/excited

    # Check post-orgasm state (high prolactin, high endorphins/oxytocin)
    if human.prolactin > 40 and human.endorphins > 40:
        return "🤤"  # Post-orgasm bliss

    # Check high prolactin (refractory period)
    if human.prolactin > 50:
        return "😮‍💨"  # Refractory/recovering

    # Check digesting
    if human.digesting > 30:
        return "🫃"  # Food coma

    # General pleasure states
    if pleasure > 70:
        return "😍"  # Very happy/pleasured

    if pleasure > 55:
        return "😊"  # Happy

    if pleasure > 45:
        return "🙂"  # Content

    if pleasure > 35:
        return "😐"  # Neutral

    if pleasure > 25:
        return "😕"  # Slightly uncomfortable

    return "😢"  # Unhappy


def format_status(human: Human, action: str = None, time: float = 0.0) -> str:
    """
    Format a status string showing action, attributes summary, and emoji.
    """
    emoji = physiology_to_emoji(human)
    pleasure = human.pleasure_score()

    lines = []

    # Header with time and emoji
    if action:
        lines.append(f"\n{'='*50}")
        lines.append(f"  {emoji} Acción: {action}")
    lines.append(f"{'='*50}")
    lines.append(f"  Tiempo: {time:.1f}h | Placer: {pleasure:.1f} | {emoji}")
    lines.append(f"{'='*50}")

    # Neurotransmitters
    lines.append(f"  Neurotransmisores:")
    lines.append(f"    Dopamina:   {human.dopamine:5.1f} {'█' * int(human.dopamine/5)}")
    lines.append(f"    Endorfinas: {human.endorphins:5.1f} {'█' * int(human.endorphins/5)}")
    lines.append(f"    Oxitocina:  {human.oxytocin:5.1f} {'█' * int(human.oxytocin/5)}")
    lines.append(f"    Serotonina: {human.serotonin:5.1f} {'█' * int(human.serotonin/5)}")

    # Physiological state
    lines.append(f"  Estado fisiológico:")
    lines.append(f"    Excitación: {human.arousal:5.1f} {'█' * int(human.arousal/5)}")
    lines.append(f"    Somnolencia:{human.sleepiness:5.1f} {'█' * int(human.sleepiness/5)}")
    lines.append(f"    Prefrontal: {human.prefrontal:5.1f} {'█' * int(human.prefrontal/5)}")

    # Mental state
    lines.append(f"  Estado mental:")
    lines.append(f"    Ansiedad:   {human.anxiety:5.1f} {'█' * int(human.anxiety/5)}")
    lines.append(f"    Absorción:  {human.absorption:5.1f} {'█' * int(human.absorption/5)}")

    # Basic needs
    lines.append(f"  Necesidades:")
    lines.append(f"    Hambre:     {human.hunger:5.1f} {'█' * int(human.hunger/5)}")
    lines.append(f"    Energía:    {human.energy:5.1f} {'█' * int(human.energy/5)}")

    # Reserves
    lines.append(f"  Reservas de NT:")
    for nt, val in human.reserves.items():
        lines.append(f"    {nt:<12}: {val:5.1f} {'█' * int(val/5)}")

    # Tolerance (only show non-zero)
    active_tolerances = {k: v for k, v in human.tolerance.items() if v > 0.01}
    if active_tolerances:
        lines.append(f"  Tolerancia:")
        for cat, val in active_tolerances.items():
            pct = val * 100
            lines.append(f"    {cat:<12}: {pct:5.1f}% {'█' * int(pct/5)}")

    # Cue salience (only show non-zero)
    active_cues = {k: v for k, v in human.cue_salience.items() if v > 0.01}
    if active_cues:
        lines.append(f"  Saliencia de cues:")
        for cat, val in active_cues.items():
            pct = val * 100
            lines.append(f"    {cat:<12}: {pct:5.1f}% {'█' * int(pct/5)}")

    # Special states
    if human.edging_buildup > 5:
        lines.append(f"  Acumulación edging: {human.edging_buildup:.1f}")
    if human.digesting > 5:
        lines.append(f"  Digiriendo: {human.digesting:.1f}")
    if human.time_since_orgasm < 2:
        lines.append(f"  Tiempo desde orgasmo: {human.time_since_orgasm:.1f}h")

    # Active rebounds
    if human.rebound_queue:
        lines.append(f"  Rebounds activos: {len(human.rebound_queue)}")

    lines.append(f"{'='*50}\n")

    return '\n'.join(lines)

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
                        apply_event(human, event_name, event)
                        current_event = event_name
                        event_index += 1

                        # Sub-step through event duration
                        steps_for_event = max(1, int(event.duration / self.time_step))
                        for _ in range(steps_for_event):
                            apply_decay(human, self.time_step)
                            human.clamp_values()
                            if not human.is_viable():
                                viable = False
                                break
                            pleasure = human.pleasure_score()
                            total_pleasure += pleasure * self.time_step
                            current_time += self.time_step
                            time_steps += 1
                            timeline.append((current_time, pleasure, current_event))
                            if verbose:
                                print(f"t={current_time:.2f}h | {current_event or 'decay':<20} | "
                                      f"pleasure={pleasure:.1f} | {human}")
                            current_event = None  # only label first sub-step
                        continue
                    else:
                        # Can't apply this event, skip it
                        event_index += 1
                        continue
                else:
                    event_index += 1
                    continue

            # No event applied - decay step
            apply_decay(human, self.time_step)
            human.clamp_values()

            if not human.is_viable():
                viable = False
                break

            pleasure = human.pleasure_score()
            total_pleasure += pleasure * self.time_step
            time_steps += 1
            current_time += self.time_step

            if verbose:
                print(f"t={current_time:.2f}h | {'decay':<20} | "
                      f"pleasure={pleasure:.1f} | {human}")

            timeline.append((current_time, pleasure, None))

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

# =============================================================================
# INTERACTIVE MODE
# =============================================================================

def interactive_mode():
    """
    Run an interactive single-player mode where the user chooses actions.
    """
    sim = Simulation(time_step=0.1)
    human = Human()
    current_time = 0.0
    total_pleasure = 0.0

    print("\n" + "="*50)
    print("  🎮 TAMAGOTCHI HEDONISTA - Modo Interactivo")
    print("="*50)
    print("\nObjetivo: Maximizar el placer de tu personaje.")
    print("Elige acciones sabiamente para mantenerlo feliz y viable.\n")

    # Show initial state
    print(format_status(human, "Estado inicial", current_time))

    while human.is_viable():
        # Get available events
        events = sim.events
        available_events = []

        print("\n📋 Acciones disponibles:")
        print("-" * 40)

        for i, (name, event) in enumerate(events.items(), 1):
            can_do = event.can_apply(human)
            status = "✓" if can_do else "✗"
            available_events.append((name, event, can_do))
            duration_min = int(event.duration * 60)
            print(f"  {i:2d}. [{status}] {name:<22} ({duration_min:3d} min)")
            print(f"       {event.description}")

        print(f"\n   0. Salir del juego")
        print("-" * 40)
        print(f"  Tiempo actual: {current_time:.1f}h | Placer acumulado: {total_pleasure:.1f}")

        # Get user input
        try:
            choice = input("\n👉 Elige una acción (número): ").strip()
            if not choice:
                continue

            choice_num = int(choice)

            if choice_num == 0:
                print("\n👋 Gracias por jugar!")
                print(f"\n📊 Resumen final:")
                print(f"   Tiempo total: {current_time:.1f} horas")
                print(f"   Placer total acumulado: {total_pleasure:.1f}")
                print(f"   Placer promedio: {total_pleasure/max(current_time, 0.1):.1f}")
                break

            if choice_num < 1 or choice_num > len(available_events):
                print("❌ Opción inválida. Intenta de nuevo.")
                continue

            event_name, event, can_do = available_events[choice_num - 1]

            if not can_do:
                print(f"❌ No puedes hacer '{event_name}' ahora. Revisa los requisitos.")
                continue

            # Apply the event
            apply_event(human, event_name, event)

            # Sub-step through event duration
            steps_for_event = max(1, int(event.duration / sim.time_step))
            for _ in range(steps_for_event):
                apply_decay(human, sim.time_step)
                human.clamp_values()
                if not human.is_viable():
                    break
                pleasure = human.pleasure_score()
                total_pleasure += pleasure * sim.time_step
                current_time += sim.time_step

            # Show result
            print(format_status(human, event_name, current_time))

        except ValueError:
            print("❌ Por favor ingresa un número válido.")
            continue
        except KeyboardInterrupt:
            print("\n\n👋 Juego interrumpido.")
            break

    # Game over check
    if not human.is_viable():
        print("\n" + "="*50)
        print("  💀 GAME OVER - Tu personaje ya no es viable")
        print("="*50)

        if human.energy <= 5:
            print("  Causa: Agotamiento total")
        elif human.hunger >= 95:
            print("  Causa: Muriendo de hambre")
        elif human.sleepiness >= 95:
            print("  Causa: Se quedó dormido")
        elif human.physical_health <= 10:
            print("  Causa: Salud física crítica")
        elif human.psychological_health <= 10:
            print("  Causa: Salud mental crítica")

        print(f"\n📊 Resumen final:")
        print(f"   Tiempo sobrevivido: {current_time:.1f} horas")
        print(f"   Placer total acumulado: {total_pleasure:.1f}")
        print(f"   Placer promedio: {total_pleasure/max(current_time, 0.1):.1f}")


if __name__ == "__main__":
    interactive_mode()