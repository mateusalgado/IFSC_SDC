# Activity 01 - Wireless link budget and propagation

This activity estimates the reach of an ESP32-WROOM-32 Wi-Fi link using free-space and indoor log-distance propagation models. The calculations compare transmitter power and receiver sensitivity at two data rates, then examine how the path-loss exponent changes the nominal range.

## 1. Datasheet and assumptions

The RF parameters come from the local Espressif ESP32-WROOM-32 Datasheet, version 3.7, Table 17 for transmit power and Table 19 for receive sensitivity. The antenna gains are assumptions allowed by the assignment.

| Parameter | 802.11b at 1 Mbit/s | 802.11g at 54 Mbit/s |
|---|---|---|
| Transmit power | 19.5 dBm | 14.0 dBm |
| Receiver sensitivity | −97.0 dBm | −75.0 dBm |
| Transmit antenna gain | 2 dBi assumed | 2 dBi assumed |
| Receive antenna gain | 2 dBi assumed | 2 dBi assumed |
| Carrier frequency | 2,437 MHz | 2,437 MHz |

The reference distance is d₀ = 1 m. The model uses PLmax for the maximum tolerable path loss, n for the path-loss exponent and σ for the standard deviation of shadowing in dB.

At 1 Mbit/s, the radio uses DSSS and a more sensitive receive mode. At 54 Mbit/s, OFDM with 64-QAM on the data subcarriers supports a higher data rate while requiring a stronger received signal. The transmit power also decreases. Both changes reduce the available loss budget.

## 2. Free-space range

The maximum tolerable loss follows directly from the link budget.

> PLmax = Ptx + Gt + Gr − S

At 1 Mbit/s, PLmax = 19.5 + 2 + 2 − (−97) = 120.50 dB. At 54 Mbit/s, PLmax = 14 + 2 + 2 − (−75) = 93.00 dB.

The free-space path loss is

> FSPL = 32.44 + 20 log₁₀(fMHz) + 20 log₁₀(dkm)

Solving for distance gives

> dkm = 10^[(PLmax − 32.44 − 20 log₁₀(fMHz))/20]

At 2,437 MHz, the model gives approximately 10.38 km at 1 Mbit/s and 0.438 km at 54 Mbit/s. These are zero-margin, unobstructed model limits with the assumed antenna gains.

The difference in loss budget is 27.5 dB. Of that total, 5.5 dB comes from transmit power and 22 dB from sensitivity. The resulting distance ratio is about 23.7. This follows from the exponential relationship between distance and a loss budget expressed in decibels.

## 3. Indoor propagation

The log-distance model represents the median path loss in dB as a function of distance. Shadowing is represented by a random variable Xσ with zero mean and standard deviation σ.

> PL(d) = PL(d₀) + 10n log₁₀(d/d₀) + Xσ

At the 1 m reference distance, free-space loss is approximately 40.18 dB. For the nominal calculation, Xσ is set to zero and the 120.50 dB budget from the 1 Mbit/s mode is used.

> d = d₀ × 10^[(PLmax − PL(d₀))/(10n)]

| Environment | Exponent n | Shadowing σ | Nominal model distance |
|---|---|---|---|
| Office, mild obstruction | 2.4 | 9.6 dB | 2,222 m |
| Office, severe obstruction | 3.0 | 7.0 dB | 476 m |
| Factory, line of sight | 2.0 | 3.0 dB | 10,379 m |
| Factory, obstructed | 3.3 | 6.8 dB | 272 m |

The office and factory distances are extrapolations of the mathematical model. They do not establish measured indoor coverage or account for the dimensions of a real building.

## 4. Comparison and discussion

The obstructed factory has the shortest nominal range because its path-loss exponent is the largest. Compared with the free-space result, its predicted reach is about 38 times smaller. The severe-obstruction office follows at 476 m.

The factory line-of-sight case uses n = 2, matching the exponent of the free-space model. With the same reference loss and budget, the two calculations therefore give essentially the same distance.

Shadowing describes spatial variations around the median path loss. It is distinct from small-scale multipath fading. A larger σ means that a link with the same nominal distance can experience a wider range of received power levels.

A fade margin reduces the loss budget used in the design.

> PLdesign = PLmax − M

A margin proportional to σ increases the probability of exceeding the sensitivity threshold. A finite margin corresponds to a target outage probability rather than an absolute guarantee. The assignment discusses margins of roughly one to two standard deviations as an illustrative design choice.

## 5. Conclusion

The data rate changes both transmit power and receive sensitivity, producing a large difference in the available loss budget. Propagation conditions then determine how quickly that budget is consumed with distance.

The results are analytical estimates with assumed antenna gains and zero initial fade margin. Practical range also depends on obstructions, antenna installation, interference, fading and protocol timing. The calculation script in the activity folder provides the numerical steps used in the report.

## Reference

Espressif Systems. ESP32-WROOM-32 Datasheet, version 3.7, Tables 17 and 19. A local copy is stored in the activity reference folder.
