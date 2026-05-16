# 003 RadioStorage shema-1804-6 Reconstruction

This folder contains a local reconstruction of the amplifier schematic from:

`https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png`

## Recognized Circuit

- `VT1`: KT3102A NPN common-emitter voltage amplifier, `Bf = 100`.
- `VT2`: KT817A NPN upper emitter follower, `Bf = 50`.
- `VT3`: KT816A PNP lower emitter follower, `Bf = 50`.
- `VD1`, `VD2`: KD521A bias diodes between output transistor bases.
- `R1`: recognized as 180 ohm in the image, then tuned to the common E24 value 2.4 kOhm in this model.
- `R2`: recognized as 6.2 kOhm in the image, then retuned to the common E24 value 47 kOhm for use with `R3 = 10 kOhm` and `R5 = 100 ohm`; connected from the output emitter node to the VT1 base in this model.
- `R3`: 10 kOhm VT1 base return.
- `R5`: 100 ohm VT1 emitter degeneration resistor.
- `R4`: recognized as the input potentiometer/load, modeled as 470 kOhm.
- `C1`: 1000 uF supply decoupling.
- `C2`: 4700 uF output coupling capacitor for this recalculated run.
- `C3`: 10 uF input coupling capacitor.
- `B1`: speaker load, modeled as the requested 8 ohm load.

Passive parts use common value series: E24 for resistors and common electrolytic capacitor values for `C1`, `C2`, and `C3`.

## ngspice Check

The reconstructed model converged in ngspice. After adding `R5 = 100 ohm` in the VT1 emitter circuit, `R1` and `R2` were retuned for `R3 = 10 kOhm`, about half supply at `out`, and about 10 mA through the output stage.

Operating point from `data/ngspice.log`:

- `V(b_in)`: about 0.882 V
- `V(e_vt1)`: about 0.222 V
- `V(drive)`: about 5.411 V
- `V(b_top)`: about 6.720 V
- `V(out)`: about 6.062 V before output capacitor
- `V(load)`: about 0.000 V DC after output capacitor
- VT2 collector current: about 9.62 mA
- VT3 collector current: about 9.52 mA
- Total supply current in this simplified transistor model: about 11.82 mA

This no-emitter-resistor diode-biased output stage remains thermally sensitive; the current is very dependent on transistor and diode models.

## Key 1 kHz Result

For a 1.0 mV peak sine input:

- Output power at 1 kHz into 8 ohm: `0.0006 mW`
- Load RMS voltage at 1 kHz: `0.002 V`
- THD estimate at 1 kHz, harmonics 2-5 from ngspice transient data: `0.024 %`

## Non-Clipping Check

The selected transient input level is intentionally small so the simulated output does not clip.

- Sine input swing: `0.0020 Vpp`.
- Output node before C2: `6.0594..6.0655 V`.
- Rail headroom at that node: at least `5.9345 V`.
- Speaker/load swing after C2: `0.0061 Vpp`.

## Square-Wave Response

Square-wave transient runs use a 2.0 mVpp input and show the load voltage after 60 ms of settling.

- 1 kHz: load swing about `0.006 Vpp`.
- 10 kHz: load swing about `0.005 Vpp`.

## Files

- `source/shema-1804-6.png`: original downloaded image.
- `schematic/reconstructed_amplifier.svg/png`: redrawn schematic using transistor symbols.
- `schematic/reconstructed_amplifier_bootstrap.svg/png`: bootstrap/voltage-addition variant with split upper bias resistor and C4.
- `netlists/radiostorage_amp_reconstructed.cir`: main ngspice netlist.
- `data/ac_response.csv`: AC gain/phase data from ngspice.
- `data/transient_1khz.csv`: 1 kHz transient data from ngspice.
- `data/frequency_sweep.csv`: frequency sweep with power and THD estimates.
- `data/square/*.csv`: 1 kHz and 10 kHz square-wave transient data.
- `plots/sine_response_1khz.svg/png`: 1 kHz sine-wave transient plot.
- `plots/bootstrap_sine_response_1khz.svg/png`: 1 kHz sine-wave transient plot for the voltage-addition variant.
- `plots/*.svg/png`: generated plots.
