# 003 RadioStorage shema-1804-6 Reconstruction

This folder contains a local reconstruction of the amplifier schematic from:

`https://radiostorage.net/uploads/Image/schemes/18/shema-1804-6.png`

## Recognized Circuit

- `VT1`: KT3102A NPN common-emitter voltage amplifier, `Bf = 100`.
- `VT2`: KT817A NPN upper emitter follower, `Bf = 50`.
- `VT3`: KT816A PNP lower emitter follower, `Bf = 50`.
- `VD1`, `VD2`: KD521A bias diodes between output transistor bases.
- `R1`: recognized as 180 ohm in the image, then tuned to the standard E96 value 2.37 kOhm in this model.
- `R2`: recognized as 6.2 kOhm in the image, then tuned to the standard E96 value 6.98 kOhm in this model.
- `R3`: 1 kOhm VT1 base return.
- `R4`: recognized as the input potentiometer/load, modeled as 470 kOhm.
- `C1`: 1000 uF supply decoupling.
- `C2`: 4700 uF output coupling capacitor for this recalculated run.
- `C3`: 10 uF input coupling capacitor.
- `B1`: speaker load, modeled as the requested 8 ohm load.

Passive parts use standard value series: E96 for the two bias resistors that set operating point, E24/E12 for the other resistors, and common electrolytic capacitor values for `C1`, `C2`, and `C3`.

## ngspice Check

The reconstructed model converged in ngspice. With `Bf = 100` for VT1 and `Bf = 50` for VT2/VT3, `R1` and `R2` are tuned for about 10 mA through the output transistors and for the output emitter node to stay near half supply.

Operating point from `data/ngspice.log`:

- `V(b_in)`: about 0.651 V
- `V(drive)`: about 5.306 V
- `V(b_top)`: about 6.618 V
- `V(out)`: about 5.959 V before output capacitor
- `V(load)`: 0 V DC after output capacitor
- VT2 collector current: about 10.13 mA
- VT3 collector current: about 10.13 mA
- Total supply current in this simplified transistor model: about 12.40 mA

This no-emitter-resistor diode-biased output stage remains thermally sensitive; the current is very dependent on transistor and diode models.

## Key 1 kHz Result

For a 1.0 mV peak sine input:

- Output power at 1 kHz into 8 ohm: `0.0220 mW`
- Load RMS voltage at 1 kHz: `0.013 V`
- THD estimate at 1 kHz, harmonics 2-5 from ngspice transient data: `0.821 %`

## Non-Clipping Check

The selected transient input level is intentionally small so the simulated output does not clip.

- Sine input swing: `0.0020 Vpp`.
- Output node before C2: `5.9400..5.9775 V`.
- Rail headroom at that node: at least `5.9400 V`.
- Speaker/load swing after C2: `0.0375 Vpp`.

## Square-Wave Response

Square-wave transient runs use a 2.0 mVpp input and show the load voltage after 60 ms of settling.

- 1 kHz: load swing about `0.040 Vpp`.
- 10 kHz: load swing about `0.032 Vpp`.

## Files

- `source/shema-1804-6.png`: original downloaded image.
- `schematic/reconstructed_amplifier.svg/png`: redrawn schematic using transistor symbols.
- `netlists/radiostorage_amp_reconstructed.cir`: main ngspice netlist.
- `data/ac_response.csv`: AC gain/phase data from ngspice.
- `data/transient_1khz.csv`: 1 kHz transient data from ngspice.
- `data/frequency_sweep.csv`: frequency sweep with power and THD estimates.
- `data/square/*.csv`: 1 kHz and 10 kHz square-wave transient data.
- `plots/*.svg/png`: generated plots.
