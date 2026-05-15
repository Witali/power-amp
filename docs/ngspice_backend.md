# ngspice Backend

The project can now run a real open-source SPICE simulator locally.

Installed local binary:

```text
local_tools/ngspice/Spice64/bin/ngspice_con.exe
```

`local_tools/` is ignored by Git, so the binary distribution is not committed.

## Runner

Use the wrapper:

```powershell
.\tools\run_ngspice.ps1 -Netlist .\path\to\circuit.cir -OutputDir .\results\00x_name\data
```

The wrapper:

- uses `ngspice_con.exe`, not the GUI `ngspice.exe`;
- runs batch mode;
- writes `ngspice.log` into the output directory;
- lets `.control` commands in the netlist write CSV files beside the log.

## Verified Example

Smoke-test result:

```text
results/002_ngspice_rc_lowpass
```

Source netlist:

```text
spice_examples/001_rc_lowpass/rc_lowpass.cir
```

The example runs:

- `.op`
- `.ac dec 40 10 1Meg`
- `.tran 10u 5m`

and writes:

- `data/ac_response.csv`
- `data/transient.csv`
- `plots/ac_gain_phase.png`
- `plots/transient.png`
- `schematic/rc_lowpass.png`

## Notes

For future amplifier work, prefer ngspice as the truth source for:

- operating point and bias currents;
- AC gain/phase response;
- transient waveforms;
- `.four` harmonic analysis;
- `.meas` statements for repeatable metrics.

The earlier Python component simulator is still useful for quick topology screening, but real candidate circuits should graduate to ngspice netlists before we trust the numbers.
