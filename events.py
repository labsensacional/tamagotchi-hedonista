import random
from dataclasses import dataclass, field
from typing import Callable

from human import Human

# Module-level flag for probabilistic outcomes (tests can toggle off)
ENABLE_PROBABILISTIC = True

# =============================================================================
# BASELINE DECAY - Homeostasis
# =============================================================================

# Each parameter decays toward its baseline at a certain rate per hour
BASELINES = {
    'dopamine': 50.0,
    'oxytocin': 30.0,       # passive bonding, relaxation, diffuse pleasure
    'endorphins': 20.0,
    'serotonin': 50.0,
    'prolactin': 10.0,      # low baseline, spikes after orgasm
    'vasopressin': 20.0,    # active arousal, focus, intensity, dominance
    'arousal': 20.0,
    'prefrontal': 50.0,
    'absorption': 30.0,     # baseline self-awareness (low absorption)
    'sleepiness': 20.0,     # baseline alertness (low sleepiness)
    'hunger': 50.0,         # hunger increases over time (baseline is "somewhat hungry")
    'energy': 50.0,
    'anxiety': 30.0,        # moderate baseline anxiety (correlates with cortisol)
}

# Decay rate: fraction of distance to baseline recovered per hour
DECAY_RATES = {
    'dopamine': 0.15,       # relatively fast
    'oxytocin': 0.10,       # medium
    'endorphins': 0.20,     # fast decay
    'serotonin': 0.05,      # slow, stable
    'prolactin': 0.08,      # slow decay - refractory period lasts a while
    'vasopressin': 0.15,    # moderate decay
    'arousal': 0.25,        # fast without stimulation
    'prefrontal': 0.10,     # medium
    'sleepiness': 0.15,     # alertness returns gradually
    'anxiety': 0.12,        # moderate decay toward baseline (cortisol half-life ~1h)
    'absorption': 0.20,     # decays relatively fast without stimulation
}

# =============================================================================
# TOLERANCE & RESERVES - Physiological Realism
# =============================================================================

# Maps each event to its tolerance category
EVENT_CATEGORIES = {
    'light_stimulation': 'sexual',
    'intense_stimulation': 'sexual',
    'edging': 'sexual',
    'orgasm': 'sexual',
    'light_pain': 'pain',
    'temperature_play': 'pain',
    'cuddling': 'social',
    'massage': 'social',
    'deep_breathing': 'breathwork',
    'holotropic_breathing': 'breathwork',
    'snack': 'food',
    'eat': 'food',
    'sleep': 'rest',
    'rest': 'rest',
    'wait': 'rest',
    'mdma': 'drugs',
    'weed': 'drugs',
    'mushrooms': 'drugs',
    'lsd': 'drugs',
    'poppers': 'drugs',
    'ketamine': 'drugs',
    'tobacco': 'drugs',
    'caffeine': 'drugs',
    'alcohol': 'drugs',
    'amphetamines': 'drugs',
    'cocaine': 'drugs',
    'nitrous': 'drugs',
}

# How much tolerance increases per use of each category
TOLERANCE_GAINS = {
    'sexual': 0.12,
    'pain': 0.10,
    'social': 0.06,
    'breathwork': 0.08,
    'food': 0.05,
    'rest': 0.0,
    'drugs': 0.15,
}

# How fast tolerance decays per hour (toward 0)
TOLERANCE_DECAY_RATES = {
    'sexual': 0.08,
    'pain': 0.10,
    'social': 0.12,
    'breathwork': 0.10,
    'food': 0.15,
    'rest': 0.0,
    'drugs': 0.04,
}

# Reserve constants
RESERVE_REPLENISH_RATE = 5.0    # per hour, for each NT
SLEEP_RESERVE_RESTORE = 40.0    # how much reserves restore on sleep
SLEEP_TOLERANCE_REDUCE = 0.15   # how much tolerance drops on sleep

# Sustained delivery constants
SUSTAINED_FRACTION = 0.4        # 40% of boost delivered over time
SUSTAINED_DURATION = 0.25       # hours
ORGASM_IMMEDIATE_FRACTION = 0.9 # orgasm is 90% immediate, 10% sustained


# =============================================================================
# HELPERS
# =============================================================================

def nt_boost(human: Human, attr: str, raw_amount: float, is_orgasm: bool = False):
    """
    Apply a neurotransmitter boost with reserve scaling and sustained delivery.

    - Scales by reserve level (min 15% at reserve=0, 100% at reserve=100)
    - Consumes reserves (0.5 reserve per point of boost)
    - Splits immediate/sustained (60/40 normally, 90/10 for orgasm)
    - Enqueues sustained portion in human.active_effects
    """
    if raw_amount <= 0:
        return

    # Map NT attr to reserve key
    reserve_key = attr  # dopamine, serotonin, endorphins, oxytocin
    if reserve_key not in human.reserves:
        # Not a tracked NT, apply directly
        setattr(human, attr, getattr(human, attr) + raw_amount)
        return

    # Scale by reserve level: 15% minimum at 0, 100% at 100
    reserve_level = human.reserves[reserve_key]
    scale_factor = 0.15 + 0.85 * (reserve_level / 100.0)
    scaled_amount = raw_amount * scale_factor

    # Consume reserves (0.5 per point of boost)
    human.reserves[reserve_key] -= raw_amount * 0.5

    # Split immediate vs sustained
    if is_orgasm:
        immediate_frac = ORGASM_IMMEDIATE_FRACTION
    else:
        immediate_frac = 1.0 - SUSTAINED_FRACTION

    immediate = scaled_amount * immediate_frac
    sustained = scaled_amount * (1.0 - immediate_frac)

    # Apply immediate portion
    setattr(human, attr, getattr(human, attr) + immediate)

    # Enqueue sustained portion
    if sustained > 0 and SUSTAINED_DURATION > 0:
        rate = sustained / SUSTAINED_DURATION
        human.active_effects.append({
            'attr': attr,
            'rate': rate,
            'remaining_hours': SUSTAINED_DURATION,
        })

    # Opponent-process rebound: large boosts schedule a delayed negative rebound
    if raw_amount > 10 and reserve_key in human.reserves:
        rebound_amount = scaled_amount * 0.3
        human.rebound_queue.append({
            'attr': attr,
            'amount': -rebound_amount,
            'delay_remaining': 0.5,
            'duration': 1.0,
        })


def compute_receptivity(human: Human, category: str) -> float:
    """
    How receptive the human is to this category of event based on current state.
    Returns -0.5 (backfire) to 1.0 (fully receptive).

    This is the "appraisal/gating" layer: determines whether an action lands well
    or backfires. Magnitude effects are lighter here since pleasure_score() already
    handles anxiety/absorption magnitude via Yerkes-Dodson and absorption factor.

    Positive range [0, 1]: gates how much of the event's benefits land.
    Negative range [-0.5, 0): event backfires — triggers explicit aversive consequences.
    """
    r = 1.0

    if category == 'sexual':
        # High anxiety gates out sexual receptivity
        if human.anxiety > 50:
            r -= (human.anxiety - 50) / 50 * 1.2
        # Overthinking (high prefrontal) reduces receptivity
        if human.prefrontal > 60:
            r -= (human.prefrontal - 60) / 40 * 0.3
        # Existing arousal improves receptivity
        if human.arousal > 20:
            r += (human.arousal - 20) / 80 * 0.3
        # Absorption helps (being in the moment)
        if human.absorption > 30:
            r += (human.absorption - 30) / 70 * 0.2

    elif category == 'social':
        # High anxiety makes socializing aversive
        if human.anxiety > 50:
            r -= (human.anxiety - 50) / 50 * 1.2
        # Low energy makes socializing draining
        if human.energy < 25:
            r -= (25 - human.energy) / 25 * 0.4
        # Existing oxytocin buffers anxiety penalty (feeling connected)
        if human.oxytocin > 35:
            r += (human.oxytocin - 35) / 65 * 0.4

    elif category == 'pain':
        # Pain without arousal context is just pain
        if human.arousal < 30:
            r -= (30 - human.arousal) / 30 * 1.8
        # Absorption helps convert pain to pleasure (play/safety proxy)
        if human.absorption > 40:
            r += (human.absorption - 40) / 60 * 0.3
        # High anxiety makes pain threatening rather than playful
        if human.anxiety > 55:
            r -= (human.anxiety - 55) / 45 * 0.5

    elif category == 'breathwork':
        # Very high anxiety can make breathwork counterproductive (panic)
        if human.anxiety > 70:
            r -= (human.anxiety - 70) / 30 * 0.5

    elif category == 'food':
        # High anxiety reduces food enjoyment
        if human.anxiety > 60:
            r -= (human.anxiety - 60) / 40 * 0.3

    elif category == 'drugs':
        # High anxiety + drugs can go wrong
        if human.anxiety > 55:
            r -= (human.anxiety - 55) / 45 * 0.5
        # Low psychological health makes drug experiences risky
        if human.psychological_health < 40:
            r -= (40 - human.psychological_health) / 40 * 0.4

    # 'rest' category: always receptive (r stays 1.0)

    return max(-0.5, min(1.0, r))


def apply_backfire(human: Human, category: str, severity: float):
    """
    Explicit aversive consequences when an action backfires (negative receptivity).
    severity is 0..0.5 (the absolute value of negative receptivity).

    Each category has specific backfire dynamics rather than generic sign-flipping.
    """
    if category == 'sexual':
        # Unwanted sexual stimulation during panic → more anxiety, self-consciousness
        human.anxiety += severity * 20
        human.absorption -= severity * 15
        human.prefrontal += severity * 10  # rumination, self-monitoring

    elif category == 'social':
        # Social interaction while panicking → social anxiety spiral
        human.anxiety += severity * 25
        human.absorption -= severity * 10
        human.prefrontal += severity * 15  # overthinking, rumination
        human.psychological_health -= severity * 2

    elif category == 'pain':
        # Pain without arousal/play context → just hurts
        human.anxiety += severity * 20
        human.physical_health -= severity * 3
        human.absorption -= severity * 10

    elif category == 'breathwork':
        # Breathwork during extreme anxiety → hyperventilation panic
        human.anxiety += severity * 15

    elif category == 'food':
        # Eating while very anxious → nausea, discomfort
        human.anxiety += severity * 10
        human.digesting += severity * 15

    elif category == 'drugs':
        # Bad trip / panic on drugs
        human.anxiety += severity * 30
        human.psychological_health -= severity * 4
        human.absorption -= severity * 15


def apply_event(human: Human, event_name: str, event: 'Event'):
    """
    Central wrapper that orchestrates tolerance, event application, and tolerance update.

    1. Calculate effectiveness from tolerance (max 60% reduction at tolerance=1.0)
    2. Call event.apply(human, effectiveness)
    3. Update tolerance for the event's category
    """
    category = EVENT_CATEGORIES.get(event_name, 'rest')
    tolerance = human.tolerance.get(category, 0.0)

    # Tolerance: 1.0 at tolerance=0, 0.4 at tolerance=1.0
    tolerance_factor = 1.0 - tolerance * 0.6

    # Context receptivity: -0.5 to 1.0
    receptivity = compute_receptivity(human, category)

    if receptivity >= 0:
        # Normal mode: gate benefits by receptivity and tolerance
        effectiveness = tolerance_factor * receptivity
        event.apply(human, effectiveness)
    else:
        # Backfire mode: benefits don't land (eff=0), unscaled costs still apply,
        # plus explicit aversive consequences
        event.apply(human, 0)
        apply_backfire(human, category, severity=abs(receptivity))

    # Update tolerance (builds regardless of whether experience was good or bad)
    gain = TOLERANCE_GAINS.get(category, 0.0)
    if gain > 0:
        human.tolerance[category] = min(1.0, human.tolerance.get(category, 0.0) + gain)

    # Cue learning: good experiences increase wanting, bad ones decrease it
    if receptivity >= 0:
        salience_gain = gain * 0.5
        human.cue_salience[category] = min(1.0, human.cue_salience.get(category, 0.0) + salience_gain)
    else:
        salience_loss = abs(receptivity) * 0.1
        human.cue_salience[category] = max(0.0, human.cue_salience.get(category, 0.0) - salience_loss)

    # Apply cue-driven dopamine boost (wanting increases even as liking decreases)
    cue_dopamine = human.cue_salience.get(category, 0.0) * 2
    if cue_dopamine > 0:
        human.dopamine += cue_dopamine


# =============================================================================
# DECAY
# =============================================================================

def apply_decay(human: Human, dt: float):
    """
    Apply homeostatic decay - values drift toward baseline.
    dt is time in hours.
    """
    # === HOMEOSTATIC DECAY with reserve-depressed baselines ===
    for attr, baseline in BASELINES.items():
        if attr in DECAY_RATES:
            current = getattr(human, attr)
            rate = DECAY_RATES[attr]

            # If this is a tracked NT reserve, depress baseline when reserves are low
            effective_baseline = baseline
            if attr in human.reserves:
                reserve = human.reserves[attr]
                if reserve < 100:
                    # At reserve=0, baseline drops to 60% of normal
                    effective_baseline = baseline * (1.0 - (1.0 - reserve / 100.0) * 0.4)

            # Exponential decay toward (possibly depressed) baseline
            new_value = current + (effective_baseline - current) * rate * dt
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

    # Drowsiness disrupts sustained attention needed for absorption/flow
    if human.sleepiness > 60:
        sleepy_absorb = (human.sleepiness - 60) / 40  # 0 to 1
        human.absorption -= sleepy_absorb * 4 * dt

    # Track time since orgasm
    human.time_since_orgasm += dt

    # Edging buildup decays slowly
    human.edging_buildup *= (1 - 0.05 * dt)

    # === A. Process active_effects (sustained delivery) ===
    remaining_effects = []
    for effect in human.active_effects:
        delivery = effect['rate'] * dt
        current = getattr(human, effect['attr'])
        setattr(human, effect['attr'], current + delivery)
        effect['remaining_hours'] -= dt
        if effect['remaining_hours'] > 0:
            remaining_effects.append(effect)
    human.active_effects = remaining_effects

    # === A2. Process rebound queue (opponent-process) ===
    remaining_rebounds = []
    for rebound in human.rebound_queue:
        if rebound['delay_remaining'] > 0:
            rebound['delay_remaining'] -= dt
            remaining_rebounds.append(rebound)
        else:
            rate = rebound['amount'] / rebound['duration']
            delivery = rate * dt
            current = getattr(human, rebound['attr'])
            setattr(human, rebound['attr'], current + delivery)
            rebound['duration'] -= dt
            if rebound['duration'] > 0:
                remaining_rebounds.append(rebound)
    human.rebound_queue = remaining_rebounds

    # === B. Tolerance decay ===
    for category, decay_rate in TOLERANCE_DECAY_RATES.items():
        if decay_rate > 0 and category in human.tolerance:
            human.tolerance[category] = max(
                0.0,
                human.tolerance[category] - decay_rate * dt
            )

    # === B2. Cue salience decay (very slow - sensitization persists) ===
    for category in human.cue_salience:
        human.cue_salience[category] = max(0.0, human.cue_salience[category] - 0.02 * dt)

    # === C. Reserve replenishment ===
    for nt in human.reserves:
        human.reserves[nt] += RESERVE_REPLENISH_RATE * dt

    # Anxiety increases with unmet needs
    if human.hunger > 50:
        human.anxiety += (human.hunger - 50) * 0.05 * dt
    if human.energy < 30:
        human.anxiety += (30 - human.energy) * 0.05 * dt

    # High anxiety suppresses absorption (can't get into flow when anxious)
    if human.anxiety > 50:
        anxiety_suppression = (human.anxiety - 50) / 50  # 0 to 1
        human.absorption -= anxiety_suppression * 5 * dt

    # Low prefrontal facilitates absorption (hypofrontality = flow states)
    if human.prefrontal < 40:
        human.absorption += (40 - human.prefrontal) * 0.1 * dt

    # High arousal can increase absorption (getting lost in sensation)
    if human.arousal > 60:
        human.absorption += (human.arousal - 60) * 0.08 * dt

    # === PROLACTIN EFFECTS ===
    # High prolactin suppresses dopamine (post-orgasm refractory)
    if human.prolactin > 20:
        prolactin_factor = (human.prolactin - 20) / 80  # 0 to 1
        human.dopamine -= prolactin_factor * 8 * dt  # suppresses dopamine
        human.arousal -= prolactin_factor * 10 * dt  # suppresses arousal (refractory)
        human.sleepiness += prolactin_factor * 5 * dt  # causes sleepiness

    # === VASOPRESSIN EFFECTS ===
    # High vasopressin increases focus and intensity but adds vigilance/tension
    if human.vasopressin > 40:
        vaso_factor = (human.vasopressin - 40) / 60  # 0 to 1
        human.prefrontal -= vaso_factor * 3 * dt  # reduces analytical thinking (more primal)
        human.absorption += vaso_factor * 3 * dt  # increases focus/intensity

    # High vasopressin adds slight anxiety (vigilance, tension)
    if human.vasopressin > 50:
        vaso_tension = (human.vasopressin - 50) / 50  # 0 to 1
        human.anxiety += vaso_tension * 2 * dt

    # === OXYTOCIN EFFECTS ===
    # High oxytocin promotes diffuse absorption (body immersion, safety)
    if human.oxytocin > 40:
        oxy_factor = (human.oxytocin - 40) / 60  # 0 to 1
        human.absorption += oxy_factor * 2 * dt

    # Vasopressin and oxytocin have opposing tendencies
    # High oxytocin tends to reduce vasopressin and vice versa (soft antagonism)
    if human.oxytocin > 50 and human.vasopressin > 30:
        human.vasopressin -= (human.oxytocin - 50) * 0.02 * dt
    if human.vasopressin > 50 and human.oxytocin > 30:
        human.oxytocin -= (human.vasopressin - 50) * 0.02 * dt

    # === D. Consequences of extreme states ===
    if human.dopamine > 85:
        human.psychological_health -= (human.dopamine - 85) * 0.1 * dt
    if human.anxiety > 70:
        human.psychological_health -= (human.anxiety - 70) * 0.1 * dt
    if human.arousal > 90:
        human.physical_health -= (human.arousal - 90) * 0.15 * dt
    if human.absorption > 90:
        human.psychological_health -= (human.absorption - 90) * 0.1 * dt
    if human.energy < 15:
        human.physical_health -= (15 - human.energy) * 0.1 * dt
    if human.endorphins > 80:
        human.physical_health -= (human.endorphins - 80) * 0.08 * dt

    human.clamp_values()


# =============================================================================
# EVENTS
# =============================================================================

@dataclass
class Event:
    """
    An event/action that can be applied to a Human.
    apply now takes (Human, effectiveness) where effectiveness is 0.4-1.0.
    """
    name: str
    duration: float  # hours
    apply: Callable[[Human, float], None]
    category: str = 'rest'
    can_apply: Callable[[Human], bool] = field(default=lambda h: True)
    description: str = ""


def make_events() -> dict[str, Event]:
    """Create and return all available events."""

    events = {}

    # --- Basic needs ---

    def snack(h, eff=1.0):
        """Light snack - minimal digestive load."""
        h.hunger -= 15              # cost: not scaled
        h.digesting += 10           # cost: not scaled
        h.energy += 2               # cost: not scaled
        nt_boost(h, 'dopamine', 5 * eff)
        h.anxiety -= 3 * eff

    events['snack'] = Event(
        name='snack',
        duration=0.1,
        apply=snack,
        category='food',
        can_apply=lambda h: h.hunger > 10,
        description="Have a light snack"
    )

    def eat(h, eff=1.0):
        """Full meal - satisfying but causes post-meal drowsiness."""
        h.hunger -= 50              # cost: not scaled
        h.digesting += 50           # cost: not scaled
        h.sleepiness += 15          # cost: not scaled
        h.arousal -= 10             # cost: not scaled
        h.prefrontal -= 5           # cost: not scaled
        h.energy += 5               # cost: not scaled
        nt_boost(h, 'dopamine', 10 * eff)
        nt_boost(h, 'serotonin', 8 * eff)
        h.anxiety -= 10 * eff
        h.absorption += 5 * eff

    events['eat'] = Event(
        name='eat',
        duration=0.5,
        apply=eat,
        category='food',
        can_apply=lambda h: h.hunger > 25,
        description="Eat a full meal (causes drowsiness)"
    )

    def sleep(h, eff=1.0):
        h.energy += 35
        h.hunger += 10
        h.dopamine = BASELINES['dopamine']
        h.serotonin += 10
        h.psychological_health += 2
        h.arousal = 10
        h.edging_buildup = 0
        h.prefrontal = 60
        h.sleepiness = 10
        h.digesting = 0
        h.anxiety = BASELINES['anxiety']
        h.absorption = BASELINES['absorption']
        h.prolactin = BASELINES['prolactin']
        h.vasopressin = BASELINES['vasopressin']
        # Sleep special: restore reserves and reduce tolerance
        for nt in h.reserves:
            h.reserves[nt] += SLEEP_RESERVE_RESTORE
        for cat in h.tolerance:
            h.tolerance[cat] = max(0.0, h.tolerance[cat] - SLEEP_TOLERANCE_REDUCE)
        # Clear active effects and rebounds
        h.active_effects.clear()
        h.rebound_queue.clear()
        # Sleep reduces cue salience slightly
        for cat in h.cue_salience:
            h.cue_salience[cat] = max(0.0, h.cue_salience[cat] - 0.05)

    events['sleep'] = Event(
        name='sleep',
        duration=2.0,
        apply=sleep,
        category='rest',
        can_apply=lambda h: h.energy < 60 or h.sleepiness > 50,
        description="Take a restful nap"
    )

    # --- Sexual/arousal events ---

    def light_stimulation(h, eff=1.0):
        h.edging_buildup += 10       # cost: not scaled
        h.energy -= 3                # cost: not scaled
        h.prefrontal -= 5            # cost: not scaled
        h.arousal += 15 * eff
        nt_boost(h, 'dopamine', 10 * eff)
        h.anxiety -= 5 * eff
        h.absorption += 10 * eff
        h.vasopressin += 8 * eff

    events['light_stimulation'] = Event(
        name='light_stimulation',
        duration=0.25,
        apply=light_stimulation,
        category='sexual',
        description="Light sexual stimulation, teasing"
    )

    def intense_stimulation(h, eff=1.0):
        h.edging_buildup += 25       # cost: not scaled
        h.energy -= 8                # cost: not scaled
        h.prefrontal -= 15           # cost: not scaled
        h.arousal += 30 * eff
        nt_boost(h, 'dopamine', 20 * eff)
        nt_boost(h, 'endorphins', 10 * eff)
        h.anxiety -= 10 * eff
        h.absorption += 20 * eff
        h.vasopressin += 15 * eff
        # Probabilistic: premature orgasm at high arousal
        if ENABLE_PROBABILISTIC and h.arousal > 70 and random.random() < 0.08:
            orgasm(h, eff)

    events['intense_stimulation'] = Event(
        name='intense_stimulation',
        duration=0.25,
        apply=intense_stimulation,
        category='sexual',
        can_apply=lambda h: h.arousal > 30,
        description="Intense sexual stimulation"
    )

    def edging(h, eff=1.0):
        """Maintain high arousal without orgasm - builds up pleasure potential."""
        h.edging_buildup += 15       # cost: not scaled
        h.energy -= 5                # cost: not scaled
        h.prefrontal -= 10           # cost: not scaled
        h.anxiety += 5               # cost: tension from holding back
        h.arousal = min(95, h.arousal + 10 * eff)
        nt_boost(h, 'dopamine', (15 + h.edging_buildup * 0.2) * eff)
        nt_boost(h, 'endorphins', 5 * eff)
        h.absorption += 15 * eff
        h.vasopressin += 12 * eff
        # Probabilistic: lose control at very high arousal
        if ENABLE_PROBABILISTIC and h.arousal > 80 and random.random() < 0.12:
            orgasm(h, eff)

    events['edging'] = Event(
        name='edging',
        duration=0.25,
        apply=edging,
        category='sexual',
        can_apply=lambda h: h.arousal > 50,
        description="Edge - maintain high arousal without release"
    )

    def orgasm(h, eff=1.0):
        """
        Release - brief spike then CRASH.
        Orgasm character depends on vasopressin vs oxytocin balance.
        Prolactin surge and dopamine crash are NOT scaled (they are costs).
        """
        bonus = h.edging_buildup * 0.3

        vaso_oxy_ratio = h.vasopressin / max(h.oxytocin, 10)

        # The spike - NT boosts use is_orgasm=True for 90% immediate
        nt_boost(h, 'endorphins', (50 + bonus) * eff, is_orgasm=True)

        if vaso_oxy_ratio > 1:
            h.vasopressin += 20 * eff
            nt_boost(h, 'oxytocin', 25 * eff, is_orgasm=True)
            nt_boost(h, 'dopamine', 10 * eff, is_orgasm=True)
        else:
            nt_boost(h, 'oxytocin', 45 * eff, is_orgasm=True)
            h.vasopressin += 5 * eff
            nt_boost(h, 'serotonin', 5 * eff, is_orgasm=True)

        # COSTS - NOT scaled by effectiveness
        prolactin_surge = 50 + h.edging_buildup * 0.3
        h.prolactin += prolactin_surge
        h.dopamine = max(25, h.dopamine * 0.5)

        # Post-orgasm state (costs)
        h.arousal = 5
        h.energy -= 20
        h.prefrontal = 25
        h.sleepiness += 15 + prolactin_surge * 0.1
        nt_boost(h, 'serotonin', 10 * eff, is_orgasm=True)

        h.anxiety = max(5, h.anxiety - 30 * eff)
        h.absorption = min(100, h.absorption + 25 * eff)

        h.time_since_orgasm = 0
        h.edging_buildup = 0

    def can_orgasm(h):
        return h.arousal > 70 and h.prolactin < 30

    events['orgasm'] = Event(
        name='orgasm',
        duration=0.1,
        apply=orgasm,
        category='sexual',
        can_apply=can_orgasm,
        description="Orgasm - character depends on vasopressin/oxytocin balance"
    )

    # --- Pain/adrenaline (small doses enhance pleasure) ---

    def light_pain(h, eff=1.0):
        """Light pain (spanking, pinching) - releases endorphins."""
        h.prefrontal -= 5            # cost: not scaled
        h.anxiety += 3               # cost: brief startle
        nt_boost(h, 'endorphins', 20 * eff)
        nt_boost(h, 'dopamine', 8 * eff)
        h.arousal += 10 * eff
        h.absorption += 15 * eff
        h.vasopressin += 12 * eff

    events['light_pain'] = Event(
        name='light_pain',
        duration=0.1,
        apply=light_pain,
        category='pain',
        description="Light pain stimulus (spanking, pinching)"
    )

    def temperature_play(h, eff=1.0):
        """Ice or heat - shock to system, endorphin release."""
        h.prefrontal -= 8            # cost: not scaled
        h.anxiety += 3               # cost: brief startle
        nt_boost(h, 'endorphins', 15 * eff)
        nt_boost(h, 'dopamine', 5 * eff)
        h.arousal += 8 * eff
        h.absorption += 12 * eff
        h.vasopressin += 10 * eff

    events['temperature_play'] = Event(
        name='temperature_play',
        duration=0.1,
        apply=temperature_play,
        category='pain',
        description="Temperature play (ice, heat)"
    )

    # --- Social/bonding ---

    def cuddling(h, eff=1.0):
        h.prefrontal -= 5            # cost: not scaled
        nt_boost(h, 'oxytocin', 25 * eff)
        nt_boost(h, 'serotonin', 10 * eff)
        h.psychological_health += 1 * eff
        h.arousal += 5 * eff
        h.anxiety -= 15 * eff
        h.absorption += 10 * eff
        h.vasopressin -= 8 * eff

    events['cuddling'] = Event(
        name='cuddling',
        duration=0.5,
        apply=cuddling,
        category='social',
        description="Intimate cuddling and touch"
    )

    def massage(h, eff=1.0):
        h.prefrontal -= 10           # cost: not scaled
        nt_boost(h, 'oxytocin', 15 * eff)
        nt_boost(h, 'endorphins', 12 * eff)
        nt_boost(h, 'serotonin', 8 * eff)
        h.energy += 5
        h.physical_health += 1 * eff
        h.anxiety -= 20 * eff
        h.absorption += 15 * eff
        h.vasopressin -= 10 * eff

    events['massage'] = Event(
        name='massage',
        duration=0.5,
        apply=massage,
        category='social',
        description="Receive a relaxing massage"
    )

    # --- Breathwork/altered states ---

    def deep_breathing(h, eff=1.0):
        """Calming breathwork - parasympathetic activation + dive reflex."""
        h.prefrontal -= 10           # cost: not scaled
        h.arousal -= 5               # dive reflex: parasympathetic suppresses arousal
        nt_boost(h, 'serotonin', 8 * eff)
        h.psychological_health += 1 * eff
        h.energy += 3
        h.anxiety -= 15 * eff
        h.absorption += 8 * eff

    events['deep_breathing'] = Event(
        name='deep_breathing',
        duration=0.25,
        apply=deep_breathing,
        category='breathwork',
        description="Deep, slow breathing exercises"
    )

    def holotropic_breathing(h, eff=1.0):
        """Intense breathwork - altered state, endorphin release."""
        h.energy -= 10               # cost: not scaled
        h.prefrontal -= 25           # cost: not scaled
        nt_boost(h, 'endorphins', 25 * eff)
        nt_boost(h, 'dopamine', 15 * eff)
        h.arousal += 15 * eff
        h.anxiety -= 10 * eff
        h.absorption += 30 * eff
        h.vasopressin += 10 * eff
        nt_boost(h, 'oxytocin', 10 * eff)

    events['holotropic_breathing'] = Event(
        name='holotropic_breathing',
        duration=0.5,
        apply=holotropic_breathing,
        category='breathwork',
        can_apply=lambda h: h.energy > 30,
        description="Intense holotropic breathwork"
    )

    # --- Rest/recovery ---

    def rest(h, eff=1.0):
        """Just rest, do nothing - recovery."""
        h.energy += 5
        h.prefrontal += 5
        h.anxiety -= 5
        h.absorption -= 5

    events['rest'] = Event(
        name='rest',
        duration=0.25,
        apply=rest,
        category='rest',
        description="Rest quietly"
    )

    def wait(h, eff=1.0):
        """Do nothing - just let time pass. Used for pacing."""
        h.energy += 2
        h.anxiety += 3
        h.absorption -= 3

    events['wait'] = Event(
        name='wait',
        duration=0.25,
        apply=wait,
        category='rest',
        description="Wait, do nothing"
    )

    # --- Recreational drugs ---

    def mdma(h, eff=1.0):
        """MDMA - massive serotonin/oxytocin release, empathogenic."""
        h.energy -= 25               # cost: not scaled
        h.prefrontal -= 30           # cost: not scaled
        nt_boost(h, 'serotonin', 40 * eff)
        nt_boost(h, 'oxytocin', 35 * eff)
        nt_boost(h, 'dopamine', 25 * eff)
        nt_boost(h, 'endorphins', 20 * eff)
        h.anxiety -= 30 * eff
        # Probabilistic: overwhelming experience
        if ENABLE_PROBABILISTIC and random.random() < 0.05:
            h.anxiety += 30
            h.physical_health -= 5

    events['mdma'] = Event(
        name='mdma',
        duration=3.0,
        apply=mdma,
        category='drugs',
        can_apply=lambda h: h.energy > 30,
        description="MDMA - empathogenic serotonin/oxytocin release"
    )

    def weed(h, eff=1.0):
        """Cannabis - mild dopamine, absorption boost, anxiolytic."""
        h.energy -= 5                # cost: not scaled
        h.prefrontal -= 20           # cost: not scaled
        h.hunger += 25               # cost: munchies
        h.sleepiness += 15           # cost: sedation
        nt_boost(h, 'dopamine', 15 * eff)
        h.absorption += 25 * eff
        h.anxiety -= 20 * eff

    events['weed'] = Event(
        name='weed',
        duration=2.0,
        apply=weed,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Cannabis - relaxation, absorption, munchies"
    )

    def mushrooms(h, eff=1.0):
        """Psilocybin mushrooms - deep absorption, ego dissolution."""
        h.energy -= 10               # cost: not scaled
        h.prefrontal -= 35           # cost: not scaled
        h.anxiety += 15              # cost: come-up anxiety
        h.absorption += 40 * eff
        nt_boost(h, 'endorphins', 20 * eff)
        nt_boost(h, 'serotonin', 15 * eff)
        nt_boost(h, 'dopamine', 10 * eff)
        # Probabilistic: bad trip
        if ENABLE_PROBABILISTIC and random.random() < 0.15:
            h.anxiety += 40
            h.absorption = 10
            h.prefrontal += 20

    events['mushrooms'] = Event(
        name='mushrooms',
        duration=4.0,
        apply=mushrooms,
        category='drugs',
        can_apply=lambda h: h.energy > 30,
        description="Psilocybin - deep absorption, risk of bad trip"
    )

    def lsd(h, eff=1.0):
        """LSD - long-lasting absorption, sensory enhancement."""
        h.energy -= 15               # cost: not scaled
        h.prefrontal -= 40           # cost: not scaled
        h.anxiety += 20              # cost: come-up anxiety
        h.sleepiness -= 20           # can't sleep on acid
        h.absorption += 45 * eff
        nt_boost(h, 'dopamine', 15 * eff)
        nt_boost(h, 'serotonin', 10 * eff)
        nt_boost(h, 'endorphins', 15 * eff)
        # Probabilistic: bad trip
        if ENABLE_PROBABILISTIC and random.random() < 0.10:
            h.anxiety += 40
            h.absorption = 10
            h.prefrontal += 20

    events['lsd'] = Event(
        name='lsd',
        duration=6.0,
        apply=lsd,
        category='drugs',
        can_apply=lambda h: h.energy > 30,
        description="LSD - long absorption boost, risk of bad trip"
    )

    def poppers(h, eff=1.0):
        """Poppers - brief vasodilation, arousal boost."""
        h.prefrontal -= 25           # cost: not scaled
        h.energy -= 3                # cost: not scaled
        h.physical_health -= 2       # cost: not scaled
        h.arousal += 25 * eff
        h.absorption += 20 * eff
        h.vasopressin += 15 * eff

    events['poppers'] = Event(
        name='poppers',
        duration=0.05,
        apply=poppers,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Poppers - brief vasodilation, arousal spike"
    )

    def ketamine(h, eff=1.0):
        """Ketamine - dissociative, deep absorption, pain relief."""
        h.prefrontal -= 40           # cost: not scaled
        h.energy -= 10               # cost: not scaled
        h.sleepiness += 15           # cost: sedation
        h.arousal -= 15              # cost: dissociation suppresses arousal
        h.absorption += 35 * eff
        nt_boost(h, 'endorphins', 25 * eff)
        nt_boost(h, 'dopamine', 10 * eff)
        h.anxiety -= 20 * eff

    events['ketamine'] = Event(
        name='ketamine',
        duration=1.0,
        apply=ketamine,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Ketamine - dissociative, absorption, pain relief"
    )

    def tobacco(h, eff=1.0):
        """Tobacco - mild dopamine, brief anxiolytic."""
        h.physical_health -= 1       # cost: not scaled
        nt_boost(h, 'dopamine', 8 * eff)
        h.arousal += 5 * eff
        h.anxiety -= 8 * eff
        h.energy += 3

    events['tobacco'] = Event(
        name='tobacco',
        duration=0.1,
        apply=tobacco,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Tobacco - mild stimulant, brief anxiety relief"
    )

    def caffeine(h, eff=1.0):
        """Caffeine - alertness, mild dopamine, increases anxiety."""
        h.anxiety += 10              # cost: jitteriness
        nt_boost(h, 'dopamine', 8 * eff)
        h.arousal += 10 * eff
        h.sleepiness -= 25 * eff
        h.energy += 10
        h.prefrontal += 10 * eff

    events['caffeine'] = Event(
        name='caffeine',
        duration=2.0,
        apply=caffeine,
        category='drugs',
        can_apply=lambda h: True,
        description="Caffeine - alertness, wakefulness"
    )

    def alcohol(h, eff=1.0):
        """Alcohol - anxiolytic, disinhibition, sedating."""
        h.prefrontal -= 25           # cost: not scaled
        h.energy -= 10               # cost: not scaled
        h.sleepiness += 15           # cost: sedation
        h.physical_health -= 2       # cost: not scaled
        nt_boost(h, 'dopamine', 15 * eff)
        h.anxiety -= 25 * eff
        h.absorption += 10 * eff
        h.arousal += 10 * eff
        # Probabilistic: vomiting at high arousal
        if ENABLE_PROBABILISTIC and h.arousal > 60 and random.random() < 0.10:
            h.hunger += 20
            h.energy -= 10
            h.digesting = 0

    events['alcohol'] = Event(
        name='alcohol',
        duration=1.5,
        apply=alcohol,
        category='drugs',
        can_apply=lambda h: h.energy > 15,
        description="Alcohol - anxiolytic, disinhibition"
    )

    def amphetamines(h, eff=1.0):
        """Amphetamines - strong dopamine, energy, focus."""
        h.anxiety += 20              # cost: not scaled
        h.physical_health -= 3       # cost: not scaled
        h.hunger -= 20               # appetite suppression
        h.sleepiness -= 30           # can't sleep
        nt_boost(h, 'dopamine', 35 * eff)
        h.arousal += 25 * eff
        h.energy += 20
        h.prefrontal += 10 * eff

    events['amphetamines'] = Event(
        name='amphetamines',
        duration=4.0,
        apply=amphetamines,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Amphetamines - strong stimulant, dopamine surge"
    )

    def cocaine(h, eff=1.0):
        """Cocaine - intense short dopamine spike, big crash."""
        h.anxiety += 15              # cost: not scaled
        h.prefrontal -= 10           # cost: not scaled
        h.physical_health -= 3       # cost: not scaled
        nt_boost(h, 'dopamine', 45 * eff)
        h.arousal += 20 * eff
        h.energy += 15
        # Probabilistic: anxiety spike
        if ENABLE_PROBABILISTIC and random.random() < 0.08:
            h.anxiety += 35

    events['cocaine'] = Event(
        name='cocaine',
        duration=0.5,
        apply=cocaine,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Cocaine - intense short dopamine spike, harsh crash"
    )

    def nitrous(h, eff=1.0):
        """Nitrous oxide - brief euphoria, dissociation."""
        h.prefrontal -= 20           # cost: not scaled
        h.energy -= 2                # cost: not scaled
        h.physical_health -= 2       # cost: oxygen deprivation
        nt_boost(h, 'endorphins', 20 * eff)
        h.absorption += 25 * eff

    events['nitrous'] = Event(
        name='nitrous',
        duration=0.05,
        apply=nitrous,
        category='drugs',
        can_apply=lambda h: h.energy > 20,
        description="Nitrous oxide - brief euphoria, dissociation"
    )

    return events
