import { Human } from './human.js';

// Module-level flag for probabilistic outcomes (tests can toggle off)
export let ENABLE_PROBABILISTIC = true;

export function setEnableProbabilistic(v) {
  ENABLE_PROBABILISTIC = v;
}

export function getEnableProbabilistic() {
  return ENABLE_PROBABILISTIC;
}

// Pending notifications for UI — cleared each frame by drainNotifications()
let _pendingNotifications = [];

export function drainNotifications() {
  const n = _pendingNotifications.slice();
  _pendingNotifications = [];
  return n;
}

// =============================================================================
// BASELINE DECAY - Homeostasis
// =============================================================================

// Each parameter decays toward its baseline at a certain rate per hour
export const BASELINES = {
  dopamine: 50.0,
  oxytocin: 30.0,       // passive bonding, relaxation, diffuse pleasure
  endorphins: 20.0,
  serotonin: 50.0,
  prolactin: 10.0,      // low baseline, spikes after orgasm
  vasopressin: 20.0,    // active arousal, focus, intensity, dominance
  arousal: 20.0,
  prefrontal: 50.0,
  absorption: 30.0,     // baseline self-awareness (low absorption)
  sleepiness: 20.0,     // baseline alertness (low sleepiness)
  hunger: 50.0,         // hunger increases over time (baseline is "somewhat hungry")
  energy: 50.0,
  anxiety: 30.0,        // moderate baseline anxiety (correlates with cortisol)
};

// Decay rate: fraction of distance to baseline recovered per hour
export const DECAY_RATES = {
  dopamine: 0.15,       // relatively fast
  oxytocin: 0.10,       // medium
  endorphins: 0.20,     // fast decay
  serotonin: 0.05,      // slow, stable
  prolactin: 0.08,      // slow decay - refractory period lasts a while
  vasopressin: 0.15,    // moderate decay
  arousal: 0.25,        // fast without stimulation
  prefrontal: 0.10,     // medium
  sleepiness: 0.15,     // alertness returns gradually
  anxiety: 0.12,        // moderate decay toward baseline (cortisol half-life ~1h)
  absorption: 0.20,     // decays relatively fast without stimulation
};

// =============================================================================
// TOLERANCE & RESERVES - Physiological Realism
// =============================================================================

// How much tolerance increases per use of each category
export const TOLERANCE_GAINS = {
  sexual: 0.12,
  pain: 0.10,
  social: 0.06,
  breathwork: 0.08,
  food: 0.05,
  rest: 0.0,
  drugs: 0.15,
  medical: 0.0,
  life: 0.0,
};

// How fast tolerance decays per hour (toward 0)
export const TOLERANCE_DECAY_RATES = {
  sexual: 0.08,
  pain: 0.10,
  social: 0.12,
  breathwork: 0.10,
  food: 0.15,
  rest: 0.0,
  drugs: 0.04,
  medical: 0.0,
  life: 0.0,
};

// Reserve constants
export const RESERVE_REPLENISH_RATE = 5.0;    // per hour, for each NT
export const SLEEP_RESERVE_RESTORE = 40.0;    // how much reserves restore on sleep
export const SLEEP_TOLERANCE_REDUCE = 0.15;   // how much tolerance drops on sleep

// Sustained delivery constants
export const SUSTAINED_FRACTION = 0.4;        // 40% of boost delivered over time
export const SUSTAINED_DURATION = 0.25;       // hours
export const ORGASM_IMMEDIATE_FRACTION = 0.9; // orgasm is 90% immediate, 10% sustained

// =============================================================================
// OPPONENT PROCESS CONSTANTS
// =============================================================================

export const OPPONENT_PROCESS_THRESHOLD = 10;
export const OPPONENT_PROCESS_RATIO = 0.3;
export const OPPONENT_PROCESS_DELAY = 0.5;

// =============================================================================
// EFFECTIVE BASELINES (trait-modified)
// =============================================================================

/**
 * Return a per-human copy of BASELINES modified by traits (testosterone,
 * SSRI, life stress). Never mutates the shared BASELINES dict.
 * All values clamped to [0, 100].
 */
export function get_effective_baselines(human) {
  const eb = { ...BASELINES };
  const t_factor = human.testosterone / 50.0 - 1.0;  // -1 at T=0, 0 at T=50, +1 at T=100
  const ssri_pct = human.ssri_level / 100.0;
  const stress_pct = human.life_stress / 100.0;

  // Testosterone effects
  eb.arousal += t_factor * 5;
  eb.vasopressin += t_factor * 5;
  eb.anxiety -= t_factor * 5;

  // SSRI effects
  eb.serotonin += ssri_pct * 15;
  eb.prolactin += ssri_pct * 12;
  eb.anxiety -= ssri_pct * 10;
  eb.dopamine -= ssri_pct * 5;

  // Life stress effects
  eb.anxiety += stress_pct * 20;
  eb.absorption -= stress_pct * 8;

  // Clamp all to [0, 100]
  for (const k of Object.keys(eb)) {
    eb[k] = Math.max(0.0, Math.min(100.0, eb[k]));
  }

  return eb;
}

// =============================================================================
// HELPERS
// =============================================================================

function gaussRandom(mu, sigma) {
  const u = 1 - Math.random();
  const v = Math.random();
  const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  return mu + z * sigma;
}

/**
 * Apply a neurotransmitter boost with reserve scaling and sustained delivery.
 *
 * - Scales by reserve level (min 15% at reserve=0, 100% at reserve=100)
 * - Consumes reserves (0.5 reserve per point of boost)
 * - Splits immediate/sustained (60/40 normally, 90/10 for orgasm)
 * - Enqueues sustained portion in human.active_effects
 */
export function nt_boost(human, attr, raw_amount, is_orgasm = false) {
  if (raw_amount <= 0) return;

  // Map NT attr to reserve key
  const reserve_key = attr;  // dopamine, serotonin, endorphins, oxytocin
  if (!(reserve_key in human.reserves)) {
    // Not a tracked NT, apply directly
    human[attr] += raw_amount;
    return;
  }

  // Scale by reserve level: 15% minimum at 0, 100% at 100
  const reserve_level = human.reserves[reserve_key];
  const scale_factor = 0.15 + 0.85 * (reserve_level / 100.0);
  let scaled_amount = raw_amount * scale_factor;

  // SSRI dopamine capping: at max SSRI, dopamine boosts are 60% of normal
  if (attr === 'dopamine' && human.ssri_level > 0) {
    const ssri_pct = human.ssri_level / 100.0;
    scaled_amount *= (1 - ssri_pct * 0.4);
  }

  // Consume reserves (0.5 per point of boost), clamp to 0
  human.reserves[reserve_key] = Math.max(0, human.reserves[reserve_key] - raw_amount * 0.5);

  // Split immediate vs sustained
  const immediate_frac = is_orgasm ? ORGASM_IMMEDIATE_FRACTION : (1.0 - SUSTAINED_FRACTION);

  const immediate = scaled_amount * immediate_frac;
  const sustained = scaled_amount * (1.0 - immediate_frac);

  // Apply immediate portion
  human[attr] += immediate;

  // Enqueue sustained portion
  if (sustained > 0 && SUSTAINED_DURATION > 0) {
    const rate = sustained / SUSTAINED_DURATION;
    human.active_effects.push({
      attr,
      rate,
      remaining_hours: SUSTAINED_DURATION,
    });
  }

  // Opponent-process rebound: large boosts schedule a delayed negative rebound
  if (raw_amount > 10 && reserve_key in human.reserves) {
    const rebound_amount = scaled_amount * 0.3;
    human.rebound_queue.push({
      attr,
      amount: -rebound_amount,
      delay_remaining: 0.5,
      duration: 1.0,
    });
  }
}

/**
 * How receptive the human is to this category of event based on current state.
 * Returns -0.5 (backfire) to 1.0 (fully receptive).
 *
 * This is the "appraisal/gating" layer: determines whether an action lands well
 * or backfires. Magnitude effects are lighter here since pleasure_score() already
 * handles anxiety/absorption magnitude via Yerkes-Dodson and absorption factor.
 *
 * Positive range [0, 1]: gates how much of the event's benefits land.
 * Negative range [-0.5, 0): event backfires — triggers explicit aversive consequences.
 */
export function compute_receptivity(human, category) {
  let r = 1.0;

  if (category === 'sexual') {
    // High anxiety gates out sexual receptivity
    if (human.anxiety > 50) {
      r -= (human.anxiety - 50) / 50 * 1.2;
    }
    // Overthinking (high prefrontal) reduces receptivity
    if (human.prefrontal > 60) {
      r -= (human.prefrontal - 60) / 40 * 0.3;
    }
    // Existing arousal improves receptivity
    if (human.arousal > 20) {
      r += (human.arousal - 20) / 80 * 0.3;
    }
    // Absorption helps (being in the moment)
    if (human.absorption > 30) {
      r += (human.absorption - 30) / 70 * 0.2;
    }
    // DCM: Sexual Inhibition System (SIS) — the "brake", independent of anxiety.
    if (human.sexual_inhibition > 20) {
      r -= (human.sexual_inhibition - 20) / 80 * 0.8;
    }

  } else if (category === 'social') {
    // High anxiety makes socializing aversive
    if (human.anxiety > 50) {
      r -= (human.anxiety - 50) / 50 * 1.2;
    }
    // Low energy makes socializing draining
    if (human.energy < 25) {
      r -= (25 - human.energy) / 25 * 0.4;
    }
    // Existing oxytocin buffers anxiety penalty (feeling connected)
    if (human.oxytocin > 35) {
      r += (human.oxytocin - 35) / 65 * 0.4;
    }

  } else if (category === 'pain') {
    // Pain without arousal context is just pain
    if (human.arousal < 30) {
      r -= (30 - human.arousal) / 30 * 1.8;
    }
    // Absorption helps convert pain to pleasure (play/safety proxy)
    if (human.absorption > 40) {
      r += (human.absorption - 40) / 60 * 0.3;
    }
    // High anxiety makes pain threatening rather than playful
    if (human.anxiety > 55) {
      r -= (human.anxiety - 55) / 45 * 0.5;
    }

  } else if (category === 'breathwork') {
    // Very high anxiety can make breathwork counterproductive (panic)
    if (human.anxiety > 70) {
      r -= (human.anxiety - 70) / 30 * 0.5;
    }

  } else if (category === 'food') {
    // High anxiety reduces food enjoyment
    if (human.anxiety > 60) {
      r -= (human.anxiety - 60) / 40 * 0.3;
    }

  } else if (category === 'drugs') {
    // High anxiety + drugs can go wrong
    if (human.anxiety > 55) {
      r -= (human.anxiety - 55) / 45 * 0.5;
    }
    // Low psychological health makes drug experiences risky
    if (human.psychological_health < 40) {
      r -= (40 - human.psychological_health) / 40 * 0.4;
    }
  }

  // 'rest' category: always receptive (r stays 1.0)

  // Life stress penalty: hard to enjoy things when stressed (except rest)
  if (category !== 'rest') {
    const stress_pct = human.life_stress / 100.0;
    r -= stress_pct * 0.3;
  }

  // WoT: Shutdown (dorsal vagal) flattens receptivity for all categories.
  if (human.shutdown > 20) {
    r -= (human.shutdown - 20) / 80 * 0.6;
  }

  return Math.max(-0.5, Math.min(1.0, r));
}

/**
 * Explicit aversive consequences when an action backfires (negative receptivity).
 * severity is 0..0.5 (the absolute value of negative receptivity).
 */
export function apply_backfire(human, category, severity) {
  if (category === 'sexual') {
    // Unwanted sexual stimulation during panic → more anxiety, self-consciousness
    human.anxiety += severity * 20;
    human.absorption -= severity * 15;
    human.prefrontal += severity * 10;  // rumination, self-monitoring
    // DCM: failed sexual attempts strongly reinforce the SIS brake
    human.sexual_inhibition += severity * 30;

  } else if (category === 'social') {
    // Social interaction while panicking → social anxiety spiral
    human.anxiety += severity * 25;
    human.absorption -= severity * 10;
    human.prefrontal += severity * 15;  // overthinking, rumination
    human.psychological_health -= severity * 2;

  } else if (category === 'pain') {
    // Pain without arousal/play context → just hurts
    human.anxiety += severity * 20;
    human.physical_health -= severity * 3;
    human.absorption -= severity * 10;

  } else if (category === 'breathwork') {
    // Breathwork during extreme anxiety → hyperventilation panic
    human.anxiety += severity * 15;

  } else if (category === 'food') {
    // Eating while very anxious → nausea, discomfort
    human.anxiety += severity * 10;
    human.digesting += severity * 15;

  } else if (category === 'drugs') {
    // Bad trip / panic on drugs
    human.anxiety += severity * 30;
    human.psychological_health -= severity * 4;
    human.absorption -= severity * 15;
    // WoT: severe overwhelm can flip into dorsal shutdown (collapse after panic)
    human.shutdown += severity * 50;
  }
}

/**
 * Central wrapper that orchestrates tolerance, event application, and tolerance update.
 *
 * 1. Calculate effectiveness from tolerance (max 60% reduction at tolerance=1.0)
 * 2. Call event.apply(human, effectiveness)
 * 3. Update tolerance for the event's category
 */
export function apply_event(human, event_name, event) {
  const category = event.category;
  const tolerance = human.tolerance[category] ?? 0.0;

  // Tolerance: 1.0 at tolerance=0, 0.4 at tolerance=1.0
  const tolerance_factor = 1.0 - tolerance * 0.6;

  // Context receptivity: -0.5 to 1.0
  const receptivity = compute_receptivity(human, category);

  if (receptivity >= 0) {
    // Normal mode: gate benefits by receptivity and tolerance
    const effectiveness = tolerance_factor * receptivity;
    event.apply(human, effectiveness);
  } else {
    // Backfire mode: benefits don't land (eff=0), unscaled costs still apply,
    // plus explicit aversive consequences
    event.apply(human, 0);
    apply_backfire(human, category, Math.abs(receptivity));
  }

  // Update tolerance (builds regardless of whether experience was good or bad)
  const gain = TOLERANCE_GAINS[category] ?? 0.0;
  if (gain > 0) {
    human.tolerance[category] = Math.min(1.0, (human.tolerance[category] ?? 0.0) + gain);
  }

  // Cue learning: good experiences increase wanting, bad ones decrease it
  if (receptivity >= 0) {
    const salience_gain = gain * 0.5;
    human.cue_salience[category] = Math.min(1.0, (human.cue_salience[category] ?? 0.0) + salience_gain);
  } else {
    const salience_loss = Math.abs(receptivity) * 0.1;
    human.cue_salience[category] = Math.max(0.0, (human.cue_salience[category] ?? 0.0) - salience_loss);
  }

  // Apply cue-driven dopamine boost (wanting increases even as liking decreases)
  const cue_dopamine = (human.cue_salience[category] ?? 0.0) * 2;
  if (cue_dopamine > 0) {
    human.dopamine += cue_dopamine;
  }
}

// =============================================================================
// DECAY
// =============================================================================

/**
 * Apply homeostatic decay - values drift toward baseline.
 * dt is time in hours.
 */
export function apply_decay(human, dt) {
  // === HOMEOSTATIC DECAY with reserve-depressed baselines ===
  const effective_baselines = get_effective_baselines(human);
  for (const [attr, baseline] of Object.entries(effective_baselines)) {
    if (attr in DECAY_RATES) {
      const current = human[attr];
      const rate = DECAY_RATES[attr];

      // If this is a tracked NT reserve, depress baseline when reserves are low
      let effective_baseline = baseline;
      if (attr in human.reserves) {
        const reserve = human.reserves[attr];
        if (reserve < 100) {
          // At reserve=0, baseline drops to 60% of normal
          effective_baseline = baseline * (1.0 - (1.0 - reserve / 100.0) * 0.4);
        }
      }

      // Exponential decay toward (possibly depressed) baseline
      const new_value = current + (effective_baseline - current) * rate * dt;
      human[attr] = new_value;
    }
  }

  // Hunger increases over time (not decay, but drift)
  human.hunger += 3.0 * dt;  // get hungrier by 3 points per hour

  // Energy decreases over time when awake
  human.energy -= 2.0 * dt;  // lose 2 energy per hour when active

  // Life stress continuous effects
  if (human.life_stress > 0) {
    const stress_pct = human.life_stress / 100.0;
    human.absorption -= stress_pct * 2 * dt;        // absorption drain (-2/hr at max)
    human.psychological_health -= stress_pct * 0.5 * dt;  // psych health drain (-0.5/hr at max)
  }

  // Digestion effects: while digesting, sleepiness increases and arousal is suppressed
  if (human.digesting > 0) {
    // Digesting causes drowsiness (parasympathetic activation)
    human.sleepiness += human.digesting * 0.3 * dt;
    // Blood flow to gut reduces arousal capacity
    human.arousal -= human.digesting * 0.2 * dt;
    // Digestion fades over time
    human.digesting *= (1 - 0.4 * dt);  // ~40% decay per hour
    if (human.digesting < 1) {
      human.digesting = 0;
    }
  }

  // High sleepiness dampens arousal and prefrontal activity
  if (human.sleepiness > 40) {
    const sleepy_factor = (human.sleepiness - 40) / 60;  // 0 to 1
    human.arousal -= sleepy_factor * 5 * dt;
    human.prefrontal -= sleepy_factor * 3 * dt;
  }

  // Drowsiness disrupts sustained attention needed for absorption/flow
  if (human.sleepiness > 60) {
    const sleepy_absorb = (human.sleepiness - 60) / 40;  // 0 to 1
    human.absorption -= sleepy_absorb * 4 * dt;
  }

  // Track time since orgasm / exercise
  human.time_since_orgasm += dt;
  human.time_since_exercise += dt;

  // Edging buildup decays slowly
  human.edging_buildup *= (1 - 0.05 * dt);

  // === A. Process active_effects (sustained delivery) ===
  const remaining_effects = [];
  for (const effect of human.active_effects) {
    const delivery = effect.rate * dt;
    human[effect.attr] += delivery;
    effect.remaining_hours -= dt;
    if (effect.remaining_hours > 0) {
      remaining_effects.push(effect);
    }
  }
  human.active_effects = remaining_effects;

  // === A2. Process rebound queue (opponent-process) ===
  const remaining_rebounds = [];
  for (const rebound of human.rebound_queue) {
    if (rebound.delay_remaining > 0) {
      rebound.delay_remaining -= dt;
      remaining_rebounds.push(rebound);
    } else {
      const rate = rebound.amount / rebound.duration;
      const delivery = rate * dt;
      human[rebound.attr] += delivery;
      rebound.duration -= dt;
      if (rebound.duration > 0) {
        remaining_rebounds.push(rebound);
      }
    }
  }
  human.rebound_queue = remaining_rebounds;

  // === B. Tolerance decay ===
  for (const [category, decay_rate] of Object.entries(TOLERANCE_DECAY_RATES)) {
    if (decay_rate > 0 && category in human.tolerance) {
      human.tolerance[category] = Math.max(
        0.0,
        human.tolerance[category] - decay_rate * dt
      );
    }
  }

  // === B2. Cue salience decay (very slow - sensitization persists) ===
  for (const category of Object.keys(human.cue_salience)) {
    human.cue_salience[category] = Math.max(0.0, human.cue_salience[category] - 0.02 * dt);
  }

  // === C. Reserve replenishment ===
  for (const nt of Object.keys(human.reserves)) {
    human.reserves[nt] += RESERVE_REPLENISH_RATE * dt;
  }

  // Anxiety increases with unmet needs
  if (human.hunger > 50) {
    human.anxiety += (human.hunger - 50) * 0.05 * dt;
  }
  if (human.energy < 30) {
    human.anxiety += (30 - human.energy) * 0.05 * dt;
  }

  // High anxiety suppresses absorption (can't get into flow when anxious)
  if (human.anxiety > 50) {
    const anxiety_suppression = (human.anxiety - 50) / 50;  // 0 to 1
    human.absorption -= anxiety_suppression * 5 * dt;
  }

  // Low prefrontal facilitates absorption (hypofrontality = flow states)
  if (human.prefrontal < 40) {
    human.absorption += (40 - human.prefrontal) * 0.1 * dt;
  }

  // High arousal can increase absorption (getting lost in sensation)
  if (human.arousal > 60) {
    human.absorption += (human.arousal - 60) * 0.08 * dt;
  }

  // === PROLACTIN EFFECTS ===
  // High prolactin suppresses dopamine (post-orgasm refractory)
  if (human.prolactin > 20) {
    const prolactin_factor = (human.prolactin - 20) / 80;  // 0 to 1
    human.dopamine -= prolactin_factor * 8 * dt;   // suppresses dopamine
    human.arousal -= prolactin_factor * 10 * dt;   // suppresses arousal (refractory)
    human.sleepiness += prolactin_factor * 5 * dt; // causes sleepiness
  }

  // === VASOPRESSIN EFFECTS ===
  // High vasopressin increases focus and intensity but adds vigilance/tension
  if (human.vasopressin > 40) {
    const vaso_factor = (human.vasopressin - 40) / 60;  // 0 to 1
    human.prefrontal -= vaso_factor * 3 * dt;    // reduces analytical thinking
    human.absorption += vaso_factor * 3 * dt;    // increases focus/intensity
  }

  // High vasopressin adds slight anxiety (vigilance, tension)
  if (human.vasopressin > 50) {
    const vaso_tension = (human.vasopressin - 50) / 50;  // 0 to 1
    human.anxiety += vaso_tension * 2 * dt;
  }

  // === OXYTOCIN EFFECTS ===
  // High oxytocin promotes diffuse absorption (body immersion, safety)
  if (human.oxytocin > 40) {
    const oxy_factor = (human.oxytocin - 40) / 60;  // 0 to 1
    human.absorption += oxy_factor * 2 * dt;
  }

  // Vasopressin and oxytocin have opposing tendencies
  // High oxytocin tends to reduce vasopressin and vice versa (soft antagonism)
  if (human.oxytocin > 50 && human.vasopressin > 30) {
    human.vasopressin -= (human.oxytocin - 50) * 0.02 * dt;
  }
  if (human.vasopressin > 50 && human.oxytocin > 30) {
    human.oxytocin -= (human.vasopressin - 50) * 0.02 * dt;
  }

  // === SEROTONIN EFFECTS ===
  // High serotonin promotes wellbeing but also raises prolactin and suppresses dopamine
  if (human.serotonin > 60) {
    const sero_factor = (human.serotonin - 60) / 40;  // 0 to 1
    human.prolactin += sero_factor * 3 * dt;     // serotonin drives prolactin release
    human.dopamine -= sero_factor * 4 * dt;      // serotonin suppresses dopamine peaks
  }

  // === DCM: Sexual Inhibition System (SIS) decay ===
  if (human.arousal > 40 && human.prefrontal > 55) {
    const sis_build = ((human.arousal - 40) / 60) * ((human.prefrontal - 55) / 45);
    human.sexual_inhibition += sis_build * 5 * dt;
  }
  human.sexual_inhibition = Math.max(0.0, human.sexual_inhibition - 10 * dt);

  // === WoT: Shutdown (dorsal vagal) dynamics ===
  if (human.anxiety > 80 && human.energy < 25) {
    human.shutdown += (human.anxiety - 80) / 20 * 3 * dt;
  }
  // Shutdown suppresses absorption (flatness blocks immersion)
  if (human.shutdown > 30) {
    human.absorption -= (human.shutdown - 30) / 70 * 3 * dt;
  }
  // Shutdown decays slowly — can last hours without sleep
  human.shutdown = Math.max(0.0, human.shutdown - 6 * dt);

  // === D. Consequences of extreme states ===
  if (human.dopamine > 85) {
    human.psychological_health -= (human.dopamine - 85) * 0.1 * dt;
  }
  if (human.anxiety > 70) {
    human.psychological_health -= (human.anxiety - 70) * 0.1 * dt;
  }
  if (human.arousal > 90) {
    human.physical_health -= (human.arousal - 90) * 0.15 * dt;
  }
  if (human.absorption > 90) {
    human.psychological_health -= (human.absorption - 90) * 0.1 * dt;
  }
  if (human.energy < 15) {
    human.physical_health -= (15 - human.energy) * 0.1 * dt;
  }
  if (human.endorphins > 80) {
    human.physical_health -= (human.endorphins - 80) * 0.08 * dt;
  }
  // === E. Passive health regeneration ===
  // Physical health recovers slowly when basic needs are met
  if (human.hunger < 75 && human.energy > 20 && human.sleepiness < 75) {
    const regen = 1.0 - (human.hunger / 75) * 0.3 - ((75 - human.energy) / 55) * 0.3;
    human.physical_health += Math.max(0, regen) * dt;
  }
  // Psychological health recovers slowly when mind is calm
  if (human.anxiety < 55 && human.shutdown < 35) {
    const psych_regen = 0.8 * (1.0 - human.anxiety / 55 * 0.5);
    human.psychological_health += Math.max(0, psych_regen) * dt;
  }

  // Starvation: extreme hunger damages physical health
  if (human.hunger > 85) {
    human.physical_health -= (human.hunger - 85) / 15 * 5 * dt;
  }
  // Sleep deprivation: extreme sleepiness damages physical health
  if (human.sleepiness > 85) {
    human.physical_health -= (human.sleepiness - 85) / 15 * 3 * dt;
  }

  human.clamp_values();
}

// =============================================================================
// EVENTS
// =============================================================================

export class Event {
  /**
   * An event/action that can be applied to a Human.
   * apply takes (human, effectiveness) where effectiveness is 0.4-1.0.
   */
  constructor(name, duration, applyFn, category = 'rest', canApply = (_h) => true, description = '', blockedReason = '') {
    this.name = name;
    this.duration = duration;
    this.apply = applyFn;
    this.category = category;
    this.can_apply = canApply;
    this.description = description;
    this.blocked_reason = blockedReason;
    this.note = null; // optional (h) => string | null — shown as soft warning even when available
  }
}

/**
 * Create and return all available events.
 * Returns a plain object (dict) of event_name -> Event instance.
 */
export function make_events() {
  const events = {};

  // --- Basic needs ---

  function snack(h, eff = 1.0) {
    h.hunger -= 15;              // cost: not scaled
    h.digesting += 10;           // cost: not scaled
    h.energy += 2;               // cost: not scaled
    nt_boost(h, 'dopamine', 5 * eff);
    h.anxiety -= 3 * eff;
  }

  events['snack'] = new Event(
    'snack',
    0.1,
    snack,
    'food',
    (h) => h.hunger > 10,
    'Have a light snack',
    'not hungry'
  );

  function eat(h, eff = 1.0) {
    h.hunger -= 50;              // cost: not scaled
    h.digesting += 50;           // cost: not scaled
    h.sleepiness += 15;          // cost: not scaled
    h.arousal -= 10;             // cost: not scaled
    h.prefrontal -= 5;           // cost: not scaled
    h.energy += 5;               // cost: not scaled
    nt_boost(h, 'dopamine', 10 * eff);
    nt_boost(h, 'serotonin', 8 * eff);
    h.anxiety -= 10 * eff;
    h.absorption += 5 * eff;
  }

  events['eat'] = new Event(
    'eat',
    0.5,
    eat,
    'food',
    (h) => h.hunger > 25,
    'Eat a full meal (causes drowsiness)',
    'not hungry enough'
  );

  function sleep(h, eff = 1.0) {
    const eb = get_effective_baselines(h);
    h.energy += 35;
    h.hunger += 10;
    h.dopamine = eb['dopamine'];
    h.serotonin += 10;
    h.psychological_health += 2;
    h.arousal = 10;
    h.edging_buildup = 0;
    h.prefrontal = 60;
    h.sleepiness = 10;
    h.digesting = 0;
    h.anxiety = eb['anxiety'];
    h.absorption = eb['absorption'];
    h.prolactin = eb['prolactin'];
    h.vasopressin = eb['vasopressin'];
    // Sleep special: restore reserves and reduce tolerance
    for (const nt of Object.keys(h.reserves)) {
      h.reserves[nt] += SLEEP_RESERVE_RESTORE;
    }
    for (const cat of Object.keys(h.tolerance)) {
      h.tolerance[cat] = Math.max(0.0, h.tolerance[cat] - SLEEP_TOLERANCE_REDUCE);
    }
    // Clear active effects and rebounds
    h.active_effects = [];
    h.rebound_queue = [];
    // Sleep reduces cue salience slightly
    for (const cat of Object.keys(h.cue_salience)) {
      h.cue_salience[cat] = Math.max(0.0, h.cue_salience[cat] - 0.05);
    }
    // Sleep clears performance anxiety and partially resolves dorsal shutdown
    h.sexual_inhibition = 0.0;
    h.shutdown = Math.max(0.0, h.shutdown - 40.0);
  }

  events['sleep'] = new Event(
    'sleep',
    2.0,
    sleep,
    'rest',
    (h) => h.energy < 60 || h.sleepiness > 50,
    'Take a restful nap',
    'not tired enough'
  );

  // --- Sexual/arousal events ---

  function light_stimulation(h, eff = 1.0) {
    h.edging_buildup += 10;       // cost: not scaled
    h.energy -= 3;                // cost: not scaled
    h.prefrontal -= 5;            // cost: not scaled
    h.arousal += 15 * eff;
    nt_boost(h, 'dopamine', 10 * eff);
    h.anxiety -= 5 * eff;
    h.absorption += 10 * eff;
    h.vasopressin += 8 * eff;
  }

  events['light_stimulation'] = new Event(
    'light_stimulation',
    0.25,
    light_stimulation,
    'sexual',
    (_h) => true,
    'Light sexual stimulation, teasing'
  );

  // Forward declare orgasm for use in intense_stimulation and edging
  let orgasm;

  function intense_stimulation(h, eff = 1.0) {
    h.edging_buildup += 25;       // cost: not scaled
    h.energy -= 8;                // cost: not scaled
    h.prefrontal -= 15;           // cost: not scaled
    h.arousal += 30 * eff;
    nt_boost(h, 'dopamine', 20 * eff);
    nt_boost(h, 'endorphins', 10 * eff);
    h.anxiety -= 10 * eff;
    h.absorption += 20 * eff;
    h.vasopressin += 15 * eff;
    // Probabilistic: premature orgasm at high arousal
    if (ENABLE_PROBABILISTIC && h.arousal > 70 && Math.random() < 0.08) {
      orgasm(h, eff);
      _pendingNotifications.push({ text: 'unexpected release', type: 'orgasm' });
    }
  }

  events['intense_stimulation'] = new Event(
    'intense_stimulation',
    0.25,
    intense_stimulation,
    'sexual',
    (h) => h.arousal > 30,
    'Intense sexual stimulation',
    'need more arousal first'
  );

  function edging(h, eff = 1.0) {
    h.edging_buildup += 15;       // cost: not scaled
    h.energy -= 5;                // cost: not scaled
    h.prefrontal -= 10;           // cost: not scaled
    h.anxiety += 5;               // cost: tension from holding back
    h.arousal = Math.min(95, h.arousal + 10 * eff);
    nt_boost(h, 'dopamine', (15 + h.edging_buildup * 0.2) * eff);
    nt_boost(h, 'endorphins', 5 * eff);
    h.absorption += 15 * eff;
    h.vasopressin += 12 * eff;
    // Probabilistic: lose control at very high arousal
    if (ENABLE_PROBABILISTIC && h.arousal > 80 && Math.random() < 0.12) {
      orgasm(h, eff);
      _pendingNotifications.push({ text: "couldn't hold back", type: 'orgasm' });
    }
  }

  events['edging'] = new Event(
    'edging',
    0.25,
    edging,
    'sexual',
    (h) => h.arousal > 50,
    'Edge - maintain high arousal without release',
    'need higher arousal'
  );

  orgasm = function(h, eff = 1.0) {
    /**
     * Release - brief spike then CRASH.
     * Orgasm character depends on vasopressin vs oxytocin balance.
     * Prolactin surge and dopamine crash are NOT scaled (they are costs).
     */
    const bonus = h.edging_buildup * 0.3;

    const vaso_oxy_ratio = h.vasopressin / Math.max(h.oxytocin, 10);

    // The spike - NT boosts use is_orgasm=true for 90% immediate
    nt_boost(h, 'endorphins', (50 + bonus) * eff, true);

    if (vaso_oxy_ratio > 1) {
      h.vasopressin += 20 * eff;
      nt_boost(h, 'oxytocin', 25 * eff, true);
      nt_boost(h, 'dopamine', 10 * eff, true);
    } else {
      nt_boost(h, 'oxytocin', 45 * eff, true);
      h.vasopressin += 5 * eff;
      nt_boost(h, 'serotonin', 5 * eff, true);
    }

    // COSTS - NOT scaled by effectiveness
    const prolactin_surge = 50 + h.edging_buildup * 0.3;
    h.prolactin += prolactin_surge;
    h.dopamine = Math.max(25, h.dopamine * 0.5);

    // Post-orgasm state (costs)
    h.arousal = 5;
    h.energy -= 20;
    h.prefrontal = 25;
    h.sleepiness += 15 + prolactin_surge * 0.1;
    nt_boost(h, 'serotonin', 10 * eff, true);

    h.anxiety = Math.max(5, h.anxiety - 30 * eff);
    h.absorption = Math.min(100, h.absorption + 25 * eff);

    h.time_since_orgasm = 0;
    h.edging_buildup = 0;
  };

  function can_orgasm(h) {
    return h.arousal > 70 && h.prolactin < 30;
  }

  events['orgasm'] = new Event(
    'orgasm',
    0.1,
    orgasm,
    'sexual',
    can_orgasm,
    'Orgasm - character depends on vasopressin/oxytocin balance',
    (h) => h.prolactin >= 30 ? 'refractory period (prolactin high)' : 'need more arousal'
  );

  // Sexual inhibition/SSRI notes — shown as soft warnings in the action list
  const _sexualNote = (h) => {
    const parts = [];
    if (h.ssri_level > 20) parts.push(`SSRIs dulling arousal & dopamine response`);
    if (h.sexual_inhibition > 40) parts.push(`inhibition dampening response`);
    return parts.length ? parts.join(' · ') : null;
  };
  events['light_stimulation'].note  = _sexualNote;
  events['intense_stimulation'].note = _sexualNote;
  events['edging'].note             = _sexualNote;
  events['orgasm'].note             = _sexualNote;

  // --- Pain/adrenaline (small doses enhance pleasure) ---

  function light_pain(h, eff = 1.0) {
    h.prefrontal -= 5;            // cost: not scaled
    h.anxiety += 3;               // cost: brief startle
    nt_boost(h, 'endorphins', 20 * eff);
    nt_boost(h, 'dopamine', 8 * eff);
    h.arousal += 10 * eff;
    h.absorption += 15 * eff;
    h.vasopressin += 12 * eff;
  }

  events['light_pain'] = new Event(
    'light_pain',
    0.1,
    light_pain,
    'pain',
    (_h) => true,
    'Light pain stimulus (spanking, pinching)'
  );

  function temperature_play(h, eff = 1.0) {
    h.prefrontal -= 8;            // cost: not scaled
    h.anxiety += 3;               // cost: brief startle
    nt_boost(h, 'endorphins', 15 * eff);
    nt_boost(h, 'dopamine', 5 * eff);
    h.arousal += 8 * eff;
    h.absorption += 12 * eff;
    h.vasopressin += 10 * eff;
  }

  events['temperature_play'] = new Event(
    'temperature_play',
    0.1,
    temperature_play,
    'pain',
    (_h) => true,
    'Temperature play (ice, heat)'
  );

  // --- Social/bonding ---

  function cuddling(h, eff = 1.0) {
    h.prefrontal -= 5;            // cost: not scaled
    nt_boost(h, 'oxytocin', 25 * eff);
    nt_boost(h, 'serotonin', 10 * eff);
    h.psychological_health += 1 * eff;
    h.arousal += 5 * eff;
    h.anxiety -= 15 * eff;
    h.absorption += 10 * eff;
    h.vasopressin -= 8 * eff;
  }

  events['cuddling'] = new Event(
    'cuddling',
    0.5,
    cuddling,
    'social',
    (_h) => true,
    'Intimate cuddling and touch'
  );

  function massage(h, eff = 1.0) {
    h.prefrontal -= 10;           // cost: not scaled
    nt_boost(h, 'oxytocin', 15 * eff);
    nt_boost(h, 'endorphins', 12 * eff);
    nt_boost(h, 'serotonin', 8 * eff);
    h.energy += 5;
    h.physical_health += 1 * eff;
    h.anxiety -= 20 * eff;
    h.absorption += 15 * eff;
    h.vasopressin -= 10 * eff;
  }

  events['massage'] = new Event(
    'massage',
    0.5,
    massage,
    'social',
    (_h) => true,
    'Receive a relaxing massage'
  );

  // --- Breathwork/altered states ---

  function deep_breathing(h, eff = 1.0) {
    h.prefrontal -= 10;           // cost: not scaled
    nt_boost(h, 'serotonin', 8 * eff);
    h.psychological_health += 1 * eff;
    h.energy += 3;
    h.anxiety -= 15 * eff;
    h.absorption += 8 * eff;
  }

  events['deep_breathing'] = new Event(
    'deep_breathing',
    0.25,
    deep_breathing,
    'breathwork',
    (_h) => true,
    'Deep, slow breathing exercises'
  );

  function cold_face_immersion(h, eff = 1.0) {
    h.anxiety += 5;               // cost: cold shock startle
    h.energy -= 3;                // cost: not scaled
    h.arousal -= 15 * eff;        // bradycardia, strong parasympathetic override
    h.prefrontal -= 10;           // cost: not scaled
    nt_boost(h, 'endorphins', 12 * eff);  // cold shock endorphin release
    nt_boost(h, 'serotonin', 5 * eff);
    h.anxiety -= 12 * eff;        // net calming after initial shock
    h.absorption += 5 * eff;
    h.sleepiness -= 10 * eff;     // alerting effect from cold
  }

  events['cold_face_immersion'] = new Event(
    'cold_face_immersion',
    0.05,
    cold_face_immersion,
    'breathwork',
    (h) => h.energy > 10,
    'Cold water face immersion - mammalian dive reflex',
    'too exhausted'
  );

  function holotropic_breathing(h, eff = 1.0) {
    h.energy -= 10;               // cost: not scaled
    h.prefrontal -= 25;           // cost: not scaled
    nt_boost(h, 'endorphins', 25 * eff);
    nt_boost(h, 'dopamine', 15 * eff);
    h.arousal += 15 * eff;
    h.anxiety -= 10 * eff;
    h.absorption += 30 * eff;
    h.vasopressin += 10 * eff;
    nt_boost(h, 'oxytocin', 10 * eff);
  }

  events['holotropic_breathing'] = new Event(
    'holotropic_breathing',
    0.5,
    holotropic_breathing,
    'breathwork',
    (h) => h.energy > 30,
    'Intense holotropic breathwork',
    'need more energy'
  );

  // --- Rest/recovery ---

  function rest(h, eff = 1.0) {
    h.energy += 5;
    h.prefrontal += 5;
    h.anxiety -= 5;
    h.absorption -= 5;
  }

  events['rest'] = new Event(
    'rest',
    0.25,
    rest,
    'rest',
    (_h) => true,
    'Rest quietly'
  );

  function wait(h, eff = 1.0) {
    h.energy += 2;
    h.anxiety += 3;
    h.absorption -= 3;
  }

  events['wait'] = new Event(
    'wait',
    0.25,
    wait,
    'rest',
    (_h) => true,
    'Wait, do nothing'
  );

  // --- Recreational drugs ---

  function mdma(h, eff = 1.0) {
    h.energy -= 25;               // cost: not scaled
    h.prefrontal -= 30;           // cost: not scaled
    nt_boost(h, 'serotonin', 40 * eff);
    nt_boost(h, 'oxytocin', 35 * eff);
    nt_boost(h, 'dopamine', 25 * eff);
    nt_boost(h, 'endorphins', 20 * eff);
    h.anxiety -= 30 * eff;
    // Probabilistic: overwhelming experience
    if (ENABLE_PROBABILISTIC && Math.random() < 0.05) {
      h.anxiety += 30;
      h.physical_health -= 5;
      _pendingNotifications.push({ text: 'too much, too fast', type: 'overwhelm' });
    }
  }

  events['mdma'] = new Event(
    'mdma',
    3.0,
    mdma,
    'drugs',
    (h) => h.energy > 30,
    'MDMA - empathogenic serotonin/oxytocin release',
    'need more energy (costs 25)'
  );

  function weed(h, eff = 1.0) {
    h.energy -= 5;                // cost: not scaled
    h.prefrontal -= 20;           // cost: not scaled
    h.hunger += 25;               // cost: munchies
    h.sleepiness += 15;           // cost: sedation
    nt_boost(h, 'dopamine', 15 * eff);
    h.absorption += 25 * eff;
    h.anxiety -= 20 * eff;
  }

  events['weed'] = new Event(
    'weed',
    2.0,
    weed,
    'drugs',
    (h) => h.energy > 20,
    'Cannabis - relaxation, absorption, munchies',
    'need more energy'
  );

  function mushrooms(h, eff = 1.0) {
    h.energy -= 10;               // cost: not scaled
    h.prefrontal -= 35;           // cost: not scaled
    h.anxiety += 15;              // cost: come-up anxiety
    h.absorption += 40 * eff;
    nt_boost(h, 'endorphins', 20 * eff);
    nt_boost(h, 'serotonin', 15 * eff);
    nt_boost(h, 'dopamine', 10 * eff);
    // Probabilistic: bad trip
    if (ENABLE_PROBABILISTIC && Math.random() < 0.15) {
      h.anxiety += 40;
      h.absorption = 10;
      h.prefrontal += 20;
      _pendingNotifications.push({ text: 'bad trip', type: 'bad-trip' });
    }
  }

  events['mushrooms'] = new Event(
    'mushrooms',
    4.0,
    mushrooms,
    'drugs',
    (h) => h.energy > 30,
    'Psilocybin - deep absorption, risk of bad trip',
    'need more energy (costs 10)'
  );

  function lsd(h, eff = 1.0) {
    h.energy -= 15;               // cost: not scaled
    h.prefrontal -= 40;           // cost: not scaled
    h.anxiety += 20;              // cost: come-up anxiety
    h.sleepiness -= 20;           // can't sleep on acid
    h.absorption += 45 * eff;
    nt_boost(h, 'dopamine', 15 * eff);
    nt_boost(h, 'serotonin', 10 * eff);
    nt_boost(h, 'endorphins', 15 * eff);
    // Probabilistic: bad trip
    if (ENABLE_PROBABILISTIC && Math.random() < 0.10) {
      h.anxiety += 40;
      h.absorption = 10;
      h.prefrontal += 20;
      _pendingNotifications.push({ text: 'bad trip', type: 'bad-trip' });
    }
  }

  events['lsd'] = new Event(
    'lsd',
    6.0,
    lsd,
    'drugs',
    (h) => h.energy > 30,
    'LSD - long absorption boost, risk of bad trip',
    'need more energy (costs 15)'
  );

  function poppers(h, eff = 1.0) {
    h.prefrontal -= 25;           // cost: not scaled
    h.energy -= 3;                // cost: not scaled
    h.physical_health -= 2;       // cost: not scaled
    h.arousal += 25 * eff;
    h.absorption += 20 * eff;
    h.vasopressin += 15 * eff;
  }

  events['poppers'] = new Event(
    'poppers',
    0.05,
    poppers,
    'drugs',
    (h) => h.energy > 20,
    'Poppers - brief vasodilation, arousal spike',
    'need more energy'
  );

  function ketamine(h, eff = 1.0) {
    h.prefrontal -= 40;           // cost: not scaled
    h.energy -= 10;               // cost: not scaled
    h.sleepiness += 15;           // cost: sedation
    h.arousal -= 15;              // cost: dissociation suppresses arousal
    h.absorption += 35 * eff;
    nt_boost(h, 'endorphins', 25 * eff);
    nt_boost(h, 'dopamine', 10 * eff);
    h.anxiety -= 20 * eff;
  }

  events['ketamine'] = new Event(
    'ketamine',
    1.0,
    ketamine,
    'drugs',
    (h) => h.energy > 20,
    'Ketamine - dissociative, absorption, pain relief',
    'need more energy'
  );

  function tobacco(h, eff = 1.0) {
    h.physical_health -= 1;       // cost: not scaled
    nt_boost(h, 'dopamine', 8 * eff);
    h.arousal += 5 * eff;
    h.anxiety -= 8 * eff;
    h.energy += 3;
  }

  events['tobacco'] = new Event(
    'tobacco',
    0.1,
    tobacco,
    'drugs',
    (h) => h.energy > 20,
    'Tobacco - mild stimulant, brief anxiety relief',
    'need more energy'
  );

  function caffeine(h, eff = 1.0) {
    h.anxiety += 10;              // cost: jitteriness
    nt_boost(h, 'dopamine', 8 * eff);
    h.arousal += 10 * eff;
    h.sleepiness -= 25 * eff;
    h.energy += 10;
    h.prefrontal += 10 * eff;
  }

  events['caffeine'] = new Event(
    'caffeine',
    2.0,
    caffeine,
    'drugs',
    (_h) => true,
    'Caffeine - alertness, wakefulness'
  );

  function alcohol(h, eff = 1.0) {
    h.prefrontal -= 25;           // cost: not scaled
    h.energy -= 10;               // cost: not scaled
    h.sleepiness += 15;           // cost: sedation
    h.physical_health -= 2;       // cost: not scaled
    nt_boost(h, 'dopamine', 15 * eff);
    h.anxiety -= 25 * eff;
    h.absorption += 10 * eff;
    h.arousal += 10 * eff;
    // Probabilistic: vomiting at high arousal
    if (ENABLE_PROBABILISTIC && h.arousal > 60 && Math.random() < 0.10) {
      h.hunger += 20;
      h.energy -= 10;
      h.digesting = 0;
      _pendingNotifications.push({ text: 'sick...', type: 'sick' });
    }
  }

  events['alcohol'] = new Event(
    'alcohol',
    1.5,
    alcohol,
    'drugs',
    (h) => h.energy > 15,
    'Alcohol - anxiolytic, disinhibition',
    'need more energy'
  );

  function amphetamines(h, eff = 1.0) {
    h.anxiety += 20;              // cost: not scaled
    h.physical_health -= 3;       // cost: not scaled
    h.hunger -= 20;               // appetite suppression
    h.sleepiness -= 30;           // can't sleep
    nt_boost(h, 'dopamine', 35 * eff);
    h.arousal += 25 * eff;
    h.energy += 20;
    h.prefrontal += 10 * eff;
  }

  events['amphetamines'] = new Event(
    'amphetamines',
    4.0,
    amphetamines,
    'drugs',
    (h) => h.energy > 20,
    'Amphetamines - strong stimulant, dopamine surge',
    'need more energy'
  );

  function cocaine(h, eff = 1.0) {
    h.anxiety += 15;              // cost: not scaled
    h.prefrontal -= 10;           // cost: not scaled
    h.physical_health -= 3;       // cost: not scaled
    nt_boost(h, 'dopamine', 45 * eff);
    h.arousal += 20 * eff;
    h.energy += 15;
    // Probabilistic: anxiety spike
    if (ENABLE_PROBABILISTIC && Math.random() < 0.08) {
      h.anxiety += 35;
      _pendingNotifications.push({ text: 'heart racing', type: 'anxiety' });
    }
  }

  events['cocaine'] = new Event(
    'cocaine',
    0.5,
    cocaine,
    'drugs',
    (h) => h.energy > 20,
    'Cocaine - intense short dopamine spike, harsh crash',
    'need more energy'
  );

  function nitrous(h, eff = 1.0) {
    h.prefrontal -= 20;           // cost: not scaled
    h.energy -= 2;                // cost: not scaled
    h.physical_health -= 2;       // cost: oxygen deprivation
    nt_boost(h, 'endorphins', 20 * eff);
    h.absorption += 25 * eff;
  }

  events['nitrous'] = new Event(
    'nitrous',
    0.05,
    nitrous,
    'drugs',
    (h) => h.energy > 20,
    'Nitrous oxide - brief euphoria, dissociation',
    'need more energy'
  );

  // --- Medical events ---

  function take_ssri(h, eff = 1.0) {
    h.ssri_level += 8;
    h.serotonin += 3 * eff;
    h.anxiety += 5;  // early side effect: nausea
    h.ssri_level = Math.max(0.0, Math.min(100.0, h.ssri_level));
    _pendingNotifications.push({ text: 'serotonin rising — dopamine & sexual response will be blunted', type: 'ssri' });
  }

  events['take_ssri'] = new Event(
    'take_ssri',
    0.1,
    take_ssri,
    'medical',
    (_h) => true,
    'Take SSRI medication'
  );

  function stop_ssri(h, eff = 1.0) {
    h.ssri_level -= 12;
    h.anxiety += 10;
    h.serotonin -= 5;
    h.ssri_level = Math.max(0.0, Math.min(100.0, h.ssri_level));
    _pendingNotifications.push({ text: 'withdrawal — serotonin crashes, anxiety spikes', type: 'ssri-stop' });
  }

  events['stop_ssri'] = new Event(
    'stop_ssri',
    0.1,
    stop_ssri,
    'medical',
    (h) => h.ssri_level > 10,
    'Stop SSRI medication (withdrawal)',
    'not on SSRIs'
  );

  function testosterone_injection(h, eff = 1.0) {
    h.testosterone += 10;
    h.energy += 5;
    h.arousal += 5 * eff;
    h.anxiety += 3;  // injection stress
    h.testosterone = Math.max(0.0, Math.min(100.0, h.testosterone));
  }

  events['testosterone_injection'] = new Event(
    'testosterone_injection',
    0.25,
    testosterone_injection,
    'medical',
    (_h) => true,
    'Testosterone injection'
  );

  function anti_androgen(h, eff = 1.0) {
    h.testosterone -= 10;
    h.anxiety -= 3;
    h.arousal -= 5;
    h.testosterone = Math.max(0.0, Math.min(100.0, h.testosterone));
  }

  events['anti_androgen'] = new Event(
    'anti_androgen',
    0.1,
    anti_androgen,
    'medical',
    (h) => h.testosterone > 10,
    'Anti-androgen medication',
    'testosterone already low'
  );

  function therapy_session(h, eff = 1.0) {
    h.life_stress -= 8;
    h.psychological_health += 3;
    h.anxiety -= 10;
    h.prefrontal += 10;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'prefrontal strengthening — anxiety baseline and life stress easing', type: 'life-good' });
  }

  events['therapy_session'] = new Event(
    'therapy_session',
    1.0,
    therapy_session,
    'medical',
    (_h) => true,
    'Therapy session'
  );

  // --- Exercise ---

  function exercise(h, eff = 1.0) {
    h.energy -= 20;               // cost: not scaled — takes effort
    h.hunger += 20;               // cost: burns calories
    h.sleepiness += 10;           // cost: tires you out
    h.physical_health += 8 * eff;
    nt_boost(h, 'endorphins', 20 * eff);
    nt_boost(h, 'dopamine', 10 * eff);
    nt_boost(h, 'serotonin', 8 * eff);
    h.anxiety -= 15 * eff;
    h.arousal += 8 * eff;
    h.time_since_exercise = 0;
    _pendingNotifications.push({ text: 'endorphin rush — physical health improving', type: 'life-good' });
  }

  events['exercise'] = new Event(
    'exercise',
    1.0,
    exercise,
    'life',
    (h) => h.energy > 25 && h.time_since_exercise >= 24,
    'Exercise — endorphins, physical health boost (once per day)',
    (h) => h.time_since_exercise < 24
      ? `need to rest (${Math.ceil(24 - h.time_since_exercise)}h cooldown)`
      : 'need more energy (costs 20)'
  );

  // --- Life events ---

  function job_loss(h, eff = 1.0) {
    h.life_stress += 25;
    h.anxiety += 20;
    h.psychological_health -= 5;
    h.energy -= 10;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'stress+25 — serotonin & dopamine baselines drop, libido suppressed', type: 'life-bad' });
  }

  events['job_loss'] = new Event(
    'job_loss',
    0.5,
    job_loss,
    'life',
    (h) => h.life_stress < 80,
    'Job loss',
    'already too stressed'
  );

  function financial_crisis(h, eff = 1.0) {
    h.life_stress += 30;
    h.anxiety += 25;
    h.psychological_health -= 8;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'stress+30 — chronic anxiety builds, hedonic capacity blunted', type: 'life-bad' });
  }

  events['financial_crisis'] = new Event(
    'financial_crisis',
    0.5,
    financial_crisis,
    'life',
    (h) => h.life_stress < 85,
    'Financial crisis',
    'already too stressed'
  );

  function breakup(h, eff = 1.0) {
    h.life_stress += 20;
    h.anxiety += 15;
    h.oxytocin -= 15;
    h.psychological_health -= 10;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'oxytocin crashes — bonding circuits deprived, low mood incoming', type: 'life-bad' });
  }

  events['breakup'] = new Event(
    'breakup',
    1.0,
    breakup,
    'life',
    (_h) => true,
    'Breakup'
  );

  function get_job(h, eff = 1.0) {
    h.life_stress -= 20;
    h.anxiety -= 10;
    nt_boost(h, 'dopamine', 10 * eff);
    h.psychological_health += 3;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'stress−20 — dopamine & serotonin baselines recovering', type: 'life-good' });
  }

  events['get_job'] = new Event(
    'get_job',
    0.5,
    get_job,
    'life',
    (h) => h.life_stress > 15,
    'Get a new job',
    'life stress already low'
  );

  function resolve_finances(h, eff = 1.0) {
    h.life_stress -= 15;
    h.anxiety -= 8;
    h.psychological_health += 2;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'stress−15 — chronic anxiety easing, energy floor rising', type: 'life-good' });
  }

  events['resolve_finances'] = new Event(
    'resolve_finances',
    0.5,
    resolve_finances,
    'life',
    (h) => h.life_stress > 10,
    'Resolve financial issues',
    'no financial stress to resolve'
  );

  function new_relationship(h, eff = 1.0) {
    h.life_stress -= 10;
    nt_boost(h, 'oxytocin', 20 * eff);
    nt_boost(h, 'dopamine', 15 * eff);
    h.anxiety -= 5;
    h.psychological_health += 5;
    h.life_stress = Math.max(0.0, Math.min(100.0, h.life_stress));
    _pendingNotifications.push({ text: 'oxytocin & dopamine surge — bonding circuits activated', type: 'life-good' });
  }

  events['new_relationship'] = new Event(
    'new_relationship',
    1.0,
    new_relationship,
    'life',
    (_h) => true,
    'New relationship'
  );

  return events;
}
