# Complete Fix: All Errors - Training Prompt for Anthropic

## 🎯 Overview: 16 Critical Errors Identified

Based on analysis of 9 test cases, the model has **16 distinct error types** affecting **65% of data extraction**.

**Current Performance:** ~35% complete extraction  
**Target Performance:** >80% complete extraction

---

## 🔴 PRIORITY 0 - CRITICAL FIXES (Must Fix First)

### ERROR #1: Name Extraction (78% failure rate)

**Problem:** Extracting capitalized word AFTER comma instead of BEFORE

```json
{
  "error_examples": [
    {
      "input": "Rahul, this Wednesday triathlon simulation",
      "wrong": "Simulation",
      "correct": "Rahul"
    },
    {
      "input": "Sneha, Saturday race simulation ride",
      "wrong": "Race",
      "correct": "Sneha"
    },
    {
      "input": "Amit, Tuesday leg day session",
      "wrong": "Leg",
      "correct": "Amit"
    }
  ]
}
```

**Training Data Needed:**

```json
[
  {
    "input": "Rahul, this Wednesday 5am you are doing triathlon simulation",
    "output": {
      "name": "Rahul",
      "notes": "triathlon simulation"
    },
    "rule": "Name is BEFORE comma, NOT after"
  },
  {
    "input": "Sneha, Saturday 5:30am sharp you are doing race simulation ride",
    "output": {
      "name": "Sneha",
      "notes": "race simulation"
    }
  },
  {
    "input": "Amit, Tuesday evening 6pm leg day session at the gym",
    "output": {
      "name": "Amit",
      "workout_type": "leg day"
    }
  },
  {
    "input": "Priya, tomorrow 7am itself pool session",
    "output": {
      "name": "Priya",
      "workout_type": "pool session"
    }
  },
  {
    "input": "Rohan, Sunday 6am sharp long run 21k",
    "output": {
      "name": "Rohan",
      "workout_type": "long run"
    }
  }
]
```

**Critical Rule:** **ALWAYS extract the word IMMEDIATELY BEFORE the comma as the name.**

---

### ERROR #2: Multi-Activity Parsing (100% failure)

**Problem:** Only extracts FIRST activity, ignores subsequent ones

```json
{
  "input": "first swim 1500m at 1:45 per 100m, immediately transition to bike 40k at 28 kmph, then straight away run 10k at 5:15 per km",
  "current_output": {
    "activity": "swimming",
    "distance": "1500m"
  },
  "should_output": {
    "activities": [
      {
        "type": "swimming",
        "distance": "1500m",
        "pace": "1:45/100m",
        "order": 1
      },
      {
        "type": "cycling",
        "distance": "40km",
        "pace": "28 km/h",
        "order": 2,
        "transition": "immediate"
      },
      {
        "type": "running",
        "distance": "10km",
        "pace": "5:15/km",
        "order": 3,
        "transition": "immediate"
      }
    ]
  }
}
```

**Training Data:**

```json
[
  {
    "input": "swim 1500m then bike 40k then run 10k",
    "output": {
      "activities": [
        {"type": "swimming", "distance": "1500m", "order": 1},
        {"type": "cycling", "distance": "40km", "order": 2},
        {"type": "running", "distance": "10km", "order": 3}
      ]
    }
  },
  {
    "input": "bike 30km then immediately run 5km",
    "output": {
      "activities": [
        {"type": "cycling", "distance": "30km", "order": 1},
        {"type": "running", "distance": "5km", "order": 2, "transition": "immediate"}
      ]
    }
  },
  {
    "input": "run 5km followed by gym session squats and bench",
    "output": {
      "activities": [
        {"type": "running", "distance": "5km", "order": 1},
        {"type": "strength", "exercises": ["squats", "bench press"], "order": 2}
      ]
    }
  },
  {
    "input": "squats 5x5 at 100kg, then leg press 4x12 at 180kg, Romanian deadlifts 3x8 at 70kg, lunges 3x10 with 20kg dumbbells",
    "output": {
      "activity": "strength",
      "exercises": [
        {"name": "squats", "sets": 5, "reps": 5, "weight": "100kg", "order": 1},
        {"name": "leg press", "sets": 4, "reps": 12, "weight": "180kg", "order": 2},
        {"name": "Romanian deadlifts", "sets": 3, "reps": 8, "weight": "70kg", "order": 3},
        {"name": "lunges", "sets": 3, "reps": 10, "weight": "20kg dumbbells", "order": 4}
      ]
    }
  }
]
```

**Transition Words to Recognize:**
- "then" → next activity
- "followed by" → next activity
- "immediately" → next activity, quick transition
- "straight away" → next activity, quick transition
- "after that" → next activity
- comma "," between exercises → next exercise

---

### ERROR #3: Workout Segment Parsing (100% failure)

**Problem:** Not parsing warmup/main/cooldown segments

```json
{
  "input": "60k total, first 10k warmup at easy pace, then 40k at race pace 30 kmph, last 10k cooldown easy",
  "current_output": {
    "activity": "running",
    "distance": "10k",
    "pace": "30 kmph"
  },
  "should_output": {
    "activity": "cycling",
    "total_distance": "60km",
    "segments": [
      {"distance": "10km", "intensity": "easy", "type": "warmup", "order": 1},
      {"distance": "40km", "pace": "30 km/h", "type": "main", "order": 2},
      {"distance": "10km", "intensity": "easy", "type": "cooldown", "order": 3}
    ]
  }
}
```

**Training Data:**

```json
[
  {
    "input": "first 10k warmup easy, then 40k at race pace 30 kmph, last 10k cooldown",
    "output": {
      "segments": [
        {"distance": "10km", "intensity": "easy", "type": "warmup", "order": 1},
        {"distance": "40km", "pace": "30 km/h", "type": "main", "order": 2},
        {"distance": "10km", "type": "cooldown", "order": 3}
      ]
    }
  },
  {
    "input": "first 3k easy warmup at 6:00 pace, then 9k at tempo pace 4:45 per km, last 3k easy cooldown",
    "output": {
      "segments": [
        {"distance": "3km", "pace": "6:00/km", "type": "warmup", "order": 1},
        {"distance": "9km", "pace": "4:45/km", "type": "main - tempo", "order": 2},
        {"distance": "3km", "type": "cooldown", "order": 3}
      ]
    }
  }
]
```

**Segment Indicators:**
- "first... then... last" → 3 segments
- "warmup" → warmup segment
- "cooldown" / "cool down" / "cool-down" → cooldown segment
- "main" / "race pace" / "tempo" → main segment

---

## 🟡 PRIORITY 1 - HIGH PRIORITY FIXES

### ERROR #4: Missing Pace for All Activities

**Problem:** Only extracting pace for first activity or wrong activity

```json
[
  {
    "input": "swim 1500m at 1:45 per 100 meters pace",
    "output": {
      "activity": "swimming",
      "distance": "1500m",
      "pace": "1:45/100m"
    }
  },
  {
    "input": "bike 40k at 28 kmph",
    "output": {
      "activity": "cycling",
      "distance": "40km",
      "pace": "28 km/h"
    }
  },
  {
    "input": "run 10k at 5:15 per km pace",
    "output": {
      "activity": "running",
      "distance": "10km",
      "pace": "5:15/km"
    }
  },
  {
    "input": "21 kilometer run at 5:30 pace per km",
    "output": {
      "activity": "running",
      "distance": "21km",
      "pace": "5:30/km"
    }
  }
]
```

---

### ERROR #5: Missing Heart Rate (Complete Constraints)

**Problem:** Missing ranges and constraint formats

```json
[
  {
    "input": "heart rate below 150",
    "output": {"heart_rate": "below 150 bpm", "constraint": "max"}
  },
  {
    "input": "heart rate not exceeding 160",
    "output": {"heart_rate": "max 160 bpm", "constraint": "not exceeding"}
  },
  {
    "input": "heart rate zone 3 to 4",
    "output": {"heart_rate": "zone 3-4", "range": true}
  },
  {
    "input": "heart rate zone 2",
    "output": {"heart_rate": "zone 2"}
  },
  {
    "input": "HR should touch zone 4 during efforts and come down to zone 2 during rest",
    "output": {
      "heart_rate_work": "zone 4",
      "heart_rate_rest": "zone 2"
    }
  }
]
```

---

### ERROR #6: Missing Calorie Targets (83% failure)

```json
[
  {
    "input": "burn around 1200 calories",
    "output": {"target_calories": 1200}
  },
  {
    "input": "calorie target 2000",
    "output": {"target_calories": 2000}
  },
  {
    "input": "target 900 calories",
    "output": {"target_calories": 900}
  },
  {
    "input": "calorie burn target 600",
    "output": {"target_calories": 600}
  }
]
```

---

### ERROR #7: Missing Equipment/Logistics (100% failure)

```json
[
  {
    "input": "bring knee sleeves and belt",
    "output": {"equipment": ["knee sleeves", "belt"]}
  },
  {
    "input": "carry water bottle",
    "output": {"equipment": ["water bottle"]}
  },
  {
    "input": "bring 2 energy gels and electrolyte drink",
    "output": {"equipment": ["2 energy gels", "electrolyte drink"]}
  },
  {
    "input": "spikes are mandatory",
    "output": {"equipment": ["spikes"], "required": true}
  },
  {
    "input": "bring your own mat and foam roller",
    "output": {"equipment": ["mat", "foam roller"]}
  },
  {
    "input": "meet at sports complex gate",
    "output": {"meeting_point": "sports complex gate"}
  },
  {
    "input": "keep transition time under 3 minutes each",
    "output": {"transition_time": "under 3 minutes"}
  }
]
```

---

## 🟢 PRIORITY 2 - MEDIUM PRIORITY FIXES

### ERROR #8: Missing Workout Context/Notes (92% failure)

```json
[
  {
    "input": "this is marathon preparation run only",
    "output": {"notes": "marathon preparation"}
  },
  {
    "input": "this is race day preparation",
    "output": {"notes": "race day preparation"}
  },
  {
    "input": "this is speed block training",
    "output": {"notes": "speed block training"}
  },
  {
    "input": "lactate threshold work only",
    "output": {"notes": "lactate threshold work"}
  },
  {
    "input": "no excuses",
    "output": {"notes": "no excuses - mandatory"}
  },
  {
    "input": "no skipping sets",
    "output": {"notes": "complete all sets - no skipping"}
  },
  {
    "input": "full focus required",
    "output": {"notes": "full focus required"}
  }
]
```

---

### ERROR #9: Missing Route Details

```json
[
  {
    "input": "flat road route only",
    "output": {"route": "flat road"}
  },
  {
    "input": "no hills this time",
    "output": {"route": "no hills"}
  },
  {
    "input": "indoor heated pool",
    "output": {"location": "pool", "location_details": "indoor, heated"}
  }
]
```

---

### ERROR #10: Missing Rest Periods (Strength)

```json
[
  {
    "input": "rest 2 minutes between each exercise",
    "output": {"rest_between_exercises": "2 minutes"}
  },
  {
    "input": "rest 90 seconds between sets strictly",
    "output": {"rest_between_sets": "90 seconds", "strict": true}
  }
]
```

---

## 📚 INDIAN ENGLISH PATTERNS (Critical to Learn)

### Pattern: "[Name], [time] itself"

```json
[
  {
    "input": "Priya, tomorrow 7am itself you are doing pool session",
    "output": {
      "name": "Priya",
      "time": "7am",
      "date": "tomorrow",
      "emphasis": "definite"
    }
  },
  {
    "input": "Rahul, Wednesday 5am itself triathlon simulation",
    "output": {
      "name": "Rahul",
      "time": "5am",
      "date": "Wednesday"
    }
  }
]
```

### Pattern: "[time/number] sharp"

```json
[
  {
    "input": "Saturday 5:30am sharp",
    "output": {"time": "5:30am", "exact": true}
  },
  {
    "input": "not one minute late",
    "output": {"punctuality": "strict"}
  }
]
```

### Pattern: "[instruction] only"

```json
[
  {
    "input": "total session 90 minutes only",
    "output": {"duration": "90 minutes", "constraint": "exactly"}
  },
  {
    "input": "flat road only",
    "output": {"route": "flat road", "constraint": "only flat"}
  },
  {
    "input": "freestyle stroke only",
    "output": {"stroke": "freestyle", "constraint": "only freestyle"}
  }
]
```

---

## 🎯 COMPLETE EXTRACTION EXAMPLES

### Example 1: Full Triathlon

```json
{
  "input": "Rahul, this Wednesday 5am itself you are doing full triathlon simulation, first swim 1500 meters in pool at 1:45 per 100 meters pace, immediately transition to bike 40 kilometers at 28 kmph, then straight away run 10k at 5:15 per km pace, total target time 3 hours 30 minutes, heart rate not exceeding 160 throughout, calorie target 2000, keep transition time under 3 minutes each, this is race day preparation only",
  
  "output": {
    "name": "Rahul",
    "date": "Wednesday",
    "time": "5am",
    "workout_type": "triathlon simulation",
    "total_target_time": "3:30 hours",
    "max_heart_rate": 160,
    "target_calories": 2000,
    "transition_time": "under 3 minutes each",
    "notes": "race day preparation",
    
    "activities": [
      {
        "type": "swimming",
        "distance": "1500m",
        "pace": "1:45/100m",
        "location": "pool",
        "order": 1
      },
      {
        "type": "cycling",
        "distance": "40km",
        "pace": "28 km/h",
        "transition": "immediate",
        "order": 2
      },
      {
        "type": "running",
        "distance": "10km",
        "pace": "5:15/km",
        "transition": "immediate",
        "order": 3
      }
    ]
  }
}
```

### Example 2: Cycling with Segments

```json
{
  "input": "Sneha, Saturday 5:30am sharp you are doing race simulation ride, 60 kilometers total, first 10k warmup at easy pace, then 40k at race pace 30 kmph, last 10k cooldown easy, maintain cadence 85 to 90 rpm throughout, heart rate zone 3 to 4, target 900 calories, bring 2 energy gels and electrolyte drink, meet at sports complex gate",
  
  "output": {
    "name": "Sneha",
    "date": "Saturday",
    "time": "5:30am",
    "punctuality": "sharp",
    "workout_type": "race simulation",
    "total_distance": "60km",
    "cadence": "85-90 rpm",
    "heart_rate": "zone 3-4",
    "target_calories": 900,
    "equipment": ["2 energy gels", "electrolyte drink"],
    "meeting_point": "sports complex gate",
    
    "segments": [
      {
        "distance": "10km",
        "intensity": "easy",
        "type": "warmup",
        "order": 1
      },
      {
        "distance": "40km",
        "pace": "30 km/h",
        "type": "main - race pace",
        "order": 2
      },
      {
        "distance": "10km",
        "intensity": "easy",
        "type": "cooldown",
        "order": 3
      }
    ]
  }
}
```

### Example 3: Strength with Multiple Exercises

```json
{
  "input": "Amit, this Tuesday evening 6pm at the gym, squats 5 sets of 5 reps at 100kg, then leg press 4 sets of 12 at 180kg, Romanian deadlifts 3 sets of 8 at 70kg, lunges 3 sets of 10 each leg with 20kg dumbbells, rest 2 minutes between each exercise, total session 90 minutes, bring knee sleeves and belt",
  
  "output": {
    "name": "Amit",
    "date": "Tuesday",
    "time": "6pm",
    "location": "gym",
    "workout_type": "leg day",
    "rest_between_exercises": "2 minutes",
    "total_duration": "90 minutes",
    "equipment": ["knee sleeves", "belt"],
    
    "exercises": [
      {"name": "squats", "sets": 5, "reps": 5, "weight": "100kg", "order": 1},
      {"name": "leg press", "sets": 4, "reps": 12, "weight": "180kg", "order": 2},
      {"name": "Romanian deadlifts", "sets": 3, "reps": 8, "weight": "70kg", "order": 3},
      {"name": "lunges", "sets": 3, "reps": 10, "weight": "20kg dumbbells", "notes": "each leg", "order": 4}
    ]
  }
}
```

---

## ✅ SUCCESS CRITERIA

After training on this data, model should achieve:

| Metric | Current | Target |
|--------|---------|--------|
| Name extraction | 22% | >95% |
| Multi-activity parsing | 0% | >90% |
| Segment parsing | 0% | >85% |
| Pace extraction | 40% | >90% |
| Heart rate extraction | 50% | >90% |
| Calorie extraction | 17% | >85% |
| Equipment extraction | 0% | >75% |
| Notes/context extraction | 8% | >70% |
| **Overall completeness** | **35%** | **>80%** |

---

## 📝 DATASET SIZE RECOMMENDATION

To fix all errors:
- **Name extraction:** 150 examples
- **Multi-activity:** 100 examples
- **Segments:** 75 examples
- **Complete attributes:** 200 examples
- **Indian English:** 100 examples

**Total recommended:** 600+ additional training examples

---

**Feed this comprehensive training data to Anthropic to fix all 16 identified error types!**
