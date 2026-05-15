# 002 ngspice RC Low-Pass

This result verifies that the project can use a real open-source SPICE backend.

Simulator:

- ngspice-46 console binary, installed locally under `local_tools/ngspice`.
- Runner: `tools/run_ngspice.ps1`.

Circuit:

- `Vin`: DC 0, AC 1, transient sine 1 V peak at 1 kHz
- `R1`: 1 kOhm
- `C1`: 100 nF
- `Rload`: 100 kOhm
- Ideal cutoff without load interaction: 1591.5 Hz

Files:

- `schematic/rc_lowpass.svg`
- `schematic/rc_lowpass.png`
- `plots/ac_gain_phase.svg`
- `plots/ac_gain_phase.png`
- `plots/transient.svg`
- `plots/transient.png`
- `data/ngspice.log`
- `data/ac_response.csv`
- `data/transient.csv`

Run again:

```powershell
.\tools\run_ngspice.ps1 -Netlist .\spice_examples\001_rc_lowpass\rc_lowpass.cir -OutputDir .\results\002_ngspice_rc_lowpass\data
python .\spice_examples\001_rc_lowpass\generate_assets.py
.\tools\render_svg_png.ps1 -InputSvg .\results\002_ngspice_rc_lowpass\schematic\rc_lowpass.svg -OutputPng .\results\002_ngspice_rc_lowpass\schematic\rc_lowpass.png -Scale 2
.\tools\render_svg_png.ps1 -InputSvg .\results\002_ngspice_rc_lowpass\plots\ac_gain_phase.svg -OutputPng .\results\002_ngspice_rc_lowpass\plots\ac_gain_phase.png -Scale 2
.\tools\render_svg_png.ps1 -InputSvg .\results\002_ngspice_rc_lowpass\plots\transient.svg -OutputPng .\results\002_ngspice_rc_lowpass\plots\transient.png -Scale 2
```
