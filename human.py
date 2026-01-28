from dataclasses import dataclass, field


def create_human(testosterone: float = 50.0) -> 'Human':
    """
    Factory function to create a Human with testosterone-adjusted initial values.
    Testosterone (0-100) affects:
    - Baseline arousal: higher T = higher baseline arousal
    - Energy: higher T = slightly more energy
    - Anxiety: higher T = slightly lower baseline anxiety
    - Vasopressin baseline: higher T = higher vasopressin tendency
    """
    t_factor = testosterone / 50.0  # 1.0 at T=50, 0.0 at T=0, 2.0 at T=100

    return Human(
        testosterone=testosterone,
        arousal=15.0 + 10.0 * t_factor,           # 15-35 based on T
        energy=75.0 + 10.0 * t_factor,            # 75-95 based on T
        anxiety=35.0 - 10.0 * t_factor,           # 35-15 based on T (inverse)
        vasopressin=15.0 + 10.0 * t_factor,       # 15-35 based on T
    )


@dataclass
class Human:
    """
    Simulates basic human physiology with neurotransmitters and vital parameters.
    All values are on a 0-100 scale unless noted otherwise.
    """
    # === BASELINE CONFIGURATION (set before simulation, affects initial values) ===
    # Testosterone level: affects baseline arousal, energy, dominance tendencies
    # This is a trait, not a state - set once at creation, doesn't change during simulation
    testosterone: float = 50.0   # 0 = very low T, 100 = very high T

    # === NEUROTRANSMITTERS ===
    dopamine: float = 50.0       # reward, motivation, pleasure anticipation
    oxytocin: float = 30.0       # bonding, trust, relaxation, "passive" pleasure, diffuse/body orgasm
    endorphins: float = 20.0     # pain relief, euphoria
    serotonin: float = 50.0      # mood stability, wellbeing

    # === HORMONES (dynamic) ===
    prolactin: float = 10.0      # post-orgasm hormone, causes refractory period, suppresses dopamine
    vasopressin: float = 20.0    # "active" arousal, focus, intensity, dominance, genital-focused orgasm

    # === PHYSIOLOGICAL STATE ===
    arousal: float = 20.0        # physical/sexual arousal (HR, blood flow, etc)
    prefrontal: float = 50.0     # prefrontal cortex activity (control, analysis, low = hypofrontality)
    sleepiness: float = 20.0     # drowsiness (0 = alert, 100 = falling asleep)

    # === MENTAL STATE ===
    # Anxiety correlates with cortisol levels - high cortisol = high anxiety
    # Cortisol is the stress hormone; we model its subjective effects through anxiety
    anxiety: float = 30.0        # mental tension, worry, stress (cortisol proxy). 0 = calm, 100 = panic
    absorption: float = 30.0     # immersion in experience (0 = self-aware, 100 = trance/flow)

    # Basic needs
    hunger: float = 20.0         # 0 = full, 100 = starving
    energy: float = 80.0         # 0 = exhausted, 100 = fully rested

    # Health (slower changing)
    physical_health: float = 80.0
    psychological_health: float = 70.0

    # Internal state tracking
    time_since_orgasm: float = 0.0  # hours since last orgasm (for refractory)
    edging_buildup: float = 0.0     # accumulated arousal without release
    digesting: float = 0.0          # post-meal digestion state (causes drowsiness)

    # === PHYSIOLOGICAL REALISM ===
    tolerance: dict = field(default_factory=lambda: {
        'sexual': 0.0, 'pain': 0.0, 'social': 0.0,
        'breathwork': 0.0, 'food': 0.0, 'rest': 0.0, 'drugs': 0.0
    })
    reserves: dict = field(default_factory=lambda: {
        'dopamine': 100.0, 'serotonin': 100.0,
        'endorphins': 100.0, 'oxytocin': 100.0
    })
    active_effects: list = field(default_factory=list)
    rebound_queue: list = field(default_factory=list)
    cue_salience: dict = field(default_factory=lambda: {
        'sexual': 0.0, 'pain': 0.0, 'social': 0.0,
        'breathwork': 0.0, 'food': 0.0, 'rest': 0.0, 'drugs': 0.0
    })

    def clamp_values(self):
        """Keep all values within valid bounds."""
        self.dopamine = max(0, min(100, self.dopamine))
        self.oxytocin = max(0, min(100, self.oxytocin))
        self.endorphins = max(0, min(100, self.endorphins))
        self.serotonin = max(0, min(100, self.serotonin))
        self.prolactin = max(0, min(100, self.prolactin))
        self.vasopressin = max(0, min(100, self.vasopressin))
        self.arousal = max(0, min(100, self.arousal))
        self.prefrontal = max(0, min(100, self.prefrontal))
        self.sleepiness = max(0, min(100, self.sleepiness))
        self.anxiety = max(0, min(100, self.anxiety))
        self.absorption = max(0, min(100, self.absorption))
        self.hunger = max(0, min(100, self.hunger))
        self.energy = max(0, min(100, self.energy))
        self.physical_health = max(0, min(100, self.physical_health))
        self.psychological_health = max(0, min(100, self.psychological_health))
        self.edging_buildup = max(0, min(100, self.edging_buildup))
        self.digesting = max(0, min(100, self.digesting))
        for k in self.reserves:
            self.reserves[k] = max(0, min(100, self.reserves[k]))
        for k in self.tolerance:
            self.tolerance[k] = max(0.0, min(1.0, self.tolerance[k]))
        for k in self.cue_salience:
            self.cue_salience[k] = max(0.0, min(1.0, self.cue_salience[k]))

    def pleasure_score(self) -> float:
        """
        Composite pleasure score - what we want to maximize.
        Weighted combination of feel-good neurotransmitters,
        modulated by anxiety (reduces pleasure) and absorption (amplifies pleasure).
        """
        base_pleasure = (
            self.dopamine * 0.20 +      # wanting/motivation, not hedonic per se
            self.endorphins * 0.35 +     # actual hedonic "liking" signal
            self.oxytocin * 0.20 +       # bonding/warmth pleasure
            self.serotonin * 0.25        # contentment/wellbeing
        )

        # Yerkes-Dodson inverted-U: moderate anxiety (~35) is optimal
        # Too low = understimulated, too high = overwhelmed
        if self.anxiety <= 35:
            # Rising: 0.92 at anxiety=0, 1.05 at anxiety=35
            anxiety_factor = 0.92 + (self.anxiety / 35) * 0.13
        else:
            # Falling: 1.05 at anxiety=35, 0.60 at anxiety=100
            anxiety_factor = 1.05 - ((self.anxiety - 35) / 65) * 0.45

        # Absorption bonus: high absorption amplifies pleasure
        # At absorption=100, pleasure is amplified by 30%
        absorption_factor = 1.0 + (self.absorption / 100) * 0.3

        return base_pleasure * anxiety_factor * absorption_factor

    def is_viable(self) -> bool:
        """Check if human is in a viable state (not dead/incapacitated)."""
        return (
            self.energy > 5 and
            self.hunger < 95 and
            self.physical_health > 10 and
            self.psychological_health > 10 and
            self.sleepiness < 95  # too sleepy = falls asleep
        )

    def __repr__(self):
        res = self.reserves
        return (
            f"Human(T={self.testosterone:.0f}, dopa={self.dopamine:.1f}, oxy={self.oxytocin:.1f}, "
            f"vaso={self.vasopressin:.1f}, prol={self.prolactin:.1f}, "
            f"arousal={self.arousal:.1f}, anxiety={self.anxiety:.1f}, "
            f"absorb={self.absorption:.1f}, sleepy={self.sleepiness:.1f}, "
            f"res=[D:{res['dopamine']:.0f} S:{res['serotonin']:.0f} "
            f"E:{res['endorphins']:.0f} O:{res['oxytocin']:.0f}])"
        )

