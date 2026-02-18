import csv
import json
import re
import spacy
from spacy.tokens import DocBin
from tqdm import tqdm
import random
import os

# Load a blank English model
nlp = spacy.blank("en")


def find_substring_indices(text, substring):
    """Find start and end indices of a substring, case-insensitive logic/fuzzy matching could be added here."""
    if not substring:
        return -1, -1
    
    # Try exact match first
    start = text.find(substring)
    if start != -1:
        return start, start + len(substring)
    
    # Try case-insensitive
    start = text.lower().find(substring.lower())
    if start != -1:
        return start, start + len(substring)
    
    return -1, -1


def process_csv(csv_path):
    """Process the existing CSV dataset with pre-labeled JSON outputs."""
    training_data = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row['Coach Input']
            json_str = row['Parsed Output (JSON)']
            
            try:
                data = json.loads(json_str)
            except:
                continue
                
            entities = []
            
            # Mappings of JSON keys to NER Labels
            field_mappings = {
                "athlete": "PERSON",
                "distance": "DISTANCE",
                "time": "TIME",
                "pace": "PACE",
                "task_type": "ACTIVITY",
                "exercise": "EXERCISE"
            }
            
            for key, label in field_mappings.items():
                value = data.get(key)
                if not value:
                    continue
                
                if not isinstance(value, str):
                    value = str(value)
                    
                start, end = find_substring_indices(text, value)
                
                if start == -1:
                     if key == "task_type":
                         if value == "running" and "run" in text.lower():
                             value = "run"
                         elif value == "cycling" and "bike" in text.lower():
                             value = "bike"
                         elif value == "cycling" and "ride" in text.lower():
                             value = "ride"
                         elif value == "swimming" and "swim" in text.lower():
                             value = "swim"
                         elif value == "strength" and "lift" in text.lower():
                             value = "lift"
                         start, end = find_substring_indices(text, value)

                if start != -1:
                    entities.append((start, end, label))
            
            entities.sort(key=lambda x: x[0])
            
            final_entities = []
            if entities:
                last_end = -1
                for start, end, label in entities:
                    if start >= last_end:
                        final_entities.append((start, end, label))
                        last_end = end
                
                training_data.append((text, final_entities))

    return training_data


# ──────────────────────────────────────────────────────────
#  Auto-labeling for gap_filling_dataset.json
# ──────────────────────────────────────────────────────────

# Known name patterns used in the gap dataset (extracted from analysis)
_GAP_NAMES = {
    "Ayaan", "Sourav", "Advait", "Fernando", "Gabriela", "Ganesh", "Lars",
    "Myra", "Olga", "Wei", "Ayesha", "Partha", "Saanvi", "Sakura", "Zara",
    "Pierre", "Bilal", "Taka", "Mei", "Jun", "Chiamaka", "Subramaniam",
    "Chinonso", "Imran", "Sana", "Vihaan", "François", "Shaurya", "Isabella",
    "Narayanan", "Svetlana", "Kofi", "Björn", "Krishnan", "Matteo",
    "Venkatesan", "Aryan", "André", "Mandla", "Aadhya", "Carmen",
    "Hiro", "Giovanni", "Yui", "Debashis", "Balakrishnan", "Ira", "Zola",
    "Carlos", "Luca", "Dhruv", "Ramesh", "Ming", "Thor", "Sipho",
    "Li", "Kenji", "Marco", "Ahmed", "Navya", "Sven", "Ling",
    "Yuki", "Irina", "Diego", "Sandip", "Usman", "Mukesh", "José",
    "Natasha", "Björn",
    # Casual speech dataset names
    "Ayo", "Rishi", "Farid", "Gita", "Ngozi", "Paulo", "Dimitri",
    "Ananya", "Efe", "Lucía", "Kaede", "Boris", "Priti", "Emeka",
    "Rashid", "Yara", "Dmitri", "Fumiko", "Omari", "Ada",
    "Viktor", "Rina", "Tariq", "Chidera", "Rosa",
    "Nikolai", "Kenzo", "Freya", "Hassan", "Meera",
    # Common names in the CSV
    "Justin", "Ravi", "Ryan", "Neha", "Marcus", "Priya", "Sneha",
    "David", "Alex", "Sam", "Sarah", "John", "Mike", "Lisa",
    "Rahul", "Amit", "Emma", "James", "Maria",
}

# Build a case-insensitive lookup
_NAMES_LOWER = {n.lower(): n for n in _GAP_NAMES}

# Activity keywords and their canonical forms
_ACTIVITY_PATTERNS = [
    # Multi-word first (order matters for matching)
    (r"\bbench\s+press\b", "ACTIVITY"),
    (r"\bleg\s+press\b", "ACTIVITY"),
    (r"\bleg\s+day\b", "ACTIVITY"),
    (r"\bhill\s+repeats?\b", "ACTIVITY"),
    (r"\btempo\s+run\b", "ACTIVITY"),
    (r"\brecovery\s+run\b", "ACTIVITY"),
    (r"\bfartlek\s+session\b", "ACTIVITY"),
    (r"\bfartlek\b", "ACTIVITY"),
    (r"\bcross[\s-]?country\b", "ACTIVITY"),
    (r"\btrack\s+session\b", "ACTIVITY"),
    (r"\bplyometric\b", "ACTIVITY"),
    (r"\bplyometrics\b", "ACTIVITY"),
    (r"\bcircuit\s+training\b", "ACTIVITY"),
    (r"\bkettlebell\b", "ACTIVITY"),
    (r"\bdeadlift\b", "ACTIVITY"),
    (r"\bsquats?\b", "ACTIVITY"),
    (r"\blunges?\b", "ACTIVITY"),
    (r"\bpull[\s-]?ups?\b", "ACTIVITY"),
    (r"\bpush[\s-]?ups?\b", "ACTIVITY"),
    (r"\bburpees?\b", "ACTIVITY"),
    (r"\bbox\s+jumps?\b", "ACTIVITY"),
    (r"\bHIIT\s+session\b", "ACTIVITY"),
    (r"\bHIIT\b", "ACTIVITY"),
    (r"\byoga\b", "ACTIVITY"),
    (r"\bstretching\b", "ACTIVITY"),
    (r"\bintervals?\b", "ACTIVITY"),
    (r"\brun\b", "ACTIVITY"),
    (r"\brunning\b", "ACTIVITY"),
    (r"\bswim\b", "ACTIVITY"),
    (r"\bswimming\b", "ACTIVITY"),
    (r"\bcycle\b", "ACTIVITY"),
    (r"\bcycling\b", "ACTIVITY"),
    (r"\bbike\b", "ACTIVITY"),
    (r"\bride\b", "ACTIVITY"),
    (r"\bhike\b", "ACTIVITY"),
    (r"\bhiking\b", "ACTIVITY"),
    (r"\bsprint\b", "ACTIVITY"),
    (r"\bjog\b", "ACTIVITY"),
    (r"\bjogging\b", "ACTIVITY"),
    (r"\brow\b", "ACTIVITY"),
    (r"\browing\b", "ACTIVITY"),
    (r"\blift\b", "ACTIVITY"),
    (r"\bworkout\b", "ACTIVITY"),
]


def _auto_label_text(text):
    """
    Auto-label a raw coaching input sentence.
    Returns a list of (start, end, label) entity tuples.
    """
    entities = []
    text_lower = text.lower()

    # ── 1. PERSON detection ──
    # Pattern: "for <Name>" at end
    m = re.search(r"\bfor\s+([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+(?:\s+[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)?)\s*$", text)
    if m and m.group(1).lower() in _NAMES_LOWER:
        entities.append((m.start(1), m.end(1), "PERSON"))

    # Pattern: "<Name>," at start
    if not entities:
        m = re.match(r"^([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)\s*,", text)
        if m and m.group(1).lower() in _NAMES_LOWER:
            entities.append((m.start(1), m.end(1), "PERSON"))

    # Pattern: "assign/schedule/give <Name> (to|for)?"
    if not entities:
        m = re.search(r"\b(?:assign|schedule|give)\s+([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)", text)
        if m and m.group(1).lower() in _NAMES_LOWER:
            entities.append((m.start(1), m.end(1), "PERSON"))

    # Pattern: "ok/hey <Name> should/has/needs"
    if not entities:
        m = re.search(r"\b(?:ok|hey|yo|like|so)\s+([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)\b", text)
        if m and m.group(1).lower() in _NAMES_LOWER:
            entities.append((m.start(1), m.end(1), "PERSON"))

    # Pattern: "<Name> needs/should/has/will/gotta"  
    if not entities:
        m = re.search(r"\b([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+)\s+(?:needs?|should|has|will|gotta|gonna)\b", text)
        if m and m.group(1).lower() in _NAMES_LOWER:
            entities.append((m.start(1), m.end(1), "PERSON"))

    # Fallback: scan for any known name (case-insensitive word boundary match)
    if not entities:
        for name_lower, name_orig in _NAMES_LOWER.items():
            pattern = r"\b" + re.escape(name_orig) + r"\b"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                entities.append((m.start(), m.end(), "PERSON"))
                break

    # ── 2. DISTANCE detection ──
    # "10km", "5 miles", "2000m", "10k", "8x400m"
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(km|kilometers?|miles?|k|m|meters?)\b", text_lower):
        start = m.start()
        end = m.end()
        # Find actual position in original text
        entities.append((start, end, "DISTANCE"))

    # ── 3. TIME detection ──
    # "6am", "7:30pm", "5:30am"
    for m in re.finditer(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", text_lower):
        entities.append((m.start(), m.end(), "TIME"))
    # "morning", "evening", "tonight", "afternoon"
    for m in re.finditer(r"\b(morning|evening|tonight|afternoon|night)\b", text_lower):
        entities.append((m.start(), m.end(), "TIME"))

    # ── 4. PACE detection ──
    # "5:00/km", "5:00 per km", "25 kmph", "25 km/h"
    for m in re.finditer(r"\b(\d{1,2}:\d{2}\s*/\s*km|\d{1,2}:\d{2}\s+per\s+km)\b", text_lower):
        entities.append((m.start(), m.end(), "PACE"))
    for m in re.finditer(r"\b(\d+(?:\.\d+)?\s*(?:km/?h|kmph|mph))\b", text_lower):
        entities.append((m.start(), m.end(), "PACE"))

    # ── 5. ACTIVITY detection (use regex patterns) ──
    found_activities = set()
    for pattern, label in _ACTIVITY_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            # Avoid duplicates / overlaps
            span_key = (m.start(), m.end())
            if span_key not in found_activities:
                overlaps = False
                for s, e, _ in entities:
                    if not (m.end() <= s or m.start() >= e):
                        overlaps = True
                        break
                if not overlaps:
                    entities.append((m.start(), m.end(), label))
                    found_activities.add(span_key)
                    break  # Only match the first occurrence of each pattern

    # ── Deduplicate and sort ──
    entities.sort(key=lambda x: x[0])

    # Remove overlapping entities (keep the first/longest)
    final = []
    last_end = -1
    for start, end, label in entities:
        if start >= last_end:
            final.append((start, end, label))
            last_end = end

    return final


def process_gap_json(json_path):
    """
    Process gap_filling_dataset.json — reads raw input text,
    auto-labels entities using heuristics, returns training format.
    """
    training_data = []

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for entry in data:
        text = entry.get("input", "").strip()
        if not text:
            continue

        entities = _auto_label_text(text)

        if entities:
            training_data.append((text, entities))

    return training_data


def train_spacy_model(data):
    db = DocBin()
    
    skipped = 0
    for text, annotations in tqdm(data):
        doc = nlp.make_doc(text)
        ents = []
        for start, end, label in annotations:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is None:
                skipped += 1
            else:
                ents.append(span)
        
        try:
             doc.ents = spacy.util.filter_spans(ents)
             db.add(doc)
        except Exception as e:
            skipped += 1

    print(f"Skipped {skipped} entities/docs due to alignment issues.")
    return db


if __name__ == "__main__":
    all_data = []

    # ── Source 1: CSV dataset ──
    csv_file = "data/comprehensive_training_dataset_randomized_900.csv"
    if not os.path.exists(csv_file):
        # Fallback to old location
        csv_file = "comprehensive_training_dataset_randomized_900.csv"

    if os.path.exists(csv_file):
        print(f"Processing CSV: {csv_file}...")
        csv_data = process_csv(csv_file)
        print(f"  → {len(csv_data)} examples from CSV")
        all_data.extend(csv_data)
    else:
        print("Warning: CSV dataset not found, skipping.")

    # ── Source 2: Gap-filling JSON dataset ──
    gap_file = "data/gap_filling_dataset.json"
    if os.path.exists(gap_file):
        print(f"Processing JSON: {gap_file}...")
        gap_data = process_gap_json(gap_file)
        print(f"  → {len(gap_data)} examples from gap dataset")
        all_data.extend(gap_data)
    else:
        print("Warning: Gap-filling dataset not found, skipping.")

    print(f"\nTotal combined training examples: {len(all_data)}")

    if not all_data:
        print("Error: No training data found.")
        exit(1)

    # Shuffle and split 80/20
    random.seed(42)
    random.shuffle(all_data)
    split_idx = int(len(all_data) * 0.8)
    train_data = all_data[:split_idx]
    dev_data = all_data[split_idx:]

    print(f"Train: {len(train_data)}, Dev: {len(dev_data)}")

    # Save to disk
    train_db = train_spacy_model(train_data)
    train_db.to_disk("./train.spacy")
    
    dev_db = train_spacy_model(dev_data)
    dev_db.to_disk("./dev.spacy")
    
    print("\n✅ Created train.spacy and dev.spacy. Ready to train!")
    print("Run: python3 -m spacy train config.cfg --output ./output --paths.train ./train.spacy --paths.dev ./dev.spacy")
