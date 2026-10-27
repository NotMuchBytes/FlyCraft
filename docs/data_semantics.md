# FlyWire/Codex Data Semantics Used in Phase 2

Checked: 2026-09-21. This document separates published data meaning from
FlyCraft model choices. Where the available official material did not establish
an answer, it is marked **UNKNOWN**.

## Sources consulted

- [Codex dataset page](https://codex.flywire.ai/api/download?dataset=fafb) — identifies FAFB v783 as the Female Adult Fly Brain release with 139,255 neurons.
- [Official Codex source: data schema](https://github.com/murthylab/codex/blob/main/codex/data/catalog.py) — declares the connection table as one row per `(pre_root_id, post_root_id, neuropil)` tuple.
- [Official Codex source: connection representation](https://github.com/murthylab/codex/blob/main/codex/data/connections.py) — sums `syn_count` across regions when constructing partner counts while retaining per-neuropil rows separately.
- [Official Codex source: neuron initialization](https://github.com/murthylab/codex/blob/main/codex/data/neuron_data_initializer.py) — defines neuron neurotransmitter fields as prediction information with confidence scores and treats connection rows as directed.
- [Official Codex FAQ source](https://github.com/murthylab/codex/blob/main/codex/data/faq_qa_kb.py) — documents the normal Codex threshold of at least five synapses per connected pair and states that the display `group`/name basis is the neuropil(s) with the most synaptic connections.
- [FlyWire v783 connectivity release](https://doi.org/10.5281/zenodo.10676866) — defines the proofread connection product as one row per neuron-neuron pair and neuropil, and `syn_count` as the number of synapses for that pair in that neuropil.
- [Dorkenwald et al. 2024](https://doi.org/10.1038/s41586-024-07558-y) — defines a connection from A to B as the set of chemical synapses from A to B, discusses false positives/negatives, uses five synapses for its principal analyses, and notes that another optic-lobe analysis used two.
- [Eckstein et al. 2024](https://doi.org/10.1016/j.cell.2024.03.016) — describes synapse-level transmitter prediction, neuron-level majority voting and confidence, classification accuracy, limitations, and receptor-dependent connection sign.

## Answers to the requested semantic questions

### 1. What does one connection row represent?

**DATA:** One directed presynaptic-neuron/postsynaptic-neuron/neuropil tuple.
The raw IDs identify the source and target neurons; the neuropil identifies the
brain region assigned to those synapses.

The local file is the unthresholded Princeton export: its observed minimum
`syn_count` is 1. The official Codex application normally presents a
five-synapse-thresholded connectivity graph. The exact public documentation for
the filename suffix `princeton_no_threshold` was not exposed on the unsigned
download page, but the contents match the official tuple schema and the v783
proofread connection definition.

### 2–3. Why can the same pre/post pair appear multiple times?

**DATA:** Connections are separated by neuropil. A directed pair with synapses
in multiple neuropils therefore has multiple rows. Phase 1 measured 22,285,323
rows but 19,773,733 unique directed pairs. Exact duplicate rows were zero.

### 4. What does `syn_count` represent?

**DATA:** The number of detected chemical synapses from that presynaptic neuron
to that postsynaptic neuron within the row's neuropil. It is a structural count,
not a voltage, current, conductance, or calibrated physiological strength.

Published FlyWire work describes synapse count as a useful proxy for connection
strength, all else equal, while warning that automatic detection includes
errors. It recommends thresholds chosen for the analysis rather than one
universal rule. Codex's standard displayed graph uses five or more synapses;
the present unthresholded file deliberately includes weaker records.

### 5–6. What is edge-level `nt_type`, and is it inferred from the source?

**DATA:** It is one of the six predicted small-molecule transmitter labels used
by Codex: `ACH`, `GABA`, `GLUT`, `DA`, `SER`, or `OCT`. Transmitter prediction is
performed from EM imagery around presynaptic sites. The published method then
uses presynaptic-site votes to derive a neuron-level prediction under a
Dale's-law approximation.

The accessible official schema stores `nt_type` on every connection row but
does not explicitly document the export pipeline that copies/derives that
single label. In this exact local export, all **20,837,661** edge records whose
presynaptic neuron has a nonblank metadata `nt_type` match that presynaptic
label, with **0 mismatches**; **1,447,662** records have a presynaptic neuron
whose metadata categorical type is blank. Thus a presynaptic-neuron origin is
strongly supported for this file, but the undocumented implementation detail is
not promoted to a universal biological fact.

### 7. What is `neurons.csv.gz`?

**DATA:** It is one row per released root ID. In this snapshot it contains the
root ID, an automatically assigned connectivity/neuropil group, a categorical
neuron-level transmitter prediction and confidence, and six averaged
transmitter-score columns. It is not the missing curated Cell Types table and
not the missing Classification/Hierarchical Annotations table.

### 8. How should transmitter score columns be interpreted?

**DATA:** The classifier produces six synapse-level transmitter probabilities.
The `*_avg` fields are averages for the respective transmitter across the
neuron's presynaptic sites. The categorical `nt_type` is based on accumulated
presynaptic-site evidence. `nt_type_score` is the authors' neuron-level
confidence score, based on the proportion of presynapses voting for the chosen
class together with classifier confusion information; it is not simply an
experimentally measured probability of biological truth.

The paper reports high but imperfect test accuracy and specifically discusses
co-transmission, unmodelled transmitters, and inconsistent/low-confidence
predictions. FlyCraft preserves these values but does not use them to assign
sign in the Phase 2 default model.

### 9. What does `NO_CONS` mean in `group`?

The official Codex FAQ says the group/name basis comes from neuropils with the
most synaptic connections. However, the accessible official documentation and
source inspected here do not define the literal token `NO_CONS`.

**UNKNOWN:** Its exact expansion and assignment rule are not established by
the available official sources. FlyCraft treats it as an opaque group label and
does not expand it to “no consensus” without a source.

### 10. Confidence and filtering recommendations

- Connection filtering should be analysis-specific. Five synapses is the main
  Codex/paper convention; two has been used for optic-lobe analyses. This first
  propagation experiment keeps the supplied unthresholded structural graph so
  that preprocessing is lossless, then compresses weights numerically.
- No official universal `nt_type_score` cutoff was found. Codex's UI colors
  confidence bands, but that display behavior is not treated as a scientific
  exclusion recommendation.
- Transmitter identity does not determine connection sign alone. The published
  neurotransmitter study states that function depends on both upstream
  transmitter and downstream receptors: acetylcholine is generally excitatory,
  GABA generally inhibitory, and glutamate can be either in flies.

## FlyCraft Phase 2 engineering choices

These are **MODEL ASSUMPTIONS**, not dataset facts:

1. Include all 139,255 metadata neurons. The 139 absent from the edge list are
   retained as disconnected nodes. This preserves the declared released
   population and avoids inventing a reason for their absence.
2. Assign dense indices by ascending unsigned `root_id`. This is deterministic.
3. Aggregate all neuropil rows for a directed pair by summing `syn_count`.
   Neuropil-specific structure is lost in the first simulator, while total
   structural count is preserved.
4. Store the aggregate graph as raw unsigned counts in CSR with rows as targets
   and columns as sources.
5. Default propagation uses unsigned weights. No receptor-specific sign is
   claimed. Unknown transmitter values remain active with gain +1 under the
   explicit `unknown_policy="positive"` setting.
6. Default numerical weights are `0.03 * log1p(syn_count)`. `raw`, `sqrt`,
   `log1p`, `clipped`, and `normalized_clipped` transforms are implemented.
7. The synchronous leaky-integrate-and-fire-like update is a computational
   abstraction for propagation tests, not a model of exact Drosophila
   physiology.
