# No-Overall-Feedback Amplifier Topology Study

Simulation method: pure-Python behavioral model, because no local ngspice/LTspice binary was available. All candidates used +/-15 V rails, 8 ohm load, 1 kHz sine tests, Class AB output bias, total voltage gain Av = 10, no global feedback, and identical ranking rules.

## Internet Design Ideas Used

- [Pass DIY, The Zen Amplifier](https://www.passdiy.com/project/amplifiers/the-zen-amplifier): single-ended MOSFET Class A simplicity and high-bias behavior.
- [Pass DIY, Cascode Amplifier Design](https://www.passdiy.com/project/amplifiers/cascode-amplifier-design): cascode as a way to reduce device capacitance modulation without leaning on global feedback.
- [Pass DIY, Zen Variations 6](https://www.passdiy.com/project/amplifiers/zen-variations-6): balanced/Son-of-Zen cancellation and symmetry ideas.
- [First Watt F4](https://www.firstwatt.com/product/f4/): no-voltage-gain, no-feedback power buffer idea.
- [Andiha, Class A Cascode Power Amplifier](https://www.andiha.no/audio/projects/cascode.html): no-feedback folded cascode VAS and compound emitter follower output.

This is useful for choosing a topology direction, not for signing off a hardware design. The selected topology still needs transistor-level SPICE, SOA protection, compensation, PCB layout, and bench validation.

## Selected topology: Variant 07

**Complementary folded cascode, CFP AB output**

Best headroom and local output linearity, but CFP stability must be proven carefully.

## Ranking

| Rank | ID | Score | 1 W THD % | 5 W THD % | Clean W @ 1% THD | Damping | Offset mV | Topology |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 07 | 88.49 | 0.1025 | 0.0501 | 9.0 | 145.5 | 8.0 | Complementary folded cascode, CFP AB output |
| 2 | 10 | 80.75 | 0.1035 | 0.0638 | 8.0 | 72.7 | 25.0 | Quasi-complementary high-bias AB |
| 3 | 06 | 78.18 | 0.1483 | 0.075 | 6.0 | 133.3 | 14.0 | Complementary cascoded VAS, triple EF AB |
| 4 | 08 | 76.49 | 0.1809 | 0.0852 | 7.0 | 88.9 | 10.0 | Balanced-cancellation cascode, double EF AB |
| 5 | 05 | 76.07 | 0.198 | 0.096 | 8.0 | 80.0 | 12.0 | Complementary cascoded VAS, double EF AB |
| 6 | 09 | 75.84 | 0.1923 | 0.0905 | 8.0 | 100.0 | 14.0 | Diamond input, symmetric cascode, double EF AB |
| 7 | 04 | 73.63 | 0.2256 | 0.1091 | 8.0 | 66.7 | 14.0 | Folded cascode VAS, double EF AB |
| 8 | 03 | 69.94 | 0.2712 | 0.1375 | 7.0 | 57.1 | 15.0 | BJT differential input, cascoded VAS, double EF AB |
| 9 | 01 | 64.8 | 0.3105 | 0.163 | 7.0 | 50.0 | 35.0 | Single-ended cascoded VAS, double EF AB |
| 10 | 02 | 64.38 | 0.2824 | 0.146 | 7.0 | 53.3 | 45.0 | JFET input, single-ended cascode, double EF AB |

## Why the selected topology wins

- On +/-15 V rails, output-stage headroom matters more than it did in the +/-35 V comparison.
- The selected low-voltage folded-cascode/CFP approach preserves more output swing than a triple emitter follower.
- The complementary feedback pair is only a local output-stage loop; there is still no overall OUT-to-input feedback path.
- It has the strongest combination of clean power, damping estimate, and crossover behavior in this AB/low-voltage comparison.
- Variant 05, the complementary cascoded VAS with double emitter follower, is the safer fallback if CFP stability is a concern.
