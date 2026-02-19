import os
import re
from datetime import datetime, timedelta

# SpaCy is optional — parser works with pure regex when unavailable
try:
    import spacy
    model_path = "./output/model-best"
    if os.path.exists(model_path):
        nlp = spacy.load(model_path)
        print(f"Loaded custom model from {model_path}")
    else:
        try:
            nlp = spacy.load("en_core_web_sm")
            print("Loaded generic model en_core_web_sm")
        except OSError:
            nlp = None
            print("No spaCy base model found, using regex-only parsing")
except ImportError:
    nlp = None
    print("SpaCy not installed — using regex-only parsing")


# ─── Date / Time Inference Helpers ───────────────────────────────────────────

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


def _infer_date(text: str) -> str | None:
    """Attempt to infer a concrete date from natural language."""
    text_lower = text.lower()
    today = datetime.now()

    # "tomorrow"
    if "tomorrow" in text_lower:
        d = today + timedelta(days=1)
        return d.strftime("%A, %B %d, %Y")

    # "today"
    if "today" in text_lower:
        return today.strftime("%A, %B %d, %Y")

    # "day after tomorrow"
    if "day after tomorrow" in text_lower:
        d = today + timedelta(days=2)
        return d.strftime("%A, %B %d, %Y")

    # "in X days"
    m = re.search(r"in\s+(\d+)\s+days?", text_lower)
    if m:
        d = today + timedelta(days=int(m.group(1)))
        return d.strftime("%A, %B %d, %Y")

    # "this weekend"
    if "this weekend" in text_lower:
        days_until_sat = (5 - today.weekday()) % 7
        if days_until_sat == 0 and today.weekday() != 5:
            days_until_sat = 7
        sat = today + timedelta(days=days_until_sat)
        sun = sat + timedelta(days=1)
        return f"Weekend ({sat.strftime('%B %d')} - {sun.strftime('%B %d, %Y')})"

    # "next week"
    if "next week" in text_lower:
        days_until_mon = (7 - today.weekday()) % 7
        if days_until_mon == 0:
            days_until_mon = 7
        mon = today + timedelta(days=days_until_mon)
        return f"Week of {mon.strftime('%B %d, %Y')}"

    # Named day: "monday", "tuesday", etc.
    for day_name, day_num in DAY_MAP.items():
        # Use word boundary to avoid partial matches
        if re.search(rf"\b{day_name}\b", text_lower):
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # next occurrence
            d = today + timedelta(days=days_ahead)
            return d.strftime("%A, %B %d, %Y")

    return None


def _infer_time(text: str) -> str | None:
    """Extract or infer time from text."""
    text_lower = text.lower()

    # Specific time: "6am", "7:30pm", "6:00 am"
    m = re.search(r"(\d{1,2})(:\d{2})?\s*(am|pm)", text_lower)
    if m:
        hour = int(m.group(1))
        minutes = m.group(2) or ":00"
        period = m.group(3).upper()
        return f"{hour}{minutes} {period}"

    # General time references
    if "early morning" in text_lower or "early" in text_lower:
        return "Early Morning"
    if "morning" in text_lower:
        return "Morning"
    if "afternoon" in text_lower:
        return "Afternoon"
    if "after work" in text_lower or "evening" in text_lower:
        return "Evening"
    if "night" in text_lower:
        return "Night"

    return None


# ─── Activity Detection ─────────────────────────────────────────────────────

# Ordered list — priority matters! More specific activities first, generic last.
_ACTIVITY_PRIORITY = [
    ("Triathlon", ["triathlon", "tri session"]),
    ("Swimming", ["swim", "pool session", "freestyle", "backstroke", "breaststroke"]),
    ("Cycling", ["bike", "cycle", "cycling", "ride"]),
    ("Running", ["run", "jog", "sprint", "marathon", "tempo run", "fartlek",
                 "long run", "easy run"]),
    ("Strength Training", ["lift", "squat", "bench", "deadlift", "press", "curl",
                           "strength", "weight", "pull-up", "pullup",
                           "push-up", "pushup", "dumbbell", "barbell",
                           "leg day", "upper body", "conditioning"]),
    ("HIIT", ["hiit", "high intensity", "tabata", "circuit"]),
    ("Yoga", ["yoga", "mobility", "stretching", "flexibility", "foam roll"]),
    ("Hiking", ["hike", "hiking", "trek"]),
    ("Cardio", ["cardio", "elliptical", "stairmaster"]),
    ("Rest", ["rest day", "off day"]),
    ("Match/Game", ["game", "match", "tournament"]),
]


def _detect_activity(text: str) -> str | None:
    text_lower = text.lower()
    for activity, keywords in _ACTIVITY_PRIORITY:
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                return activity
    return None


# ─── Extraction Helpers ──────────────────────────────────────────────────────

# Words that should never be treated as athlete names
_NAME_STOPWORDS = {
    "a", "an", "the", "to", "him", "her", "me", "new", "workout", "some",
    "he", "she", "they", "it", "you", "we", "i", "someone", "ok", "so", "if",
    "this", "that", "then", "first", "next", "also", "just", "please", "kindly",
    "assign", "give", "schedule", "do", "make", "set", "plan",
    "run", "swim", "bike", "cycle", "lift", "jog", "sprint", "hike",
    "easy", "hard", "long", "short", "tempo", "interval", "recovery",
    "simulation", "race", "leg", "upper", "mobility", "conditioning",
}


def _extract_athlete(text: str, doc) -> str | None:
    """Extract athlete name via NER then regex fallback."""
    # Priority 1: "Name, ..." pattern (name before first comma)
    m = re.match(r"^\s*([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)\s*,", text)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in _NAME_STOPWORDS:
            return candidate.title()

    # Priority 2: NER model
    if doc:
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.title()

    # Priority 3: "assign/give/schedule <Name>"
    m = re.search(r"(?:assign|give|schedule)\s+(\w+)", text, re.IGNORECASE)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in _NAME_STOPWORDS:
            return candidate.title()

    # Priority 4: "... to <Name>"
    m = re.search(r"(?:assign|give)\s+.*?\s+to\s+(\w+)", text, re.IGNORECASE)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in _NAME_STOPWORDS:
            return candidate.title()

    # Priority 5: "<Name> needs to / should / will"
    m = re.search(r"^(\w+)\s+(?:needs?\s+to|should|will|has|have|gotta)\b", text, re.IGNORECASE)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in _NAME_STOPWORDS:
            return candidate.title()

    # Priority 6: "for <Name>" at end
    m = re.search(r"\bfor\s+([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)\s*[.,!]?\s*$", text)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in _NAME_STOPWORDS:
            return candidate.title()

    return None


def _extract_multiple_athletes(text: str) -> list[str] | None:
    """Check for 'X and Y' pattern to detect multiple athletes."""
    m = re.search(r"(\w+)\s+and\s+(\w+)\s+(?:both|all|each)?\s*(?:need|should|will|have)\b", text, re.IGNORECASE)
    if m:
        stopwords = {"he", "she", "they", "it", "you", "we", "i"}
        a1 = m.group(1)
        a2 = m.group(2)
        if a1.lower() not in stopwords and a2.lower() not in stopwords:
            return [a1.title(), a2.title()]
    return None


def _extract_distance(text: str, doc) -> str | None:
    text_lower = text.lower()

    # First try spaCy NER, but validate it looks like a real distance
    if doc:
        for ent in doc.ents:
            if ent.label_ == "DISTANCE":
                # Validate: must contain a number + unit
                if re.search(r"\d+\s*(?:km|kilometers?|miles?|k\b|meters?|metres?|m\b)", ent.text.lower()):
                    return ent.text

    # Priority 1: Explicit distance units (km, kilometers, miles, k)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(km|kilometers?|kilometres?|miles?|k)\b", text_lower)
    if m:
        val = m.group(1)
        unit = m.group(2)
        if unit in ("k",):
            return f"{val}k"
        elif unit.startswith("kilometer") or unit.startswith("kilometre") or unit == "km":
            return f"{val} km" if unit != "km" else f"{val} km"
        elif unit.startswith("mile"):
            return f"{val} miles" if val != "1" else f"{val} mile"
        return f"{val} {unit}"

    # Priority 2: meters — but only when NOT near calorie/calorie-like context
    m = re.search(r"(\d+(?:\.\d+)?)\s*(m(?:eters?|etres?)?)\b", text_lower)
    if m:
        val = m.group(1)
        # Check context before the number to skip calorie values
        start_pos = m.start()
        preceding = text_lower[max(0, start_pos - 25):start_pos]
        if not re.search(r"(?:calorie|cal|kcal|burn|target)\s*$", preceding):
            return f"{val} meters"

    return None


def _extract_pace(text: str, doc) -> str | None:
    if doc:
        for ent in doc.ents:
            if ent.label_ == "PACE" and re.search(r"\d", ent.text):
                return ent.text

    text_lower = text.lower()

    # Swim pace: "1:45 per 100 meters", "1:45/100m"
    m = re.search(r"(\d{1,2}:\d{2})\s*(?:per|/)\s*(?:100\s*(?:m(?:eters?)?|metres?))", text_lower)
    if m:
        return f"{m.group(1)}/100m"

    # "5:30 pace per km", "5:30/km", "5:00 per km", "5:30 per mile"
    m = re.search(r"(\d{1,2}:\d{2})\s*(?:pace\s+)?(?:/\s*km|per\s*km|/\s*mile|per\s*mile)", text_lower)
    if m:
        if "mile" in m.group(0):
            return f"{m.group(1)}/mile"
        return f"{m.group(1)}/km"

    # "at 5:30 pace" (standalone pace with no unit — default to /km)
    m = re.search(r"(?:at|@)\s+(\d{1,2}:\d{2})\s*(?:pace|min)", text_lower)
    if m:
        return f"{m.group(1)}/km"

    # "25 km/h", "25 kmph", "10 mph", "30 kmph"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:km/?h|kmph)", text_lower)
    if m:
        return f"{m.group(1)} kmph"
    m = re.search(r"(\d+(?:\.\d+)?)\s*mph", text_lower)
    if m:
        return f"{m.group(1)} mph"

    return None


def _extract_intensity(text: str) -> str | None:
    text_lower = text.lower()
    if "easy" in text_lower or "recovery" in text_lower:
        return "Easy"
    if "moderate" in text_lower or "steady" in text_lower:
        return "Moderate"
    if "hard" in text_lower or "intense" in text_lower:
        return "Hard"
    if "threshold" in text_lower:
        return "Threshold"
    if "progressive" in text_lower:
        return "Progressive"
    return None


def _extract_location(text: str) -> str | None:
    text_lower = text.lower()

    # Qualified locations: "indoor heated pool", "flat road", "running track"
    qualified_patterns = [
        (r"indoor\s+heated\s+pool", "Indoor heated pool"),
        (r"outdoor\s+pool", "Outdoor pool"),
        (r"indoor\s+pool", "Indoor pool"),
        (r"heated\s+pool", "Heated pool"),
        (r"running\s+track", "Running track"),
        (r"flat\s+road(?:\s+route)?", "Flat road"),
        (r"flat\s+route", "Flat route"),
        (r"hilly\s+(?:road|route|terrain)", "Hilly terrain"),
        (r"trail\s+(?:route|path|run)", "Trail"),
        (r"sports\s+complex", "Sports complex"),
    ]
    for pat, name in qualified_patterns:
        if re.search(pat, text_lower):
            return name

    # Basic locations
    locations = {
        "gym": "Gym", "pool": "Pool", "track": "Track",
        "park": "Park", "home": "Home", "studio": "Studio",
        "outdoor": "Outdoor", "indoor": "Indoor",
        "trail": "Trail", "road": "Road",
    }
    for kw, name in locations.items():
        if re.search(rf"\b{kw}\b", text_lower):
            return name

    # Preferred terrain: "flat road preferred"
    m = re.search(r"(flat|hilly|road|trail)\s+(?:preferred|recommended)", text_lower)
    if m:
        return m.group(0).title()

    # Route constraints: "no hills", "avoid hills"
    if re.search(r"no\s+hills?\b|avoid\s+hills?\b", text_lower):
        return "Flat (no hills)"

    return None


def _extract_duration(text: str) -> str | None:
    """Extract main workout duration, ignoring rest intervals."""
    text_lower = text.lower()

    # Composite: "3 hours 30 minutes", "1 hour 45 min"
    m = re.search(r"(\d+)\s*(?:hours?|hrs?)\s*(\d+)\s*(?:minutes?|mins?)", text_lower)
    if m:
        return f"{m.group(1)} hours {m.group(2)} minutes"

    # "total session 90 minutes", "total duration 60 min"
    m = re.search(r"total\s+(?:session|duration|time|target\s+time)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)", text_lower)
    if m:
        val = m.group(1)
        unit = m.group(2)
        if unit.startswith("min"):
            return f"{val} minutes"
        elif unit.startswith("hour") or unit.startswith("hr"):
            return f"{val} hours"

    # Skip patterns that are rest intervals
    for m in re.finditer(r"(\d+)\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)", text_lower):
        val = m.group(1)
        unit = m.group(2)
        context_after = text_lower[m.end():m.end()+15]
        context_before = text_lower[max(0,m.start()-15):m.start()]
        if "rest" in context_after or "rest" in context_before:
            continue
        if "work" in context_after or "work" in context_before:
            continue
        if unit.startswith("min"):
            unit = "minutes"
        elif unit.startswith("hour") or unit.startswith("hr"):
            unit = "hours"
        elif unit.startswith("sec"):
            unit = "seconds"
        return f"{val} {unit}"
    return None


def _extract_calories(text: str) -> str | None:
    text_lower = text.lower()
    # "1200 calories", "900 cal", "2000 kcal"
    m = re.search(r"(\d+)\s*(?:calories?|cals?|kcal)", text_lower)
    if m:
        return m.group(1)
    # "calorie target 600", "calorie burn target 900"
    m = re.search(r"calorie\s+(?:burn\s+)?(?:target|goal|aim)\s+(\d+)", text_lower)
    if m:
        return m.group(1)
    # "target 900 calories", "burn around 1200"
    m = re.search(r"(?:target|burn|aim)\s+(?:around\s+|approximately\s+)?(\d+)\s*(?:calories?|cals?|kcal)?", text_lower)
    if m:
        # Make sure we're not matching a distance or non-calorie number
        val = int(m.group(1))
        if val >= 100:  # calories are typically > 100
            return m.group(1)
    # "calorie burn around 1200"
    m = re.search(r"calorie\s+burn\s+(?:around\s+)?(\d+)", text_lower)
    if m:
        return m.group(1)
    return None


def _extract_strength_details(text: str) -> dict:
    """Extract sets, reps, weight, and individual exercises."""
    result = {}
    text_lower = text.lower()

    # Global sets/reps: "5 sets of 5 reps" or "5x5" or "4 sets of 8"
    m = re.search(r"(\d+)\s*(?:sets?\s*(?:of|x)\s*)(\d+)\s*(?:reps?)?", text_lower)
    if m:
        result["sets"] = m.group(1)
        result["reps"] = m.group(2)

    if not m:
        # "5x5" pattern
        m = re.search(r"\b(\d+)\s*x\s*(\d+)\b", text_lower)
        if m:
            result["sets"] = m.group(1)
            result["reps"] = m.group(2)

    # "to failure"
    if "to failure" in text_lower or "til failure" in text_lower:
        result["reps"] = "To failure"

    # Weight: "80kg", "30 kg", "80 lbs", "30kg dumbbells"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|lbs?|pounds?)\s*(?:dumbbells?|barbell)?", text_lower)
    if m:
        val = m.group(1)
        unit = m.group(2)
        if unit.startswith("lb") or unit.startswith("pound"):
            unit = "lbs"
        else:
            unit = "kg"
        result["weight"] = f"{val} {unit}"

    # Individual exercises: look for common exercise names
    exercises = []
    exercise_patterns = [
        (r"(bench\s*press)", "Bench Press"),
        (r"(squats?)", "Squats"),
        (r"(deadlifts?)", "Deadlifts"),
        (r"(leg\s*press)", "Leg Press"),
        (r"(lunges?)", "Lunges"),
        (r"(pull[-\s]?ups?)", "Pull-ups"),
        (r"(push[-\s]?ups?)", "Push-ups"),
        (r"(bent\s*(?:over\s+)?rows?)", "Bent Rows"),
        (r"(curls?)", "Curls"),
        (r"(shoulder\s*press)", "Shoulder Press"),
        (r"(overhead\s*press)", "Overhead Press"),
        (r"(plank)", "Plank"),
        (r"(sit[-\s]?ups?)", "Sit-ups"),
        (r"(crunches?)", "Crunches"),
        (r"(dips?)\b", "Dips"),
        (r"(lat\s*pull\s*downs?)", "Lat Pulldowns"),
    ]
    for pattern, name in exercise_patterns:
        if re.search(pattern, text_lower):
            exercises.append(name)

    if exercises:
        result["exercises"] = exercises

    return result


def _extract_hiit_details(text: str) -> dict:
    """Extract HIIT-specific details: work/rest durations, rounds."""
    result = {}
    text_lower = text.lower()

    # Work duration: "30 seconds work"
    m = re.search(r"(\d+)\s*(?:seconds?|secs?|s)\s*(?:work|on)", text_lower)
    if m:
        result["work_duration"] = f"{m.group(1)} seconds"

    # Rest duration: "15 seconds rest"
    m = re.search(r"(\d+)\s*(?:seconds?|secs?|s)\s*(?:rest|off)", text_lower)
    if m:
        result["rest_duration"] = f"{m.group(1)} seconds"

    # Rounds: "20 rounds" or "for 20 rounds"
    m = re.search(r"(\d+)\s*rounds?", text_lower)
    if m:
        result["rounds"] = m.group(1)

    # Total duration
    m = re.search(r"total\s+(\d+)\s*(minutes?|mins?)", text_lower)
    if m:
        result["total_duration"] = f"{m.group(1)} minutes"

    return result


def _extract_multiple_days(text: str) -> list[str] | None:
    """Check for multiple day mentions like 'Monday Wednesday Friday'."""
    text_lower = text.lower()
    found_days = []
    today = datetime.now()

    for day_name, day_num in DAY_MAP.items():
        if len(day_name) <= 3:
            continue  # skip abbreviations to avoid double-counting
        if re.search(rf"\b{day_name}\b", text_lower):
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            d = today + timedelta(days=days_ahead)
            found_days.append((day_num, d.strftime("%A, %B %d, %Y")))

    if len(found_days) > 1:
        found_days.sort(key=lambda x: x[0])
        return [d[1] for d in found_days]
    return None


def _extract_heart_rate(text: str) -> str | None:
    """Extract heart rate targets, zones, ranges, and constraints."""
    text_lower = text.lower()

    # "not exceeding 160", "should not exceed 160"
    m = re.search(r"not\s+exceed(?:ing)?\s+(\d{2,3})", text_lower)
    if m:
        return f"Below {m.group(1)} bpm"

    # "heart rate below/under 150"
    m = re.search(r"(?:heart\s*rate|hr)\s*(?:below|under|less\s*than|<|max|not\s+exceeding)\s*(\d{2,3})", text_lower)
    if m:
        return f"Below {m.group(1)} bpm"

    # "heart rate above/over 120"
    m = re.search(r"(?:heart\s*rate|hr)\s*(?:above|over|more\s*than|>|min)\s*(\d{2,3})", text_lower)
    if m:
        return f"Above {m.group(1)} bpm"

    # Range zones: "zone 3 to 4", "zone 3-4", "zones 3 and 4"
    m = re.search(r"zone\s*(\d)\s*(?:to|-|and)\s*(\d)", text_lower)
    if m:
        return f"Zone {m.group(1)}-{m.group(2)}"

    # Dual zones: "zone 4 work, zone 2 rest" or "zone 4 during work zone 2 during rest"
    m1 = re.search(r"zone\s*(\d)\s*(?:work|during\s*work|on|active)", text_lower)
    m2 = re.search(r"zone\s*(\d)\s*(?:rest|during\s*rest|off|recovery)", text_lower)
    if m1 and m2:
        return f"Zone {m1.group(1)} (work) / Zone {m2.group(1)} (rest)"

    # Single zone: "zone 2", "HR zone 3"
    m = re.search(r"zone\s*(\d)", text_lower)
    if m:
        return f"Zone {m.group(1)}"

    # Specific BPM: "heart rate at 150"
    m = re.search(r"(?:heart\s*rate|hr)\s*(?:at|around)?\s*(\d{2,3})\s*(?:bpm|beats)?", text_lower)
    if m:
        return f"{m.group(1)} bpm"

    return None


def _extract_swimming_details(text: str) -> dict:
    """Extract swimming-specific details: sets, stroke, max duration."""
    result = {}
    text_lower = text.lower()

    # Sets: "30 sets of 100 meters", "10x100m", "20 sets of 50m"
    m = re.search(r"(\d+)\s*(?:sets?\s*(?:of|x)\s*)(\d+)\s*(?:m(?:eters?)?|metres?)", text_lower)
    if m:
        result["sets"] = m.group(1)
        result["set_distance"] = f"{m.group(2)}m"
    else:
        m = re.search(r"(\d+)\s*x\s*(\d+)\s*(?:m(?:eters?)?|metres?)?", text_lower)
        if m:
            result["sets"] = m.group(1)
            result["set_distance"] = f"{m.group(2)}m"

    # Stroke type: freestyle, backstroke, breaststroke, butterfly, medley
    strokes = ["freestyle", "backstroke", "breaststroke", "butterfly", "medley", "front crawl"]
    for stroke in strokes:
        if stroke in text_lower:
            result["stroke"] = stroke.title()
            break

    # Max/target duration: "complete in 75 minutes", "75 minutes maximum", "under 60 min"
    m = re.search(r"(?:complete|finish)\s*(?:in|within)\s*(\d+)\s*(?:minutes?|mins?)", text_lower)
    if m:
        result["max_duration"] = f"{m.group(1)} minutes"
    else:
        m = re.search(r"(\d+)\s*(?:minutes?|mins?)\s*(?:maximum|max|limit|cap)", text_lower)
        if m:
            result["max_duration"] = f"{m.group(1)} minutes"
        else:
            m = re.search(r"(?:under|within|less\s*than)\s*(\d+)\s*(?:minutes?|mins?)", text_lower)
            if m:
                result["max_duration"] = f"{m.group(1)} minutes"

    return result


def _extract_equipment(text: str) -> str | None:
    """Extract equipment, gear, and logistics mentions."""
    text_lower = text.lower()
    items = []

    # Equipment keywords (matched directly in text)
    equipment_kw = [
        ("knee sleeves", "Knee sleeves"), ("knee sleeve", "Knee sleeves"),
        ("lifting belt", "Lifting belt"),
        ("lifting straps", "Lifting straps"),
        ("foam roller", "Foam roller"),
        ("yoga mat", "Yoga mat"),
        ("water bottle", "Water bottle"),
        ("energy gel", "Energy gels"), ("energy gels", "Energy gels"),
        ("electrolyte drink", "Electrolyte drink"), ("electrolyte", "Electrolyte drink"),
        ("lifting gloves", "Lifting gloves"), ("gloves", "Gloves"),
        ("spike shoes", "Spikes"), ("spikes", "Spikes"),
    ]
    for kw, label in equipment_kw:
        if kw in text_lower and label not in items:
            items.append(label)

    # "bring X and Y" → try to capture specific objects
    m = re.search(r"bring\s+(?:your\s+)?([\w\s]+?)(?:\s+and\s+([\w\s]+?))?(?:[,.]|$)", text_lower)
    if m:
        for grp in [m.group(1), m.group(2)]:
            if grp:
                item = grp.strip()
                # Only add if it looks like an equipment item (not a person/action)
                if len(item) > 2 and item.split()[0] not in ("him", "her", "them", "the", "your"):
                    label = item.capitalize()
                    if label not in items and not any(label.lower() in existing.lower() for existing in items):
                        items.append(label)

    # "X are/is mandatory/required"
    m = re.search(r"(\w[\w\s]{2,20})\s+(?:are|is)\s+(?:mandatory|required|compulsory)", text_lower)
    if m:
        item = m.group(1).strip().capitalize()
        if not any(item.lower() in existing.lower() for existing in items):
            items.append(f"{item} (mandatory)")

    # "belt" standalone (lifting context)
    if re.search(r"\bbelt\b", text_lower) and "Lifting belt" not in items:
        # Only add in strength context
        if any(w in text_lower for w in ["squat", "deadlift", "gym", "strength", "leg"]):
            items.append("Lifting belt")

    # "straps" standalone
    if re.search(r"\bstraps\b", text_lower) and "Lifting straps" not in items:
        if any(w in text_lower for w in ["pull", "row", "gym", "strength", "upper"]):
            items.append("Lifting straps")

    # "mat" standalone (yoga/mobility context)
    if re.search(r"\bmat\b", text_lower) and "Yoga mat" not in items and "Mat" not in items:
        if any(w in text_lower for w in ["yoga", "mobility", "stretch", "foam"]):
            items.append("Mat")

    # Meeting point: "meet at X gate", "sports complex gate"
    m = re.search(r"meet\s+(?:at\s+)?(.{3,30}?)(?:\s+gate|\s*[,.]|$)", text_lower)
    if m:
        loc = m.group(1).strip()
        if len(loc) > 2:
            items.append(f"Meet at: {loc.capitalize()}")

    # Transition time: "transition time under 3 minutes"
    m = re.search(r"transition\s+time\s+(?:under|less\s+than|within|<)\s*(\d+)\s*(?:minutes?|mins?)", text_lower)
    if m:
        items.append(f"Transition time < {m.group(1)} min")

    return "; ".join(items) if items else None


def _extract_cadence(text: str) -> str | None:
    """Extract cadence/RPM targets."""
    text_lower = text.lower()
    # "85-90 rpm", "cadence 85 to 90"
    m = re.search(r"(?:cadence\s+)?(\d{2,3})\s*[-–to]+\s*(\d{2,3})\s*rpm", text_lower)
    if m:
        return f"{m.group(1)}-{m.group(2)} rpm"
    m = re.search(r"cadence\s+(\d{2,3})\s*(?:to|-)\s*(\d{2,3})", text_lower)
    if m:
        return f"{m.group(1)}-{m.group(2)} rpm"
    m = re.search(r"(\d{2,3})\s*rpm", text_lower)
    if m:
        return f"{m.group(1)} rpm"
    return None


def _extract_notes(text: str) -> str | None:
    """Extract special instructions, intentions, and notes."""
    text_lower = text.lower()
    notes = []

    if "nothing intense" in text_lower or "not intense" in text_lower:
        notes.append("Recovery - not intense")
    if "warm up" in text_lower or "warmup" in text_lower:
        notes.append("Include warm-up")
    if "cool down" in text_lower or "cooldown" in text_lower:
        notes.append("Include cool-down")
    if "stretch" in text_lower:
        notes.append("Include stretching")

    # Preparation/purpose phrases
    prep_patterns = [
        (r"marathon\s+preparation|marathon\s+prep", "Marathon preparation"),
        (r"race\s+(?:day\s+)?prep(?:aration)?", "Race preparation"),
        (r"base\s+building", "Base building"),
        (r"speed\s+(?:block\s+)?(?:work|training)", "Speed work"),
        (r"endurance\s+training", "Endurance training"),
        (r"active\s+recovery", "Active recovery"),
        (r"form\s+(?:work|drill|focus)", "Form focus"),
        (r"technique\s+(?:work|drill|focus)", "Technique focus"),
        (r"lactate\s+threshold\s+(?:work|training|run)", "Lactate threshold work"),
        (r"tempo\s+(?:work|training|run)", "Tempo work"),
        (r"race\s+day\s+simulation", "Race day simulation"),
        (r"equally\s+important\s+as", "Equally important as hard training"),
    ]
    for pat, label in prep_patterns:
        if re.search(pat, text_lower):
            notes.append(label)

    # Full focus / motivation
    if re.search(r"full\s+focus\s+(?:required|needed|mandatory)", text_lower):
        notes.append("Full focus required")

    # Coaching emphasis: "no skipping", "no excuses", "strictly", "mandatory"
    coaching_patterns = [
        (r"no\s+skipping\b", "No skipping"),
        (r"no\s+excuses?\b", "No excuses"),
        (r"\bstrictly\b", "Strict adherence"),
        (r"not\s+one\s+minute\s+late", "Be on time"),
        (r"be\s+(?:there\s+)?on\s+time", "Be on time"),
        (r"no\s+shortcuts?", "No shortcuts"),
    ]
    for pat, label in coaching_patterns:
        if re.search(pat, text_lower):
            notes.append(label)

    # Instruction phrases: "do not push beyond", "do not go faster"
    instruction_patterns = [
        (r"do\s+not\s+push\s+beyond\b.*?pace", "Do not push beyond given pace"),
        (r"do\s+not\s+go\s+faster\b", "Do not go faster than prescribed"),
        (r"do\s+not\s+skip\b", "Do not skip"),
    ]
    for pat, label in instruction_patterns:
        if re.search(pat, text_lower):
            notes.append(label)

    # Observer presence: "I will be there", "I shall observe"
    if re.search(r"i\s+will\s+be\s+(?:there|watching|present|observing)", text_lower):
        notes.append("Coach will be present")
    if re.search(r"i\s+(?:will|shall)\s+(?:observe|watch|monitor)", text_lower):
        notes.append("Coach will observe")

    # "only" qualifier at end
    m = re.search(r"(\w[\w\s]{3,30})\s+only\s*[.,!]?\s*$", text_lower)
    if m:
        phrase = m.group(1).strip()
        already_covered = False
        for n in notes:
            n_lower = n.lower()
            overlap_words = set(phrase.split()) & set(n_lower.split())
            if len(overlap_words) >= 2 or phrase in n_lower or n_lower in phrase:
                already_covered = True
                break
        if not already_covered:
            if not any(s in phrase for s in ["freestyle", "backstroke", "breaststroke", "butterfly"]):
                notes.append(f"{phrase.capitalize()} only")

    # Deduplicate preserving order
    seen = set()
    unique_notes = []
    for n in notes:
        if n not in seen:
            seen.add(n)
            unique_notes.append(n)

    return "; ".join(unique_notes) if unique_notes else None


def _extract_progressive_paces(text: str) -> tuple[str | None, str | None]:
    """Extract starting and finishing pace for progressive runs."""
    text_lower = text.lower()
    if "progressive" not in text_lower:
        return None, None

    paces = re.findall(r"(\d{1,2}:\d{2})", text_lower)
    if len(paces) >= 2:
        return f"{paces[0]}/km", f"{paces[1]}/km"
    return None, None


# ─── Main Parser ─────────────────────────────────────────────────────────────

def _build_assignment(athlete: str, text: str, doc, activity: str | None,
                      date_override: str | None = None) -> dict:
    """Build a single assignment dict with dynamic attributes."""
    attrs = []

    def add(key, value):
        if value is not None:
            attrs.append({"key": key, "value": value})

    # Core fields
    add("Name", athlete or "Unspecified")

    if not activity:
        activity = _detect_activity(text)
    add("Activity", activity or "General")

    # Build task description
    distance = _extract_distance(text, doc)
    pace = _extract_pace(text, doc)
    intensity = _extract_intensity(text)
    duration = _extract_duration(text)

    # Compose task string
    task_parts = []
    if intensity:
        task_parts.append(intensity.lower())
    if activity:
        verb_map = {
            "Running": "run", "Cycling": "ride", "Swimming": "swim",
            "Strength Training": "workout", "HIIT": "HIIT session",
            "Yoga": "yoga session", "Hiking": "hike",
        }
        task_parts.append(verb_map.get(activity, activity.lower()))
    if distance:
        task_parts.append(distance)
    if pace:
        task_parts.append(f"@ {pace}")

    task_desc = " ".join(task_parts).strip().capitalize() if task_parts else text.strip()
    add("Task", task_desc)

    # Distance & pace
    add("Distance", distance)
    add("Pace", pace)

    # Progressive paces
    start_pace, finish_pace = _extract_progressive_paces(text)
    if start_pace:
        add("Starting Pace", start_pace)
        add("Finishing Pace", finish_pace)

    # Duration (skip for HIIT — HIIT has its own Work/Rest/Total Duration fields)
    if activity != "HIIT":
        add("Duration", duration)

    # Intensity
    add("Intensity", intensity)

    # Time & Date
    time_val = _infer_time(text)
    add("Time", time_val)

    date_val = date_override or _infer_date(text)
    add("Date", date_val)

    # Location
    add("Location", _extract_location(text))

    # Calories
    add("Calories", _extract_calories(text))

    # Heart rate
    add("Heart Rate", _extract_heart_rate(text))

    # Strength-specific
    if activity == "Strength Training":
        strength = _extract_strength_details(text)
        if strength.get("exercises") and len(strength["exercises"]) > 1:
            ex_details = _parse_exercise_details(text, strength["exercises"])
            for i, (ex_name, detail) in enumerate(ex_details, 1):
                add(f"Exercise {i}", detail)
        else:
            if strength.get("exercises"):
                add("Exercise", strength["exercises"][0])
            add("Sets", strength.get("sets"))
            add("Reps", strength.get("reps"))
            add("Weight", strength.get("weight"))

    # Swimming-specific
    if activity == "Swimming":
        swim = _extract_swimming_details(text)
        add("Sets", f"{swim['sets']} × {swim['set_distance']}" if swim.get("sets") else None)
        add("Stroke", swim.get("stroke"))
        add("Max Duration", swim.get("max_duration"))

    # Cycling-specific
    if activity == "Cycling":
        add("Cadence", _extract_cadence(text))

    # HIIT-specific
    if activity == "HIIT":
        hiit = _extract_hiit_details(text)
        add("Work Duration", hiit.get("work_duration"))
        add("Rest Duration", hiit.get("rest_duration"))
        add("Rounds", hiit.get("rounds"))
        add("Total Duration", hiit.get("total_duration"))

    # Rest period (non-HIIT) — seconds or minutes
    if activity != "HIIT":
        m = re.search(r"(?:rest|recovery)\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?)", text.lower())
        if not m:
            m = re.search(r"(\d+)\s*(seconds?|secs?|s|minutes?|mins?)\s*(?:rest|recovery|between)", text.lower())
        if m:
            val = m.group(1)
            unit = m.group(2)
            if unit.startswith("min"):
                add("Rest", f"{val} minutes")
            else:
                add("Rest", f"{val} seconds")

    # Equipment & logistics
    add("Equipment", _extract_equipment(text))

    # Notes
    add("Notes", _extract_notes(text))

    return {"attributes": attrs}


def _parse_exercise_details(text: str, exercises: list[str]) -> list[tuple[str, str]]:
    """Try to extract per-exercise details (sets x reps) from text."""
    results = []
    text_lower = text.lower()

    for ex in exercises:
        # Look for pattern near the exercise name: "squats 4 sets of 8"
        ex_lower = ex.lower().replace("-", "[-\\s]?")
        m = re.search(
            rf"{ex_lower}\s*[-,:]?\s*(\d+)\s*sets?\s*(?:of|x)\s*(\d+)\s*(?:reps?)?",
            text_lower
        )
        if m:
            detail = f"{ex} - {m.group(1)} sets × {m.group(2)} reps"
        else:
            # Check for "X sets of Y" immediately before the exercise name
            m2 = re.search(
                rf"(\d+)\s*sets?\s*(?:of|x)\s*(\d+)\s*(?:reps?)?\s*[-,:]?\s*{ex_lower}",
                text_lower
            )
            if m2:
                detail = f"{ex} - {m2.group(1)} sets × {m2.group(2)} reps"
            else:
                # Check for "to failure"
                m3 = re.search(rf"{ex_lower}\s*.*?(?:to|til)\s*failure", text_lower)
                if m3:
                    # Find sets count nearby
                    m4 = re.search(rf"(\d+)\s*sets?\s*.*?{ex_lower}", text_lower)
                    sets_str = f"{m4.group(1)} sets " if m4 else ""
                    detail = f"{ex} - {sets_str}to failure"
                else:
                    detail = ex

        # Append weight if found near exercise
        m_w = re.search(rf"{ex_lower}\s*.*?(\d+(?:\.\d+)?)\s*(kg|lbs?)\s*(?:dumbbells?|barbell)?",
                        text_lower)
        if m_w:
            detail += f" @ {m_w.group(1)}{m_w.group(2)}"
            # Also check for equipment
            if "dumbbell" in text_lower:
                detail += " dumbbells"

        results.append((ex, detail))

    return results


def _split_into_segments(text: str) -> list[dict] | None:
    """Split text into workout segments for multi-activity or phased workouts.
    Returns a list of dicts with 'text' and optional 'label' keys, or None."""
    text_lower = text.lower()

    # Check for multi-activity transition markers
    # Pattern: "swim X ... transition/then bike Y ... then run Z"
    activities_found = []
    for activity, keywords in _ACTIVITY_PRIORITY:
        if activity in ("Rest", "Match/Game", "Cardio", "HIIT"):
            continue
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                activities_found.append(activity)
                break

    # Multi-activity (e.g., Triathlon): split by transition words
    if len(activities_found) >= 2:
        # Try to split by transition phrases
        parts = re.split(
            r"(?:,\s*)?(?:then\s+|followed\s+by\s+|transition\s+to\s+|after\s+that\s+|next\s+)",
            text, flags=re.IGNORECASE
        )
        if len(parts) >= 2:
            segments = []
            for part in parts:
                part = part.strip()
                if len(part) < 5:
                    continue
                activity = _detect_activity(part)
                if activity:
                    segments.append({"text": part, "activity": activity})
            if len(segments) >= 2:
                return segments

    # Phase-based: "first X ... then Y ... last Z" — same activity, different phases
    phase_parts = re.split(
        r"(?:,\s*)?(?:then\s+|followed\s+by\s+|after\s+that\s+|(?<=,\s)last\s+)",
        text, flags=re.IGNORECASE
    )
    if len(phase_parts) >= 2:
        has_segment_markers = bool(re.search(
            r"\b(?:first|last)\s+\d+\s*(?:km?|miles?|k)\b", text_lower
        ))
        if has_segment_markers:
            # Detect the primary activity for the whole workout
            parent_activity = _detect_activity(text)
            segments = []
            for i, part in enumerate(phase_parts):
                part = part.strip()
                if len(part) < 5:
                    continue
                if i == 0 or "warmup" in part.lower() or "warm up" in part.lower():
                    label = "Warmup"
                elif i == len(phase_parts) - 1 or "cooldown" in part.lower() or "cool down" in part.lower():
                    label = "Cooldown"
                else:
                    label = "Main"
                if "easy" in part.lower():
                    if i == 0:
                        label = "Warmup"
                    elif i == len(phase_parts) - 1:
                        label = "Cooldown"
                # Use parent activity for all segments (they're the same sport)
                segments.append({"text": part, "label": label, "activity": parent_activity})
            if len(segments) >= 2:
                return segments

    return None


def parse_workout_text(text: str) -> dict:
    """
    Dynamic workout parser. Returns:
    {
        "assignments": [ { "attributes": [ {"key": ..., "value": ...}, ... ] } ],
        "original_text": "...",
        "confidence": "High" | "Medium" | "Low"
    }
    """
    if not text or len(text.strip()) < 5:
        return {
            "assignments": [],
            "error": "No significant speech detected.",
            "original_text": text,
        }

    doc = nlp(text) if nlp else None

    if doc:
        print(f"DEBUG: Detected Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")

    # ── Check for multi-athlete scenario ────────────────────────────────
    multi_athletes = _extract_multiple_athletes(text)
    multi_days = _extract_multiple_days(text)

    activity = _detect_activity(text)
    if doc:
        for ent in doc.ents:
            if ent.label_ == "ACTIVITY" and not activity:
                activity = ent.text

    # ── Check for multi-activity / segmented workout ────────────────────
    segments = _split_into_segments(text)
    athlete = _extract_athlete(text, doc)

    assignments = []

    if segments and len(segments) >= 2:
        # Multi-activity or segmented workout
        # Shared attributes: name, time, date, heart rate, calories, equipment, notes
        time_val = _infer_time(text)
        date_val = _infer_date(text)
        hr_val = _extract_heart_rate(text)
        cal_val = _extract_calories(text)
        equip_val = _extract_equipment(text)
        notes_val = _extract_notes(text)

        for seg in segments:
            seg_text = seg["text"]
            seg_activity = seg.get("activity") or _detect_activity(seg_text) or activity
            seg_doc = nlp(seg_text) if nlp else None

            assignment = _build_assignment(
                athlete, seg_text, seg_doc, seg_activity
            )

            # Override shared fields from full text
            attrs = assignment["attributes"]
            attr_keys = {a["key"] for a in attrs}

            if "Time" not in attr_keys and time_val:
                attrs.append({"key": "Time", "value": time_val})
            if "Date" not in attr_keys and date_val:
                attrs.append({"key": "Date", "value": date_val})
            if "Heart Rate" not in attr_keys and hr_val:
                attrs.append({"key": "Heart Rate", "value": hr_val})
            if "Calories" not in attr_keys and cal_val:
                attrs.append({"key": "Calories", "value": cal_val})
            if "Equipment" not in attr_keys and equip_val:
                attrs.append({"key": "Equipment", "value": equip_val})
            if "Notes" not in attr_keys and notes_val:
                attrs.append({"key": "Notes", "value": notes_val})

            # Add segment label if present
            if seg.get("label"):
                attrs.insert(3, {"key": "Segment", "value": seg["label"]})

            # Ensure name is from the full text
            for a in attrs:
                if a["key"] == "Name":
                    a["value"] = athlete or "Unspecified"
                    break

            assignments.append(assignment)

    elif multi_athletes:
        for ath in multi_athletes:
            if multi_days:
                for day in multi_days:
                    assignments.append(
                        _build_assignment(ath, text, doc, activity, date_override=day)
                    )
            else:
                assignments.append(
                    _build_assignment(ath, text, doc, activity)
                )
    elif multi_days:
        for day in multi_days:
            assignments.append(
                _build_assignment(athlete, text, doc, activity, date_override=day)
            )
    else:
        assignments.append(
            _build_assignment(athlete, text, doc, activity)
        )

    # ── Calculate confidence ─────────────────────────────────────────────
    if assignments:
        sample = assignments[0]["attributes"]
        filled = sum(1 for a in sample if a["value"] is not None
                     and a["key"] not in ("Name", "Activity", "Task"))
        if filled >= 3:
            confidence = "High"
        elif filled >= 1:
            confidence = "Medium"
        else:
            confidence = "Low"
    else:
        confidence = "Low"

    # Remove attributes with None values
    for assignment in assignments:
        assignment["attributes"] = [
            a for a in assignment["attributes"] if a["value"] is not None
        ]

    if not assignments or all(len(a["attributes"]) <= 2 for a in assignments):
        return {
            "assignments": [],
            "error": "Could not understand the workout instruction.",
            "original_text": text,
        }

    return {
        "assignments": assignments,
        "original_text": text,
        "confidence": confidence,
    }
