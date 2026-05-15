# Results Folder

This folder stores generated artifacts in one subfolder per circuit or study.

Naming convention:

```text
001_short_circuit_name
002_next_circuit_name
003_other_topic
```

Each result folder should keep all files needed to inspect or reproduce that circuit:

- `schematic/`: schematic drawings in SVG and PNG.
- `plots/`: graph drawings in SVG and PNG.
- `data/`: CSV or other numeric simulation data.
- `netlists/`: SPICE-style netlists.
- `source/`: scripts used to generate or simulate the result.
- `README.md`: short description, assumptions, and key numbers.

PNG export convention:

- Keep SVG as the editable/vector master.
- Generate PNG at 2x scale unless a different resolution is clearly better.
- Prefer readable PNG sizes: around `1800x1000` for graphs and `3000px+` wide for detailed schematics.
