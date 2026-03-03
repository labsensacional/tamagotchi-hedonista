## Decisiones de diseño

- El sistema se entiende como dos subsistemas
    - Backend
        - Tiene todas las reglas logicas del sistema. Crea instancia de personaje dadas unas variables metas y la clase humano y actions
        - Aplica las actions y actualiza el estado del personaje
    - Frontend
        - Sitio web que muestra de forma visual y sonora como esta el personaje
            - Hay animaciones y sonidos para cada accion. Quizas eventualmente pueden ir cambiando
            - El personaje es algo tierno que atrapa. Quizas eventualmente se podria personalizar?

- Las acciones son secuenciales, no se pueden componer y hacer en paralelo. Si fuera de interes explorar esa interaccion, por ejemplo "consumir marihuana en un tanque de flotacion" o "penetrasion anal mientras se hace deepthroat" entonces se debe crear una accion nueva que contenga las dos juntas
- No se modelan mecanismos de inferencia de affect se modelan de forma explicita en acciones, por ejemplo "recibir un abrazo de un amigo" se asume por default positivo y que genera un juicio positivo y una experiencia de placer. Aunque se pueden modelar mecanicas donde cosas como el cortisol afecten esas acciones, que ciertas acciones cambien de polaridad cuento el cortisol esta alto y el prefrontal cortes esta muy activo o cosas asi (no hay tiempo de sentir placer si estas preocupado por algo) o por ejemplo cuando estas muy caliente, todo se convierte en placer y algo sexual, incluso dolor, insultos y demas.
- Las animaciones y el personaje tienen ciertas animaciones pero son predefinidas, siempre mas o menos iguales, esta en una habitacion, no puede moverse de ahi, no hay un espacio caminable o algo asi
- No se modelan los detalles fisicos del mundo, como se mueve el personaje o cosas asi. El foco esta en abstraer acciones en el mundo como algo que se da por sentado que se puede lograr de hacer y abstraer fisiologia de bajo nivel del cuerpo como modulos a grandes rasgos (niveles de neurotransmisores, sistema digestivo, prefrontal cortex, atencion, arousal, ...) y modelar como 
- Los modelos no tienen motivaciones, no toman decisiones, el usuario las toma por ellos
- El objetivo es mantener lo mas simple posible un simulador que logra capturar dinamicas sobre como distintas acciones afectan a la gente en terminos de cuan bien la pasan
    - dinamicas donde no es todo tan simple como "acciones buenas y malas" sino que emergen patrones complejos como pasa en el bdsm donde se consigue placer y extasis mezclando valencias

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

## UI overview

The interface is split into two areas:

**Top (avatar section):** a procedural p5.js monster whose shape and animation reflect the current state — anxious states trigger a shake animation, sleepiness causes a drooping slow bob, high liking triggers a bounce or sway. A HUD in the corner shows liking, anxiety, energy, and arousal as small bars. The background image fades to match the last action taken.

**Bottom (controls):** a search bar, a category grid (sexual / social / pain / breathwork / food / rest / drugs / medical / life), and a recent-actions strip. Tapping a category drills into its action list; the search bar filters across all actions in real time.

**Audio:** Tone.js procedural ambient pads (slow attack/release, no arpeggios). The chord progression, BPM, low-pass filter cutoff, distortion, and reverb wetness all modulate continuously from the current state — sleepiness muffles and slows everything, anxiety adds distortion and speeds the chord changes, shutdown collapses to near silence with heavy reverb. A short SFX tone plays on each action.

