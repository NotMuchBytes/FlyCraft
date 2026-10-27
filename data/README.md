# Data

Local FlyWire/Codex exports used by FlyCraft are stored here. They are not
intended for redistribution until upstream licensing has been checked.

See `../docs/initial_data_report.md` for inspected schemas and limitations.

`processed/` is generated locally by `tools/prepare_connectome.py` and contains:

- `neuron_index.npz`: ascending `uint64` root IDs and compact transmitter codes.
- `connectome_raw_csr.npz`: target-row/source-column aggregate `uint32` counts.
- `build_metadata.json`: source hashes, counts, orientation, memory, and timing.

The original compressed CSV files are never overwritten by preprocessing.

Additional official FAFB v783 annotation exports downloaded from the Codex
static-data bucket on 2026-09-21:

- `classification.csv.gz`: 139,255 rows; hierarchical `flow`, `super_class`,
  `class`, `sub_class`, `hemilineage`, `side`, and `nerve` annotations; SHA-256
  `e946b552f4056dfc977707be0674609832c3f64332a22d69dc0d9615e7aae663`.
- `consolidated_cell_types.csv.gz`: 138,327 rows; resolved primary and
  additional cell types. Its root IDs are a strict subset of `neurons.csv.gz`:
  928 of the 139,255 metadata neurons have no consolidated cell-type row and
  there are no extra IDs. SHA-256
  `8aba246d71dc40361677493629972ce3883048c3d02010adc42bda22962a1a2d`.

Source base URL:
`https://storage.googleapis.com/flywire-data/codex/data/fafb/783/`.

Phase 3 generated these interface artifacts in `processed/`:

- `phase3_input_population.csv`: 9,706 photoreceptor candidates supported by
  both visual and hierarchical annotations.
- `phase3_output_population.csv`: 1,305 explicitly descending neurons.
- `phase3_interface_indices.npz`: compact dense-index arrays and output sides.
- `phase3_metadata.json`: source schemas, hashes, coverage, and selection counts.
