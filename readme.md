# sensagotchi

sensagotchi (_sensations watch_) is a small simulation framework for modeling limbic and affective dynamics under abstract human actions.

It treats actions like “jerking off”, “going to a party”, “losing your job”, or “receiving light pain” not as narrative events, but as perturbations to a physiological–affective system that evolves over time.

_Try it [here](https://sensagotchi.labsensacional.com/)!_

## What is this for?

The main use case is to explore how **sequences of actions** (not single actions) shape subjective experience over time.

Instead of asking “is this action good or bad?”, the simulator asks:

- What happens if you do this for 3 hours?
- How do pleasure, exhaustion, rebound, and recovery interact?
- Why do some combinations feel unexpectedly intense or unexpectedly empty?

### What this is NOT

- Not a realistic neuroscience or medical model
- Not a therapy or self-help tool
- Not a porn simulator
- Not a moral system of “healthy vs unhealthy”
- Not an autonomous AI agent with goals or beliefs

The simulator does not decide what to do.
The user does.

## Running the website

No build step, no server required — just serve `src/` as static files:

```bash
cd src
python -m http.server 5000
```

Open `http://localhost:5000`. Also accessible from a phone on the same network at `http://<your-local-ip>:5000`.

### Running the tests

The project is heavily test-driven. Tests are not just for correctness, but encode **conceptual invariants** such as:

- No single action can be repeated forever without diminishing returns
- Fast pleasure produces delayed cost
- Arousal can be misattributed across domains
- Moderate anxiety can amplify pleasure (Yerkes–Dodson)
- Absorption is fragile under anxiety and sleepiness

#### Internal Logic Test

Tests use [vitest](https://vitest.dev/). Install dev dependencies once, then run:

```bash
cd src/internal-logic
npm install
npm test
```

#### Emotional Expression Test

You can open `src/static/emotions-expression-test.html` to manually test this. Or try the latest release [here](https://sensagotchi.labsensacional.com/emotions-expression-test)

## Future Work

Multi Agent: A basic system with many agents in a 2D space could be initialized where dynamics such as the following could be implemented
- emotional contagion (influence on the emotions of nearby agents)
- arousal synchronization
- mismatch dynamics
- oxytocin/vasopressin cross-coupling (dominance/submission? Leary circuits 2 and 4: emotional-territorial and attachment and social identity mental spaces?)
