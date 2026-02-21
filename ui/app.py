import os
import sys

# Import game logic from ../internal-logic/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'internal-logic'))

from flask import Flask, jsonify, request, render_template
from human import Human, create_human
from events import make_events, apply_event, apply_decay

app = Flask(__name__)

# --------------------------------------------------------------------------
# In-memory game state (single player, reset on server restart)
# --------------------------------------------------------------------------
_human = create_human()
_events = make_events()
_last_actions = []   # list of action name strings (most recent last)


def human_to_dict(h: Human) -> dict:
    return {
        'dopamine':             round(h.dopamine, 1),
        'oxytocin':             round(h.oxytocin, 1),
        'endorphins':           round(h.endorphins, 1),
        'serotonin':            round(h.serotonin, 1),
        'prolactin':            round(h.prolactin, 1),
        'vasopressin':          round(h.vasopressin, 1),
        'arousal':              round(h.arousal, 1),
        'prefrontal':           round(h.prefrontal, 1),
        'sleepiness':           round(h.sleepiness, 1),
        'anxiety':              round(h.anxiety, 1),
        'absorption':           round(h.absorption, 1),
        'hunger':               round(h.hunger, 1),
        'energy':               round(h.energy, 1),
        'physical_health':      round(h.physical_health, 1),
        'psychological_health': round(h.psychological_health, 1),
        'sexual_inhibition':    round(h.sexual_inhibition, 1),
        'shutdown':             round(h.shutdown, 1),
        'liking_score':         round(h.liking_score(), 1),
        'wanting_score':        round(h.wanting_score(), 1),
        'is_viable':            h.is_viable(),
    }


def events_by_category() -> dict:
    """Return all events grouped by category, with can_apply evaluated
    against the current _human state."""
    cats: dict = {}
    for name, event in _events.items():
        cat = event.category
        cats.setdefault(cat, []).append({
            'name':        name,
            'description': event.description,
            'duration':    event.duration,
            'can_apply':   event.can_apply(_human),
        })
    return cats


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/state')
def get_state():
    return jsonify({
        'state':        human_to_dict(_human),
        'last_actions': _last_actions[-3:],
    })


@app.route('/api/events')
def get_events():
    return jsonify(events_by_category())


@app.route('/api/action/<name>', methods=['POST'])
def do_action(name):
    global _last_actions

    if name not in _events:
        return jsonify({'error': 'unknown action'}), 404

    event = _events[name]
    if not event.can_apply(_human):
        return jsonify({'error': 'cannot apply right now'}), 400

    apply_event(_human, name, event)
    apply_decay(_human, event.duration)
    _human.clamp_values()

    _last_actions.append(name)
    if len(_last_actions) > 20:
        _last_actions = _last_actions[-20:]

    return jsonify({
        'state':        human_to_dict(_human),
        'last_actions': _last_actions[-3:],
        'events':       events_by_category(),   # updated can_apply after action
    })


@app.route('/api/reset', methods=['POST'])
def reset():
    global _human, _last_actions
    _human = create_human()
    _last_actions = []
    return jsonify({
        'state':        human_to_dict(_human),
        'last_actions': [],
        'events':       events_by_category(),
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
