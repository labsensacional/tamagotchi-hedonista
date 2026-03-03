/* =============================================================
   TAMAGOTCHI HEDONISTA — main.js
   ============================================================= */

import { Human, create_human } from './internal-logic/human.js';
import { make_events, apply_event, apply_decay, drainNotifications } from './internal-logic/events.js';

// ── State ──────────────────────────────────────────────────────
let currentState   = null;
let _human         = null;
let _events        = null;
let _lastActions   = [];
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
    exercise:             'life',
    job_loss:             'life',
    financial_crisis:     'life',
    breakup:              'life',
    get_job:              'life',
    resolve_finances:     'life',
    new_relationship:     'life',
};

// ── Avatar animation logic ─────────────────────────────────────
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
    // Update p5.js monster visual state
    if (window.updateMonsterFromApp) window.updateMonsterFromApp(s);

    // Swap CSS animation class on the container (body motion)
    const anim      = getAnimation(s);
    const container = $('avatar-container');
    const animClasses = ['anim-idle','anim-sway','anim-bounce',
                         'anim-shake','anim-droop','anim-barely-moving'];
    container.classList.remove(...animClasses);
    container.classList.add('anim-' + anim);
}

function updateHUD(s) {
    const bars = [
        { id: 'hud-hunger',    val: s.hunger              },
        { id: 'hud-anxiety',   val: s.anxiety             },
        { id: 'hud-sleepiness',val: s.sleepiness          },
        { id: 'hud-psych',     val: s.psychological_health},
        { id: 'hud-physical',  val: s.physical_health     },
        { id: 'hud-energy',    val: s.energy              },
    ];
    bars.forEach(({ id, val }) => {
        const el = $(id);
        if (el) el.style.width = `${Math.max(0, Math.min(100, val))}%`;
    });
    updateHUDDetail(s);
}

// Color per field (CSS custom property --dc on .detail-fill)
const DETAIL_COLORS = {
    dopamine:             '#fdcb6e', serotonin:            '#55efc4', endorphins:  '#fd79a8',
    oxytocin:             '#74b9ff', prolactin:            '#a29bfe', vasopressin: '#e17055',
    arousal:              '#a29bfe', energy:               '#00b894', sleepiness:  '#636e72',
    hunger:               '#e67e22', anxiety:              '#ee5a24', prefrontal:  '#0984e3',
    absorption:           '#6c5ce7', shutdown:             '#2d3436',
    physical_health:      '#55efc4', psychological_health: '#74b9ff',
};

const DETAIL_GROUPS = [
    { label: 'Neurotransmitters', rows: [
        ['dopamine',    'dopamine'   ],
        ['serotonin',   'serotonin'  ],
        ['endorphins',  'endorphins' ],
        ['oxytocin',    'oxytocin'   ],
        ['prolactin',   'prolactin'  ],
        ['vasopressin', 'vasopressin'],
    ]},
    { label: 'Body', rows: [
        ['arousal',    'arousal'   ],
        ['energy',     'energy'    ],
        ['sleepiness', 'sleepiness'],
        ['hunger',     'hunger'    ],
    ]},
    { label: 'Mind', rows: [
        ['anxiety',    'anxiety'   ],
        ['prefrontal', 'prefrontal'],
        ['absorption', 'absorption'],
        ['shutdown',   'shutdown'  ],
    ]},
    { label: 'Health', rows: [
        ['physical_health',      'physical'     ],
        ['psychological_health', 'psychological'],
    ]},
];

function updateHUDDetail(s) {
    const el = $('hud-detail');
    if (!el) return;
    el.innerHTML = DETAIL_GROUPS.map(g => `
        <div class="detail-group">
            <div class="detail-group-label">${g.label}</div>
            ${g.rows.map(([key, label]) => {
                const val = Math.round(s[key] ?? 0);
                const col = DETAIL_COLORS[key] || 'rgba(255,255,255,0.45)';
                return `<div class="detail-row">
                    <span class="detail-key">${label}</span>
                    <div class="detail-bar">
                        <div class="detail-fill" style="width:${val}%;--dc:${col}"></div>
                    </div>
                    <span class="detail-val">${val}</span>
                </div>`;
            }).join('')}
        </div>`).join('');
}

function human_to_dict(h) {
    return {
        dopamine:             Math.round(h.dopamine * 10) / 10,
        oxytocin:             Math.round(h.oxytocin * 10) / 10,
        endorphins:           Math.round(h.endorphins * 10) / 10,
        serotonin:            Math.round(h.serotonin * 10) / 10,
        prolactin:            Math.round(h.prolactin * 10) / 10,
        vasopressin:          Math.round(h.vasopressin * 10) / 10,
        arousal:              Math.round(h.arousal * 10) / 10,
        prefrontal:           Math.round(h.prefrontal * 10) / 10,
        sleepiness:           Math.round(h.sleepiness * 10) / 10,
        anxiety:              Math.round(h.anxiety * 10) / 10,
        absorption:           Math.round(h.absorption * 10) / 10,
        hunger:               Math.round(h.hunger * 10) / 10,
        energy:               Math.round(h.energy * 10) / 10,
        physical_health:      Math.round(h.physical_health * 10) / 10,
        psychological_health: Math.round(h.psychological_health * 10) / 10,
        sexual_inhibition:    Math.round(h.sexual_inhibition * 10) / 10,
        shutdown:             Math.round(h.shutdown * 10) / 10,
        liking_score:         Math.round(h.liking_score() * 10) / 10,
        wanting_score:        Math.round(h.wanting_score() * 10) / 10,
        is_viable:            h.is_viable(),
    };
}

function events_by_category() {
    const cats = {};
    for (const [name, event] of Object.entries(_events)) {
        const cat = event.category;
        if (!cats[cat]) cats[cat] = [];
        const reason = event.blocked_reason;
        const noteFn = event.note;
        cats[cat].push({
            name,
            description:    event.description,
            duration:       event.duration,
            can_apply:      event.can_apply(_human),
            blocked_reason: typeof reason === 'function' ? reason(_human) : (reason || ''),
            note:           typeof noteFn === 'function' ? noteFn(_human) : null,
        });
    }
    return cats;
}

function updateBackground(actionName) {
    const key  = ACTION_BG[actionName] || 'default';
    const bg   = $('bg');
    // Cross-fade: create new bg then swap
    bg.style.backgroundImage = `url('backgrounds/${key}.jpg')`;
}

function updateRecentActions(lastActions) {
    const el = $('recent-actions');
    const chips = lastActions.slice().reverse().map(a =>
        `<span class="recent-chip" onclick="applyAction('${a}')">${a.replace(/_/g, ' ')}</span>`
    ).join('');
    el.innerHTML = `<span class="recent-label">recent:</span>${chips}`;
}

// Color per notification type
const NOTIF_COLORS = {
    'orgasm':    '#fd79a8',
    'overwhelm': '#fdcb6e',
    'bad-trip':  '#d63031',
    'sick':      '#55efc4',
    'anxiety':   '#e17055',
    'ssri':      '#74b9ff',
    'ssri-stop': '#a29bfe',
    'life-bad':  '#e17055',
    'life-good': '#00b894',
    'action':    'rgba(255,255,255,0.75)',
};

let _notifTimer = null;

function showEventNotification(text, type) {
    const el = $('event-notification');
    if (!el) return;

    // Clear any existing timer so previous message doesn't cut the new one short
    if (_notifTimer) { clearTimeout(_notifTimer); _notifTimer = null; }

    const color = NOTIF_COLORS[type] || 'rgba(255,255,255,0.9)';
    el.innerHTML = `<div class="event-notif" style="--notif-color:${color}">${text}</div>`;

    _notifTimer = setTimeout(() => {
        el.innerHTML = '';
        _notifTimer = null;
    }, 3000);
}

// ── Action summary notification ────────────────────────────
const _SUMMARY_VARS = [
    'dopamine','serotonin','endorphins','oxytocin','prolactin','vasopressin',
    'arousal','energy','sleepiness','hunger','anxiety','prefrontal','absorption',
    'physical_health','psychological_health',
];

function buildActionSummary(before, after) {
    const changes = _SUMMARY_VARS
        .map(k => ({ k, d: Math.round((after[k] ?? 0) - (before[k] ?? 0)) }))
        .filter(x => Math.abs(x.d) >= 3)
        .sort((a, b) => Math.abs(b.d) - Math.abs(a.d))
        .slice(0, 3);
    if (!changes.length) return null;
    return changes.map(x => `${x.k} ${x.d > 0 ? '+' : ''}${x.d}`).join('  ·  ');
}

// ── Death screen ───────────────────────────────────────────
function checkDeath(state) {
    if (state.physical_health <= 0 || state.psychological_health <= 0) {
        const el = $('death-screen');
        if (el) el.classList.remove('hidden');
        return true;
    }
    return false;
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
            ${!a.can_apply && a.blocked_reason ? `<div class="action-blocked-reason">⚠ ${a.blocked_reason}</div>` : ''}
            ${a.note ? `<div class="action-note">⚠ ${a.note}</div>` : ''}
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
function applyAction(name) {
    if (!audioStarted && !audioMuted) startAudio();

    const event = _events[name];
    if (!event || !event.can_apply(_human)) return;

    const before = human_to_dict(_human);
    apply_event(_human, name, event);
    const afterEvent = human_to_dict(_human);  // pre-decay snapshot for clean diff
    apply_decay(_human, event.duration);
    _human.clamp_values();

    const notifications = drainNotifications();
    if (notifications.length > 0) {
        notifications.forEach(n => showEventNotification(n.text, n.type));
    } else {
        const msg = buildActionSummary(before, afterEvent);
        if (msg) showEventNotification(msg, 'action');
    }

    _lastActions.push(name);
    if (_lastActions.length > 20) _lastActions = _lastActions.slice(-20);

    allEvents = events_by_category();
    const finalState = human_to_dict(_human);
    applyStateToUI(finalState, _lastActions.slice(-3));
    updateBackground(name);
    playSFX(name);

    if (checkDeath(finalState)) return;

    // Re-render current view with updated can_apply
    const q = $('search-input').value.trim();
    if (q) {
        $('search-input').dispatchEvent(new Event('input'));
    } else if (currentCategory) {
        renderActionList(allEvents[currentCategory] || [], true);
    } else {
        renderCategories();
    }
}

// ── Reset ──────────────────────────────────────────────────────
function resetGame() {
    const death = $('death-screen');
    if (death) death.classList.add('hidden');
    if (_notifTimer) { clearTimeout(_notifTimer); _notifTimer = null; }
    const notifEl = $('event-notification');
    if (notifEl) notifEl.innerHTML = '';
    _human = create_human();
    _lastActions = [];
    allEvents = events_by_category();
    currentCategory = null;
    applyStateToUI(human_to_dict(_human), []);
    $('bg').style.backgroundImage = "url('backgrounds/default.jpg')";
    renderCategories();
}

// ── Init ───────────────────────────────────────────────────────
function init() {
    _human = create_human();
    _events = make_events();
    _lastActions = [];
    allEvents = events_by_category();
    applyStateToUI(human_to_dict(_human), []);
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
document.addEventListener('click', () => $('hud').classList.remove('open'));

// Expose globals for inline onclick handlers (ES modules don't auto-expose to window)
window.resetGame       = resetGame;
window.toggleAudio     = toggleAudio;
window.applyAction     = applyAction;
window.selectCategory  = selectCategory;
window.renderCategories = renderCategories;
