"""Taxonomy and thresholds, GENERATED from soundsofhome_to_echollm_reviewed.ipynb (Stage 0 + Stage 4).
Do not edit: regenerate with `python scripts/gen_taxonomy.py`; scripts/test_taxonomy.py fails if this drifts."""

PRIVACY_LABELS = {'Child singing',
 'Conversation',
 'Female singing',
 'Female speech, woman speaking',
 'Male singing',
 'Male speech, man speaking',
 'Music',
 'Narration, monologue',
 'Singing',
 'Speech'}
PRIVACY_THR = 0.2
PRIVACY_PAD_SEC = 1.0
MAX_MASKED_FRAC = 0.02
FRAME_THR = 0.2
ACT_MIN_PEAK = 0.5
ACT_MIN_COVERAGE = 0.3
BG_MIN_PEAK = 0.3
BG_MIN_COVERAGE = 0.5
SILENCE_LABELS = {'White noise', 'Static', 'Silence'}
SILENCE_COVERAGE = 0.8
SEG_SEC = 10.0
SEG_HOP_SEC = 10.0
NULL_SENTENCE = 'There is no meaningful home event happening.'

ACTIVITY_MAP = {'Shower': 'Shower',
 'Bathtub (filling or washing)': 'Shower',
 'Electric shaver, electric razor': 'Electric Razor',
 'Electric toothbrush': 'Electric Toothbrush',
 'Toothbrush': 'Electric Toothbrush',
 'Toilet flush': 'Toilet Flushing',
 'Hair dryer': 'Hairdryer',
 'Dog': 'Petting Dog (Barking)',
 'Bark': 'Petting Dog (Barking)',
 'Bow-wow': 'Petting Dog (Barking)',
 'Growling': 'Petting Dog (Barking)',
 'Cat': 'Petting Cat (Meowing)',
 'Meow': 'Petting Cat (Meowing)',
 'Purr': 'Petting Cat (Meowing)',
 'Typing': 'Typing on Keyboard',
 'Computer keyboard': 'Typing on Keyboard',
 'Typewriter': 'Typing on Keyboard',
 'Printer': 'Printer',
 'Telephone bell ringing': 'Phone Ringing',
 'Telephone': 'Phone Ringing',
 'Cellphone buzz, vibrating alert': 'Phone Ringing',
 'Shuffling cards': 'Shredder',
 'Blender': 'Blender',
 'Blender, food processor': 'Blender',
 'Microwave oven': 'Microwave',
 'Coffee grinder': 'Coffee Grinder',
 'Food processor': 'Food Processor',
 'Chopping (food)': 'Chopping Board',
 'Cutting': 'Chopping Board',
 'Water tap, faucet': 'Running Water in Sink',
 'Sink (filling or washing)': 'Running Water in Sink',
 'Pour': 'Running Water in Sink',
 'Beep, bleep': 'Timer Beeping',
 'Ding': 'Timer Beeping',
 'Alarm': 'Timer Beeping',
 'Vacuum cleaner': 'Vacuum Cleaner',
 'Baby cry, infant cry': 'Baby Crying',
 'Crying, sobbing': 'Baby Crying'}

BACKGROUND_MAP = {'Air conditioning': 'Air Conditioning',
 'Mechanical fan': 'Air Conditioning',
 'Ventilation': 'Air Conditioning',
 'Traffic noise, roadway noise': 'Traffic Noise',
 'Vehicle': 'Traffic Noise',
 'Car': 'Traffic Noise',
 'Car passing by': 'Traffic Noise',
 'Motor vehicle (road)': 'Traffic Noise',
 'Bird': 'Birds Chirping',
 'Bird vocalization, bird call, bird song': 'Birds Chirping',
 'Chirp, tweet': 'Birds Chirping',
 'Rain': 'Raining',
 'Raindrop': 'Raining',
 'Rain on surface': 'Raining',
 'Refrigerator': 'Fridge Humming',
 'Hum': 'Fridge Humming',
 'Mains hum': 'Fridge Humming',
 'Washing machine': 'Laundry',
 'Dishwasher': 'Dishwasher',
 'Walk, footsteps': 'Footsteps',
 'Footsteps': 'Footsteps',
 'Shuffle': 'Footsteps'}

NEW_ACTIVITIES = {'Television': 'Watching Television',
 'Radio': 'Watching Television',
 'Door': 'Opening or Closing a Door',
 'Sliding door': 'Opening or Closing a Door',
 'Cupboard open or close': 'Opening or Closing a Door',
 'Drawer open or close': 'Opening or Closing a Drawer',
 'Clock': 'Clock Ticking',
 'Tick-tock': 'Clock Ticking',
 'Writing': 'Writing by Hand',
 'Snoring': 'Snoring',
 'Cutlery, silverware': 'Handling Cutlery or Dishes',
 'Dishes, pots, and pans': 'Handling Cutlery or Dishes'}

IGNORE = {'Animal',
 'Breathing',
 'Buzz',
 'Child singing',
 'Conversation',
 'Domestic animals, pets',
 'Environmental noise',
 'Female singing',
 'Female speech, woman speaking',
 'Heart sounds, heartbeat',
 'Inside, large room or hall',
 'Inside, small room',
 'Male singing',
 'Male speech, man speaking',
 'Mechanisms',
 'Mouse',
 'Music',
 'Narration, monologue',
 'Noise',
 'Rodents, rats, mice',
 'Silence',
 'Singing',
 'Snake',
 'Snort',
 'Sound effect',
 'Speech',
 'Static',
 'White noise',
 'Wild animals'}

UNLEARNABLE_HERE = ['People Talking', 'Playing Piano', 'Playing Video Games (Mario)']


def activity_map(policy: str) -> dict:
    """'strict' = EchoScriptor's 24 classes only; 'extended' adds NEW_ACTIVITIES (TV, doors, drawers, cutlery...)."""
    if policy not in ("strict", "extended"):
        raise ValueError(f"policy must be strict|extended, got {policy!r}")
    return {**ACTIVITY_MAP, **NEW_ACTIVITIES} if policy == "extended" else dict(ACTIVITY_MAP)

