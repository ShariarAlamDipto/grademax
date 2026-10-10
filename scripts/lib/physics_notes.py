"""
The Summary and Equations section printed at the front of the Physics workbook.

The Physics counterpart of lib/mathsb_notes.py, in the same shape so the same
renderer (lib.formula_render) sets it: every chapter and section of the 4PH1
book in the book's own order, each with

  * a SUMMARY: what the topic asks and the point that most often costs marks
  * KEY EQUATIONS: the relationships the specification says to "know and use"
    or "use" for that section, written as the spec writes them

Equations are taken from the Pearson 4PH1 specification (Issue 2, April 2018),
section 2. Anything the spec gives only on the paper's own formulae page is
still listed here -- this is a revision reference, and a student practising a
section needs the equation beside it either way.

mathtext limits are the same as for Maths B: no `array`/`pmatrix`; use \\frac
and keep each line short enough to fit the page width.
"""

from __future__ import annotations

# (chapter, [(section, title, [summary lines], [equation lines])])
Section = tuple[int, str, list[str], list[str]]

NOTES: list[tuple[int, list[Section]]] = [
    (1, [
        (1, "Movement and position", [
            r"On a distance-time graph the GRADIENT is the speed; on a velocity-time "
            r"graph the gradient is the acceleration and the AREA under it is the distance.",
            r"A deceleration is a negative acceleration – keep the sign in the working.",
        ], [
            r"$\mathrm{average\ speed} = \dfrac{\mathrm{distance\ moved}}{\mathrm{time\ taken}}$",
            r"$a = \dfrac{v - u}{t}$",
            r"$v^2 = u^2 + 2as$",
        ]),
        (2, "Forces and their effects", [
            r"Find the RESULTANT force first; only the resultant changes the motion. "
            r"Balanced forces mean constant velocity, not necessarily rest.",
            r"Mass is in kg and does not change; weight is a force in N and depends on g.",
        ], [
            r"$F = m \times a$",
            r"$W = m \times g$",
        ]),
        (3, "Stopping distance and terminal velocity", [
            r"Stopping distance = thinking distance + braking distance. Tiredness, drugs "
            r"and distraction lengthen THINKING distance; wet roads, worn tyres and brakes "
            r"lengthen BRAKING distance; speed lengthens both.",
            r"Terminal velocity is reached when drag has grown to equal weight, so the "
            r"resultant force – and the acceleration – is zero.",
        ], [
            r"$\mathrm{stopping\ distance} = \mathrm{thinking\ distance} + \mathrm{braking\ distance}$",
        ]),
        (4, "Hooke's law and elastic behaviour", [
            r"Extension is proportional to force only on the straight, initial part of the "
            r"force-extension graph. Extension = new length - original length.",
            r"Elastic means the material returns to its original shape when the force is removed.",
        ], [
            r"$\mathrm{extension} \propto \mathrm{force}$ (linear region only)",
        ]),
        (5, "Momentum", [
            r"Momentum is a vector: give one direction a + sign and keep it throughout. "
            r"Total momentum before = total momentum after a collision or explosion.",
            r"Crumple zones, airbags and seat belts INCREASE the time of a collision, which "
            r"reduces the force for the same change in momentum.",
        ], [
            r"$p = m \times v$",
            r"$F = \dfrac{mv - mu}{t}$",
        ]),
        (6, "Moments and centre of gravity", [
            r"Use the PERPENDICULAR distance from the pivot to the line of the force. "
            r"In equilibrium, clockwise moments = anticlockwise moments about any point.",
            r"For a beam on two supports, moving a load towards one support increases the "
            r"upward force from that support.",
        ], [
            r"$\mathrm{moment} = \mathrm{force} \times \mathrm{perpendicular\ distance\ from\ the\ pivot}$",
        ]),
    ]),
    (2, [
        (1, "Mains electricity and electrical power", [
            r"Fuses and circuit breakers protect by breaking the circuit when the current is too "
            r"large; the earth wire gives a low-resistance path so the fuse blows.",
            r"Choose the fuse rating just ABOVE the normal working current, from I = P / V.",
        ], [
            r"$P = I \times V$",
            r"$E = I \times V \times t$",
        ]),
        (2, "Current, voltage and resistance in circuits", [
            r"Series: same current everywhere, voltages add up. Parallel: same voltage across "
            r"each branch, branch currents add up to the supply current.",
            r"A filament lamp's resistance rises as it heats; a diode conducts one way only; "
            r"LDR resistance falls in light; thermistor resistance falls as it warms.",
        ], [
            r"$V = I \times R$",
            r"$R_{\mathrm{total}} = R_1 + R_2$  (series)",
        ]),
        (3, "Charge, current and energy transfer", [
            r"Current is the rate of flow of charge; in metals the charge carriers are electrons.",
            r"Voltage is the energy transferred per unit charge: 1 V = 1 J/C.",
        ], [
            r"$Q = I \times t$",
            r"$E = Q \times V$",
        ]),
        (4, "Electric charge", [
            r"Insulators are charged by friction: ELECTRONS move, never positive charge. The one "
            r"that gains electrons becomes negative.",
            r"Like charges repel, unlike charges attract. Explain dangers (sparks when refuelling) "
            r"and uses (photocopiers, inkjet printers) in terms of electron movement.",
        ], []),
    ]),
    (3, [
        (1, "Properties of waves", [
            r"Transverse waves oscillate at right angles to the direction of energy transfer; "
            r"longitudinal waves oscillate parallel to it. Waves transfer energy, not matter.",
            r"A moving source bunches the waves ahead of it (shorter wavelength, higher "
            r"frequency) and spreads them behind – the Doppler effect.",
        ], [
            r"$v = f \times \lambda$",
            r"$f = \dfrac{1}{T}$",
        ]),
        (2, "The electromagnetic spectrum", [
            r"In order of DECREASING wavelength: radio, microwaves, infrared, visible, "
            r"ultraviolet, X-rays, gamma. All travel at the same speed in a vacuum.",
            r"Give a specific use and a specific harm for each region (e.g. UV: sterilising "
            r"water / skin cancer).",
        ], []),
        (3, "Light: reflection, refraction and total internal reflection", [
            r"Measure angles from the NORMAL. Light bends towards the normal entering a denser "
            r"material.",
            r"Total internal reflection needs light going from the denser material AND an angle "
            r"of incidence greater than the critical angle.",
        ], [
            r"$n = \dfrac{\sin i}{\sin r}$",
            r"$\sin c = \dfrac{1}{n}$",
        ]),
        (4, "Sound", [
            r"Sound is longitudinal and needs a medium. Humans hear 20 Hz to 20 000 Hz.",
            r"Pitch depends on frequency; loudness on amplitude. For an echo, the sound "
            r"travels there AND back.",
        ], [
            r"$v = f \times \lambda$",
            r"$\mathrm{speed} = \dfrac{\mathrm{distance}}{\mathrm{time}}$",
        ]),
    ]),
    (4, [
        (1, "Energy stores, transfers and efficiency", [
            r"Energy is never used up – it is transferred between stores, and the wasted "
            r"part usually ends up as thermal energy in the surroundings.",
            r"In a Sankey diagram the width of each arrow is proportional to the energy.",
        ], [
            r"$\mathrm{efficiency} = \dfrac{\mathrm{useful\ energy\ output}}{\mathrm{total\ energy\ input}} \times 100\%$",
        ]),
        (2, "Thermal energy transfer", [
            r"Conduction is through solids by vibrating particles (and free electrons in "
            r"metals); convection is by currents in fluids as heated fluid becomes less dense "
            r"and rises; radiation is infrared and needs no medium.",
            r"Dull black surfaces are the best emitters and absorbers; shiny silver the worst.",
        ], []),
        (3, "Work and power", [
            r"Work done is energy transferred. When an object falls, GPE lost = KE gained "
            r"(ignoring air resistance) – use it to find a speed without the equations of motion.",
            r"Power is how FAST energy is transferred.",
        ], [
            r"$W = F \times d$",
            r"$GPE = m \times g \times h$",
            r"$KE = \dfrac{1}{2} \times m \times v^2$",
            r"$P = \dfrac{W}{t}$",
        ]),
        (4, "Energy resources and electricity generation", [
            r"Describe the energy transfers in order, e.g. chemical → thermal → kinetic "
            r"(turbine) → electrical (generator).",
            r"Compare resources on renewability, reliability, cost and environmental impact.",
        ], []),
    ]),
    (5, [
        (1, "Density and pressure", [
            r"Convert units before substituting: 1 g/cm^3 = 1000 kg/m^3, 1 cm^2 = 0.0001 m^2.",
            r"Pressure in a fluid acts equally in all directions and increases with depth.",
        ], [
            r"$\rho = \dfrac{m}{V}$",
            r"$p = \dfrac{F}{A}$",
            r"$\Delta p = h \times \rho \times g$",
        ]),
        (2, "Change of state and specific heat capacity", [
            r"During melting or boiling the temperature stays CONSTANT: the energy breaks bonds "
            r"between particles instead of raising their kinetic energy.",
            r"Specific heat capacity is the energy to raise 1 kg by 1 degree C.",
        ], [
            r"$\Delta Q = m \times c \times \Delta T$",
        ]),
        (3, "Ideal gas molecules", [
            r"Gas pressure comes from molecules colliding with the walls. Always use KELVIN in "
            r"gas calculations: T(K) = T(degrees C) + 273.",
            r"Kelvin temperature is proportional to the average kinetic energy of the molecules.",
        ], [
            r"$\dfrac{p_1}{T_1} = \dfrac{p_2}{T_2}$",
            r"$p_1 V_1 = p_2 V_2$",
        ]),
    ]),
    (6, [
        (1, "Magnetism", [
            r"Field lines run from N to S and never cross; closer lines mean a stronger field.",
            r"Soft magnetic materials (iron) magnetise and demagnetise easily; hard ones "
            r"(steel) keep their magnetism.",
        ], []),
        (2, "Electromagnetism", [
            r"A current produces a magnetic field. A current-carrying wire in a magnetic field "
            r"feels a force – use the LEFT-hand rule (thuMb = Motion, First = Field, seCond = Current).",
            r"The force increases with current and field strength, and reverses if either is reversed.",
        ], []),
        (3, "Electromagnetic induction", [
            r"A voltage is induced when a conductor cuts magnetic field lines; it increases with "
            r"speed, field strength and number of turns.",
            r"Transformers work only with a.c. High-voltage transmission means a lower current, "
            r"so less energy is wasted heating the cables.",
        ], [
            r"$\dfrac{V_p}{V_s} = \dfrac{N_p}{N_s}$",
            r"$V_p \times I_p = V_s \times I_s$",
        ]),
    ]),
    (7, [
        (1, "Atoms and radioactive emissions", [
            r"Alpha is a helium nucleus (stopped by paper), beta is a fast electron (stopped by "
            r"a few mm of aluminium), gamma is EM radiation (reduced by thick lead).",
            r"In a nuclear equation both the mass numbers and the atomic numbers must balance.",
        ], []),
        (2, "Half-life, uses and dangers of radioactivity", [
            r"Half-life is the time for the activity (or number of undecayed nuclei) to halve. "
            r"Subtract background count before reading a half-life off a graph.",
            r"Contamination is radioactive material on or in an object; irradiation is exposure "
            r"to radiation, and does not make the object radioactive.",
        ], [
            r"$\mathrm{after}\ n\ \mathrm{half\text{-}lives:\ activity} = \dfrac{A_0}{2^n}$",
        ]),
        (3, "Fission and fusion", [
            r"Fission: a neutron is absorbed by U-235, which splits into two daughter nuclei and "
            r"2-3 neutrons – a chain reaction. Control rods absorb neutrons; the moderator slows them.",
            r"Fusion joins small nuclei and needs very high temperature and pressure to "
            r"overcome the repulsion between positive nuclei.",
        ], []),
    ]),
    (8, [
        (1, "Motion in the universe", [
            r"Gravity provides the centripetal force that keeps planets, moons, comets and "
            r"satellites in orbit. Comet orbits are highly elliptical.",
            r"g is different on different planets because it depends on their mass and radius.",
        ], [
            r"$\mathrm{orbital\ speed} = \dfrac{2 \pi r}{T}$",
        ]),
        (2, "Stellar evolution", [
            r"A star's colour shows its surface temperature: red is coolest, blue hottest.",
            r"Sun-like star: nebula → protostar → main sequence → red giant → white dwarf. "
            r"Much more massive: red supergiant → supernova → neutron star or black hole.",
        ], []),
        (3, "Cosmology", [
            r"Light from distant galaxies is red-shifted; the further away the galaxy, the "
            r"greater the red-shift, so the universe is expanding.",
            r"Evidence for the Big Bang: galactic red-shift and the cosmic microwave background (CMB).",
        ], [
            r"$\dfrac{\Delta \lambda}{\lambda_0} = \dfrac{v}{c}$",
        ]),
    ]),
]


def flow_blocks(chapter_titles: dict[int, str],
                chapters: set[int] | None = None) -> list[dict]:
    """The reference section as blocks for lib.formula_render; see mathsb_notes."""
    out: list[dict] = []
    for number, sections in NOTES:
        if chapters is not None and number not in chapters:
            continue
        for index, (section, title, summary, results) in enumerate(sections):
            out.append({
                "chapter": (f"{number}   {chapter_titles.get(number, '')}"
                            if index == 0 else None),
                "heading": f"{number}.{section}   {title}",
                "notes": summary,
                "lines": results,
            })
    return out
