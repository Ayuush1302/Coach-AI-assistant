import csv
import json
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
                "exercise": "EXERCISE" # For strength/intervals
            }
            
            # Special handling for Activity because text often says "run" but JSON says "running"
            # We will try to find keywords if exact match fails
            
            for key, label in field_mappings.items():
                value = data.get(key)
                if not value:
                    continue
                
                # Convert non-string values to string (e.g. reps: 10)
                if not isinstance(value, str):
                    value = str(value)
                    
                start, end = find_substring_indices(text, value)
                
                # If parsed value not found exactly, try heuristics for common mismatches
                if start == -1:
                     if key == "task_type":
                         # Heuristics for tasks
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
            
            # Filter overlapping entities (SpaCy requires this)
            # We keep the longer entity if overlap occurs, or just greedy
            # Simple sorting by start index
            entities.sort(key=lambda x: x[0])
            
            final_entities = []
            if entities:
                # Basic overlap removal
                last_end = -1
                for start, end, label in entities:
                    if start >= last_end:
                        final_entities.append((start, end, label))
                        last_end = end
                
                training_data.append((text, final_entities))

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
        
        # Filter overlaps again at Span level just in case
        try:
             doc.ents = spacy.util.filter_spans(ents)
             db.add(doc)
        except Exception as e:
            # print(f"Skipping doc: {e}")
            skipped += 1

    print(f"Skipped {skipped} entities/docs due to alignment issues.")
    return db

if __name__ == "__main__":
    csv_file = "comprehensive_training_dataset_randomized_900.csv"
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        exit(1)
        
    print(f"Processing {csv_file}...")
    full_data = process_csv(csv_file)
    print(f"Found {len(full_data)} valid training examples.")
    
    # Shuffle and split
    random.shuffle(full_data)
    split_idx = int(len(full_data) * 0.8)
    train_data = full_data[:split_idx]
    dev_data = full_data[split_idx:]
    
    # Save to disk
    train_db = train_spacy_model(train_data)
    train_db.to_disk("./train.spacy")
    
    dev_db = train_spacy_model(dev_data)
    dev_db.to_disk("./dev.spacy")
    
    print("Created train.spacy and dev.spacy. Ready to train!")
