from dataclasses import dataclass


@dataclass
class Human:
    """
    Simulates basic human physiology with neurotransmitters and vital parameters.
    All values are on a 0-100 scale unless noted otherwise.
    """
    # Neurotransmitters
    dopamine: float = 50.0       # reward, motivation, pleasure anticipation
    oxytocin: float = 30.0       # bonding, trust, social pleasure
    endorphins: float = 20.0     # pain relief, euphoria
    serotonin: float = 50.0      # mood stability, wellbeing

    # Physiological state
    arousal: float = 20.0        # physical/sexual arousal (HR, blood flow, etc)
    prefrontal: float = 50.0     # prefrontal cortex activity (control, analysis)
    sleepiness: float = 20.0     # drowsiness (0 = alert, 100 = falling asleep)

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

    def clamp_values(self):
        """Keep all values within valid bounds."""
        self.dopamine = max(0, min(100, self.dopamine))
        self.oxytocin = max(0, min(100, self.oxytocin))
        self.endorphins = max(0, min(100, self.endorphins))
        self.serotonin = max(0, min(100, self.serotonin))
        self.arousal = max(0, min(100, self.arousal))
        self.prefrontal = max(0, min(100, self.prefrontal))
        self.sleepiness = max(0, min(100, self.sleepiness))
        self.hunger = max(0, min(100, self.hunger))
        self.energy = max(0, min(100, self.energy))
        self.physical_health = max(0, min(100, self.physical_health))
        self.psychological_health = max(0, min(100, self.psychological_health))
        self.edging_buildup = max(0, min(100, self.edging_buildup))
        self.digesting = max(0, min(100, self.digesting))

    def pleasure_score(self) -> float:
        """
        Composite pleasure score - what we want to maximize.
        Weighted combination of feel-good neurotransmitters.
        """
        return (
            self.dopamine * 0.35 +
            self.endorphins * 0.30 +
            self.oxytocin * 0.20 +
            self.serotonin * 0.15
        )

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
        return (
            f"Human(dopa={self.dopamine:.1f}, oxy={self.oxytocin:.1f}, "
            f"endor={self.endorphins:.1f}, sero={self.serotonin:.1f}, "
            f"arousal={self.arousal:.1f}, sleepy={self.sleepiness:.1f}, "
            f"hunger={self.hunger:.1f}, energy={self.energy:.1f})"
        )

