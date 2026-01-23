from dataclasses import dataclass, field
from typing import Callable

from human import Human

# =============================================================================
# BASELINE DECAY - Homeostasis
# =============================================================================

# Each parameter decays toward its baseline at a certain rate per hour
BASELINES = {
    'dopamine': 50.0,
    'oxytocin': 30.0,
    'endorphins': 20.0,
    'serotonin': 50.0,
    'arousal': 20.0,
    'prefrontal': 50.0,
    'sleepiness': 20.0,   # baseline alertness (low sleepiness)
    'hunger': 50.0,       # hunger increases over time (baseline is "somewhat hungry")
    'energy': 50.0,
}

# Decay rate: fraction of distance to baseline recovered per hour
DECAY_RATES = {
    'dopamine': 0.15,     # relatively fast
    'oxytocin': 0.10,     # medium
    'endorphins': 0.20,   # fast decay
    'serotonin': 0.05,    # slow, stable
    'arousal': 0.25,      # fast without stimulation
    'prefrontal': 0.10,   # medium
    'sleepiness': 0.15,   # alertness returns gradually
}


def apply_decay(human: Human, dt: float):
    """
    Apply homeostatic decay - values drift toward baseline.
    dt is time in hours.
    """
    for attr, baseline in BASELINES.items():
        if attr in DECAY_RATES:
            current = getattr(human, attr)
            rate = DECAY_RATES[attr]
            # Exponential decay toward baseline
            new_value = current + (baseline - current) * rate * dt
            setattr(human, attr, new_value)

    # Hunger increases over time (not decay, but drift)
    human.hunger += 3.0 * dt  # get hungrier by 3 points per hour

    # Energy decreases over time when awake
    human.energy -= 2.0 * dt  # lose 2 energy per hour when active

    # Digestion effects: while digesting, sleepiness increases and arousal is suppressed
    if human.digesting > 0:
        # Digesting causes drowsiness (parasympathetic activation)
        human.sleepiness += human.digesting * 0.3 * dt
        # Blood flow to gut reduces arousal capacity
        human.arousal -= human.digesting * 0.2 * dt
        # Digestion fades over time
        human.digesting *= (1 - 0.4 * dt)  # ~40% decay per hour
        if human.digesting < 1:
            human.digesting = 0

    # High sleepiness dampens arousal and prefrontal activity
    if human.sleepiness > 40:
        sleepy_factor = (human.sleepiness - 40) / 60  # 0 to 1
        human.arousal -= sleepy_factor * 5 * dt
        human.prefrontal -= sleepy_factor * 3 * dt

    # Track time since orgasm
    human.time_since_orgasm += dt

    # Edging buildup decays slowly
    human.edging_buildup *= (1 - 0.05 * dt)

    human.clamp_values()


# =============================================================================
# EVENTS
# =============================================================================

@dataclass
class Event:
    """
    An event/action that can be applied to a Human.
    """
    name: str
    duration: float  # hours
    apply: Callable[[Human], None]
    can_apply: Callable[[Human], bool] = field(default=lambda h: True)
    description: str = ""


def make_events() -> dict[str, Event]:
    """Create and return all available events."""

    events = {}

    # --- Basic needs ---

    def snack(h):
        """Light snack - minimal digestive load."""
        h.hunger -= 15
        h.dopamine += 5  # small food pleasure
        h.digesting += 10  # minimal digestion
        h.energy += 2

    events['snack'] = Event(
        name='snack',
        duration=0.1,
        apply=snack,
        can_apply=lambda h: h.hunger > 10,
        description="Have a light snack"
    )

    def eat(h):
        """Full meal - satisfying but causes post-meal drowsiness."""
        h.hunger -= 50
        h.dopamine += 10  # food pleasure
        h.serotonin += 8  # carbs boost serotonin
        # Parasympathetic activation from digestion
        h.digesting += 50  # triggers drowsiness over time
        h.sleepiness += 15  # immediate slight drowsiness
        h.arousal -= 10  # blood flow diverts to digestion
        h.prefrontal -= 5  # mental fog from food coma
        # Initial energy from food, but will crash
        h.energy += 5

    events['eat'] = Event(
        name='eat',
        duration=0.5,
        apply=eat,
        can_apply=lambda h: h.hunger > 25,
        description="Eat a full meal (causes drowsiness)"
    )

    def sleep(h):
        h.energy += 35
        h.hunger += 10  # wake up hungrier
        h.dopamine = BASELINES['dopamine']  # reset to baseline
        h.serotonin += 10
        h.psychological_health += 2
        h.arousal = 10
        h.edging_buildup = 0
        h.prefrontal = 60  # refreshed mind
        h.sleepiness = 10  # wake up alert
        h.digesting = 0  # digestion completes during sleep

    events['sleep'] = Event(
        name='sleep',
        duration=2.0,  # power nap
        apply=sleep,
        can_apply=lambda h: h.energy < 60 or h.sleepiness > 50,
        description="Take a restful nap"
    )

    # --- Sexual/arousal events ---

    def light_stimulation(h):
        h.arousal += 15
        h.dopamine += 10
        h.prefrontal -= 5
        h.edging_buildup += 10
        h.energy -= 3

    events['light_stimulation'] = Event(
        name='light_stimulation',
        duration=0.25,
        apply=light_stimulation,
        description="Light sexual stimulation, teasing"
    )

    def intense_stimulation(h):
        h.arousal += 30
        h.dopamine += 20
        h.endorphins += 10
        h.prefrontal -= 15
        h.edging_buildup += 25
        h.energy -= 8

    events['intense_stimulation'] = Event(
        name='intense_stimulation',
        duration=0.25,
        apply=intense_stimulation,
        can_apply=lambda h: h.arousal > 30,
        description="Intense sexual stimulation"
    )

    def edging(h):
        """Maintain high arousal without orgasm - builds up pleasure potential."""
        h.arousal = min(95, h.arousal + 10)
        h.dopamine += 15 + h.edging_buildup * 0.2  # more buildup = more reward
        h.endorphins += 5
        h.prefrontal -= 10
        h.edging_buildup += 15
        h.energy -= 5

    events['edging'] = Event(
        name='edging',
        duration=0.25,
        apply=edging,
        can_apply=lambda h: h.arousal > 50,
        description="Edge - maintain high arousal without release"
    )

    def orgasm(h):
        """
        Release - brief spike then CRASH.
        Models male ejaculation with prolactin-induced dopamine crash.
        """
        bonus = h.edging_buildup * 0.3  # edging pays off in endorphins/oxytocin

        # The spike (brief moment of orgasm) - mainly endorphins and oxytocin
        h.endorphins += 50 + bonus
        h.oxytocin += 40

        # THE CRASH - prolactin surge crashes dopamine significantly
        # Dopamine drops to well below baseline after ejaculation
        h.dopamine = max(20, h.dopamine * 0.3)  # crash to 30% of current, min 20

        # Post-orgasm state
        h.arousal = 5  # very low, refractory
        h.energy -= 20
        h.prefrontal = 25  # post-orgasm mental fog/bliss
        h.sleepiness += 15  # makes you sleepy
        h.serotonin += 10  # calm/satisfied feeling

        # Reset
        h.time_since_orgasm = 0
        h.edging_buildup = 0

    events['orgasm'] = Event(
        name='orgasm',
        duration=0.1,
        apply=orgasm,
        can_apply=lambda h: h.arousal > 70 and h.time_since_orgasm > 1.0,  # 1h refractory
        description="Orgasm with ejaculation - causes dopamine crash"
    )

    # --- Pain/adrenaline (small doses enhance pleasure) ---

    def light_pain(h):
        """Light pain (spanking, pinching) - releases endorphins."""
        h.endorphins += 20
        h.dopamine += 8
        h.arousal += 10
        h.prefrontal -= 5

    events['light_pain'] = Event(
        name='light_pain',
        duration=0.1,
        apply=light_pain,
        description="Light pain stimulus (spanking, pinching)"
    )

    def temperature_play(h):
        """Ice or heat - shock to system, endorphin release."""
        h.endorphins += 15
        h.arousal += 8
        h.dopamine += 5
        h.prefrontal -= 8

    events['temperature_play'] = Event(
        name='temperature_play',
        duration=0.1,
        apply=temperature_play,
        description="Temperature play (ice, heat)"
    )

    # --- Social/bonding ---

    def cuddling(h):
        h.oxytocin += 25
        h.serotonin += 10
        h.prefrontal -= 5
        h.psychological_health += 1
        h.arousal += 5

    events['cuddling'] = Event(
        name='cuddling',
        duration=0.5,
        apply=cuddling,
        description="Intimate cuddling and touch"
    )

    def massage(h):
        h.oxytocin += 15
        h.endorphins += 12
        h.serotonin += 8
        h.energy += 5
        h.physical_health += 1
        h.prefrontal -= 10

    events['massage'] = Event(
        name='massage',
        duration=0.5,
        apply=massage,
        description="Receive a relaxing massage"
    )

    # --- Breathwork/altered states ---

    def deep_breathing(h):
        """Calming breathwork - parasympathetic activation."""
        h.serotonin += 8
        h.prefrontal -= 10
        h.psychological_health += 1
        h.energy += 3

    events['deep_breathing'] = Event(
        name='deep_breathing',
        duration=0.25,
        apply=deep_breathing,
        description="Deep, slow breathing exercises"
    )

    def holotropic_breathing(h):
        """Intense breathwork - altered state, endorphin release."""
        h.endorphins += 25
        h.dopamine += 15
        h.prefrontal -= 25  # hypofrontality
        h.arousal += 15
        h.energy -= 10

    events['holotropic_breathing'] = Event(
        name='holotropic_breathing',
        duration=0.5,
        apply=holotropic_breathing,
        can_apply=lambda h: h.energy > 30,
        description="Intense holotropic breathwork"
    )

    # --- Rest/recovery ---

    def rest(h):
        """Just rest, do nothing - recovery."""
        h.energy += 5
        h.prefrontal += 5

    events['rest'] = Event(
        name='rest',
        duration=0.25,
        apply=rest,
        description="Rest quietly"
    )

    def wait(h):
        """Do nothing - just let time pass. Used for pacing."""
        h.energy += 2  # slight recovery from resting

    events['wait'] = Event(
        name='wait',
        duration=0.25,  # 15 minutes of waiting
        apply=wait,
        description="Wait, do nothing"
    )

    return events

