# tamagotchi-hedonista

tamagotchi-hedonista is a small simulation framework for modeling limbic and affective dynamics under abstract human actions.

It treats actions like “jerking off”, “going to a party”, “losing your job”, or “receiving light pain” not as narrative events, but as perturbations to a physiological–affective system that evolves over time.

## What is this for?

The main use case is to explore how **sequences of actions** (not single actions) shape subjective experience over time.

Instead of asking “is this action good or bad?”, the simulator asks:

- What happens if you do this for 3 hours?
- How do pleasure, exhaustion, rebound, and recovery interact?
- Why do some combinations feel unexpectedly intense or unexpectedly empty?

## What this is NOT

- Not a realistic neuroscience or medical model
- Not a therapy or self-help tool
- Not a porn simulator
- Not a moral system of “healthy vs unhealthy”
- Not an autonomous AI agent with goals or beliefs

The simulator does not decide what to do.
The user does.

## Que es?

Algunas ideas posibles

- primera persona? Algun personaje generico tipo don satur/sonic/...
- monstruo? frankenstein? zombie? egregore? demon? sucubus? homunculo?
- fantasma?
- vampiro?
- esclavo
- robot humanoide
- animal humanoide
- alien humanoide
- pokemon

## Tests as axioms

The project is heavily test-driven.

El proyecto tiene tests en `test.py` para facilitar chequear que se cumplan ciertos comportamientos o invariantes.

Tests are not just for correctness, but encode **conceptual invariants** such as:

- No single action can be repeated forever without diminishing returns
- Fast pleasure produces delayed cost
- Arousal can be misattributed across domains
- Moderate anxiety can amplify pleasure (Yerkes–Dodson)
- Absorption is fragile under anxiety and sleepiness

If a refactor breaks a test, it means a theory was violated.

## Design principles

- Prefer dynamics over realism
- Prefer few expressive variables over many precise ones
- Pleasure is temporal, not instantaneous
- Valence can mix (pain, fear, guilt can amplify pleasure)
- Rest and recovery are first-class mechanics

### Some keywords and sentences

- Unlike The Sims or Disco Elysium, this is not a story about a person — it is a playable model of the forces that make experiences feel good, bad, or overwhelming over time.

- physiological sandbox
- affect simulator

## Decisiones de diseño

- Las acciones son secuenciales, no se pueden componer y hacer en paralelo. Si fuera de interes explorar esa interaccion, por ejemplo "consumir marihuana en un tanque de flotacion" o "penetrasion anal mientras se hace deepthroat" entonces se debe crear una accion nueva que contenga las dos juntas
- No se modelan mecanismos de inferencia de affect se modelan de forma explicita en acciones, por ejemplo "recibir un abrazo de un amigo" se asume por default positivo y que genera un juicio positivo y una experiencia de placer. Aunque se pueden modelar mecanicas donde cosas como el cortisol afecten esas acciones, que ciertas acciones cambien de polaridad cuento el cortisol esta alto y el prefrontal cortes esta muy activo o cosas asi (no hay tiempo de sentir placer si estas preocupado por algo) o por ejemplo cuando estas muy caliente, todo se convierte en placer y algo sexual, incluso dolor, insultos y demas.
- Las animaciones y el personaje tienen ciertas animaciones pero son predefinidas, siempre mas o menos iguales, esta en una habitacion, no puede moverse de ahi, no hay un espacio caminable o algo asi
- No se modelan los detalles fisicos del mundo, como se mueve el personaje o cosas asi. El foco esta en abstraer acciones en el mundo como algo que se da por sentado que se puede lograr de hacer y abstraer fisiologia de bajo nivel del cuerpo como modulos a grandes rasgos (niveles de neurotransmisores, sistema digestivo, prefrontal cortex, atencion, arousal, ...) y modelar como 
- Los modelos no tienen motivaciones, no toman decisiones, el usuario las toma por ellos
- El objetivo es mantener lo mas simple posible un simulador que logra capturar dinamicas sobre como distintas acciones afectan a la gente en terminos de cuan bien la pasan
    - dinamicas donde no es todo tan simple como "acciones buenas y malas" sino que emergen patrones complejos como pasa en el bdsm donde se consigue placer y extasis mezclando valencias

- El sistema se entiende como dos subsistemas
    - Backend
        - Tiene todas las reglas logicas del sistema. Crea instancia de personaje dadas unas variables metas y la clase humano y actions
        - Aplica las actions y actualiza el estado del personaje
    - Frontend
        - Sitio web que muestra de forma visual y sonora como esta el personaje
            - Hay animaciones y sonidos para cada accion. Quizas eventualmente pueden ir cambiando
            - El personaje es algo tierno que atrapa. Quizas eventualmente se podria personalizar?

## Project structure

```
repo/
├── readme.md
├── internal-logic/       # Simulation engine (pure Python, no dependencies)
│   ├── human.py          # Human dataclass: neurotransmitters, state variables, scores
│   ├── events.py         # All events/actions + decay, tolerance, receptivity logic
│   ├── simulation.py     # Simulation runner utility
│   └── tests.py          # Axiom-based test suite (run: python tests.py)
└── ui/                   # Web interface
    ├── app.py            # Flask server — imports internal-logic, exposes REST API
    ├── requirements.txt  # flask, Pillow
    ├── generate_placeholders.py  # Creates mock avatar/background images
    ├── templates/
    │   └── index.html    # Single-page mobile-first UI
    └── static/
        ├── style.css     # Layout, animations (shake/sway/bounce/droop/...)
        ├── main.js       # UI logic + Tone.js procedural audio
        ├── avatar/       # base.png + expr_*.png (replace with your art)
        └── backgrounds/  # category/action background images (replace with your art)
```

## Running the UI

```bash
cd ui
pip install -r requirements.txt
python generate_placeholders.py   # only needed once, or after adding new backgrounds
python app.py                     # serves at http://localhost:5000
```

Also accessible from a phone on the same network at `http://<your-local-ip>:5000`.

## UI overview

The interface is split into two areas:

**Top (avatar section):** a layered PNG avatar whose expression and animation reflect the current state — anxious states trigger a shake animation, sleepiness causes a drooping slow bob, high liking triggers a bounce or sway. A HUD in the corner shows liking, anxiety, energy, and arousal as small bars. The background image fades to match the last action taken.

**Bottom (controls):** a search bar, a category grid (sexual / social / pain / breathwork / food / rest / drugs / medical / life), and a recent-actions strip. Tapping a category drills into its action list; the search bar filters across all actions in real time.

**Audio:** Tone.js procedural ambient pads (slow attack/release, no arpeggios). The chord progression, BPM, low-pass filter cutoff, distortion, and reverb wetness all modulate continuously from the current state — sleepiness muffles and slows everything, anxiety adds distortion and speeds the chord changes, shutdown collapses to near silence with heavy reverb. A short SFX tone plays on each action.

## Replacing placeholder assets

- `ui/static/avatar/base.png` — body silhouette, no expression, transparent background
- `ui/static/avatar/expr_<name>.png` — expression overlays: `neutral`, `happy`, `ecstatic`, `sad`, `anxious`, `sleepy`, `blank`
- `ui/static/backgrounds/<key>.jpg` — one per category (`sexual`, `social`, `pain`, `breathwork`, `food`, `rest`, `sleep`, `drugs`, `medical`, `life`, `default`). Add per-action overrides by mapping action names in `ACTION_BG` in `main.js`.

## Ideas a futuro

Si se inicializa un sistema basico con muchos agentes en un espacio 2D y se implementan dinamicas como
- emotional contagion (influencia sobre emociones de agentes cercanos)
- arousal synchronization
- mismatch dynamics
- oxytocin/vasopressin cross coupling (dominacion/sumision? Leary Circuit 2 and 4: Emotional-Territorial and Attachment & social identity mind spaces?)

## References

### Related projects

- https://github.com/labsensacional/emotions2json
- https://github.com/labsensacional/awesome-psiconautica
- https://docs.google.com/spreadsheets/d/1s9trDSetQ5hrr_zyj3EGdeczWDgy_0nUTfji4pLOaCQ/

- Tamagotchi
- The Sims y Simcity
- Dwarf Fortress
- Disco Elysium
- Cruelty Squad
- sandspiel.club y orb.farm (Max Bittker and Lu Wilson projeects)
    - https://studio.sandspiel.club/
    - https://sandpond.cool/
- game of life, boids, particle life, Abelian sandpile model

### Related ideas

Some useful concepts below. Besides that this [google slide](https://docs.google.com/presentation/d/1D18EzWCCm2uJj_vKiyX8DbENNaOz5JuJHXbCjgbvYlI/edit?usp=sharing) about key ideas of labsensacional.com can be useful.

#### Neurophysiology, affect, and embodiment
- Misattribution of arousal  
- Somatic markers  
- Emotional lability  
- Cue learning  
- C-tactile (CT) fibers  
- Runner’s high  
- Flow states  
- Yerkes–Dodson curve  
- Dopamine as “wanting” vs “liking” (Berridge’s distinction)

#### Emotion, cognition, and appraisal theories
- Appraisal theory  
- Affect as information hypothesis  
  - Misattribution of affect  
- Two-factor theory of emotion  
- Transactional Model of Stress and Coping (Richard Lazarus)

#### Sensory modulation and altered states
- ASMR  
- Sensory isolation  
- Mammalian dive reflex (MDR)  
- Trance level / hypnotic susceptibility tests (Harvard, Stanford, etc.)  
- Peter J. Carroll – Gnosis techniques (excitatory and inhibitory types)

#### Movement, breath, and embodied practices
- Yoga techniques (lion pose, asanas, pranayamas, tantric energy play, …)  
- Breathwork / pranayamas  
- Raves, ecstatic dance, Osho dynamic meditations  
- Play, games, conversational humour, videogames  

#### Sexuality, erotic practices, and pleasure engineering
- Ahegao face  
- Sensation play  
- Self-flagellation techniques (American tribes; Fakir Mustafa)  
- Orgasmic Yoga ideas (Joseph Kramer, Barbara Carrellas, Annie Sprinkle: angergasms, crygasms, laughgasms, …)  
- Multiorgasm, edging  
- Sex toys (Magic Wand, Sybian, fuck machines, electro-play / e-stim, stim box)

#### Drugs, psychopharmacology, and rating systems
- Recreational drugs and their effects  
- Shulgin Rating Scale; TiHKAL; PiHKAL  
- Louis Lewin (books)

#### Culture, philosophy, and critical frameworks
- Visión no binaria: placer/dolor, género, identidad, humano/salvaje  
- Testo Junkie and Manifiesto contrasexual — Paul B. Preciado  
- Hurts So Good: The Science and Culture of Pain on Purpose (2021) — Leigh Cowart  
- Sexual Secrets: The Alchemy of Ecstasy (1999) — Nik Douglas, Penny Slinger  
- The History of Sexuality — Michel Foucault  
- Ericksonian hypnosis and neuro-linguistic programming (NLP) ideas  
- Triune brain
- Timothy Leary. / Robert Anton Wilson’s 8-Circuit Model

#### Psychology, psychiatry, and sexology (classics)
- The Erotic Mind: Unlocking the Inner Sources of Passion and Fulfillment — Jack Morin  
- The Expression of the Emotions in Man and Animals — Charles Darwin  
- The Man Who Mistook His Wife for a Hat — Oliver Sacks  
- Kinsey and Masters & Johnson studies

#### Dynamical Systems

- Self-organized criticality

#### Mas cosas

- Opponent-Process Theory (Solomon & Corbit)                                                                                                                                       
- Gate Control Theory of Pain (Melzack & Wall)                                                                                                                                     
- Neuromatrix Theory of Pain (Melzack)                                                                                                                                             
- Incentive Salience / “wanting vs liking” (Berridge & Robinson)                                                                                                                   
- Dual Control Model of sexual response (Bancroft & Janssen)                                                                                                                       
- Window of Tolerance (Siegel / Ogden)                                                                                                                                             
- Polyvagal Theory (Porges)                                                                                                                                                        
- Affective systems: SEEKING/PLAY/PANIC/LUST etc. (Panksepp)                                                                                                                       
- Benign Violation Theory (McGraw & Warren) — if relevant                                                                                                                          
- Predictive processing / allostasis framing (Sterling; Friston; Barrett) — if useful as integration glue                                                                          
- Dynamical systems / attractor models (Kelso; Thelen; Marc Lewis)    