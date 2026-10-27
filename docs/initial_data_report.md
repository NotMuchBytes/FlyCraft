# FlyCraft Initial Data Report

Generated: 2026-09-20T22:24:16+03:00

## Scope and scientific status

This is an inspection of structural FlyWire/Codex exports, not a functioning digital fly brain. These files do not specify complete neuron dynamics, synaptic dynamics, learning rules, consciousness, or Minecraft knowledge. No simulator, learning, or Minecraft work was done in Phase 1.

## Dataset

- Declared dataset: FAFB v783, Female Adult Fly Brain (from the project brief; the CSV schemas contain no independent version field).
- Files loaded: 3
- Total compressed size: 265.11 MiB (277,991,365 bytes)
- Missing expected exports: Cell Types, Classification / Hierarchical Annotations

| File | Bytes | Compression | Detected role |
| --- | --- | --- | --- |
| connections_princeton_no_threshold.csv.gz | 275,679,780 | gzip | connections |
| neurons.csv.gz | 1,679,884 | gzip | neurotransmitter_predictions |
| visual_neuron_types.csv.gz | 631,701 | gzip | visual_annotations |

## Exact schemas

### `connections_princeton_no_threshold.csv.gz`

| Column | Sample-inferred type |
| --- | --- |
| pre_root_id | integer |
| post_root_id | integer |
| neuropil | text |
| syn_count | integer |
| nt_type | text |

Sample rows:

```text
['720575940625363947', '720575940623224444', 'ME_L', '12', 'GABA']
['720575940613354467', '720575940616690107', 'ME_L', '1', 'ACH']
['720575940630432382', '720575940618518557', 'ME_L', '67', 'ACH']
```

### `neurons.csv.gz`

| Column | Sample-inferred type |
| --- | --- |
| root_id | integer |
| group | text |
| nt_type | text |
| nt_type_score | floating point |
| da_avg | floating point |
| ser_avg | floating point |
| gaba_avg | floating point |
| glut_avg | floating point |
| ach_avg | floating point |
| oct_avg | floating point |

Sample rows:

```text
['720575940596125868', 'LO.LOP', 'ACH', '0.57', '0.03', '0.0', '0.05', '0.28', '0.57', '0.07']
['720575940597856265', 'ME', 'ACH', '0.85', '0.01', '0.0', '0.03', '0.04', '0.85', '0.07']
['720575940597944841', 'ME.LO', 'ACH', '0.82', '0.02', '0.0', '0.01', '0.05', '0.82', '0.09']
```

### `visual_neuron_types.csv.gz`

| Column | Sample-inferred type |
| --- | --- |
| root_id | integer |
| type | text |
| family | text |
| subsystem | text |
| category | text |
| side | text |

Sample rows:

```text
['720575940596125868', 'T5c', 'T5 Neuron', 'Motion', 'intrinsic', 'right']
['720575940597856265', 'Tm16', 'Transmedullary', 'Color', 'intrinsic', 'right']
['720575940597944841', 'Tm7', 'Transmedullary', 'Color', 'intrinsic', 'right']
```

## Connectome

- Unique neurons appearing in graph: **139,116**
- Valid directed connection records: **22,285,323**
- Unique directed neuron-to-neuron pairs: **19,773,733**
- Total `syn_count` / aggregate connection weight: **76,944,499**
- Malformed rows: **0**
- Exact duplicate rows beyond first: **0** across **0** duplicated keys
- Extra rows sharing a pre/post pair: **2,511,590** across **1,838,294** repeated pairs. These can represent separate neuropils/annotations and are not automatically errors.

### Weight distribution

- Minimum: 1
- Maximum: 2633
- Mean: 3.452698
- Population standard deviation: 8.023959
- P50: 1
- P90: 7
- P95: 12
- P99: 31

Most common weights:

| Weight | Records |
| --- | --- |
| 1 | 11,556,934 |
| 2 | 3,871,278 |
| 3 | 1,936,841 |
| 4 | 1,166,218 |
| 5 | 774,475 |
| 6 | 549,546 |
| 7 | 405,809 |
| 8 | 309,717 |
| 9 | 241,405 |
| 10 | 192,123 |
| 11 | 155,867 |
| 12 | 128,385 |

### Strongest connection records

| Weight | Pre root ID | Post root ID | Neuropil | Edge NT | Pre NT | Post NT | Pre visual type | Post visual type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2633 | 720575940650935673 | 720575940640736371 | LO_R | GABA | GABA | ACH | Li32 | Li30 |
| 2597 | 720575940628069501 | 720575940633305681 | LO_L | GABA | GABA | ACH | Li32 | Li30 |
| 2238 | 720575940644702112 | 720575940625952755 | LO_L | GABA | GABA | GABA | LT39 | Li33 |
| 2175 | 720575940623475324 | 720575940627497244 | LO_R | GABA | GABA | GABA | LT39 | Li33 |
| 1858 | 720575940644702112 | 720575940633305681 | LO_L | GABA | GABA | ACH | LT39 | Li30 |
| 1856 | 720575940611563310 | 720575940618554041 | ME_R | GABA | GABA | GABA | Sm42 | Sm41 |
| 1737 | 720575940629382150 | 720575940634612194 | LOP_R | GABA | GABA | GABA | LPi12 | LPi15 |
| 1702 | 720575940623475324 | 720575940640736371 | LO_R | GABA | GABA | ACH | LT39 | Li30 |
| 1695 | 720575940627190556 | 720575940628307026 | LOP_R | GABA | GABA | GABA | LPi14 | Am1 |
| 1605 | 720575940623444044 | 720575940613686698 | ME_L | GABA | GABA | GABA | Sm42 | Sm41 |
| 1594 | 720575940634612194 | 720575940627706398 | LOP_R | GABA | GABA | GABA | LPi15 | VCH |
| 1583 | 720575940628307026 | 720575940634612194 | LOP_R | GABA | GABA | GABA | Am1 | LPi15 |
| 1563 | 720575940632504874 | 720575940628307026 | LOP_R | GABA | GABA | GABA | LPi14 | Am1 |
| 1554 | 720575940634612194 | 720575940639209956 | LOP_R | GABA | GABA | GABA | LPi15 | DCH |
| 1482 | 720575940621619627 | 720575940606756030 | ME_R | ACH | ACH | GABA | cM16 | Pm13 |
| 1416 | 720575940619991862 | 720575940627502338 | LOP_L | GABA | GABA | GABA | LPi15 | VCH |
| 1329 | 720575940627190556 | 720575940632427603 | LOP_R | GABA | GABA | ACH | LPi14 | H2 |
| 1298 | 720575940627497244 | 720575940632821352 | LO_R | GABA | GABA | GLUT | Li33 | Li28 |
| 1295 | 720575940629513222 | 720575940619991862 | LOP_L | GABA | GABA | GABA | Am1 | LPi15 |
| 1289 | 720575940625000200 | 720575940619991862 | LOP_L | GABA | GABA | GABA | LPi12 | LPi15 |

## Metadata

### `neurons.csv.gz` (neurotransmitter_predictions)

- Rows: 139,255
- Unique root IDs: 139,255
- Malformed rows: 0
- Exact duplicate rows: 0
- Duplicate root IDs: 0

Top `group` values:

| group | Rows |
| --- | --- |
| ME | 43,241 |
| ME.LO | 16,312 |
| LA | 6,446 |
| ME.LOP | 6,071 |
| LO.LOP | 5,863 |
| NO_CONS | 5,074 |
| LO | 5,052 |
| GNG | 4,692 |
| MB_CA.MB_ML | 3,139 |
| AVLP | 2,825 |
| AL | 2,762 |
| SMP | 2,302 |

Top `nt_type` values:

| nt_type | Rows |
| --- | --- |
| ACH | 82,298 |
| GLUT | 19,605 |
| GABA | 16,017 |
| SER | 1,021 |
| DA | 584 |
| OCT | 72 |

### `visual_neuron_types.csv.gz` (visual_annotations)

- Rows: 95,079
- Unique root IDs: 95,079
- Malformed rows: 0
- Exact duplicate rows: 0
- Duplicate root IDs: 0

Top `family` values:

| family | Rows |
| --- | --- |
| Transmedullary | 17,947 |
| Photo Receptors | 9,706 |
| Medulla Intrinsic | 7,858 |
| Lamina Monopolar | 7,652 |
| Distal Medulla | 6,536 |
| T4 Neuron | 6,243 |
| T5 Neuron | 6,002 |
| Transmedullary Y | 5,278 |
| LC | 3,902 |
| T2 Neuron | 3,240 |
| Serpentine Medulla | 2,956 |
| Centrifugal | 2,955 |

Top `subsystem` values:

| subsystem | Rows |
| --- | --- |
| Motion | 15,614 |
| Color | 15,248 |
| Object | 14,804 |
| OFF | 10,999 |
| ON | 9,965 |
| Photoreceptors | 9,706 |
| Luminance | 6,433 |
| Form | 3,713 |
| Polarization | 153 |

Top `category` values:

| category | Rows |
| --- | --- |
| intrinsic | 86,639 |
| boundary | 8,440 |

Top `side` values:

| side | Rows |
| --- | --- |
| left | 47,530 |
| right | 47,291 |
| left,right | 258 |

### Candidate interface populations

- Broad visual candidate pool: 95,079 visual-annotated neurons, including 9,706 rows whose family is labeled `Photo Receptors`.
- A visual annotation does not prove that every listed cell is a primary sensory input. Final selection requires cell-type/classification evidence and literature review.
- Descending/output candidates: **not reliably identifiable from the available tables**. The missing Cell Types and Classification exports are needed before selection.
- The neurotransmitter table covers 139,255 unique neuron IDs; 119,597 have a non-empty categorical `nt_type` and 19,658 are blank. These are predictions, not exact synaptic physiology.

## Performance

- Connection analysis: 169.079 seconds
- End-to-end analysis: 171.006 seconds
- Peak observed process working set: 272.06 MiB
- Estimated minimal future CSR arrays (float32 weights, int32 indices/pointers): 151.39 MiB
- Estimated minimal neuron state (three float32 arrays + uint8 spike): 1.72 MiB
- Minimal core estimate before mappings, metadata, logs, and temporary buffers: 153.12 MiB

## Problems and uncertainties

- The brief named `C:\Users\Hamzah`, which does not exist here. The OS-resolved Desktop for the active profile was used: `C:\Users\anass\OneDrive\Desktop`.
- Cell Types and Classification / Hierarchical Annotations exports were not present. Nothing was fabricated or downloaded.
- FAFB v783 identity comes from the brief, not a version column in these files.
- `syn_count` is treated as aggregate connection weight based on its actual field name; source aggregation semantics should be verified against official Codex documentation before simulation.

## Phase boundary

Phase 1 stops here. No simulator, environment, Minecraft integration, learning, or training has started.
