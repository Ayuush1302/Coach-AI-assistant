import os
import re
import spacy

# Load SpaCy model (Custom trained > Generic > None)
model_path = "./output/model-best"
try:
    if os.path.exists(model_path):
        nlp = spacy.load(model_path)
        print(f"Loaded custom model from {model_path}")
    else:
        nlp = spacy.load("en_core_web_sm")
        print("Loaded generic model en_core_web_sm")
except OSError:
    nlp = None
    print("Warning: No spacy model found.")

def parse_workout_text(text: str) -> dict:
    """
    Refined parser using Custom NER model.
    """
    if not text or len(text.strip()) < 5:
         return {
            "athlete": None,
            "task_type": None,
            "error": "No significant speech detected."
        }

    text_lower = text.lower()
    doc = nlp(text) if nlp else None
    
    # Initialize fields
    athlete = None
    task_type = None
    distance = None
    time_scheduled = None
    pace = None
    
    # 1. Extraction via NER (Custom Model Labels: PERSON, ACTIVITY, DISTANCE, TIME, PACE)
    if doc:
        print(f"DEBUG: Detected Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                athlete = ent.text
            elif ent.label_ == "ACTIVITY":
                # Trust the model more, even if it has digits (e.g. "5k run", "10x400m")
                task_type = ent.text
            elif ent.label_ == "DISTANCE":
                distance = ent.text
            elif ent.label_ == "TIME":
                time_scheduled = ent.text
            elif ent.label_ == "PACE":
                pace = ent.text

    # 2. Robust Fallbacks & Validations

    # Athlete: Regex Fallback
    if not athlete:
        # "assign ayush ..." -> match "ayush"
        match = re.search(r"(?:assign|give|to) (\w+)", text, re.IGNORECASE)
        # Avoid common stopwords
        if match:
             candidate = match.group(1)
             if candidate.lower() not in ["a", "an", "the", "to", "him", "her", "me", "new", "workout"]:
                 athlete = candidate.title()
        
        if not athlete:
             match = re.search(r"assign .* to (\w+)", text, re.IGNORECASE)
             if match: athlete = match.group(1).title()

    # Task Type: Fallback
    if not task_type:
         # Try to find common activity verbs/nouns if model failed
         # We want to support "anything", so we look for structure "do [ACTIVITY]" or simple keywords
         
         # Common sports keywords (expanded)
         if "run" in text_lower or "jog" in text_lower: task_type = "Run"
         elif "bike" in text_lower or "cycle" in text_lower: task_type = "Cycling"
         elif "swim" in text_lower or "pool" in text_lower: task_type = "Swimming"
         elif "lift" in text_lower or "strength" in text_lower or "gym" in text_lower: task_type = "Strength"
         elif "rest" in text_lower or "recovery" in text_lower: task_type = "Rest"
         elif "yoga" in text_lower: task_type = "Yoga"
         elif "hike" in text_lower: task_type = "Hiking"
         elif "game" in text_lower or "match" in text_lower: task_type = "Match/Game"
         
         # Fallback: Extract from "do X"
         if not task_type:
             match = re.search(r"\bdo\s+([a-zA-Z]+)", text_lower)
             if match and match.group(1) not in ["not", "rounds", "laps", "sets", "reps", "km", "miles"]:
                 task_type = match.group(1).title()

    # Quantity/Distance: Regex Fallback (Expanded units)
    if not distance:
        # Matches: "10km", "10 km", "10 rounds", "5 laps", "3 sets", "10x400m"
        # Negative lookahead (?!/) prevents matching "20km" inside "20km/h"
        
        # Unit-based match
        dist_match = re.search(r"(\d+(?:\.\d+)?\s*(?:km|miles|k|m)(?![\w/])|rounds|laps|sets|reps|x\d+|min|sec|hours)", text_lower)
        if dist_match: 
            distance = dist_match.group(0).strip()
        else:
             # Check for "10 x 400" pattern
             x_match = re.search(r"(\d+\s*x\s*\d+\s*\w*)", text_lower)
             if x_match:
                 distance = x_match.group(1)
             else:
                 # Check for simple "10 rounds" (the | inside group above might be tricky with precendence)
                 # Let's split it for clarity
                 rounds_match = re.search(r"(\d+\s*(?:rounds|laps|sets|reps))", text_lower)
                 if rounds_match: distance = rounds_match.group(1)
                 else:
                     # Basic km/miles again with lookahead
                     basic_dist = re.search(r"(\d+(?:\.\d+)?\s*(?:km|miles|k|m)(?![\w/]))", text_lower)
                     if basic_dist: distance = basic_dist.group(1)


    # Time: Regex Fallback
    if not time_scheduled:
        time_match = re.search(r"(\d{1,2}(:\d{2})?\s?(am|pm))", text_lower)
        if time_match: time_scheduled = time_match.group(1)

    # Pace: Regex Fallback
    if not pace:
         pace_match = re.search(r"(\d{1,2}:\d{2}(/km|/mile)?)", text_lower)
         if pace_match: pace = pace_match.group(1)



    # Calculate parsing confidence
    confidence = "Low"
    detected_fields = [athlete, task_type, distance, pace, time_scheduled]
    detected_count = sum(1 for f in detected_fields if f is not None)
    
    if detected_count >= 3:
        confidence = "High"
    elif detected_count >= 1:
        confidence = "Medium"

    if detected_count == 0:
         return {
            "athlete": None,
            "task_type": None,
            "error": "Could not understand the workout instruction."
        }

    return {
        "athlete": athlete or "Unspecified",
        "task_type": task_type or "General",
        "distance": distance,
        "pace": pace,
        "time": time_scheduled,
        "confidence": confidence,
        "original_text": text,
        "parsed_details": {
             "note": f"Parsed using {'Custom Model' if os.path.exists(model_path) else 'Generic Rules'}"
        }
    }

