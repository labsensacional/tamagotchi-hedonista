/* =============================================================
   TAMAGOTCHI HEDONISTA — main.js
   ============================================================= */

'use strict';

// ── State ──────────────────────────────────────────────────────
let currentState   = null;
let allEvents      = {};        // { category: [{ name, description, duration, can_apply }] }
let currentCategory = null;    // null = show category grid
let audioStarted   = false;
let audioMuted     = false;

// ── Category metadata ──────────────────────────────────────────
const CAT_META = {
    sexual:    { emoji: '💫', label: 'sexual'    },
    social:    { emoji: '🤝', label: 'social'    },
    pain:      { emoji: '⚡', label: 'pain'      },
    breathwork:{ emoji: '🌬️', label: 'breath'    },
    food:      { emoji: '🍎', label: 'food'      },
    rest:      { emoji: '😴', label: 'rest'      },
    drugs:     { emoji: '💊', label: 'drugs'     },
    medical:   { emoji: '🏥', label: 'medical'   },
    life:      { emoji: '🌍', label: 'life'      },
};

// ── Background mapping (action → bg key) ──────────────────────
const ACTION_BG = {
    sleep:                'sleep',
    rest:                 'rest',
    wait:                 'rest',
    eat:                  'food',
    snack:                'food',
    orgasm:               'sexual',
    light_stimulation:    'sexual',
    intense_stimulation:  'sexual',
    edging:               'sexual',
    cuddling:             'social',
    massage:              'social',
    light_pain:           'pain',
    temperature_play:     'pain',
    deep_breathing:       'breathwork',
    cold_face_immersion:  'breathwork',
    holotropic_breathing: 'breathwork',
    mdma:                 'drugs',
    weed:                 'drugs',
    mushrooms:            'drugs',
    lsd:                  'drugs',
    cocaine:              'drugs',
    alcohol:              'drugs',
    amphetamines:         'drugs',
    ketamine:             'drugs',
    poppers:              'drugs',
    tobacco:              'drugs',
    nitrous:              'drugs',
    caffeine:             'drugs',
    take_ssri:            'medical',
    stop_ssri:            'medical',
    therapy_session:      'medical',
    testosterone_injection:'medical',
    anti_androgen:        'medical',
    job_loss:             'life',
    financial_crisis:     'life',
    breakup:              'life',
    get_job:              'life',
    resolve_finances:     'life',
    new_relationship:     'life',
};

// ── Avatar expression + animation logic ───────────────────────
function getExpression(s) {
    if (s.shutdown     > 40)                     return 'blank';
    if (s.anxiety      > 70)                     return 'anxious';
    if (s.sleepiness   > 65)                     return 'sleepy';
    if (s.liking_score > 65 && s.arousal > 55)   return 'ecstatic';
    if (s.liking_score > 48)                     return 'happy';
    if (s.liking_score < 20)                     return 'sad';
    return 'neutral';
}

function getAnimation(s) {
    if (s.shutdown   > 40)                     return 'barely-moving';
    if (s.sleepiness > 60)                     return 'droop';
    if (s.anxiety    > 60)                     return 'shake';
    if (s.liking_score > 65 && s.arousal > 55) return 'bounce';
    if (s.liking_score > 48)                   return 'sway';
    return 'idle';
}

// ── DOM helpers ────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function updateAvatar(s) {
    const expr      = getExpression(s);
    const anim      = getAnimation(s);
    const container = $('avatar-container');
    const exprImg   = $('avatar-expr');

    // Swap expression (fade via opacity transition in CSS)
    const nextSrc = `/static/avatar/expr_${expr}.png`;
    if (exprImg.src !== nextSrc) {
        exprImg.style.opacity = '0';
        setTimeout(() => {
            exprImg.src = nextSrc;
            exprImg.style.opacity = '1';
        }, 200);
    }

    // Swap animation class
    const animClasses = ['anim-idle','anim-sway','anim-bounce',
                         'anim-shake','anim-droop','anim-barely-moving'];
    container.classList.remove(...animClasses);
    container.classList.add('anim-' + anim);
}

function updateHUD(s) {
    const bars = [
        { id: 'hud-liking',  val: s.liking_score },
        { id: 'hud-anxiety', val: s.anxiety       },
        { id: 'hud-energy',  val: s.energy        },
        { id: 'hud-arousal', val: s.arousal       },
    ];
    bars.forEach(({ id, val }) => {
        const el = $(id);
        if (el) el.style.width = `${Math.max(0, Math.min(100, val))}%`;
    });
}

function updateBackground(actionName) {
    const key  = ACTION_BG[actionName] || 'default';
    const bg   = $('bg');
    // Cross-fade: create new bg then swap
    bg.style.backgroundImage = `url('/static/backgrounds/${key}.jpg')`;
}

function updateRecentActions(lastActions) {
    const el = $('recent-actions');
    const chips = lastActions.slice().reverse().map(a =>
        `<span class="recent-chip" onclick="applyAction('${a}')">${a.replace(/_/g, ' ')}</span>`
    ).join('');
    el.innerHTML = `<span class="recent-label">recent:</span>${chips}`;
}

function applyStateToUI(state, lastActions) {
    currentState = state;
    updateAvatar(state);
    updateHUD(state);
    updateRecentActions(lastActions);
    if (audioStarted && !audioMuted) updateAudio(state);
}

// ── Action area rendering ──────────────────────────────────────
function renderCategories() {
    currentCategory = null;
    const area = $('action-area');
    const cells = Object.entries(CAT_META).map(([cat, meta]) => {
        const acts = allEvents[cat] || [];
        const available = acts.filter(a => a.can_apply).length;
        return `
          <button class="category-btn" onclick="selectCategory('${cat}')">
            <span class="cat-emoji">${meta.emoji}</span>
            <span class="cat-label">${meta.label}</span>
            <span style="font-size:10px;color:rgba(255,255,255,0.35)">${available}/${acts.length}</span>
          </button>`;
    }).join('');
    area.innerHTML = `<div class="category-grid">${cells}</div>`;
}

function selectCategory(cat) {
    currentCategory = cat;
    renderActionList(allEvents[cat] || [], true);
}

function renderActionList(actions, showBack) {
    const area  = $('action-area');
    const back  = showBack
        ? `<button class="back-btn" onclick="renderCategories()">← categories</button>`
        : '';
    const items = actions.map(a => `
        <div class="action-item ${a.can_apply ? '' : 'disabled'}"
             onclick="${a.can_apply ? `applyAction('${a.name}')` : ''}">
            <div class="action-name">${a.name.replace(/_/g, ' ')}</div>
            <div class="action-desc">${a.description}</div>
            <div class="action-dur">${a.duration}h</div>
        </div>`).join('');
    area.innerHTML = `${back}<div class="action-list">${items}</div>`;
}

// ── Search ─────────────────────────────────────────────────────
$('search-input').addEventListener('input', function () {
    const q = this.value.toLowerCase().trim();
    if (!q) {
        currentCategory ? renderActionList(allEvents[currentCategory] || [], true)
                        : renderCategories();
        return;
    }
    const results = [];
    for (const acts of Object.values(allEvents)) {
        for (const a of acts) {
            if (a.name.includes(q) || a.description.toLowerCase().includes(q)) {
                results.push(a);
            }
        }
    }
    renderActionList(results, false);
});

// ── Apply action ───────────────────────────────────────────────
async function applyAction(name) {
    if (!audioStarted && !audioMuted) startAudio();

    const res  = await fetch(`/api/action/${name}`, { method: 'POST' });
    const data = await res.json();
    if (data.error) { console.warn(data.error); return; }

    // Update event availability
    allEvents = data.events;

    applyStateToUI(data.state, data.last_actions);
    updateBackground(name);
    playSFX(name);

    // Re-render current view with updated can_apply
    const q = $('search-input').value.trim();
    if (q) {
        // trigger search re-render
        $('search-input').dispatchEvent(new Event('input'));
    } else if (currentCategory) {
        renderActionList(allEvents[currentCategory] || [], true);
    } else {
        renderCategories();
    }
}

// ── Reset ──────────────────────────────────────────────────────
async function resetGame() {
    const data = await fetch('/api/reset', { method: 'POST' }).then(r => r.json());
    allEvents  = data.events;
    currentCategory = null;
    applyStateToUI(data.state, data.last_actions);
    $('bg').style.backgroundImage = "url('/static/backgrounds/default.jpg')";
    renderCategories();
}

// ── Init ───────────────────────────────────────────────────────
async function init() {
    const [stateData, eventsData] = await Promise.all([
        fetch('/api/state').then(r => r.json()),
        fetch('/api/events').then(r => r.json()),
    ]);
    allEvents = eventsData;
    applyStateToUI(stateData.state, stateData.last_actions);
    renderCategories();
}

// =============================================================
// AUDIO — Tone.js procedural ambient pads
// =============================================================

let mainSynth, sfxSynth;
let reverbFX, distFX, lowpassFX, masterVolFX;
let chordLoop;
let currentMood = 'calm';
let chordIndex  = 0;

// Chord progressions — long ambient pads, no arpeggios.
// Voices are in bass/mid register to stay warm and non-intrusive.
const PROGRESSIONS = {
    calm: [
        ['C3', 'G3', 'E4'],
        ['A2', 'E3', 'C4'],
        ['F2', 'C3', 'A3'],
        ['G2', 'D3', 'B3'],
    ],
    happy: [
        ['C3', 'E3', 'G3', 'B3'],
        ['F3', 'A3', 'C4',     ],
        ['G3', 'B3', 'D4',     ],
        ['A3', 'C4', 'E4',     ],
    ],
    sad: [
        ['A2', 'C3', 'E3'],
        ['D2', 'F2', 'A2'],
        ['E2', 'G2', 'B2'],
        ['A2', 'E3', 'A3'],
    ],
    anxious: [
        ['B2', 'D3', 'F3', 'Ab3'],
        ['Eb3','G3', 'Bb3'      ],
        ['C3', 'Eb3','Gb3'      ],
        ['F#2','A2', 'C3'       ],
    ],
    blank: [
        ['C2', 'G2'],
        ['F2', 'C3'],
    ],
};

// Choose mood from state
function moodFromState(s) {
    if (s.shutdown     > 40)               return 'blank';
    if (s.anxiety      > 65)               return 'anxious';
    if (s.liking_score > 55 && s.arousal > 40) return 'happy';
    if (s.liking_score < 22)              return 'sad';
    return 'calm';
}

async function startAudio() {
    if (audioStarted) return;
    try {
        await Tone.start();
    } catch (e) {
        console.warn('Audio start failed:', e);
        return;
    }

    // Build effects chain: synth → dist → lowpass → reverb → masterVol → output
    reverbFX   = new Tone.Reverb({ decay: 9, wet: 0.45, preDelay: 0.08 });
    distFX     = new Tone.Distortion(0);
    lowpassFX  = new Tone.Filter({ frequency: 6000, type: 'lowpass', rolloff: -12 });
    masterVolFX= new Tone.Volume(-15);

    await reverbFX.generate();

    // Main ambient pad synth — very slow attack/release for a pad feel
    mainSynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'sine' },
        envelope: {
            attack:  3.5,
            decay:   1.0,
            sustain: 0.82,
            release: 7.0,
        },
        volume: -5,
    });

    mainSynth.chain(distFX, lowpassFX, reverbFX, masterVolFX, Tone.Destination);

    // SFX synth — short, separate chain so it bypasses pad effects
    sfxSynth = new Tone.Synth({
        oscillator: { type: 'triangle' },
        envelope: { attack: 0.02, decay: 0.25, sustain: 0.0, release: 0.4 },
        volume: -16,
    });
    sfxSynth.chain(new Tone.Volume(0), Tone.Destination);

    Tone.Transport.bpm.value = 60;

    // Loop fires every 4 measures — musical timing scales with BPM
    chordLoop = new Tone.Loop((time) => {
        const prog  = PROGRESSIONS[currentMood];
        const chord = prog[chordIndex % prog.length];
        // Hold chord for 3m (slightly shorter than loop to let it breathe)
        const dur = currentMood === 'anxious' ? '1m' : '3m';
        mainSynth.triggerAttackRelease(chord, dur, time);
        chordIndex++;
    }, '4m');

    chordLoop.start(0);
    Tone.Transport.start();

    audioStarted = true;
    $('audio-btn').textContent = '🔊';
}

// Update audio parameters in real time based on current state
function updateAudio(s) {
    if (!audioStarted || !mainSynth) return;

    const mood = moodFromState(s);
    if (mood !== currentMood) {
        currentMood = mood;
        chordIndex  = 0;   // reset progression on mood change
    }

    // BPM: calm=58, tired=44, anxious=78
    const targetBPM = s.anxiety > 65   ? 78
                    : s.sleepiness > 60 ? 44
                    : 58;
    Tone.Transport.bpm.rampTo(targetBPM, 8);

    // Low-pass filter: wide when alert, narrows when tired/shutdown
    const filterHz = s.shutdown > 40   ? 500
                   : s.sleepiness > 60 ? 1800
                   : 7000;
    lowpassFX.frequency.rampTo(filterHz, 4);

    // Distortion: increases with anxiety
    distFX.distortion = Math.min(0.55, (s.anxiety / 100) * 0.65);

    // Reverb wetness: more space when dissociated/sad, less when happy
    const wet = s.shutdown > 40  ? 0.88
              : s.liking_score < 22 ? 0.60
              : 0.42;
    reverbFX.wet.rampTo(wet, 5);

    // Master volume: quieter in shutdown, slightly louder when anxious
    const vol = s.shutdown > 40 ? -26
              : s.anxiety  > 65 ? -10
              : -15;
    masterVolFX.volume.rampTo(vol, 3);
}

// SFX: one short tone per action category
const CAT_SFX_PARAMS = {
    sexual:     { note: 'A4',  type: 'sine',     dur: '4n' },
    social:     { note: 'E4',  type: 'triangle', dur: '4n' },
    pain:       { note: 'C5',  type: 'sawtooth', dur: '8n' },
    breathwork: { note: 'D3',  type: 'sine',     dur: '2n' },
    food:       { note: 'G4',  type: 'triangle', dur: '4n' },
    rest:       { note: 'C3',  type: 'sine',     dur: '2n' },
    drugs:      { note: 'B4',  type: 'sine',     dur: '4n' },
    medical:    { note: 'F4',  type: 'triangle', dur: '8n' },
    life:       { note: 'A3',  type: 'triangle', dur: '4n' },
};

function playSFX(actionName) {
    if (!audioStarted || !sfxSynth || audioMuted) return;

    // Find category for this action
    let cat = 'rest';
    for (const [c, acts] of Object.entries(allEvents)) {
        if (acts.find(a => a.name === actionName)) { cat = c; break; }
    }

    const p = CAT_SFX_PARAMS[cat] || { note: 'C4', type: 'sine', dur: '4n' };
    sfxSynth.oscillator.type = p.type;
    sfxSynth.triggerAttackRelease(p.note, p.dur);
}

// Audio toggle
function toggleAudio() {
    if (!audioStarted) {
        startAudio();
        audioMuted = false;
        $('audio-btn').textContent = '🔊';
        return;
    }
    audioMuted = !audioMuted;
    if (audioMuted) {
        Tone.Transport.stop();
        $('audio-btn').textContent = '🔇';
    } else {
        Tone.Transport.start();
        if (currentState) updateAudio(currentState);
        $('audio-btn').textContent = '🔊';
    }
}

// =============================================================
// Boot
// =============================================================
document.addEventListener('DOMContentLoaded', init);
