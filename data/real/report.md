# Sounds of Home labels -> segments (policy: extended)

482,496 windows of 10 s from 1,344 hourly files, 14 recorders.

## Windows by kind

| kind                |      n |   pct |
|:--------------------|-------:|------:|
| DROP                | 257726 |  53.4 |
| null                | 178698 |  37   |
| activity_only       |  25998 |   5.4 |
| background_only     |  19061 |   4   |
| activity_background |   1013 |   0.2 |

## Drop reasons

| drop_reason        |      n |
|:-------------------|-------:|
| privacy_masked     | 223731 |
| no_confident_label |  33995 |

## Activities (labelled windows)

| activity                    |     n |
|:----------------------------|------:|
| Watching Television         | 57214 |
| Clock Ticking               | 18241 |
| Opening or Closing a Drawer | 18105 |
| Writing by Hand             | 10698 |
| Opening or Closing a Door   |  5056 |
| Printer                     |  2210 |
| Handling Cutlery or Dishes  |  1767 |
| Snoring                     |  1594 |
| Petting Dog (Barking)       |  1463 |
| Shower                      |  1164 |
| Running Water in Sink       |   822 |
| Vacuum Cleaner              |   726 |
| Typing on Keyboard          |   445 |
| Petting Cat (Meowing)       |   314 |
| Microwave                   |   272 |
| Electric Razor              |   196 |
| Hairdryer                   |   124 |
| Toilet Flushing             |    82 |
| Timer Beeping               |    53 |
| Phone Ringing               |    49 |
| Blender                     |    15 |
| Shredder                    |     4 |
| Electric Toothbrush         |     3 |
| Baby Crying                 |     1 |

## Backgrounds

| background       |     n |
|:-----------------|------:|
| Traffic Noise    | 15473 |
| Fridge Humming   |  8148 |
| Air Conditioning |  2909 |
| Birds Chirping   |   739 |
| Footsteps        |   362 |
| Raining          |   118 |

## Per recorder

|   recorder | home   | room        |   pair |   speech_overlap |   kitchen_ratio |   fridge | evidence_agrees   |   hours |   days |   masked_pct |   labelled_pct | top_activity        |
|-----------:|:-------|:------------|-------:|-----------------:|----------------:|---------:|:------------------|--------:|-------:|-------------:|---------------:|:--------------------|
|         01 | home_A | living_room |     02 |            0.211 |          0      |      595 | True              |      63 |      7 |          5.7 |            1.4 | Clock Ticking       |
|         02 | home_A | kitchen     |     01 |            0.211 |          1      |     3012 | True              |      63 |      7 |          3.3 |            0.6 | Clock Ticking       |
|         03 | home_B | living_room |     04 |            0.676 |          0.0104 |       31 | True              |      91 |      7 |         42.6 |            3.8 | Watching Television |
|         04 | home_B | kitchen     |     03 |            0.676 |          0.1329 |      165 | True              |      91 |      7 |         33.8 |            4.1 | Watching Television |
|         05 | home_C | kitchen     |     06 |            0.81  |          0.154  |      261 | True              |     112 |      7 |         39.4 |            3.5 | Watching Television |
|         06 | home_C | living_room |     05 |            0.81  |          0.0137 |      101 | True              |     112 |      7 |         41.2 |            1.3 | Watching Television |
|         07 | home_D | kitchen     |     08 |            0.806 |          0.3202 |      359 | False             |     112 |      7 |         58.7 |            5.1 | Writing by Hand     |
|         08 | home_D | living_room |     07 |            0.806 |          0.0061 |      907 | False             |     112 |      7 |         66   |            4.7 | Watching Television |
|         09 | home_E | living_room |     10 |            0.904 |          0.0454 |      115 | True              |     112 |      7 |         61.8 |            4.8 | Watching Television |
|         10 | home_E | kitchen     |     09 |            0.904 |          0.0696 |      472 | True              |     112 |      7 |         58.7 |            4.7 | Watching Television |
|         11 | home_F | kitchen     |     12 |            0.903 |          0.0515 |     1848 | True              |      70 |      7 |         33.2 |            1.9 | Watching Television |
|         12 | home_F | living_room |     11 |            0.903 |          0.0067 |       83 | True              |      70 |      7 |         35   |            0.8 | Watching Television |
|         13 | home_G | kitchen     |     14 |            0.886 |          0.0754 |       19 | False             |     112 |      7 |         60.3 |           28.3 | Clock Ticking       |
|         14 | home_G | living_room |     13 |            0.886 |          0.0068 |      180 | False             |     112 |      7 |         60.5 |            5.5 | Watching Television |

`home`, `room`: inferred. Pairing = greedy matching on the Jaccard overlap of speech-masked windows (two mics in one home hear the same conversations; 0.68-0.90 within a home, <0.6 across). Room = higher share of kitchen activities vs television; `fridge` is secondary evidence and `evidence_agrees` is False where it disagrees. Confirm with the dataset owners before publishing.
