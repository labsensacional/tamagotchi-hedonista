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
- boids

### Related ideas

- https://docs.google.com/presentation/d/1D18EzWCCm2uJj_vKiyX8DbENNaOz5JuJHXbCjgbvYlI/edit?usp=sharing

- missatribution of arousal
- somatic markers
- ahegao face
- mammalian dive reflex (MDR)
- testo junki and manifiesto contrasexual from preciado
- Hurts So Good - The Science and Culture of Pain on Purpose (2021) por Leigh Cowart
- Sexual Secrets - The Alchemy of Ecstasy (1999) - Nik Douglas, Penny Slinger
- The History of Sexuality by Michel Foucault
- ericksonian and neuro linguistic programming ideas
- emotional lability
- ASMR
- raves, ecstatic dance, osho dynamic meditations
- play, games, conversational humour, videogames
- Visión no binaria: placer/dolor, género, identidad, humano/salvaje 
- Yoga techniques, lion pose, asanas, paranayamas, tantric energy play, ...
- self flaggelation techniques from american tribes and fakir mustafa
- recreative drugs and its effects
- Shulgin Rating Scale, tihkal, pihkal
- louis lewin books
- Orgasmic Yoga ideas from Joseph Kramer, Barbara Carellas and Annie Sprinkle (angergasms, crygasms, laughgasms, ...)
- runner's high
- The Erotic Mind: Unlocking the Inner Sources of Passion and Fulfillment – The Psychology of Sexual Arousal, Desire, and Erotic Paradoxes Paperback
- sensation play
- sensory isolation
- Cue learning
- dopamine is "wanting" not "liking" (Berridge's distinction)
- Darwin - Expression of emotions book
- oliver sacks - the man who mistook his wife with a hat
- kinsey and masters studies
- Trance level / Hypnotic susceptibility tests (harvard, stanford, ...)
- sex toys, magic wand, sybian, fuck machines, electro play (e-stim, stim box)
- multiorgasm, edging
- breathwork, pranayamas
- flow states
- yerkes-dowson curve
- Peter J. Caroll Gnosis Techniques (excitatory and inhibitory types)
- C-tactile (CT) fibers
- Appraisal theory
- Affect as information hypothesis
    - misattribution of affect
- Two-factor theory of emotion
- Transactional Model of Stress and Coping of Richard Lazarus


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
        - Sitio web que muestra de forma visual y sonora como esta el personaje. O sea convierte stats del personaje en animaciones. Por ejemplo si tiene mucha ansiedad y hace una accion de irse de fiesta deberia mostrarse la animacion predefinida de ir a una fiesta pero el personaje deberia temblar y mostrarse apatico
            - Hay animaciones y sonidos para cada accion. Quizas eventualmente pueden ir cambiando
            - El personaje es algo tierno que atrapa. Quizas eventualmente se podria personalizar?
            - Las variables alteran como se ve (expresion facial) y como se mueve (temblar, moverse lento, rapido, tono muscular, respiracion, ...)
        - Tambien esta (minimizado) todo el detalle de stats internas
        - El sitio tiene los botones de distintas acciones para mandar a que haga el agente
            - hay un buscador para encontrar acciones escribiendo
            - tambien estan ordenadas por categorias
            - tambien aparecen las ultimas 10 que usaste
            - estaria bueno que sea compartible esto, que la gente pueda sumar y mandar acciones nuevas que crea

## Ideas a futuro

Quizas dar como modo opcional forma de convertir nuevas acciones a reglas y cargarlas. Capaz armar tutorial de como hacerlo con chatGPT. Armar prompt para que convierte "tomar marihuana y masturbarse -> regla de como afecta al agente"

Si se inicializa un sistema basico con muchos agentes en un espacio 2D y se implementan dinamicas como
- emotional contagion (influencia sobre emociones de agentes cercanos)
- arousal synchronization
- mismatch dynamics
- oxytocin/vasopressin cross coupling
