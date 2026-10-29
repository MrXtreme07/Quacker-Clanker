"""
Keyword NLP: turn a vision model's reply into ONE dashboard action word.

    to_one_word("A woman is sitting at a table eating a burger")  -> "eating"
    to_one_word("Man stands next to a stroller")                  -> "standing"
    to_one_word("A boy with a laptop on his knees")               -> "typing"

How it decides:
  1. Action verbs (eating, drinks, jogging ...)        -> strongest clue
  2. Object / place clues (burger, cup, laptop, bed ...) -> used if no action verb
  3. Posture verbs (sitting, standing)                -> used only if nothing else matched
Within each level, ACTION_PRIORITY breaks ties (more specific actions win).
"""
import re

# Same actions the dashboard has icons for
ACTIONS = [
    "sitting", "standing", "walking", "running", "eating", "drinking",
    "typing", "reading", "sleeping", "talking", "working", "exercising",
]

# Most specific first. Posture words come last so "sitting and eating" -> eating.
ACTION_PRIORITY = [
    "eating", "drinking", "typing", "reading", "sleeping", "running",
    "exercising", "walking", "talking", "working", "standing", "sitting",
]
POSTURES = {"sitting", "standing"}

# Level 1: verb forms -> action
VERBS = {
    "eating": "eat eats ate eaten eating chewing chews biting bites dining dines feeding",
    "drinking": "drink drinks drank drinking sip sips sipping gulping",
    "typing": "type types typed typing",
    "reading": "read reads reading",
    "sleeping": "sleep sleeps slept sleeping asleep nap naps napping dozing lying lies laying lays",
    "running": "run runs ran running jog jogs jogging sprint sprints sprinting racing",
    "exercising": "exercise exercises exercising workout lifting stretching stretches training",
    "walking": "walk walks walked walking strolling strolls hiking",
    "talking": "talk talks talked talking speak speaks speaking chatting chats calling conversing",
    "working": "work works worked working",
    "standing": "stand stands stood standing",
    "sitting": "sit sits sat sitting seated",
}

# Level 2: objects / places that strongly suggest an action
CLUES = {
    "eating": "meal meals lunch dinner breakfast food burger hamburger sandwich pizza snack fork spoon plate salad",
    "drinking": "cup mug bottle beverage wine beer juice straw",
    "typing": "laptop keyboard computer",
    "reading": "book books newspaper magazine",
    "sleeping": "bed pillow blanket",
    "running": "runner jogger marathon",
    "exercising": "gym weights dumbbell dumbbells yoga treadmill",
    "talking": "conversation phone",
    "working": "office desk",
}

# Multi-word phrases (checked on the whole text)
PHRASES = {
    "on the phone": "talking",
    "phone call": "talking",
    "push up": "exercising",
    "push-up": "exercising",
    "lying down": "sleeping",
}
NO_PERSON = ["no person", "no one", "nobody", "no people", "empty room"]


def _build(table):
    lookup = {}
    for action, words in table.items():
        for w in words.split():
            lookup[w] = action
    return lookup


_VERBS = _build(VERBS)
_CLUES = _build(CLUES)


def _best(found):
    return min(found, key=ACTION_PRIORITY.index)


def to_one_word(text: str) -> str:
    """Reduce a model reply to one action word, 'none' (no person) or 'unknown'."""
    t = text.lower().strip()
    words = re.findall(r"[a-z]+", t)

    if words == ["none"] or any(p in t for p in NO_PERSON):
        return "none"

    verbs = {_VERBS[w] for w in words if w in _VERBS}
    verbs |= {a for p, a in PHRASES.items() if p in t}
    clues = {_CLUES[w] for w in words if w in _CLUES}

    specific_verbs = verbs - POSTURES
    if specific_verbs:
        return _best(specific_verbs)
    if clues:
        return _best(clues)
    if verbs:
        return _best(verbs)
    return "unknown"
