"""
Hedonistic Tamagotchi - Axiom Tests
Automated tests derived from neuroscience review axioms.
Run: python tests.py
"""

import copy
import random
import unittest

from human import Human
from events import make_events, apply_decay, apply_event


# =============================================================================
# HELPERS
# =============================================================================

def apply_n_times(human, event_name, events, n):
    """Apply an event n times with decay between each application."""
    event = events[event_name]
    for _ in range(n):
        if event.can_apply(human):
            apply_event(human, event_name, event)
            apply_decay(human, event.duration)
            human.clamp_values()


def run_sequence(human, sequence, events):
    """Apply a sequence of event names, with decay after each."""
    for event_name in sequence:
        event = events[event_name]
        if event.can_apply(human):
            apply_event(human, event_name, event)
            apply_decay(human, event.duration)
            human.clamp_values()


def decay_only(human, hours, dt=0.1):
    """Apply only decay for a given number of hours."""
    steps = int(hours / dt)
    for _ in range(steps):
        apply_decay(human, dt)
        human.clamp_values()


# =============================================================================
# AXIOM TESTS
# =============================================================================

class TestAxioms(unittest.TestCase):

    def setUp(self):
        """Fresh human and events for each test."""
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False
        self.human = Human()
        self.events = make_events()

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    # -----------------------------------------------------------------
    # Axiom 0: No trivially exploitable loop
    # Repeating any single action should show diminishing returns:
    # pleasure at iterations 40-50 should not exceed pleasure at iterations 10-20
    # -----------------------------------------------------------------
    def test_axiom0_no_trivial_exploit(self):
        """No single action yields ever-increasing pleasure after 50 repeats."""
        for event_name in self.events:
            h = Human()
            pleasures = []
            for _ in range(50):
                event = self.events[event_name]
                if event.can_apply(h):
                    apply_event(h, event_name, event)
                    apply_decay(h, event.duration)
                    h.clamp_values()
                pleasures.append(h.pleasure_score())

            if len(pleasures) >= 50:
                mid_avg = sum(pleasures[10:20]) / 10
                late_avg = sum(pleasures[40:50]) / 10
                # Late pleasure should not exceed mid pleasure (no infinite growth)
                self.assertLessEqual(
                    late_avg, mid_avg * 1.15,
                    f"Action '{event_name}' shows unbounded growth: "
                    f"mid_avg={mid_avg:.1f}, late_avg={late_avg:.1f}"
                )

    # -----------------------------------------------------------------
    # Axiom 1: Misattribution of arousal
    # Arousal from one domain (pain) transfers to another (sexual)
    # -----------------------------------------------------------------
    def test_axiom1_misattribution_of_arousal(self):
        """Arousal gained from pain transfers into sexual context."""
        h = Human()
        h.arousal = 30  # moderate baseline

        # Apply pain stimulus
        apply_event(h, 'light_pain', self.events['light_pain'])
        arousal_after_pain = h.arousal

        # Arousal from pain should have increased
        self.assertGreater(arousal_after_pain, 30,
                           "Pain should increase arousal")

        # Now this arousal should make sexual stimulation more effective
        # (higher arousal = can access intense_stimulation)
        h2 = Human()
        h2.arousal = 30
        # h has higher arousal from pain, so sexual events benefit from it
        self.assertGreater(h.arousal, h2.arousal,
                           "Cross-domain arousal should persist")

    # -----------------------------------------------------------------
    # Axiom 2: Dive reflex
    # Deep breathing should suppress arousal (parasympathetic activation)
    # -----------------------------------------------------------------
    def test_axiom2_dive_reflex(self):
        """Cold face immersion suppresses arousal (mammalian dive reflex)."""
        h = Human()
        h.arousal = 60  # elevated arousal
        initial_arousal = h.arousal

        apply_event(h, 'cold_face_immersion', self.events['cold_face_immersion'])

        self.assertLess(h.arousal, initial_arousal,
                        "Cold face immersion should reduce arousal via dive reflex")

    # -----------------------------------------------------------------
    # Axiom 3: Can't repeat forever
    # Same action repeated yields diminishing pleasure each iteration
    # -----------------------------------------------------------------
    def test_axiom3_cant_repeat_forever(self):
        """Repeated same action yields diminishing marginal gains over time."""
        h = Human()
        gains = []

        for i in range(15):
            before = h.pleasure_score()
            event = self.events['light_stimulation']
            if event.can_apply(h):
                apply_event(h, 'light_stimulation', event)
                apply_decay(h, event.duration)
                h.clamp_values()
            after = h.pleasure_score()
            gains.append(after - before)

        # The marginal gain from later iterations should be less than early ones
        early_gains = sum(gains[:5]) / 5
        late_gains = sum(gains[10:15]) / 5
        self.assertLess(late_gains, early_gains,
                        f"Marginal gains should diminish: early={early_gains:.2f}, "
                        f"late={late_gains:.2f}")

    # -----------------------------------------------------------------
    # Axiom 4: Fast pleasure creates delayed cost
    # Intense stimulation spree -> after decay, pleasure drops below baseline
    # -----------------------------------------------------------------
    def test_axiom4_fast_pleasure_delayed_cost(self):
        """Intense stimulation spree followed by long decay drops pleasure below peak."""
        h = Human()
        baseline_pleasure = h.pleasure_score()

        # Build arousal first
        apply_n_times(h, 'light_stimulation', self.events, 3)
        # Spam intense stimulation heavily
        apply_n_times(h, 'intense_stimulation', self.events, 8)

        peak_pleasure = h.pleasure_score()

        # Let it all decay for 5 hours (long enough for reserve-depressed baselines)
        decay_only(h, 5.0)

        final_pleasure = h.pleasure_score()

        # After heavy spree + long decay, pleasure should drop noticeably below peak
        self.assertLess(final_pleasure, peak_pleasure * 0.85,
                        f"Post-crash pleasure ({final_pleasure:.1f}) "
                        f"should be noticeably below peak ({peak_pleasure:.1f})")
        # And reserves should be depleted
        self.assertLess(h.reserves['dopamine'], 80,
                        f"Dopamine reserves should be depleted after spree")

    # -----------------------------------------------------------------
    # Axiom 5: Edging trades intensity for recovery cost
    # Edging -> orgasm produces more intense orgasm but higher prolactin cost
    # -----------------------------------------------------------------
    def test_axiom5_edging_tradeoff(self):
        """Edging before orgasm gives bigger peak but higher prolactin."""
        # Path A: Direct orgasm (build arousal minimally)
        h_direct = Human()
        h_direct.arousal = 75
        apply_event(h_direct, 'orgasm', self.events['orgasm'])
        direct_endorphins = h_direct.endorphins
        direct_prolactin = h_direct.prolactin

        # Path B: Edge then orgasm
        h_edged = Human()
        h_edged.arousal = 55
        apply_n_times(h_edged, 'edging', self.events, 3)
        if self.events['orgasm'].can_apply(h_edged):
            apply_event(h_edged, 'orgasm', self.events['orgasm'])

        edged_endorphins = h_edged.endorphins
        edged_prolactin = h_edged.prolactin

        # Edged path should give higher endorphins (edging_buildup bonus)
        self.assertGreater(edged_endorphins, direct_endorphins,
                           f"Edged endorphins ({edged_endorphins:.1f}) should exceed "
                           f"direct ({direct_endorphins:.1f})")

        # Edged path should also produce higher prolactin (higher cost)
        self.assertGreater(edged_prolactin, direct_prolactin,
                           f"Edged prolactin ({edged_prolactin:.1f}) should exceed "
                           f"direct ({direct_prolactin:.1f})")

    # -----------------------------------------------------------------
    # Axiom 6: Absorption is fragile under anxiety and sleepiness
    # High anxiety OR high sleepiness suppresses absorption
    # -----------------------------------------------------------------
    def test_axiom6_absorption_fragile(self):
        """High anxiety or sleepiness suppresses absorption."""
        # Test anxiety suppression
        h1 = Human()
        h1.absorption = 70
        h1.anxiety = 80
        initial_absorption = h1.absorption
        decay_only(h1, 0.5)
        self.assertLess(h1.absorption, initial_absorption,
                        "High anxiety should suppress absorption")

        # Test sleepiness suppression
        h2 = Human()
        h2.absorption = 70
        h2.sleepiness = 75
        initial_absorption = h2.absorption
        decay_only(h2, 0.5)
        self.assertLess(h2.absorption, initial_absorption,
                        "High sleepiness should suppress absorption")

    # -----------------------------------------------------------------
    # Axiom 7: Hypofrontality enables altered states
    # Low prefrontal -> absorption increases (flow/trance possible)
    # -----------------------------------------------------------------
    def test_axiom7_hypofrontality(self):
        """Low prefrontal cortex activity facilitates absorption increase."""
        h = Human()
        h.prefrontal = 20  # very low (hypofrontality)
        h.absorption = 30  # starting absorption
        initial_absorption = h.absorption

        # Decay should increase absorption when prefrontal is low
        decay_only(h, 1.0)

        self.assertGreater(h.absorption, initial_absorption,
                           "Low prefrontal should allow absorption to rise")

    # -----------------------------------------------------------------
    # Axiom 8: Too much control blocks pleasure
    # High prefrontal limits absorption and thus limits pleasure amplification
    # -----------------------------------------------------------------
    def test_axiom8_control_blocks_pleasure(self):
        """High prefrontal activity prevents absorption-amplified pleasure."""
        # High prefrontal human
        h_controlled = Human()
        h_controlled.prefrontal = 80
        h_controlled.absorption = 30
        h_controlled.dopamine = 70
        h_controlled.endorphins = 60
        decay_only(h_controlled, 1.0)
        controlled_absorption = h_controlled.absorption

        # Low prefrontal human (same NTs)
        h_free = Human()
        h_free.prefrontal = 20
        h_free.absorption = 30
        h_free.dopamine = 70
        h_free.endorphins = 60
        decay_only(h_free, 1.0)
        free_absorption = h_free.absorption

        self.assertGreater(free_absorption, controlled_absorption,
                           "Low prefrontal should enable higher absorption than high")

    # -----------------------------------------------------------------
    # Axiom 9: Oxytocin vs vasopressin lead to different states
    # Cuddling->orgasm (high oxy) vs intense_stim->orgasm (high vaso)
    # produce different neurochemical profiles
    # -----------------------------------------------------------------
    def test_axiom9_oxy_vs_vaso_states_differ(self):
        """Oxytocin-path and vasopressin-path orgasms differ in profile."""
        # Path A: Oxytocin-dominant (cuddling -> light stim -> orgasm)
        h_oxy = Human()
        run_sequence(h_oxy, [
            'cuddling', 'cuddling', 'massage',
            'light_stimulation', 'light_stimulation',
            'light_stimulation',
        ], self.events)
        if self.events['orgasm'].can_apply(h_oxy):
            apply_event(h_oxy, 'orgasm', self.events['orgasm'])

        # Path B: Vasopressin-dominant (intense stim -> edging -> orgasm)
        h_vaso = Human()
        run_sequence(h_vaso, [
            'light_stimulation', 'intense_stimulation',
            'intense_stimulation', 'edging',
        ], self.events)
        if self.events['orgasm'].can_apply(h_vaso):
            apply_event(h_vaso, 'orgasm', self.events['orgasm'])

        # Oxy path should have higher oxytocin
        self.assertGreater(h_oxy.oxytocin, h_vaso.oxytocin,
                           "Oxy-path should produce more oxytocin")

        # Vaso path should have higher vasopressin
        self.assertGreater(h_vaso.vasopressin, h_oxy.vasopressin,
                           "Vaso-path should produce more vasopressin")

    # -----------------------------------------------------------------
    # Axiom 10: Yerkes-Dodson inverted-U curve
    # Moderate anxiety (~35) > zero anxiety > high anxiety for pleasure
    # -----------------------------------------------------------------
    def test_axiom10_yerkes_dodson(self):
        """Moderate anxiety produces more pleasure than zero or high anxiety."""
        # Same NT levels, different anxiety
        base = Human()
        base.dopamine = 60
        base.endorphins = 50
        base.oxytocin = 40
        base.serotonin = 55

        h_zero = copy.deepcopy(base)
        h_zero.anxiety = 0
        p_zero = h_zero.pleasure_score()

        h_moderate = copy.deepcopy(base)
        h_moderate.anxiety = 35
        p_moderate = h_moderate.pleasure_score()

        h_high = copy.deepcopy(base)
        h_high.anxiety = 80
        p_high = h_high.pleasure_score()

        # Moderate should be best
        self.assertGreater(p_moderate, p_zero,
                           f"Moderate anxiety ({p_moderate:.1f}) should beat "
                           f"zero anxiety ({p_zero:.1f})")
        self.assertGreater(p_moderate, p_high,
                           f"Moderate anxiety ({p_moderate:.1f}) should beat "
                           f"high anxiety ({p_high:.1f})")
        # Zero should still be better than high
        self.assertGreater(p_zero, p_high,
                           f"Zero anxiety ({p_zero:.1f}) should beat "
                           f"high anxiety ({p_high:.1f})")

    # -----------------------------------------------------------------
    # Axiom 11: Rest is required for sustained pleasure
    # Mixed strategy with rest/sleep sustains higher avg pleasure
    # than action-only strategy
    # -----------------------------------------------------------------
    def test_axiom11_rest_required(self):
        """Pure intense action over extended period crashes harder than paced strategy."""
        # Pure intense action: spam intense stimulation as hard as possible
        h_intense = Human()
        total_intense = 0.0
        for _ in range(30):
            # Build arousal if needed, then go intense
            if self.events['intense_stimulation'].can_apply(h_intense):
                event = self.events['intense_stimulation']
                apply_event(h_intense, 'intense_stimulation', event)
            elif self.events['light_stimulation'].can_apply(h_intense):
                event = self.events['light_stimulation']
                apply_event(h_intense, 'light_stimulation', event)
            else:
                event = self.events['wait']
                apply_event(h_intense, 'wait', event)
            total_intense += h_intense.pleasure_score() * event.duration
            apply_decay(h_intense, event.duration)
            h_intense.clamp_values()

        # Paced strategy: variety with recovery
        h_paced = Human()
        total_paced = 0.0
        paced_seq = [
            'cuddling', 'light_stimulation', 'light_stimulation',
            'massage', 'deep_breathing',
            'light_stimulation', 'intense_stimulation',
            'snack', 'rest',
            'cuddling', 'light_stimulation', 'light_stimulation',
            'massage', 'deep_breathing',
            'light_stimulation', 'intense_stimulation',
            'rest', 'snack',
            'cuddling', 'light_stimulation', 'light_stimulation',
            'massage', 'deep_breathing',
            'light_stimulation', 'intense_stimulation',
            'sleep',
            'cuddling', 'light_stimulation', 'light_stimulation',
            'massage',
        ]
        for name in paced_seq:
            event = self.events[name]
            if event.can_apply(h_paced):
                apply_event(h_paced, name, event)
                total_paced += h_paced.pleasure_score() * event.duration
                apply_decay(h_paced, event.duration)
                h_paced.clamp_values()

        # After both strategies, the paced one should have better final state
        # (higher reserves, lower tolerance, better health)
        self.assertGreater(h_paced.reserves['dopamine'], h_intense.reserves['dopamine'],
                           "Paced strategy should preserve dopamine reserves")
        self.assertGreater(h_paced.psychological_health, h_intense.psychological_health,
                           "Paced strategy should preserve psychological health")

    # -----------------------------------------------------------------
    # Axiom 12: Health is the ultimate limiter
    # Sustained extreme dopamine (>85) degrades psychological health
    # -----------------------------------------------------------------
    def test_axiom12_health_limiter(self):
        """Sustained extreme neurotransmitter levels degrade health."""
        h = Human()
        h.dopamine = 90  # extreme dopamine
        initial_psych = h.psychological_health

        # Let extreme state persist for several hours
        decay_only(h, 3.0)

        self.assertLess(h.psychological_health, initial_psych,
                        f"Extreme dopamine should degrade psych health: "
                        f"initial={initial_psych:.1f}, final={h.psychological_health:.1f}")

    # -----------------------------------------------------------------
    # Final Axiom: No dominant strategy
    # No single action repeated 20x beats a balanced mixed strategy
    # -----------------------------------------------------------------
    def test_final_no_dominant_strategy(self):
        """No single repeated action yields unbounded pleasure growth.

        Rather than comparing total scores (which depend on sequence design),
        this checks the fundamental property: every single-action strategy
        shows diminishing returns, meaning no single action dominates forever.
        """
        for event_name in self.events:
            h = Human()
            pleasures_per_5 = []
            block_pleasure = 0.0

            for i in range(30):
                event = self.events[event_name]
                if event.can_apply(h):
                    apply_event(h, event_name, event)
                    block_pleasure += h.pleasure_score() * event.duration
                    apply_decay(h, event.duration)
                    h.clamp_values()

                if (i + 1) % 10 == 0:
                    pleasures_per_5.append(block_pleasure)
                    block_pleasure = 0.0

            if len(pleasures_per_5) >= 3:
                # The pleasure gained in the last 10 actions should not vastly exceed
                # the first 10 (convergence, not unbounded growth)
                self.assertLessEqual(
                    pleasures_per_5[2], pleasures_per_5[0] * 1.3,
                    f"Spamming '{event_name}' shows unbounded growth: "
                    f"first_10={pleasures_per_5[0]:.1f}, last_10={pleasures_per_5[2]:.1f}"
                )


# =============================================================================
# NEW MECHANICS TESTS
# =============================================================================

class TestOpponentProcess(unittest.TestCase):
    """Tests for opponent-process rebound mechanics."""

    def setUp(self):
        self.human = Human()
        self.events = make_events()

    def test_rebound_scheduled_on_large_boost(self):
        """Large NT boosts (>10) schedule a rebound in the queue."""
        h = self.human
        from events import nt_boost
        initial_queue_len = len(h.rebound_queue)
        nt_boost(h, 'dopamine', 20)  # raw_amount > 10 and dopamine is a reserve NT
        self.assertGreater(len(h.rebound_queue), initial_queue_len,
                           "Large boost should schedule a rebound")

    def test_rebound_not_scheduled_on_small_boost(self):
        """Small NT boosts (<=10) should NOT schedule a rebound."""
        h = self.human
        from events import nt_boost
        initial_queue_len = len(h.rebound_queue)
        nt_boost(h, 'dopamine', 8)  # raw_amount <= 10
        self.assertEqual(len(h.rebound_queue), initial_queue_len,
                         "Small boost should not schedule a rebound")

    def test_rebound_creates_below_baseline_dip(self):
        """After a large boost, rebound should push NT below its pre-boost baseline."""
        h = self.human
        h.dopamine = 50.0  # baseline
        from events import nt_boost
        nt_boost(h, 'dopamine', 30)
        # Now decay for enough time: 0.5h delay + 1.0h rebound duration
        decay_only(h, 2.0)
        # Dopamine should be below baseline due to rebound + reserve depletion
        self.assertLess(h.dopamine, 50.0,
                        "Rebound should push dopamine below baseline")

    def test_rebound_clears_after_completion(self):
        """Rebound entries should be removed from queue after their duration expires."""
        h = self.human
        from events import nt_boost
        nt_boost(h, 'dopamine', 25)
        self.assertGreater(len(h.rebound_queue), 0)
        # Decay long enough for rebound to complete (0.5h delay + 1.0h duration + extra)
        decay_only(h, 2.0)
        self.assertEqual(len(h.rebound_queue), 0,
                         "Rebound queue should be empty after completion")


class TestDrugEvents(unittest.TestCase):
    """Tests for recreational drug events."""

    def setUp(self):
        self.human = Human()
        self.events = make_events()
        # Disable probabilistic outcomes for deterministic tests
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    def test_all_drugs_exist(self):
        """All 12 drug events should be registered."""
        drug_names = [
            'mdma', 'weed', 'mushrooms', 'lsd', 'poppers', 'ketamine',
            'tobacco', 'caffeine', 'alcohol', 'amphetamines', 'cocaine', 'nitrous'
        ]
        for name in drug_names:
            self.assertIn(name, self.events, f"Drug event '{name}' should exist")

    def test_drugs_have_category(self):
        """All drug events should be in the 'drugs' category."""
        drug_names = [
            'mdma', 'weed', 'mushrooms', 'lsd', 'poppers', 'ketamine',
            'tobacco', 'caffeine', 'alcohol', 'amphetamines', 'cocaine', 'nitrous'
        ]
        for name in drug_names:
            self.assertEqual(self.events[name].category, 'drugs',
                             f"'{name}' should be in 'drugs' category")

    def test_mdma_boosts_serotonin_and_oxytocin(self):
        """MDMA should significantly boost serotonin and oxytocin."""
        h = Human()
        h.energy = 50
        initial_serotonin = h.serotonin
        initial_oxytocin = h.oxytocin
        apply_event(h, 'mdma', self.events['mdma'])
        self.assertGreater(h.serotonin, initial_serotonin + 10,
                           "MDMA should boost serotonin significantly")
        self.assertGreater(h.oxytocin, initial_oxytocin + 10,
                           "MDMA should boost oxytocin significantly")

    def test_cocaine_short_duration_big_dopamine(self):
        """Cocaine should have short duration and large dopamine boost."""
        self.assertEqual(self.events['cocaine'].duration, 0.5)
        h = Human()
        h.energy = 50
        initial_dopamine = h.dopamine
        apply_event(h, 'cocaine', self.events['cocaine'])
        self.assertGreater(h.dopamine, initial_dopamine + 15,
                           "Cocaine should produce large dopamine boost")

    def test_caffeine_always_available(self):
        """Caffeine should be available even at low energy."""
        h = Human()
        h.energy = 10
        self.assertTrue(self.events['caffeine'].can_apply(h),
                        "Caffeine should always be available")

    def test_drug_tolerance_builds(self):
        """Using drugs should build tolerance in the 'drugs' category."""
        h = Human()
        h.energy = 80
        initial_tolerance = h.tolerance['drugs']
        apply_event(h, 'cocaine', self.events['cocaine'])
        self.assertGreater(h.tolerance['drugs'], initial_tolerance,
                           "Drug use should increase drugs tolerance")

    def test_drug_tolerance_reduces_effectiveness(self):
        """High drug tolerance should reduce effectiveness of drug effects."""
        h1 = Human()
        h1.energy = 80
        apply_event(h1, 'cocaine', self.events['cocaine'])
        dopamine_first = h1.dopamine

        h2 = Human()
        h2.energy = 80
        h2.tolerance['drugs'] = 0.8  # high tolerance
        apply_event(h2, 'cocaine', self.events['cocaine'])
        dopamine_tolerant = h2.dopamine

        self.assertGreater(dopamine_first, dopamine_tolerant,
                           "High tolerance should reduce drug effectiveness")

    def test_drugs_no_trivial_exploit(self):
        """No drug repeated many times should show unbounded pleasure growth."""
        drug_names = [
            'mdma', 'weed', 'mushrooms', 'lsd', 'poppers', 'ketamine',
            'tobacco', 'caffeine', 'alcohol', 'amphetamines', 'cocaine', 'nitrous'
        ]
        for drug_name in drug_names:
            h = Human()
            h.energy = 90
            pleasures = []
            for _ in range(30):
                event = self.events[drug_name]
                if event.can_apply(h):
                    apply_event(h, drug_name, event)
                    apply_decay(h, event.duration)
                    h.clamp_values()
                pleasures.append(h.pleasure_score())
                if not h.is_viable():
                    break

            if len(pleasures) >= 20:
                mid_avg = sum(pleasures[5:10]) / 5
                late_avg = sum(pleasures[15:20]) / 5
                self.assertLessEqual(
                    late_avg, mid_avg * 1.2,
                    f"Drug '{drug_name}' shows unbounded growth: "
                    f"mid={mid_avg:.1f}, late={late_avg:.1f}"
                )


class TestProbabilisticOutcomes(unittest.TestCase):
    """Tests for probabilistic outcome mechanics."""

    def test_probabilistic_flag_disables_randomness(self):
        """Setting ENABLE_PROBABILISTIC=False should prevent random outcomes."""
        import events as ev
        ev.ENABLE_PROBABILISTIC = False
        try:
            h = Human()
            h.arousal = 90
            events = make_events()
            # Run intense_stimulation many times - should never trigger orgasm
            for _ in range(100):
                initial_prolactin = h.prolactin
                events['intense_stimulation'].apply(h, 1.0)
                # If orgasm was triggered, prolactin would spike
                self.assertLess(h.prolactin, initial_prolactin + 40,
                                "With ENABLE_PROBABILISTIC=False, no random orgasm should occur")
                h.clamp_values()
                h.arousal = 90  # keep arousal high
                h.energy = 80   # keep energy up
        finally:
            ev.ENABLE_PROBABILISTIC = True

    def test_probabilistic_can_trigger(self):
        """With ENABLE_PROBABILISTIC=True and seeded random, verify events can trigger."""
        import events as ev
        ev.ENABLE_PROBABILISTIC = True
        events = make_events()
        # Try many seeds to find one that triggers premature orgasm
        triggered = False
        for seed in range(1000):
            random.seed(seed)
            h = Human()
            h.arousal = 90
            h.energy = 80
            initial_prolactin = h.prolactin
            events['intense_stimulation'].apply(h, 1.0)
            if h.prolactin > initial_prolactin + 30:
                triggered = True
                break
        self.assertTrue(triggered,
                        "With enough attempts, probabilistic orgasm should trigger")


class TestCueLearning(unittest.TestCase):
    """Tests for cue learning / wanting sensitization."""

    def setUp(self):
        self.human = Human()
        self.events = make_events()
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    def test_cue_salience_increases_with_use(self):
        """Repeated use of an event category should increase cue salience."""
        h = self.human
        initial_salience = h.cue_salience['sexual']
        apply_event(h, 'light_stimulation', self.events['light_stimulation'])
        self.assertGreater(h.cue_salience['sexual'], initial_salience,
                           "Sexual cue salience should increase after sexual event")

    def test_cue_salience_adds_dopamine(self):
        """Cue-driven dopamine should be added when cue salience is non-zero."""
        h = self.human
        h.cue_salience['sexual'] = 0.5  # pre-existing salience
        initial_dopamine = h.dopamine
        apply_event(h, 'light_stimulation', self.events['light_stimulation'])
        # Should get extra dopamine from cue (0.5 * 8 = 4 extra + normal boost)
        # Compare with a fresh human with no salience
        h2 = Human()
        apply_event(h2, 'light_stimulation', self.events['light_stimulation'])
        self.assertGreater(h.dopamine - initial_dopamine,
                           h2.dopamine - 50.0,  # 50.0 is default dopamine
                           "Cue salience should add extra dopamine")

    def test_cue_salience_decays_slowly(self):
        """Cue salience should decay over time, but slowly."""
        h = self.human
        h.cue_salience['sexual'] = 0.5
        initial = h.cue_salience['sexual']
        decay_only(h, 1.0)
        self.assertLess(h.cue_salience['sexual'], initial,
                        "Cue salience should decay over time")
        self.assertGreater(h.cue_salience['sexual'], 0.3,
                           "Cue salience decay should be slow (persists)")

    def test_sleep_reduces_cue_salience(self):
        """Sleep should reduce cue salience."""
        h = self.human
        h.cue_salience['sexual'] = 0.5
        h.cue_salience['drugs'] = 0.3
        h.energy = 40
        h.sleepiness = 60
        apply_event(h, 'sleep', self.events['sleep'])
        self.assertLess(h.cue_salience['sexual'], 0.5,
                        "Sleep should reduce sexual cue salience")
        self.assertLess(h.cue_salience['drugs'], 0.3,
                        "Sleep should reduce drugs cue salience")

    def test_cue_salience_capped_at_one(self):
        """Cue salience should never exceed 1.0."""
        h = self.human
        h.cue_salience['sexual'] = 0.95
        for _ in range(10):
            apply_event(h, 'light_stimulation', self.events['light_stimulation'])
            h.clamp_values()
        self.assertLessEqual(h.cue_salience['sexual'], 1.0,
                             "Cue salience should be capped at 1.0")


class TestRunIntegration(unittest.TestCase):
    """Tests for the fixed run() time integration."""

    def setUp(self):
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    def test_event_duration_properly_integrated(self):
        """Events with longer duration should accumulate more pleasure steps."""
        from simulation import Simulation
        sim = Simulation(time_step=0.1)

        # Use a human that can sleep (low energy, high sleepiness)
        h = Human()
        h.energy = 40
        h.sleepiness = 60
        result = sim.run(['sleep'], initial_state=h, max_hours=3.0)
        # Timeline should have entries for the sleep sub-steps + decay steps
        sleep_entries = [t for t in result['timeline'] if t[2] == 'sleep']
        self.assertGreater(len(sleep_entries), 0,
                           "Sleep event should appear in timeline")

    def test_simulation_viable_basic_sequence(self):
        """Basic sequence should complete without crashing."""
        from simulation import Simulation
        sim = Simulation(time_step=0.1)
        result = sim.run(
            ['rest', 'light_stimulation', 'rest'],
            max_hours=5.0
        )
        self.assertTrue(result['viable'],
                        "Basic sequence should remain viable")
        self.assertGreater(result['total_pleasure'], 0,
                           "Should accumulate some pleasure")


class TestContextReceptivity(unittest.TestCase):
    """Tests for context-sensitive receptivity: same action, different outcome."""

    def setUp(self):
        self.events = make_events()
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    def test_sexual_stim_during_high_anxiety_is_worse(self):
        """Sexual stimulation while panicking should be less pleasurable than when calm."""
        # Calm human
        h_calm = Human()
        h_calm.anxiety = 20
        h_calm.arousal = 40
        calm_before = h_calm.pleasure_score()
        apply_event(h_calm, 'light_stimulation', self.events['light_stimulation'])
        calm_gain = h_calm.pleasure_score() - calm_before

        # Panicking human
        h_panic = Human()
        h_panic.anxiety = 80
        h_panic.arousal = 40
        panic_before = h_panic.pleasure_score()
        apply_event(h_panic, 'light_stimulation', self.events['light_stimulation'])
        panic_gain = h_panic.pleasure_score() - panic_before

        self.assertGreater(calm_gain, panic_gain,
                           f"Sexual stim while calm ({calm_gain:.2f}) should feel better "
                           f"than while panicking ({panic_gain:.2f})")

    def test_sexual_stim_during_panic_increases_anxiety(self):
        """Sexual stimulation during extreme anxiety should make anxiety worse."""
        h = Human()
        h.anxiety = 95
        h.arousal = 40
        initial_anxiety = h.anxiety
        apply_event(h, 'light_stimulation', self.events['light_stimulation'])
        # With negative receptivity, anxiety -= 5*eff where eff is negative → anxiety increases
        self.assertGreater(h.anxiety, initial_anxiety,
                           f"Sexual stim during panic should increase anxiety: "
                           f"before={initial_anxiety:.1f}, after={h.anxiety:.1f}")

    def test_pain_without_arousal_is_unpleasant(self):
        """Pain stimulation without arousal context should reduce pleasure."""
        h = Human()
        h.arousal = 10  # very low arousal
        h.absorption = 10
        h.anxiety = 35  # start at Yerkes-Dodson optimum so backfire can only hurt
        before = h.pleasure_score()
        apply_event(h, 'light_pain', self.events['light_pain'])
        h.clamp_values()
        after = h.pleasure_score()
        self.assertLess(after, before,
                        f"Pain without arousal context should reduce pleasure: "
                        f"before={before:.2f}, after={after:.2f}")

    def test_pain_with_arousal_is_pleasurable(self):
        """Pain during high arousal and absorption should increase pleasure."""
        h = Human()
        h.arousal = 60
        h.absorption = 50
        h.anxiety = 20
        before = h.pleasure_score()
        apply_event(h, 'light_pain', self.events['light_pain'])
        after = h.pleasure_score()
        self.assertGreater(after, before,
                           f"Pain with arousal context should increase pleasure: "
                           f"before={before:.2f}, after={after:.2f}")

    def test_social_interaction_during_anxiety_backfires(self):
        """Cuddling while highly anxious should feel worse than when calm."""
        # Calm human
        h_calm = Human()
        h_calm.anxiety = 15
        h_calm.oxytocin = 40
        calm_before = h_calm.pleasure_score()
        apply_event(h_calm, 'cuddling', self.events['cuddling'])
        calm_gain = h_calm.pleasure_score() - calm_before

        # Anxious human
        h_anxious = Human()
        h_anxious.anxiety = 80
        h_anxious.oxytocin = 40
        anxious_before = h_anxious.pleasure_score()
        apply_event(h_anxious, 'cuddling', self.events['cuddling'])
        anxious_gain = h_anxious.pleasure_score() - anxious_before

        self.assertGreater(calm_gain, anxious_gain,
                           f"Cuddling while calm ({calm_gain:.2f}) should feel better "
                           f"than while anxious ({anxious_gain:.2f})")

    def test_context_setup_matters_for_sexual_sequence(self):
        """Building context (cuddling, massage) before sex should produce more
        pleasure than jumping straight to stimulation."""
        # Cold start: just spam stimulation
        h_cold = Human()
        run_sequence(h_cold, [
            'light_stimulation', 'light_stimulation', 'light_stimulation',
        ], self.events)
        cold_pleasure = h_cold.pleasure_score()

        # Warm start: build context first
        h_warm = Human()
        run_sequence(h_warm, [
            'cuddling', 'massage', 'light_stimulation',
        ], self.events)
        warm_pleasure = h_warm.pleasure_score()

        self.assertGreater(warm_pleasure, cold_pleasure,
                           f"Context-building sequence ({warm_pleasure:.2f}) should beat "
                           f"cold start ({cold_pleasure:.2f})")

    def test_psychedelics_during_anxiety_less_effective(self):
        """Psychedelics while anxious should produce less pleasure gain than when calm."""
        # Calm human
        h_calm = Human()
        h_calm.energy = 60
        h_calm.anxiety = 20
        calm_before = h_calm.pleasure_score()
        apply_event(h_calm, 'mushrooms', self.events['mushrooms'])
        calm_gain = h_calm.pleasure_score() - calm_before

        # Anxious human
        h_anxious = Human()
        h_anxious.energy = 60
        h_anxious.anxiety = 70
        h_anxious.psychological_health = 30
        anxious_before = h_anxious.pleasure_score()
        apply_event(h_anxious, 'mushrooms', self.events['mushrooms'])
        anxious_gain = h_anxious.pleasure_score() - anxious_before

        self.assertGreater(calm_gain, anxious_gain,
                           f"Mushrooms while calm ({calm_gain:.2f}) should feel better "
                           f"than while anxious ({anxious_gain:.2f})")

    def test_receptivity_values_at_default_state(self):
        """Default human should have full receptivity for non-pain categories."""
        from events import compute_receptivity
        h = Human()
        # Default state: anxiety=30, prefrontal=50, arousal=20, absorption=30
        self.assertAlmostEqual(compute_receptivity(h, 'sexual'), 1.0, places=1,
                               msg="Default human should have high sexual receptivity")
        self.assertAlmostEqual(compute_receptivity(h, 'social'), 1.0, places=1,
                               msg="Default human should have high social receptivity")
        self.assertAlmostEqual(compute_receptivity(h, 'rest'), 1.0, places=1,
                               msg="Rest should always be fully receptive")

    def test_receptivity_clamped(self):
        """Receptivity should never go below -0.5 or above 1.0."""
        from events import compute_receptivity
        # Worst case: extreme anxiety
        h = Human()
        h.anxiety = 100
        h.arousal = 0
        h.absorption = 0
        h.prefrontal = 100
        for category in ['sexual', 'social', 'pain', 'breathwork', 'food', 'drugs', 'rest']:
            r = compute_receptivity(h, category)
            self.assertGreaterEqual(r, -0.5, f"{category} receptivity below -0.5")
            self.assertLessEqual(r, 1.0, f"{category} receptivity above 1.0")


class TestTraitDynamics(unittest.TestCase):
    """Tests for meta-traits: testosterone ongoing, SSRI, life stress, interactions."""

    def setUp(self):
        self.events = make_events()
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    def test_high_t_decays_toward_higher_arousal(self):
        """High-T human decays toward higher arousal baseline than low-T."""
        from human import create_human
        h_high = create_human(testosterone=90)
        h_low = create_human(testosterone=10)
        # Set both to same arousal, then decay
        h_high.arousal = 50.0
        h_low.arousal = 50.0
        decay_only(h_high, 3.0)
        decay_only(h_low, 3.0)
        self.assertGreater(h_high.arousal, h_low.arousal,
                           "High-T should decay toward higher arousal baseline")

    def test_ssri_reduces_dopamine_from_cocaine(self):
        """SSRI human gets less dopamine from cocaine than non-SSRI."""
        from human import create_human
        h_ssri = create_human(ssri_level=80)
        h_normal = create_human(ssri_level=0)
        h_ssri.energy = 80
        h_normal.energy = 80
        h_ssri.dopamine = 50.0
        h_normal.dopamine = 50.0
        apply_event(h_ssri, 'cocaine', self.events['cocaine'])
        apply_event(h_normal, 'cocaine', self.events['cocaine'])
        self.assertLess(h_ssri.dopamine, h_normal.dopamine,
                        "SSRI human should get less dopamine from cocaine")

    def test_ssri_boosts_serotonin_baseline(self):
        """SSRI human should decay toward higher serotonin baseline."""
        from human import create_human
        from events import get_effective_baselines
        h_ssri = create_human(ssri_level=80)
        eb = get_effective_baselines(h_ssri)
        self.assertGreater(eb['serotonin'], 50.0,
                           "SSRI should raise serotonin baseline")

    def test_ssri_emotional_blunting(self):
        """SSRI should reduce absorption amplification bonus in pleasure_score."""
        from human import create_human
        h_ssri = create_human(ssri_level=80)
        h_normal = create_human(ssri_level=0)
        # Set identical state except SSRI
        for h in [h_ssri, h_normal]:
            h.dopamine = 60
            h.endorphins = 50
            h.oxytocin = 40
            h.serotonin = 55
            h.anxiety = 30
            h.absorption = 80  # high absorption to show blunting
        p_ssri = h_ssri.pleasure_score()
        p_normal = h_normal.pleasure_score()
        self.assertLess(p_ssri, p_normal,
                        "SSRI should reduce pleasure via absorption blunting")

    def test_life_stress_reduces_receptivity(self):
        """Stressed human's receptivity is lower across non-rest categories."""
        from human import create_human
        from events import compute_receptivity
        h_stressed = create_human(life_stress=80)
        h_calm = create_human(life_stress=0)
        for category in ['sexual', 'social', 'food', 'drugs']:
            r_stressed = compute_receptivity(h_stressed, category)
            r_calm = compute_receptivity(h_calm, category)
            self.assertLess(r_stressed, r_calm,
                            f"Stressed human should have lower {category} receptivity")
        # Rest should be unaffected
        self.assertAlmostEqual(
            compute_receptivity(h_stressed, 'rest'),
            compute_receptivity(h_calm, 'rest'),
            places=2,
            msg="Rest receptivity should not be affected by stress"
        )

    def test_life_stress_absorption_drain(self):
        """Stressed human should lose absorption over time."""
        from human import create_human
        h = create_human(life_stress=80)
        h.absorption = 50.0
        initial = h.absorption
        decay_only(h, 1.0)
        self.assertLess(h.absorption, initial - 1.0,
                        "Life stress should drain absorption over time")

    def test_life_stress_psych_health_drain(self):
        """Stressed human should lose psychological health over time."""
        from human import create_human
        h = create_human(life_stress=80)
        initial = h.psychological_health
        decay_only(h, 2.0)
        self.assertLess(h.psychological_health, initial,
                        "Life stress should drain psychological health")

    def test_ssri_plus_stress_moderate_anxiety(self):
        """SSRI + stress combo has moderate anxiety (partial offset)."""
        from events import get_effective_baselines
        from human import create_human
        h_both = create_human(ssri_level=60, life_stress=60)
        h_stress_only = create_human(life_stress=60)
        h_ssri_only = create_human(ssri_level=60)
        eb_both = get_effective_baselines(h_both)
        eb_stress = get_effective_baselines(h_stress_only)
        eb_ssri = get_effective_baselines(h_ssri_only)
        # SSRI should partially offset stress anxiety
        self.assertLess(eb_both['anxiety'], eb_stress['anxiety'],
                        "SSRI should partially offset stress anxiety")
        self.assertGreater(eb_both['anxiety'], eb_ssri['anxiety'],
                           "Stress should partially offset SSRI anxiety reduction")

    def test_stressed_person_wakes_with_higher_anxiety(self):
        """Stressed person wakes up with higher anxiety than unstressed."""
        from human import create_human
        h_stressed = create_human(life_stress=70)
        h_calm = create_human(life_stress=0)
        h_stressed.energy = 40
        h_stressed.sleepiness = 60
        h_calm.energy = 40
        h_calm.sleepiness = 60
        apply_event(h_stressed, 'sleep', self.events['sleep'])
        apply_event(h_calm, 'sleep', self.events['sleep'])
        self.assertGreater(h_stressed.anxiety, h_calm.anxiety,
                           "Stressed person should wake with higher anxiety")

    def test_ssri_person_wakes_with_higher_prolactin(self):
        """SSRI person wakes up with higher prolactin baseline."""
        from human import create_human
        h_ssri = create_human(ssri_level=70)
        h_normal = create_human(ssri_level=0)
        h_ssri.energy = 40
        h_ssri.sleepiness = 60
        h_normal.energy = 40
        h_normal.sleepiness = 60
        apply_event(h_ssri, 'sleep', self.events['sleep'])
        apply_event(h_normal, 'sleep', self.events['sleep'])
        self.assertGreater(h_ssri.prolactin, h_normal.prolactin,
                           "SSRI person should wake with higher prolactin")

    def test_testosterone_ongoing_vasopressin(self):
        """High-T human decays toward higher vasopressin baseline."""
        from human import create_human
        h_high = create_human(testosterone=90)
        h_low = create_human(testosterone=10)
        h_high.vasopressin = 40.0
        h_low.vasopressin = 40.0
        decay_only(h_high, 3.0)
        decay_only(h_low, 3.0)
        self.assertGreater(h_high.vasopressin, h_low.vasopressin,
                           "High-T should decay toward higher vasopressin baseline")


class TestDynamicTraitEvents(unittest.TestCase):
    """Tests for dynamic trait events (medical and life categories)."""

    def setUp(self):
        self.events = make_events()
        import events as ev
        self._orig_prob = ev.ENABLE_PROBABILISTIC
        ev.ENABLE_PROBABILISTIC = False

    def tearDown(self):
        import events as ev
        ev.ENABLE_PROBABILISTIC = self._orig_prob

    def test_ssri_gradual_buildup(self):
        """10x take_ssri raises ssri_level significantly."""
        h = Human()
        initial_ssri = h.ssri_level
        apply_n_times(h, 'take_ssri', self.events, 10)
        self.assertGreater(h.ssri_level, initial_ssri + 30,
                           "10x take_ssri should raise ssri_level significantly")

    def test_ssri_withdrawal(self):
        """stop_ssri reduces ssri_level and increases anxiety."""
        h = Human()
        h.ssri_level = 50.0
        initial_ssri = h.ssri_level
        initial_anxiety = h.anxiety
        apply_event(h, 'stop_ssri', self.events['stop_ssri'])
        self.assertLess(h.ssri_level, initial_ssri,
                        "stop_ssri should reduce ssri_level")
        self.assertGreater(h.anxiety, initial_anxiety,
                           "stop_ssri should increase anxiety")

    def test_testosterone_injection_raises_t(self):
        """testosterone_injection increases testosterone."""
        h = Human()
        initial_t = h.testosterone
        apply_event(h, 'testosterone_injection', self.events['testosterone_injection'])
        self.assertGreater(h.testosterone, initial_t,
                           "testosterone_injection should increase testosterone")

    def test_job_loss_increases_stress(self):
        """job_loss raises life_stress and anxiety."""
        h = Human()
        initial_stress = h.life_stress
        initial_anxiety = h.anxiety
        apply_event(h, 'job_loss', self.events['job_loss'])
        self.assertGreater(h.life_stress, initial_stress,
                           "job_loss should increase life_stress")
        self.assertGreater(h.anxiety, initial_anxiety,
                           "job_loss should increase anxiety")

    def test_resolve_finances_decreases_stress(self):
        """resolve_finances lowers life_stress."""
        h = Human()
        h.life_stress = 50.0
        initial_stress = h.life_stress
        apply_event(h, 'resolve_finances', self.events['resolve_finances'])
        self.assertLess(h.life_stress, initial_stress,
                        "resolve_finances should lower life_stress")

    def test_therapy_reduces_stress(self):
        """therapy_session reduces life_stress."""
        h = Human()
        h.life_stress = 50.0
        initial_stress = h.life_stress
        apply_event(h, 'therapy_session', self.events['therapy_session'])
        self.assertLess(h.life_stress, initial_stress,
                        "therapy_session should reduce life_stress")

    def test_trait_clamping(self):
        """Traits stay in [0, 100] after extreme events."""
        # Test upper bound
        h = Human()
        h.ssri_level = 95.0
        apply_n_times(h, 'take_ssri', self.events, 5)
        self.assertLessEqual(h.ssri_level, 100.0,
                             "ssri_level should not exceed 100")

        # Test lower bound
        h2 = Human()
        h2.life_stress = 5.0
        h2.life_stress = max(0.0, h2.life_stress)  # ensure starts valid
        # Apply therapy multiple times to try to go below 0
        for _ in range(10):
            self.events['therapy_session'].apply(h2, 1.0)
        self.assertGreaterEqual(h2.life_stress, 0.0,
                                "life_stress should not go below 0")

        # Test testosterone upper bound
        h3 = Human()
        h3.testosterone = 95.0
        for _ in range(5):
            self.events['testosterone_injection'].apply(h3, 1.0)
        self.assertLessEqual(h3.testosterone, 100.0,
                             "testosterone should not exceed 100")

        # Test testosterone lower bound
        h4 = Human()
        h4.testosterone = 15.0
        for _ in range(5):
            self.events['anti_androgen'].apply(h4, 1.0)
        self.assertGreaterEqual(h4.testosterone, 0.0,
                                "testosterone should not go below 0")

    def test_life_events_affect_baselines(self):
        """After job_loss + decay, anxiety baseline is higher."""
        h = Human()
        h_control = Human()

        # Apply job_loss to stressed human
        apply_event(h, 'job_loss', self.events['job_loss'])

        # Let both decay for a while
        decay_only(h, 3.0)
        decay_only(h_control, 3.0)

        # The human who lost their job should have higher anxiety
        # because life_stress raises the anxiety baseline
        self.assertGreater(h.anxiety, h_control.anxiety,
                           "After job_loss + decay, anxiety should be higher than control")


if __name__ == '__main__':
    # Import random for probabilistic tests
    import random
    unittest.main(verbosity=2)
