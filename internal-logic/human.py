from dataclasses import dataclass, field, fields


def create_human(testosterone: float = 50.0, ssri_level: float = 0.0,
                  life_stress: float = 0.0) -> 'Human':
    """
    Factory function to create a Human with trait-adjusted initial values.
    Testosterone (0-100) affects:
    - Baseline arousal: higher T = higher baseline arousal
    - Energy: higher T = slightly more energy
    - Anxiety: higher T = slightly lower baseline anxiety
    - Vasopressin baseline: higher T = higher vasopressin tendency
    SSRI (0-100) affects serotonin, prolactin, anxiety, dopamine baselines.
    Life stress (0-100) affects anxiety and absorption baselines.
    """
    t_factor = testosterone / 50.0  # 1.0 at T=50, 0.0 at T=0, 2.0 at T=100

    return Human(
        testosterone=testosterone,
        ssri_level=ssri_level,
        life_stress=life_stress,
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
    ssri_level: float = 0.0      # 0-100, psychiatric medication dose
    life_stress: float = 0.0     # 0-100, background chronic stress

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

    # === DUAL CONTROL MODEL (Bancroft & Janssen) ===
    # Sexual response is governed by two independent systems.
    # arousal already acts as a proxy for SES (excitation / "gas pedal").
    # sexual_inhibition is the SIS ("brake"): builds from self-monitoring and
    # performance anxiety; operates independently of arousal.
    sexual_inhibition: float = 0.0  # 0 = no brake, 100 = full inhibition

    # === WINDOW OF TOLERANCE / POLYVAGAL (Siegel / Porges) ===
    # When overwhelmed beyond threshold, the system can flip into dorsal vagal
    # shutdown: flatness, numbing, anhedonia — distinct from the hyperarousal
    # (high anxiety) failure mode. Blocks all valence, not just positive.
    shutdown: float = 0.0           # 0 = normal, 100 = full dorsal collapse

    # === PHYSIOLOGICAL REALISM ===
    tolerance: dict = field(default_factory=lambda: {
        'sexual': 0.0, 'pain': 0.0, 'social': 0.0,
        'breathwork': 0.0, 'food': 0.0, 'rest': 0.0, 'drugs': 0.0,
        'medical': 0.0, 'life': 0.0
    })
    reserves: dict = field(default_factory=lambda: {
        'dopamine': 100.0, 'serotonin': 100.0,
        'endorphins': 100.0, 'oxytocin': 100.0
    })
    active_effects: list = field(default_factory=list)
    rebound_queue: list = field(default_factory=list)
    cue_salience: dict = field(default_factory=lambda: {
        'sexual': 0.0, 'pain': 0.0, 'social': 0.0,
        'breathwork': 0.0, 'food': 0.0, 'rest': 0.0, 'drugs': 0.0,
        'medical': 0.0, 'life': 0.0
    })

    # Fields excluded from 0-100 clamping (unbounded or non-numeric)
    _UNCLAMPED_FIELDS = frozenset({
        'time_since_orgasm',  # unbounded time counter
        'tolerance', 'reserves', 'cue_salience',  # dicts, clamped separately
        'active_effects', 'rebound_queue',  # lists, not clamped
        'ssri_level', 'life_stress',  # traits, not state
    })

    def clamp_values(self):
        """Keep all values within valid bounds.
        Float fields are clamped to [0, 100] by default.
        Dict fields have their own bounds.
        """
        for f in fields(self):
            if f.name in self._UNCLAMPED_FIELDS:
                continue
            if f.type == 'float' or f.type is float:
                val = getattr(self, f.name)
                setattr(self, f.name, max(0, min(100, val)))

        for k in self.reserves:
            self.reserves[k] = max(0, min(100, self.reserves[k]))
        for k in self.tolerance:
            self.tolerance[k] = max(0.0, min(1.0, self.tolerance[k]))
        for k in self.cue_salience:
            self.cue_salience[k] = max(0.0, min(1.0, self.cue_salience[k]))

    def yerkes_dodson_optimum(self) -> float:
        """
        Individualized optimal anxiety level for Yerkes-Dodson curve.
        Base: 35. Modified by testosterone and SSRI.
        """
        optimum = 35.0
        # High T = lower optimum (less anxiety needed for peak performance)
        optimum -= (self.testosterone - 50) / 50 * 5
        # SSRI = lower optimum (less anxiety needed)
        ssri_pct = self.ssri_level / 100.0
        optimum -= ssri_pct * 8
        return max(10.0, min(50.0, optimum))

    def liking_score(self) -> float:
        """
        Hedonic wellbeing score - how good it actually feels.
        Weighted combination of hedonic neurotransmitters (excludes dopamine),
        modulated by anxiety (Yerkes-Dodson) and absorption (amplifies experience).
        """
        base_liking = (
            self.endorphins * 0.40 +     # hedonic "liking" signal
            self.oxytocin * 0.25 +       # bonding/warmth
            self.serotonin * 0.35        # contentment/wellbeing
        )

        # Yerkes-Dodson inverted-U: individualized optimum
        optimum = self.yerkes_dodson_optimum()
        if self.anxiety <= optimum:
            # Rising: 0.92 at anxiety=0, 1.05 at optimum
            anxiety_factor = 0.92 + (self.anxiety / optimum) * 0.13
        else:
            # Falling: 1.05 at optimum, 0.60 at anxiety=100
            anxiety_factor = 1.05 - ((self.anxiety - optimum) / (100 - optimum)) * 0.45

        # Absorption bonus: high absorption amplifies pleasure
        # SSRI halves the absorption amplification (emotional blunting)
        ssri_pct = self.ssri_level / 100.0
        max_bonus = 0.3 * (1 - ssri_pct * 0.5)
        absorption_factor = 1.0 + (self.absorption / 100) * max_bonus

        # Shutdown (dorsal vagal): numbs all valence — not pain, not pleasure.
        # Distinct from anxiety: doesn't modulate, just flattens.
        shutdown_factor = 1.0 - (self.shutdown / 100) * 0.8

        return base_liking * anxiety_factor * absorption_factor * shutdown_factor

    def wanting_score(self) -> float:
        """
        Approach motivation score - how driven/compelled.
        Based on dopamine (wanting signal) and arousal (physiological drive),
        with cue salience contribution. Suppressed by prolactin and low energy.
        """
        base_wanting = (
            self.dopamine * 0.50 +       # primary wanting signal
            self.arousal * 0.25          # physiological drive
        )

        # Add cue salience contribution (max salience across categories)
        max_salience = max(self.cue_salience.values()) if self.cue_salience else 0
        base_wanting += max_salience * 25  # up to +25 from learned wanting

        # Prolactin suppression (refractory/satiation dampens wanting)
        # At prolactin=0: no suppression. At prolactin=100: 50% suppression.
        prolactin_factor = 1.0 - (self.prolactin / 100) * 0.5

        # Low energy suppression (depletion reduces drive)
        # At energy=100: no suppression. At energy=0: 40% suppression.
        energy_factor = 0.6 + (self.energy / 100) * 0.4

        # Shutdown also collapses drive — dorsal state = no wanting either
        shutdown_factor = 1.0 - (self.shutdown / 100) * 0.6

        return base_wanting * prolactin_factor * energy_factor * shutdown_factor

    def pleasure_score(self) -> float:
        """
        Backward-compatible alias for liking_score().
        """
        return self.liking_score()

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
        traits = f"T={self.testosterone:.0f}"
        if self.ssri_level > 0:
            traits += f", SSRI={self.ssri_level:.0f}"
        if self.life_stress > 0:
            traits += f", stress={self.life_stress:.0f}"
        return (
            f"Human({traits}, dopa={self.dopamine:.1f}, oxy={self.oxytocin:.1f}, "
            f"vaso={self.vasopressin:.1f}, prol={self.prolactin:.1f}, "
            f"arousal={self.arousal:.1f}, anxiety={self.anxiety:.1f}, "
            f"absorb={self.absorption:.1f}, sleepy={self.sleepiness:.1f}, "
            f"res=[D:{res['dopamine']:.0f} S:{res['serotonin']:.0f} "
            f"E:{res['endorphins']:.0f} O:{res['oxytocin']:.0f}])"
        )

