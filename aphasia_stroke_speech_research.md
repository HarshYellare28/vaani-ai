# Aphasia & Stroke: Speech Disability Mapping for Personalization

## Core Framework: Brain Region → Speech Profile

| Brain Region Damaged | Aphasia Type | Key Word/Speech Problem |
|---|---|---|
| Left inferior frontal gyrus (Broca's area) | **Broca's Aphasia** | Can't get words *out* — knows what they want to say |
| Left posterior superior temporal (Wernicke's area) | **Wernicke's Aphasia** | Words come out but are *wrong/nonsense* — unaware of errors |
| Arcuate fasciculus (connection pathway) | **Conduction Aphasia** | Can't *repeat* words — speaking and comprehension relatively ok |
| Widespread left hemisphere | **Global Aphasia** | Severe — affects everything, very few words |
| Multiple/diffuse areas | **Anomic Aphasia** | Mild — specific word-finding difficulty only |
| Insula + arcuate fasciculus | **Apraxia of Speech** | Pronunciation/motor planning breaks down |

---

## Western Aphasia Battery (WAB) — Clinical Scoring Axes

The WAB is the standard clinical tool that scores patients on 4 axes, which maps directly to personalization dimensions:

| Aphasia Type | Fluency | Comprehension | Repetition | Naming/Word-Finding |
|---|---|---|---|---|
| Global | < 5 | 0–3.9 | 0–4.9 | < 7 |
| Broca's | < 5 | 4–10 | 0–7.9 | < 9 |
| Wernicke's | > 4 | 0–6.9 | 0–7.9 | < 10 |
| Conduction | > 4 | 7–10 | 0–6.9 | < 10 |
| Anomic | > 4 | 7–10 | 7–10 | < 10 |

---

## Personalization Dimensions

| WAB Dimension | What to Personalize |
|---|---|
| **Fluency** (low = effortful speech) | Pace of interaction, response time tolerance |
| **Comprehension** (low = doesn't understand input) | Simpler vocabulary, visual cues, shorter sentences |
| **Repetition** (low = can't echo back) | Avoid repetition-based exercises |
| **Naming/Word-finding** | Word suggestion UI, category-based prompts |

---

## Word-Type Difficulties by Aphasia Type

- **Nouns** (especially proper nouns — names, places) are most commonly lost first
- **Content words** (nouns, verbs) vs. **function words** (the, and, is) — loss pattern differs by lesion site
- **Abstract words** (justice, love) are harder than **concrete/visual words** (apple, chair)
- **Low-frequency words** are harder than high-frequency everyday words
- **Emotional/automatic speech** (counting, singing, swearing) is often preserved — different neural pathway

### Word Category Loss by Lesion Location
Damage to specific temporal regions causes loss of specific noun categories:
- Tools vs. living things vs. proper nouns differ by lesion site
- Mapped at voxel level in 2023 ScienceDirect study

---

## Ischemic vs. Hemorrhagic Stroke

| Stroke Type | Speech Profile |
|---|---|
| **Ischemic** | More focal, predictable deficits — maps cleanly to aphasia types above |
| **Hemorrhagic** | More varied cognitive-communication profiles — less predictable |

Study: 47 ischemic vs. 47 hemorrhagic stroke patients assessed using ICF classification before and after 4-week rehabilitation.

---

## Key Intake Signals for Personalization

The most actionable signals at onboarding:

1. **Stroke side**: Left = language dominant in 95% of people → aphasia likely; Right = prosody/pragmatics affected
2. **Fluent vs. non-fluent**: Determines interaction pacing completely
3. **Comprehension level**: Determines complexity of language used *toward* the patient
4. **Word category deficits**: Nouns? Verbs? Proper names? These differ by lesion site
5. **Apraxia co-occurrence**: Motor planning issues on top of language — affects pronunciation consistency

---

## Research Notes

- **Lesion-Symptom Mapping (VLSM)**: Voxel-based technique correlating MRI lesion location with specific symptom patterns — most rigorous method for brain-region → deficit mapping
- **Personalized tDCS + language training** (2025 fMRI case study): Targeting specific language network gaps improved connectivity — confirms personalization has neurological grounding
- **Recovery**: Lesion location predicts long-term recovery trajectory — frontal lesions recover differently from temporal lesions

---

## Sources

- [Language systems from lesion-symptom mapping in aphasia — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9112051/)
- [Mapping spoken language and cognitive deficits in post-stroke aphasia — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2213158223001419)
- [Association of Lesion Location With Long-Term Recovery in Post-stroke Aphasia — PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6668327/)
- [ICF Classification: Ischemic vs Hemorrhagic Stroke Rehabilitation — PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9564461/)
- [Personalized Language Training and Bi-Hemispheric tDCS — PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12387334/)
- [Types of Aphasia — Atlas Aphasia](https://www.atlasaphasia.org/post/types-of-aphasia)
- [Aphasia — NIDCD NIH](https://www.nidcd.nih.gov/health/aphasia)
- [6 Types of Aphasia — Regional Neurological Associates](https://regionalneurological.com/types-of-aphasia/)
- [Predicting aphasia type from brain damage — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0010945215003299)
- [Aphasia — StatPearls NIH](https://www.ncbi.nlm.nih.gov/books/NBK559315/)
