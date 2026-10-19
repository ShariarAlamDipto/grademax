"""Assign a 4PH1 specification topic to a question from the words it uses.

The archive's existing classifications come from an LLM pass over segmented
questions and do not cover the whole 2018-2025 window, so topic is derived here
from vocabulary instead: it is transparent, reproducible and needs no model call.
Terms are weighted because some words belong to one topic only ("half-life") and
others are shared ("energy"), and the topics are checked in a fixed order so a
question mentioning both a transformer and a current lands in electromagnetism.
"""
from __future__ import annotations

import re

TOPICS: tuple[tuple[int, str, tuple[str, ...]], ...] = (
    (9, "Practical skills and data handling", (
        "best fit", "line of best", "curve of best", "independent variable",
        "dependent variable", "control variable", "anomal", "repeat the",
        "reliab", "precis", "resolution", "systematic error", "random error",
        "axes", "plot the", "significant figures", "error bar", "risk",
        "safety precaution", "method the student", "improve the accuracy",
    )),
    (8, "Astrophysics", (
        "star", "galaxy", "universe", "orbit", "planet", "comet", "nebula",
        "supernova", "red shift", "big bang", "cmb", "main sequence", "light year",
        "hertzsprung", "white dwarf", "black hole", "solar system", "moon",
        "satellite", "parsec",
    )),
    (7, "Radioactivity and particles", (
        "radioactiv", "half-life", "half life", "alpha", "beta", "gamma",
        "nucleus", "nuclei", "isotope", "decay", "geiger", "background count",
        "fission", "fusion", "becquerel", "ionis", "proton", "neutron",
        "atomic number", "mass number", "irradiat", "contaminat",
    )),
    (6, "Magnetism and electromagnetism", (
        "magnet", "solenoid", "transformer", "motor effect", "generator",
        "electromagnet", "field line", "north pole", "south pole", "flux",
        "induc", "left hand rule", "coil", "dynamo", "loudspeaker",
    )),
    (5, "Solids, liquids and gases", (
        "density", "pressure", "kinetic theory", "specific heat", "gas",
        "particle", "boiling", "melting", "evaporat", "thermal expansion",
        "absolute zero", "kelvin", "molecule", "brownian", "latent",
        "manometer", "hydraulic", "state of matter",
    )),
    (4, "Energy resources and energy transfer", (
        "efficien", "power station", "renewable", "fossil fuel", "solar panel",
        "wind turbine", "biofuel", "geothermal", "tidal", "hydroelectric",
        "conduction", "convection", "radiation from", "insulat", "sankey",
        "work done", "gravitational potential", "kinetic energy", "energy store",
        "energy transfer", "conservation of energy",
    )),
    (3, "Waves", (
        "wave", "frequency", "wavelength", "amplitude", "refract", "reflect",
        "lens", "mirror", "sound", "ultrasound", "echo", "diffract",
        "electromagnetic spectrum", "infrared", "ultraviolet", "microwave",
        "x-ray", "critical angle", "total internal", "oscillat", "ripple",
        "transverse", "longitudinal", "snell", "prism", "seismic",
    )),
    (2, "Electricity", (
        "circuit", "current", "voltage", "resistance", "resistor", "ammeter",
        "voltmeter", "ohm", "fuse", "series", "parallel", "charge", "static",
        "mains", "live wire", "earth wire", "electron flow", "potential difference",
        "lamp", "thermistor", "ldr", "diode", "coulomb", "kilowatt",
    )),
    (1, "Forces and motion", (
        "force", "velocity", "acceleration", "momentum", "moment", "newton",
        "friction", "weight", "mass", "speed", "distance", "displacement",
        "hooke", "spring", "extension", "terminal velocity", "stopping distance",
        "thinking distance", "braking", "pivot", "equilibrium", "vector",
        "scalar", "gradient", "resultant", "gravitational field strength",
    )),
)

_UNSPECIFIC = frozenset({"mass", "energy", "power", "force", "distance", "speed"})


def topic_of(text: str) -> tuple[int, str]:
    """Return the (number, name) of the topic whose vocabulary the text best matches."""
    low = text.lower()
    best: tuple[float, int, str] = (0.0, 0, "Unclassified")
    for number, name, terms in TOPICS:
        score = 0.0
        for term in terms:
            if term in low:
                score += 0.5 if term in _UNSPECIFIC else 1.0
        if score > best[0]:
            best = (score, number, name)
    return best[1], best[2]


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
