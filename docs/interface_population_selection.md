# Phase 3 interface population selection

## Input candidates

Selection rule:

```text
visual.family == "Photo Receptors"
AND classification.sub_class == "photo_receptor"
```

This yields exactly 9,706 candidates. Each machine-readable record contains
root ID, dense index, visual type/family/subsystem, classification fields, side,
consolidated primary type where available, and the inclusion reason.

The artificial sensor stimulates 50 neurons per visible sector. Cohorts are
deterministic, disjoint for the four lateral sectors, and formed from ascending
dense indices within the annotated side. `far_left` and `left` use left-side
photoreceptor candidates; `right` and `far_right` use right-side candidates;
`center` uses 25 from each side. Exact root IDs are stored under
`sector_root_ids` in `experiments/phase3/results/open_loop_results.json`.

**ENGINEERING CHOICE:** ordering and splitting by dense index is a reproducible
partition, not a claim of retinotopy. The available tables have side but no
visual-field coordinate for these cells.

## Output candidates

Selection rule:

```text
classification.super_class == "descending"
```

This yields exactly 1,305 candidates: 647 left, 650 right, and 8 other-side.
The experiment observes every one of them. Their exact root IDs and metadata
are in `data/processed/phase3_output_population.csv`.

**ENGINEERING CHOICE:** the decoder compares left- and right-annotated spike
counts. More left activity maps to `TURN_LEFT`, more right activity maps to
`TURN_RIGHT`, balanced nonzero activity maps to `FORWARD`, and no activity maps
to `NO_OP`. These action meanings are not biological claims.

## Artificial sensor

The sensor computes target bearing relative to agent heading over a 180-degree
field of view and returns one of five sectors: far left, left, center, right,
or far right. A target outside the field of view returns not visible. Distance
and a diagnostic intensity are reported, but the experiment uses binary
visibility with fixed stimulation amplitude so angular conditions are compared
at equal neural input.

