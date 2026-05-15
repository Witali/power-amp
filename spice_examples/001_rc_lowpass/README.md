# 001 RC Low-Pass ngspice Smoke Test

Small runnable ngspice netlist used to verify the local ngspice backend.

Run from the project root:

```powershell
.\tools\run_ngspice.ps1 -Netlist .\spice_examples\001_rc_lowpass\rc_lowpass.cir -OutputDir .\results\002_ngspice_rc_lowpass\data
```

Expected generated files:

- `ngspice.log`
- `ac_response.csv`
- `transient.csv`
