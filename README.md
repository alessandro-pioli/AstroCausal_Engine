# AstroCausal Engine: interactive sandbox of causal gravity and 2D orbital mechanics

**🇬🇧 English** · [🇮🇹 Italiano](README.it.md)

<sub>Canonical repository: **https://github.com/alessandro-pioli/AstroCausal_Engine**</sub>

> A real-time laboratory where gravity is recreated as a genuinely causal phenomenon: gravitational information always travels at a finite speed c. Around this core, you can observe scenarios ranging from the complete solar system to the merging of black holes to impacts between dwarf galaxies, with vectors and telemetry, an interactive orbital spawner for Keplerian orbits and Lagrange points, a complete suite of gravitational heatmaps, and the emerging visual manifestation of analogous gravitational waves.

**How to navigate the documentation.** The project is described in three complementary documents, each for a different reader:
- **This README**: for those who want to *use* the simulator. Installation, scenarios, controls, display modes, performance management.
- **[PHYSICS_AND_SCENARIO_GUIDE.md](PHYSICS_AND_SCENARIO_GUIDE.md)**: for those who want *to understand the physics*. All the equations actually implemented, the mathematics of the heatmaps, the validation against real data (GWOSC), and the numerical relativity (SXS), with GIFs and images of the phenomena.
- **[ARCHITECTURE_DEEP_DIVE.md](ARCHITECTURE_DEEP_DIVE.md)**: for those who want *to understand the engineering*. The architectural choices (DOD, JIT kernel, LOD ring buffer, CPU rendering), the problems encountered, and the solutions that worked.

---

## Preview

| dΦ/dt spirals (NS binary) | GW Strain at the pericenter (EMRI) | Liénard-Wiechert (0.7c → c) (*extreme what if*) |
|:---:|:---:|:---:|
| <img src="docs/gif/dphi_spirale_binaria.gif" width="100%" alt="Causal dΦ/dt spirals of a neutron star binary"> | <img src="docs/img/GWH_EMRI_peri.png" width="100%" alt="Quadrupole strain pulse at the pericenter of an EMRI"> | <img src="docs/gif/07_to_c_fast.gif" width="100%" alt="Liénard-Wiechert deformation of the field at relativistic velocities"> |

| Causal chaos: neutron stars around Sag A* (dΦ/dt) | Roche topology (Alpha Centauri AB) | Shell pattern (double eccentricity BNS) |
|:---:|:---:|:---:|
| <video src="https://github.com/user-attachments/assets/03e80460-fa52-413f-8dbc-311698c9bd78" controls="controls" width="100%"></video> | <img src="docs/img/Alpha_Roche.png" width="100%" alt="Roche topology of the Alpha Centauri AB pair"> | <img src="docs/img/extreme_eccentric_orbit_pattern.png" width="100%" alt="Shell pattern from the superposition of trails in a BNS with extreme double eccentricity"> |

**In summary:**
- **True causal gravity**: forces travel at finite speed *c*, not instantaneously, through history buffers at multiple resolution levels. The engine compensates for the resulting aberration rather than inheriting it ([§3 of the Physics Guide](PHYSICS_AND_SCENARIO_GUIDE.md#3-causal-aberration-dead-reckoning-and-relativistic-dynamics)).
- **Analog gravitational waves**: the wavefronts $d\Phi/dt$ in the mergers emerge from the causal dynamics (2D scalar analog, not real tensor waves), and the **GW Strain** heatmap projects the quadrupole of the retarded velocities with the true spin-2 angular symmetry.
- **LIGO probe + spectral pipeline**: records the strain (the deformation of space measured by the interferometer) of the mergers and estimates their chirp mass (the combination of masses that governs the signal), comparing it with Peters' analytical formula (the theoretical chirp trend of a radiating binary).
- **Real-time on consumer CPU**: Numba JIT kernels (compiled on the fly in machine code), up to 600,000 TPS (physics ticks per second) at 60 FPS in compact mergers.
- **Interactive sandbox**: body spawns, Keplerian orbits, Lagrange points, Newtonian/causal switch on the fly.

---

## Table of Contents

1. [Preview](#preview)
2. [Overview](#overview)
3. [Emerging Phenomena in the Model](#emerging-phenomena-in-the-model)
4. [Preset Scenarios](#preset-scenarios)
5. [Simulation Controls](#simulation-controls)
6. [Installation](#installation)
7. [Field Display Modes](#field-display-modes)
8. [Physical Model](#physical-model)
9. [Software Architecture](#software-architecture)
10. [Model Limitations and Performance Management](#model-limitations-and-performance-management)
11. [LIGO Analyzer](#ligo-analyzer)
12. [Future Developments and Scientific Disclaimer](#future-developments-and-scientific-disclaimer)

---

## Overview

**AstroCausal Engine** is an interactive gravitational simulator and a 2D celestial mechanics laboratory. Designed as an astronomical "sandbox", it allows the exploration of stable orbital dynamics in real scale (from the Solar System to systems of moons and satellites) and the study of frontier physical phenomena through a natively **causal** gravitational model: the forces do not act instantaneously, but propagate at the speed of light *c* through a system of optimized circular history buffers.

The fundamental architectural choice of the project is to operate in a **2+1D** spacetime (two spatial dimensions plus time as an explicit axis) on a flat Euclidean background, without solving the field equations of General Relativity. However, the laws remain those of real three-dimensional physics ($1/r^2$, not the $1/r$ of an intrinsically two-dimensional gravity) and time is absolute in the precise sense of the coordinated time of a **distant observer**, the same convention by which binary pulsars and gravitational waves are timed in reality. This geometric simplification allows the engine to run **in real time on any consumer PC**, stressing the CPU to calculate the physics in double-precision floating point (`float64`) via JIT parallelization.

On the causal core (Newtonian gravity evaluated at the retarded time $t - r/c$), when certain conditions are met, the engine triggers the real radiation reaction of order 2.5PN (Post-Newtonian, the perturbative order at which the loss of energy due to gravitational waves appears) and gives rise to emergent behaviors qualitatively consistent with real relativity (causal aberration, contraction of the Liénard-Wiechert-like field for sources close to $c$, i.e., the same deformation that the field of an electric charge in rapid motion undergoes, chirps and analog gravitational waves measured by a virtual LIGO probe), offering an educational laboratory for exploring and comparing classical mechanics and finite-delay causal dynamics.

The balance between physical fidelity and graphic fluidity is largely **in the hands of the user**: the engine offers a balance but allows the time step, calculation speed, and heatmap resolution to be adjusted in real time.

### Main Features

- **Interactive Sandbox & Spawner**: Dynamic insertion of celestial bodies in real time with instant setting of stable Keplerian orbits, eccentric trajectories, collisions (plunge), or positioning at the L1–L5 Lagrange points.
- **Celestial System Presets**: Extensive catalog of ready-to-use scenarios, including the complete Solar System (with 26 moons), the Jupiter system, the Earth with satellites in low orbit (ISS, Hubble), and extreme cosmic events such as binary black holes and galactic collisions.
- **Real-Time Gravitational Heatmaps**: Dynamic rendering of physical fields in the background, including the scalar gravitational potential $\Phi$, the scalar waves $d\Phi/dt$ (analog waves), the Hessian tidal stress, the topology of the Roche lobes in the co-rotating frame, and the **projected quadrupole strain (GW Strain)** with the causal radiative spirals of compact binaries.
- **Flexibility and Control**: Dynamic adjustment of the time step ($DT$), speed multipliers for physics calculations, instantaneous switch between Newtonian and causal gravity (C key), orbit tracking, and virtual LIGO probe to record gravitational strain.
- **LIGO Analyzer Pipeline**: Independent application for the spectral post-processing of wave dumps (Tukey windowing, high-pass filters, STFT spectrograms, Hilbert transform for instantaneous frequency, regression, and automatic chirp mass estimation).
- **Numba JIT Engine**: Velocity Verlet brute-force integration $O(N^2)$, compiled Just-in-Time and parallelized on the CPU cores above a body threshold (below which it remains sequential to avoid thread overhead).

---

## Emerging Phenomena in the Model

These dynamic behaviors **are not explicitly programmed**, but emerge naturally from the dynamics and dead reckoning (the extrapolation of position from known position and velocity) of the causal gravitational interaction:

<small>The thumbnails are clickable and open the folder with all available media. Each phenomenon listed here is discussed in depth, including equations and validation graphs, in the [Physics and Scenario Guide](PHYSICS_AND_SCENARIO_GUIDE.md).</small>

| | |
|---|:---:|
| **Causal propagation visible to the naked eye**: By instantly destroying or creating a body, gravitational information propagates visually at the speed of light. Distant bodies continue to "feel" the destroyed body until the absence front reaches them (and, conversely, a new body remains invisible to distant bodies until the causal front arrives). | <a href="docs/gif/"><img src="docs/gif/Sun_causal_birth.gif" width="400" alt="Causal birth of the Sun: the gravitational front propagates outward at the speed of light"></a> |
| **Visual analogy of gravitational waves**: In the dΦ/dt heatmap, compact binaries in the inspiral phase (the progressive spiral approach before the merger) produce concentric wavefronts with increasing frequency and amplitude, in perfect visual analogy with the real gravitational waves emitted by the mergers. | <a href="docs/gif/"><img src="docs/gif/dphi_spirale_binaria.gif" width="400" alt="Concentric dPhi/dt spirals emitted by a neutron star binary in inspiral"></a> |
| **Lagrange points L1–L5**: They emerge in the Earth-Moon system and can be dynamically visualized in the Lagrange Hunter. | <a href="docs/img/"><img src="docs/img/lagrM.png" width="400" alt="Lagrange Hunter with the [M] overlay: analytical theoretical markers labelled L1-L5"></a> |
| **Breathing of the Roche Lobe**: The periodic expansion and contraction of the lunar Roche Lobe in phase with its orbital eccentricity (the lobe expands at apogee and contracts at perigee). | <a href="docs/img/"><img src="docs/img/moon_earth_roche.png" width="400" alt="Roche topology of the Earth-Moon pair with the ideal circular orbit overlay"></a> |
| **Liénard-Wiechert distortion**: The causal geometric contraction of the isolines of the potential $\Phi$ transversely to the direction of motion for high-speed sources. | <a href="docs/gif/"><img src="docs/gif/07_to_c_fast.gif" width="400" alt="Lienard-Wiechert contraction of the potential isolines as the source accelerates from 0.7c toward c"></a> |
| **Gravitational Chirp**: The progressive increase in frequency and amplitude of the potential wavefronts emitted by compact binaries in inspiral driven by quadrupole dissipation. | <a href="docs/img/"><img src="docs/img/GW150914_STFT_STRAIN.png" width="400" alt="STFT spectrogram of the GW150914 strain showing the rising chirp"></a> |
| **Parameter-free BNS validation on Peters' formula**: in the GW170817 scenario (neutron star binary), the chirp mass estimated by the spectral pipeline of the virtual LIGO probe matches Peters' analytical formula with an error of only **0.97%**, in *parameter-free* mode (only equations from first principles, no calibration coefficient). [Details, graphs, and limits in §6.6.1 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#661-the-bns-scenario-gw170817-peters-vs-sxs-numerical-relativity). | <a href="docs/img/"><img src="docs/img/confronto_sxs_gw170817_bns.png" width="400" alt="BNS comparison: simulation, Peters curve and SXS:NSNS:0001 numerical relativity"></a> |
| **Emergence of the ISCO and the plunge**: In the BBH scenario (black hole binary, GW150914), the orbital separation decays until the masses reach the ISCO threshold, the Innermost Stable Circular Orbit, the last stable circular orbit below which every trajectory plunges (theoretical frequency of 62.06 Hz). At this point, the system spontaneously triggers the rapid spiral fall (plunge) at a frequency of 62.40 Hz without any forcing in the code. | <a href="docs/gif/"><img src="docs/gif/BBH_GWH_demo.gif" width="400" alt="GW Strain heatmap of a black hole binary reaching the ISCO and entering the plunge"></a> |
| **Parameter-free BBH validation on NR SXS**: in the GW150914 scenario (black hole binary), the simulated chirp trace follows the reference numerical relativity curve (SXS:BBH:0305) with an average error of **1.27%** throughout the inspiral, compared to 7.47% for Peters' analytical formula at the dominant order ([details and graphs in §6.6.2 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#662-the-bbh-scenario-gw150914-comparison-with-sxs-numerical-relativity)). | <a href="docs/img/"><img src="docs/img/confronto_sxs_gw150914.png" width="400" alt="BBH comparison: simulation, Peters curve and SXS:BBH:0305 numerical relativity"></a> |
| **The single-body dipole in dΦ/dt**: the time derivative of the potential of a body in motion alone produces a dipole front, blue in front and red behind, the base on which the spirals of the binary pair are then grafted. | <a href="docs/gif/"><img src="docs/gif/dphi_dipolo_giove.gif" width="400" alt="dPhi/dt dipole of Jupiter moving alone: blue leading front, red trailing front"></a> |
| **The passage to perihelion in EMRI**: in the early stages of the inspiral, each pericenter releases an isolated strain pulse that propagates as a concentric shell at speed $c$, separated from the next one by large regions of silence. | <a href="docs/img/"><img src="docs/img/GWH_EMRI_dezoom_early_pattern.png" width="400" alt="Isolated strain pulses released at each EMRI pericenter, propagating as concentric shells"></a> |
| **Apsidal precession in a strong field**: in compact orbits (e.g., EMRI), the orbit precesses in a rosette shape not due to a dedicated routine, but due to the Paczyński-Wiita correction at the pericenter, reinforced by the dead reckoning residue beyond the 2nd order. | <a href="docs/gif/"><img src="docs/gif/EMRI_rosetta.gif" width="400" alt="Rosette-shaped apsidal precession of an EMRI orbit"></a> |

---

## Preset Scenarios

*How to read the table*: **DT** is the time step, i.e., how much simulated time advances with each tick (smaller = more precise and "slower" in real time). The **Causal Radius** ($D_{max}$) is the distance within which the forces travel at finite speed $c$ by querying the history buffers; beyond that radius, the interaction returns to instantaneous Newtonian. Unit: $1\text{ AU}$ (Astronomical Unit) $= 149,597,870.7\text{ km}$, the average Earth-Sun distance.

| Scenario | Bodies | DT | Causal Radius | Description |
|---|:---:|:---:|:---:|---|
| **Complete Solar System** | 36 | 150 s | 64 AU | Sun, 8 planets, Pluto and 26 main moons |
| **Solar System (Light)** | 10 | 512 s | 64 AU | Only the Sun and 9 planets, without moons: higher DT without losing Keplerian fidelity, outer orbits observable in a reasonable time |
| **Galactic Orbit (Sgr A\*)** | 11 | 512 s | 64 AU | Solar System orbiting at 230 km/s around Sagittarius A\* |
| **Chaotic Cluster** | 100 | 64 s | 64 AU | N-body stress test with central BH of 1000 M☉ |
| **Earth - Moon - ISS - Hubble** | 4 | 1 s | 1 AU | Geocentric regime with ISS and Hubble in LEO orbit |
| **Sun - Earth - Moon - Artemis II** | 4 | 0.16 s | 1 AU | Passive translunar cruise of Orion on real JPL Horizons vectors, up to the free-return flyby |
| **Complete Jovian System** | 14 | 60 s | 1 AU | Jupiter and 13 moons (inner, Galilean, irregular) |
| **Approach to *c* (0.999c)** | 1 | 0.16 s | 320 LY (~20M AU) | Sun at 0.999c: Liénard-Wiechert distortion (20 GB RAM) |
| **Approach to *c* (0.9c)** | 1 | 1.6 s | 1742 LY (~110M AU) | Light version (10 GB RAM) |
| **Approach to *c* (0.7c)** | 1 | 16 s | 8710 LY (~550M AU) | Ultra-light version (5 GB RAM) |
| **NS Binary: Stable Orbit** | 2 | 1 ms | 640 AU | Two neutron stars ~1.5 M☉ at 40,000 km |
| **NS Binary: Extreme Eccentricity** | 2 | 1 μs | 3 AU | Highly eccentric twin orbits (apocenter 4000 km, pericenter 200 km) |
| **NS Binary: Pre-Collision** | 2 | 1 μs | 2 AU | Late inspiral, merger in ~59.7 s simulated |
| **GW170817** | 2 | 1 μs | 3 AU | Replica of the first multi-messenger event (merger in ~13.9 s simulated) |
| **GW150914** | 2 | 1 μs | 3 AU | First GW event detected by LIGO (merger in 52.034 s simulated, theoretically initialized at T-60s) |
| **GW190814** | 2 | 1 μs | 3 AU | The most asymmetrical merger (q = 0.112): 23 M☉ BH and 2.6 M☉ mass gap object (initialized at T-20s via Peters) |
| **Alpha Centauri + Polyphemus** | 9 | 150 s | 32 AU | Real triple system + fictional system from *Avatar* |
| **Extreme Orbits Laboratory** | 6 | 0.2 s | 2 AU | Central BH + 5 test particles (e=0 → hyperbolic) |
| **EMRI: Relativistic Plunge** | 2 | 0.05 s | 1200 AU | Extreme Mass Ratio Inspiral: a light black hole spirals into a much more massive one (ratio 1:100) |
| **Collision between Dwarf Galaxies** | 202 | 150 s | 64 AU | Near-frontal collision of two 100-star galaxies |
| **Empty Scenario** | 0 | 1 s | From astro_settings.ini | Empty universe for free construction (can be set via .ini file) |

---

## Simulation Controls

### Navigation

| Key | Action |
|:---:|---|
| `Mouse drag` | Camera pan |
| `Mouse wheel` | Zoom in/out |
| `WASD / Directional arrows` | Camera pan (continuous movement of the view) |
| `Double click on body` | Lock camera on selected body |
| `Double click on empty space` | Field probe at cursor point (Φ, dΦ/dt, Tidal) |
| `TAB` | Cycle between active bodies |

### Simulation

| Key | Action |
|:---:|---|
| `SPACE` | Pause / Resume |
| `1-5` | TPS multiplier: 1×, 10×, 100×, 1000×, 10000× physics steps per frame, adjusts simulation speed without affecting model accuracy |
| `T` | Halves the DT: more precise, halves the simulation speed, more RAM used |
| `Y` | Doubles the DT: less precise, doubles the simulation speed, less RAM used |
| `C` | Switch Newtonian ↔ Causal (complete reconstruction) |
| `BACKSPACE` | Close and return to the launcher |

### Display

| Key | Action |
|:---:|---|
| `H` | Cycle heatmap mode: OFF → Φ Scalar [Causal] → dΦ/dt [Causal] → Tidal Stress [Newtonian] → OFF |
| `L` | Cycle pair heatmaps: Lagrange Hunter → Roche Topology [Newtonian] → GW Strain [Causal] → Φ (requires body with lock and dominant attractor) |
| `R` | Show/hide orbital trails |
| `G` | Cycle heatmap resolution: AUTO → 1/1 → 1/2 → 1/4 → ... → AUTO |
| `M` | Toggle legend (in Tidal) or theoretical Lagrange markers (in Lagrange Hunter) or ideal circular orbit (in Roche Topology) |
| `F` | Key legend (overlay) |

### Tools

| Key | Action |
|:---:|---|
| `P` | Place/remove LIGO probe at cursor position |
| `N` | Open the Orbital Spawner at the cursor position |
| `K` | Request the destruction of the body with lock (confirm Y/N) |

---

## Installation

### Requirements

- **Python** 3.10+
- **Operating system**: Windows 10/11 (recommended), Linux or macOS
- **RAM**: Minimum 4 GB for standard scenarios, 8–20 GB for high-resolution relativistic scenarios (low DT)

### Dependencies

```
numpy
pygame-ce
numba
matplotlib
scipy
```

### Setup

```bash
# Clone the repository
git clone https://github.com/alessandro-pioli/AstroCausal_Engine.git
cd AstroCausal_Engine

# Install the dependencies
pip install -r requirements.txt

# Start the launcher
python launcher.py
```

> **Note**: On the first startup, Numba compiles the physics and graphics kernels and caches them to disk (therefore, only the first time). Compilation is fast, but it can produce brief **stutters** the first time you activate a function that has not yet been compiled during use (for example, during the first cycle between heatmaps). This is normal and disappears immediately afterwards.

---

## Field Display Modes

### 1. Scalar Potential Φ — `[Causal]` (H key)
Color map of the gravitational potential, calculated from the historical (causal) positions of the bodies. For a single moving body, it shows the **potential well** that accompanies it; for bodies in rapid uniform rectilinear motion, the Liénard-Wiechert denominator deforms and compresses the isolines transversely to the direction of motion (analogous to the distortion of the electric field of a moving charge). The classic red-blue "dipole" does not belong to this map, but to the dΦ/dt variation described below.

### 2. Variation of the Potential dΦ/dt — `[Causal]` (H key × 2)
Represents the temporal variation of the scalar gravitational potential, calculated from the historical (causal) positions. For a moving body sufficiently distant from the others, the characteristic **dipole** appears: a **leading blue front** (where the potential deepens as the body approaches) and a **trailing red front** (where it relaxes). In compact binary mergers, the fronts become concentric and increase in frequency and amplitude: the visual scalar analogue of gravitational waves.
* **Right fader (Sensitivity, range `[-4, 2]`):** increases or decreases the visual intensity. The higher it is, the easier it is to see the fronts of the dipoles **merge and blend** with those emitted by the more massive distant bodies; the lower it is, the more the nearby fronts are isolated, preventing the screen from being overwhelmed.

### 3. Tidal Stress (Tidal Map) — `[Newtonian]` (H key × 3)
Map of the **deviatoric norm of the Hessian matrix** of the Newtonian gravitational potential, calculated from the instantaneous positions. The components of the Hessian $\partial^2 \Phi / \partial x_i \partial x_j$ are calculated analytically for each body:

$$H_{ij} = G \cdot m \left(\frac{\delta_{ij}}{r^3} - \frac{3 x_i x_j}{r^5}\right)$$

The stress displayed is the **difference between the two eigenvalues of the Hessian**, $\sqrt{(\Phi_{xx} - \Phi_{yy})^2 + 4\Phi_{xy}^2}$ (proportional to the deviatoric part of the tensor): it measures the maximum **shear stress**, i.e., how much a body would be stretched in one direction and compressed in the orthogonal direction. It highlights areas of extreme tidal stress (for example, the orbit of Io around Jupiter). The coloring is on fixed physical scales: from blue (safe region) to red (structural disintegration) to white (near the singularity). The `M` key shows the **legend** with the thresholds, so you can see at a glance at what stress a body would be disintegrated.

### 4.A. Lagrange Hunter — `[Newtonian]` (L key with selected body)
Co-rotating 2-body frame (selected body + dominant attractor) for identifying orbital equilibria. This mode does not render a continuous heatmap of the field, but identifies and highlights the **L1–L5 Lagrange points** as discrete bright points on a completely black background. The kernel calculates the gradient and the Hessian of the potential and uses a **distance estimator based on the Newton-Raphson method in 2D** ($r_{est} = |H^{-1} \nabla \Phi|$) to draw shaded "blobs" at the gradient zeros. The points are classified topologically using the Hessian: the unstable saddle points (L1, L2, L3) appear as **red points**, while the stable maxima of the co-rotating potential (L4, L5) appear as **blue points**. The local minima of the potential (gravitational wells at the center of the bodies, with $D > 0$ and $\text{Tr}(H) > 0$) are excluded from the filter on the Hessian trace, preventing the appearance of false blue blobs superimposed on the bodies. Pressing `M` overlays the analytical theoretical markers for an immediate comparison with the points that emerge numerically from the calculation.
* **Right fader (Sensitivity, range `[-8, 8]`, default `0.0`):** Adjusts the size of the displayed Lagrange points. By reducing the sensitivity, the points shrink to indicate the exact equilibrium coordinate precisely; by increasing it, the points expand to show the surrounding area of gravitational attraction. Thanks to automatic calibration, the default value of `0.0` clearly shows the points for any system (from Saturn to binary black holes).
* **Note on use (Planets vs Moons):** In systems where the planet is very small compared to its star, the L3, L4, and L5 points are very weak and tend to blend together, fading along the entire orbit. In systems where the mass ratio is more balanced (such as a large moon orbiting its planet), all points instead emerge clearly, sharply, and well separated.

### 4.B. Roche Topology — `[Newtonian]` (L key × 2)
Map of the **effective potential in the co-rotating frame** of the selected pair (body + dominant attractor). The angular velocity $\omega$ is kinematically derived from the instantaneous specific angular momentum of the pair ($h = \vec{r} \times \vec{v}_{rel}$, $\omega = h / r^2$): the frame rotates like a **rigid disk** (each point co-rotates at the same $\omega$, with linear velocity $v = \omega r$). The effective potential adds the complete N-body gravity and the centrifugal term, net of the free-fall drag due to third bodies.

The map encodes **two independent pieces of information**, to be read separately:

- **Brightness = modulus of the net force** $|\nabla \Phi_{eff}|$, on a logarithmic scale. Where the force is almost zero, the map is **dark**: these are the **equilibrium points** and the low-force channels (the Lagrange points, primarily the L1 saddle between the two bodies). Black therefore marks *where a co-rotating particle would not feel a net force*.
- **Color = sign of the determinant of the Hessian** $D = \Phi_{xx}\Phi_{yy} - \Phi_{xy}^2$, i.e., the local *curvature* of the potential, **independent of the brightness**:
 - **Red ($D < 0$, saddle)**: dominates near the bodies. There, a co-rotating particle **would fall towards the attractor**: gravity prevails and stretches the potential (radial elongation, transverse compression).
 - **Blue ($D > 0$, dome)**: dominates far from the bodies. There, the co-rotating velocity $v = \omega r$ exceeds the Keplerian velocity $\sqrt{GM/r}$: the centrifugal force prevails and a co-rotating particle **would be thrown outward**.

The **Roche lobe** does not coincide with the boundary between red and blue (that is the line where the curvature $D$ changes sign, a different geometric locus): it is the **equipotential of $\Phi_{eff}$ that passes through L1**, and it can be visually read from the **dark channels** around the bodies. The low-force "eight" figure that closes right on the L1 saddle marks the maximum volume that a body can occupy before its matter overflows (*Roche Lobe Overflow*). The more extreme the mass ratio, the more the secondary's lobe shrinks into an elongated "drop" along the tidal axis.
* **Right fader (Sensitivity, range `[-8, 8]`):** raises or lowers the overall brightness to bring out the faintest details or darken the background.
* **Left fader (Contrast, range `[0, 100]`):** controls the sharpness of the brightness transition; increasing it thins the dark channels around L1 and makes them sharper, making it easier to identify the overflow point.

### 4.C. GW Strain (Quadrupole) — `[Causal]` (L key × 3)
The most sophisticated visualization of the dynamic field: it maps the **projected quadrupole gravitational strain** of the selected pair. For each pixel, the kernel reads the position and velocity of each body **at the retarded time of that pixel** (double causal retrieval on the history buffers), subtracts the motion of the center of mass, and projects the retarded velocity along the pixel-source direction: the quadratic difference between the radial and tangential components reproduces the exact quadrupole angular symmetry ($\ell=2$) of the real gravitational radiation, with the characteristic four alternating cyan/red lobes and, for compact binaries in inspiral, the **radiative macro-spirals** propagating outward at speed $c$. It is the spatial counterpart of the point LIGO probe (same physics, same kinetic regularization). The complete mathematics, the effects of per-body causality, and the post-merger artifacts are documented in [§7.6 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#76-projected-strain-gw-quadrupole-strain).
* **Right fader (Sensitivity):** shared with Roche mode; scales the visual amplitude of the strain (asinh compression, which preserves faint details in the far field without saturating the peaks near the pair).

---

## Physical Model

The model is **2+1D with absolute time**: all the dynamics exist in the two dimensions of the plane (a slice of the 3D universe, with the $1/r^2$ laws of three-dimensional physics) while a single universal clock marks the time for each body. It is the point of view of a **distant observer**, without time dilation or curved metric. Relativity enters from the side of the interactions, with causality at finite speed $c$ and the corrections described below ([full framework in §1 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#1-background-the-causal-model-and-the-2d-approximation)).

### Fundamental equation

The interaction between each pair of bodies follows Newton's law of universal gravitation:

```
F = G · M · m / r²
```

with the crucial difference that the position, velocity, and mass of the source body are **taken from the history buffer** at the retarded time $t_{ret} = t - r/c$, where $r$ is the distance and $c$ is the speed of light.

For sources in relativistic motion, the gravitational potential is corrected by inserting the classical **Liénard-Wiechert** denominator $(dist - \vec{v} \cdot \vec{r}/c)$ to describe the field contraction, concentrating the gravitational force orthogonally to the direction of motion ([further details in §5 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#5-liénard-wiechert-deformation)).

---

> [!NOTE]
> ### How the simulator avoids aberration instability
> In discrete causal gravity, the aberration of force (due to the fact that gravity points towards the retarded position) introduces a fictitious torque that tends to rapidly widen the celestial orbits. To mitigate this numerical instability and preserve long-term Keplerian stability, the engine implements a **Hybrid Dead Reckoning** (the technique, borrowed from navigation, of estimating where a body *is now* based on where it was and its velocity) at the JIT kernel level:
>
> 1. **Quadratic Dead Reckoning (2nd order Taylor)**: for stable orbits and ordinary velocities, the position of the source is extrapolated by integrating historical velocity and acceleration at the instant of emission:
> $$\vec{x}_ {eff} = \vec{x}_ {ret} + \vec{v}_ {ret} \Delta t_ {flight} + \frac{1}{2}\vec{a}_ {ret} \Delta t_ {flight}^2$$
> 2. **Dead Reckoning bypass in the GW Regime**: in an extreme relativistic regime (close to the merger, with **relative** velocity of the pair greater than 10% of $c$ and distance less than $1000 \cdot R_s$; for equal masses the criterion is equivalent to 5% of $c$ for a single body, but it also remains valid for asymmetric pairs where the heavy body moves slowly), the engine disables linear extrapolation and uses the **exact present position** of the source for both direction and distance in the calculation of forces. This fundamentally eliminates the accumulation of periodic radial error $O((v/c)^2)$ responsible for orbital instability.

---

### Reaction to gravitational radiation (Real 2.5PN term)

In compact binary mergers, the orbit decays due to the emission of gravitational waves. The engine implements first-order non-conservative dissipative acceleration (**2.5PN-order radiation reaction**) according to the **Damour-Deruelle** real relativistic formulation for the relative acceleration $\vec{a}_{rel}$ (theoretical context and history of implementation in [§6.2-6.5 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#62-what-are-post-newtonian-orders-and-25pn)):

$$\vec{a}_{rel} = \frac{8}{5}\frac{G^2 M \mu}{c^5 r^3}\Big[\dot{r}\big(18v^2 + \tfrac{2}{3}\tfrac{GM}{r} - 25\dot{r}^2\big)\hat{n} - \big(6v^2 - 2\tfrac{GM}{r} - 15\dot{r}^2\big)\vec{v}\Big] $$

where $M$ is the total mass of the pair, $\mu$ is the reduced mass, $\hat{n}$ is the separation unit vector, and $\vec{v}$ is the relative velocity. This acceleration is calculated and applied to each body based on its reciprocal mass contribution ($m_{src}/M$), ensuring the conservation of the overall linear momentum. The calculation operates in *parameter-free* mode, delegating the evolution of the orbit solely to the theoretical expression of order $2.5\text{PN}$.

### Integration Scheme: Velocity Verlet

To ensure the conservation of orbital energy and the long-term stability of complex gravitational systems, the engine adopts a **Velocity Verlet** integration scheme (implemented in the Numba JIT kernels in `kernel_single.py`, `kernel_double.py`, and `kernel_triple.py`; the analysis of the truncation error is in [§4 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#4-numerical-methods-velocity-verlet-truncation-error-and-dt)). Each physics integration step follows this precise time sequence:

1. **First "Half-Kick" of the velocities** (with warm-start of the accelerations at time $t=0$ pre-calculated during the rebuild phase via NumPy broadcasting):
 $$\vec{v}\left(t + \frac{\Delta t}{2}\right) = \vec{v}(t) + \frac{1}{2} \vec{a}(t) \Delta t$$
2. **Position update ("Drift")**:
 $$\vec{x}(t + \Delta t) = \vec{x}(t) + \vec{v}\left(t + \frac{\Delta t}{2}\right) \Delta t$$
3. **Sequential collision resolution**:
 Any physical contact or capture at the event horizon instantly changes positions and velocities before the forces are calculated.
4. **Causal calculation of forces and acceleration**:
 The accelerations $\vec{a}(t + \Delta t)$ are calculated by evaluating the causal gravitational forces produced by all bodies, querying the history buffers at the instant of emission ($t_{ret} = t - r/c$).
5. **Relativistic correction of inertia**:
 Below the threshold of $v^2 = 0.5 c^2$ (≈ 0.707 c), the acceleration remains unchanged. Above that threshold, it is rescaled by the inverse Lorentz factor, which suppresses it as $v \to c$:
 $$\vec{a}_{eff}(t + \Delta t) = \vec{a}(t + \Delta t) \cdot \sqrt{1 - \frac{v^2}{c^2}}$$
 Beyond the threshold $v^2 = 0.999 c^2$ (about $0.9995 c$), the acceleration is completely zeroed: under ordinary conditions, a body can no longer be pushed beyond that limit.
6. **Second "Half-Kick" of the velocities**:
 $$\vec{v}(t + \Delta t) = \vec{v}\left(t + \frac{\Delta t}{2}\right) + \frac{1}{2} \vec{a}_{eff}(t + \Delta t) \Delta t$$

### The Determining Role of DT (Time Step)

The **DT** parameter ($\Delta t$) is the fundamental constant that governs the temporal discretization of the model. Its choice is the most determining factor in the balance between physical accuracy, sampling capacity, and system resources, due to three competing dynamics:

#### 1. Accuracy of Numerical Integration
As the time step of the Velocity Verlet algorithm, $\Delta t$ defines the local truncation error of the trajectory ($O(\Delta t^4)$ for the positions).
- In ordinary systems (e.g., stable planetary orbits), $\Delta t$ can rise to the order of minutes (in the complete Solar System, 150 s is used), beyond which the fidelity of the orbits begins to degrade.
- In compact and relativistic systems (e.g., inspiral and merger of compact binaries), the accelerations and velocities of the bodies vary extremely over fractions of a second. To prevent causal aberration and dissipative forces from introducing numerical instabilities (causing the expulsion or premature merger of bodies), it is mathematically necessary to set a microscopic $\Delta t$, down to $1\ \mu\text{s}$.

#### 2. Linear Memory Scaling (RAM) and Causal Radius Limit
Since gravitational forces propagate at the finite speed $c$, each body must calculate the interactions by going up its light cone to the maximum flight time:
$$t_{flight\_max} = \frac{D_{max}}{c}$$
where $D_{max}$ is the maximum operational causal distance set for the scenario. The logical depth of the memory ring buffers for each body must cover at least $t_{flight\_max}$. The number of elements $N_{elements}$ to be allocated for each buffer of each body therefore scales as:
$$N_{elements} = \frac{t_{flight\_max}}{\Delta t} \propto O\left(\frac{1}{\Delta t}\right)$$

This relationship shows how the RAM requirement is inversely proportional to $\Delta t$. However, the constraint is managed upstream: each preset chooses its own **causal cone radius** ($D_{max}$), and the `SimulationManager` **reads** it, sizing the buffers accordingly to optimize memory. For this reason, the predefined scenarios have "ideal" values of $D_{max}$, chosen on a case-by-case basis:
- **In Binary Mergers (e.g., GW170817 or GW150914)**: Despite a microscopic $\Delta t$ ($1\ \mu\text{s}$), the scenario occupies a few hundred MB of RAM. This is because the `SimulationManager` sets the maximum causal radius $D_{max}$ to only **3 AU** (Astronomical Units), a small distance but amply sufficient to describe the entire final inspiral and coalescence phase of the pair.
- **In relativistic approaches to *c* (e.g., at 0.999c)**: The very high RAM consumption (**~20 GB**) is a deliberate design choice. To trace the cumulative effect of wave propagation and highlight in the heatmap **320 years of history of emission** of the gravitational signal geometrically compressed by the relativistic deformations of Liénard-Wiechert, a huge temporal depth of the buffer is required, which causes memory usage to skyrocket.

#### 3. Calculation Frequency (TPS)
With the same hardware performance (TPS - Ticks Per Second), a smaller $\Delta t$ slows the progression of the simulated real time with respect to the user's real clock time. The engine compensates for this effect by multiplying the calculations per frame (via the in-game speed multiplier `1-5`), but at the cost of an additional linear calculation load on the CPU.

### The Role of the Simulation Radius (Sim Radius)

The **Simulation Radius** (or *Sim Radius*) defines the maximum extent of the causal interaction. It works as a sort of "radar" or causal horizon centered on each celestial body:
* **Within the radius limit:** The gravitational attraction between two bodies is calculated at finite speed $c$ by querying the history buffers. Physical causality is 100% guaranteed.
* **Beyond the radius limit:** To optimize RAM and prevent memory blocks, the interaction is processed instantly according to classical Newtonian law (infinite speed).

For an ideal simulation, the simulation radius must be set to a value large enough to allow each body to easily reach any other active coordinate in the scenario. This causes the causal horizons to overlap entirely, ensuring reciprocal and consistent causality throughout the simulation.

---


## Software Architecture

```
AstroCausal_Engine/
├── launcher.py              # Tkinter launch GUI (preset, DT, resolution)
├── main_gui.py              # Main Pygame loop (events, physics, rendering)
├── ligo_analyzer.py         # LIGO post-processing (spectrograms, chirp mass)
├── astro_settings.ini       # User configuration file (editable)
├── config.py                # Internal settings loader (do not modify)
├── core/
│   ├── data.py              # Global state: NumPy arrays, physical constants
│   ├── engine.py            # Physics engine (JIT kernel orchestrator)
│   ├── bodies.py            # CelestialBody class
│   ├── presets.py           # Scenario definitions (Solar System, GW, etc.)
│   ├── simulation_manager.py # Dynamic reconstruction (rebuild, alloc, snapshot)
│   ├── space_probe.py       # LIGO probe controller
│   ├── global_state.py      # UI/simulation state (pause, view mode, etc.)
│   ├── event_handler.py     # Pygame event dispatcher
│   └── jit_kernels/         # Numba JIT kernels
│       ├── kernel_single.py      # Integration with single buffer (L0)
│       ├── kernel_double.py      # Integration with double buffer (L0 + L1)
│       ├── kernel_triple.py      # Integration with triple buffer (L0 + L1 + L2)
│       ├── graphics_kernel.py    # Field rendering (Φ, dΦ, Roche, Tidal)
│       └── kernel_helper_inline.py # Core of the computation: causal forces, dead reckoning, collisions, LIGO probe
├── ui/
│   ├── camera.py             # 2D camera (pan, zoom, lock)
│   ├── gravity_renderer.py   # GPU-like heatmap renderer on CPU
│   ├── master_renderer.py    # Final layer composition
│   ├── overlay_renderer.py   # HUD, telemetry, legends
│   ├── input_controller.py   # Input → action mapping
│   ├── orbital_spawner.py    # Interactive spawner with Lagrange points
│   ├── hud_components.py     # Vertical faders for sensitivity
│   ├── game_console.py       # In-game console with timestamped logs
│   └── tutorial_popup.py     # Tutorial popup system
└── utils/
    ├── loading_splash.py     # Loading splash screen
    ├── formatting.py         # Unit formatting (km, AU, dt)
    ├── performance_manager.py # Heatmap resolution auto-tuner
    ├── event_logger.py       # Impact and death tracker
    └── gc_worker.py          # Asynchronous garbage collector
```

### Execution flow

```
launcher.py  ──(subprocess)──►  main_gui.py
                                    │
                                    ├─ show_splash_and_load()
                                    │   ├─ presets.get_preset()
                                    │   └─ rebuild_simulation()    ← allocates buffers, computes memory
                                    │
                                    ├─ Engine(bodies)              ← compiles JIT kernels
                                    │
                                    └─ MAIN LOOP
                                        ├─ EventHandler.handle_events()
                                        ├─ Engine.tick(speed_mult)
                                        │   └─ kernel_single / kernel_double / kernel_triple
                                        └─ MasterRenderer.render_all()
                                            └─ GravityRenderer → graphics_kernel
```

> For the full account of the engineering choices (DOD, branchless dispatch, asynchronous GC, adaptive LOD buffers), see the document [ARCHITECTURE_DEEP_DIVE.md](ARCHITECTURE_DEEP_DIVE.md).

## Model Limitations and Performance Management

AstroCausal Engine is an educational and numerical exploration tool. It has the following physics limitations with respect to formal general relativity:

- **Flat space (Euclidean)**: There is no curvature of spacetime (no metric). The gravitational field is modeled as a classical scalar/vector force field superimposed on a flat Euclidean background.
- **2D approximation**: The simulation takes place on a two-dimensional plane. This alters the real 3D radial kinematics and the energy balance of real systems.
- **Analog gravitational waves (two levels of abstraction)**: no visualization solves Einstein's field equations. The first level, the heatmap $d\Phi/dt$, shows the real causal propagation of a scalar field: the spiral fronts and the chirp are a visual and kinematic analogue, without a tensor structure. The second level, the **GW Strain** heatmap, implements the classic quadrupole formula (weak field approximation) projected pixel by pixel at the retarded time: it reproduces the real spin-2 angular symmetry with the four alternating lobes, eliminating the spurious dipole contributions. The pair of independent polarizations $h_+$/$h_\times$ (here there is only one effective projected polarization) and the acceleration term of the complete formula, excluded for numerical stability, are left out ([the complete picture is in §7.7 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#77-the-nature-of-the-simulators-waves-levels-of-abstraction)).
- **Computational cost $O(N^2)$**: The calculation of the forces is brute-force, pair by pair. The cost scales quadratically with the number of bodies: doubling $N$ quadruples the calculations per tick. Furthermore, the numerical accuracy and the estimate of the chirp mass depend on the choice of the time step $DT$: reducing the $DT$ (down to the microsecond for mergers) increases the accuracy at the expense of RAM consumption.
- **Symbolic nature of collisions and merger**: Dynamic orbital physics and causal dissipation are rigorously applied until the moment of geometric impact (for solid/ordinary bodies) or entry into the respective ISCO / event horizon (for black holes). The exact moment of the collision (merger) and the subsequent union into a single body are modeled in a purely kinetic and symbolic way (conservation of momentum, instantaneous fusion of masses, and empirical mass loss). The real complexities of relativistic magnetohydrodynamics, neutrino emissions, the structural deformation of bodies, and the complex *ringdown* phase of post-merger spacetime are completely omitted.
- **Absence of tidal disruption**: bodies change mass and state only by **geometric collision**, never by tidal stress. A star that greatly exceeds the Roche limit, and which in reality would be torn to pieces at a distance, remains intact here. This can produce occasional pseudo-relativistic jets that would not physically occur, because the body would have already been destroyed beforehand. As a visual mitigation, the **Tidal Map** (with its color scale and legend) allows you to recognize at a glance when a body would be disrupted at a distance and when it would not.

### Computational Bottleneck and Graphics Optimizations (CPU Rendering)

Running an interactive physics simulation at **60 FPS** (the *frames* generated per second) means having a maximum budget of **16.6 ms per frame**. In this time interval, the CPU must sequentially run both the physics engine and the rendering of the gravitational field heatmaps in the background.

The real load is largely **in the hands of the user**. The engine offers a balance but allows it to be adjusted in real time: you can deliberately throttle either the **graphics side** (high resolution with many bodies in the scene) or the **physics side** (many bodies with a high multiplier).

The two extremes: with more than twenty bodies at multiplier `5` (10,000×: the engine aims for 10,000 physics ticks per frame), it is normal to drop below 10 FPS. It is a user choice, because it is needed when you want the maximum advancement of the simulated time (more TPS, at a potentially massive cost of FPS). On the other hand, in compact mergers at $\Delta t = 1 \mu\text{s}$, few bodies are needed: there, the engine can handle **600,000 TPS and 60 FPS stably even with the dΦ/dt heatmap at native 2K resolution**, and the high multipliers run without bottlenecks. In fact, several presets use $\Delta t = 1 \mu\text{s}$ with the expected event at 15 simulated seconds or more: at 600,000 TPS, the simulation runs at about **0.6 simulated seconds for each real second**, enough to quickly reach the vicinity of the event, before lowering the multiplier and slowing down by orders of magnitude until the individual microseconds can be observed in super slow-motion. In short, the engine finds the balance but it remains interactive: the strategies below are used to consciously govern it, not to survive everyday use.

The asymptotic analysis of the cost per frame (physics versus rendering per pixel, with the worst-case formula) is documented in [§2.3](ARCHITECTURE_DEEP_DIVE.md#23-the-visualized-side-the-graphics-kernel) and [§3](ARCHITECTURE_DEEP_DIVE.md#3-heatmap-rendering-and-fps-management) of ARCHITECTURE_DEEP_DIVE.md. For practical purposes, one relationship is sufficient: the **TPS (Ticks Per Second)**, the actual physics advance rate, are the product of the multiplier's ticks per frame (keys **1-5**: 1, 10, 100, 1000, or 10000) times the real FPS. The engine adopts a predefined target of **60 FPS** (which can be unlocked or modified in the `.ini` file): at 60 FPS with a multiplier of `5`, the theoretical ceiling is **600,000 TPS** (as in the presets of compact 2-body mergers). In very crowded scenarios (e.g., galactic clashes with ~200 bodies), the weight of the physics lowers the real FPS, proportionally dragging the TPS down as well.

**Concrete example (complete Solar System, 36 bodies, on the reference hardware).** Physics alone supports a ceiling of about **75,000 TPS**. Since the multiplier does not require TPS but **ticks per frame**, the effect is as follows:
* **Multiplier `5`** (10,000 ticks/frame): to stay at 60 FPS, 600,000 TPS would be needed, far beyond the limit. The engine still executes the 10,000 ticks required per frame, so the FPS drops to $75{,}000 / 10{,}000 = 7.5$ FPS.
* **Multiplier `4`** (1,000 ticks/frame): $1,000 \times 60 = 60,000$ TPS is enough for 60 FPS, below the ceiling. The scenario returns to being fluid at 60 FPS.

The rule of thumb is $\text{FPS} = \min(60,\ \text{TPS ceiling} / \text{ticks per frame})$: when a scenario is populated, simply lower the multiplier to bring the FPS back to the maximum, choosing each time how much simulated time to sacrifice for smoothness.

There is also a lever **orthogonal** to the multiplier: if you need to accelerate the simulated time **without losing FPS**, just double the DT (`Y` key). Each tick advances twice the simulated time with the same calculation cost, so the speed of time doubles without sacrificing a single frame. Here the price is not FPS but numerical precision, so it is only worthwhile where the physical context allows it (stable orbits, far from relativistic regimes that require a microscopic DT).

The pixel-by-pixel calculation of heatmaps is the dominant graphics load on the CPU. To contain it, the engine uses three levers:

1. **Resolution of the contained window (default 1200x800)**: the reduced resolution natively limits the number of pixels to be calculated. Full-screen startup scales the grid and requires significantly higher CPU resources.
2. **Dynamic grid scaling (Auto-Tuner or G key)**: if the frame rate drops below 30 FPS, the Auto-Tuner progressively reduces the grid resolution down to 1/16 per axis (up to 256 times fewer pixels to calculate). The same scale can be cycled manually with the **G** key.
3. **Exclusion of minor masses**: in the heatmap of the potential $\Phi$, bodies of negligible mass compared to the dominant body are automatically excluded from rendering (e.g., minor moons next to a gas giant); the threshold and mechanism are in [§2.3 of ARCHITECTURE_DEEP_DIVE.md](ARCHITECTURE_DEEP_DIVE.md#23-the-visualized-side-the-graphics-kernel).

**Summary: how to recover FPS and speed up the simulation**

| Action | Effect | Cost |
|---|---|---|
| Lower the speed multiplier (keys `1`–`5`) | fewer physics ticks per frame, therefore FPS recovered (raising it towards `5` *can* cause them to drop, but not always) | less simulated time per frame |
| Double the DT time step (`Y` key) | more simulated time speed **with the same FPS**, and even less RAM | only numerical precision (where the physical context allows it) |
| Reduce the resolution of the heatmap (`G` key, cycles through the scale factors) | lighter field rendering, FPS recovered | visual detail of the heatmap |
| Turn off the heatmap (`H` key, cycle through the modes until OFF) | resets the graphics cost: the entire frame budget goes to physics, maximum FPS gain | no heatmap on screen |

---

### Memory Management and Structure of the 3 Buffers

Causal propagation requires access to past states that are arbitrarily deep in time. To avoid RAM explosion and protect the CPU cache, the history is a ring buffer system with **three hierarchical levels of resolution**: L0 samples every single tick for close interactions, L1 and L2 sample the remote past at gradually lower resolution. Not all levels are always allocated: at each startup, the engine chooses the combination (only L0, L0+L1, or all three) by comparing the estimated footprint with the L3 cache of the CPU detected on the machine, so the same simulation can allocate different buffers on different PCs. If the requested memory exceeds the available memory, an OOM (Out Of Memory) protection intercepts the error and displays it with a graphic dialog instead of closing the program.

#### Implementation details (reference)
The fine mechanics of the buffers are fully documented in **[§2 of ARCHITECTURE_DEEP_DIVE.md](ARCHITECTURE_DEEP_DIVE.md#2-the-ring-buffer-and-the-position-history)**, where you can find: the 3D data structure `[body, slot, 5 parameters]` with dimensions to the power of 2 and indices managed via **AND bitmask** (to eliminate the cost of modulo division in hot loops); the **sampling strides** of L1 (32 ticks) and L2 (256 ticks) with the mode selection criteria; the **ultra-ECO placeholder allocation** with OOM protection; the L0 → L1 → L2 **causal cascade query** with the complete Earth-Sun numerical example; the **double causal retrieval** (two cascade readings to solve the implicit time-of-flight equation); and the reconstruction of **historical accelerations by finite differences** (the buffers do not store them, to save memory).

---

## LIGO Analyzer

The LIGO analyzer is an independent pipeline accessible from the launcher, intended for the spectral post-processing of the `.npy` binary dumps generated by the simulation probe.

### How to record a signal
During a simulation, the probe is placed with the `P` key on a point in space (ideally near a binary in inspiral; the system suggests when and where through the RADAR alerts). From that moment, at each tick the probe accumulates in a ring buffer the strain $(v_x^2 - v_y^2)\cdot m/r$ relative to the center of mass, always reading the L0 buffer at high resolution. The signal is saved as `.npy` in `ligo_output/` upon exiting the simulation (or when changing DT), ready to be loaded into the analyzer.

### Analysis Pipeline

1. **Loading**: Reading of the binary file and extraction of the DT used to determine the sampling frequency $f_s$.
2. **Pre-processing**: Detrending (removal of the mean offset). The algorithm identifies the maximum peak of the strain on the raw data *before* applying the taper window (Tukey). Previously, by performing the windowing first, the final taper dampened the merger peak (located at the far right of the file), causing the maximum peak to be erroneously detected shifted backwards (to the left, along the rising ramp) and offsetting all calculation checkpoints.
3. **Automatic gatekeeper**: Signal classification to distinguish impulsive signals and negligible noise from actual coherent binary chirp signals.
 - **SPECTRAL** (coherent chirp detected): proceeds with filtering, spectrogram, and chirp mass estimation.
 - **RADIOMETRIC** (impulse/collision/noise): skips filtering and spectrogram, directly shows the unfiltered RAW strain and the cumulative radiated energy map.
4. **Filtering (SPECTRAL only)**: 5 Hz Butterworth high-pass filter to isolate the orbital strain from environmental fluctuations.
5. **Spectrogram (SPECTRAL only)**: Short-Time Fourier Transform (STFT) with Hann window, 95% overlap, and spectral zero-padding.
6. **Chirp Tracker (Hilbert) (SPECTRAL only)**: Extraction of the instantaneous frequency $f(t)$ via Hilbert transform of the analytic signal, with Savitzky-Golay smoothing.
7. **Chirp mass estimate (SPECTRAL only)**: Direct adaptation of the Peters power law $f(\tau)\propto\tau^{-3/8}$ to the cleaned frequency trace in the window prior to the merger (median of the point-by-point estimates), then inverting the classic Peters formula. The method replaced the previous linear regression of $df/dt$, which amplified the curvature of the chirp into a systematic error ([details in §8.8 of the physics guide](PHYSICS_AND_SCENARIO_GUIDE.md#88-the-analyzers-analysis-pipeline-ligo_analyzerpy)).

### Peters' formula (Instantaneous frequency)

$$f(\tau) = \frac{1}{\pi} \left(\frac{5}{256}\right)^{3/8} \left(\frac{c^3}{G M_{chirp}}\right)^{5/8} \tau^{-3/8}$$

### Inversion for the estimate of $M_{chirp}$

$$M_{chirp} = \frac{c^3}{G} \left[\frac{5}{96 \pi^{8/3}} \frac{\dot{f}}{f^{11/3}} \right] ^{3/5}$$

where $f$ is the instantaneous frequency detected and $\dot{f} = df/dt$ is its time derivative.

---

## Future Developments and Scientific Disclaimer

> [!WARNING]
> ### Validation Disclaimer
> The author is neither a physicist nor a mathematician by trade. The engine, its architecture, the numerical choices and the validation work are the author's own. The simulator explicitly computes a small set of standard formulas (retarded-time gravity, Velocity Verlet, Liénard-Wiechert, Paczyński-Wiita, Damour-Deruelle $2.5\text{PN}$ reaction), taken from standard references; no free calibration coefficients remain and the engine runs **parameter-free**. Language models were used as writing assistance for the documentation, and for a few implementation details that are flagged in the relevant sections. The formal treatment would still benefit a great deal from a look by professionals in the field, an aspect already outlined in the **Roadmap** below.

### Roadmap & To-Do List

- [ ] **Graphics Offloading to GPU (GLSL/Shader)**: Currently, the calculation and rendering of heatmaps (potential, waves, tidal stress) are performed entirely on the CPU, limiting the visual resolution in real time. The future goal is to delegate the entire rendering to the GPU via GLSL shaders asynchronously, while strictly maintaining the physics calculation and the history buffers in double precision (`float64`) on the CPU to avoid drift and numerical errors. Relevant side effect: once the rendering kernels (currently parallelized with `prange` on the `width` axis, see `core/jit_kernels/graphics_kernel.py`) leave the CPU, the freed cores return milliseconds per tick to the physics loop `O(N²)`, opening up a currently non-existent calculation budget that could allow the calculation of conservative post-Newtonian terms (1PN, 2PN).
- [ ] **Generation of Kernels via Template (to be studied)**: Evaluate a build-time code generator (e.g., `jinja2` or `string.Template`) that produces the specific single/double/triple and parallel/sequential files from a single abstract kernel, with the buffer constants statically expanded. It would keep the loop hot without `if` (the template pastes the right code for each variant before compilation), eliminating manual duplication of the scaffolding.
- [ ] **Artificial Injection of Directional Energy ("Piloting" of bodies)**: Evaluate the introduction of directional inputs to trigger thrust or piloted acceleration on a selected body, allowing the user to actively deflect orbital trajectories and study the waves emerging from active maneuvers.
- [ ] **Expert evaluation of the model's quantitative potential**: Seek input from professionals in the field to determine whether this engine can serve as a quantitative basis for something beyond dissemination: third-party experiments focused on gravitational causality, new heatmap families, or potential as a basis for surrogate models. With the full awareness that it may not lend itself to any of these speculations and remain, with dignity, in the visual and didactic realm.
- [ ] **Stabilization of the Real Quadrupole Strain**: Solve the numerical instability that is generated by implementing the strain based on the second derivatives of the mass quadrupole moment ($\ddot{I}$), which currently fluctuates and diverges near the merger with respect to the kinematic proxy based on relative velocities.

---

## License

This project is distributed under the **GNU GPL v3.0** license. In summary: anyone can study, use, and modify the code, but any redistribution, even modified, must remain open source under the same license and acknowledge the origin. The full text is in the [LICENSE](LICENSE) file.

Copyright © 2026 Alessandro Pioli

---

## Author

Developed by **Alessandro Pioli**. Independent project for the simulation and visualization of emergent causal gravitational physics.
