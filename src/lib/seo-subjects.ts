/**
 * SEO-Enhanced Subject Data
 * Complete subject definitions with topics, metadata, and SEO content for programmatic page generation
 */

export type Level = "igcse" | "ial"

export interface Topic {
  code: string
  name: string
  slug: string
  description: string
  keywords: string[]
}

export interface SEOSubject {
  slug: string
  name: string
  level: Level
  levelDisplay: string
  examBoard: string
  examCode: string
  colorKey: "physics" | "maths" | "biology" | "chemistry" | "ict" | "english" | "other"
  
  // SEO Metadata
  metaTitle: string
  metaDescription: string
  h1: string
  shortDescription: string
  longDescription: string
  keywords: string[]
  
  // Topics
  topics: Topic[]
  
  // Content
  faqs: { question: string; answer: string }[]
  
  // Past paper years available
  yearsAvailable: number[]
}

// ============================================================================
// IGCSE PHYSICS
// ============================================================================
export const igcsePhysics: SEOSubject = {
  slug: "physics",
  name: "Physics",
  level: "igcse",
  levelDisplay: "IGCSE",
  examBoard: "Edexcel",
  examCode: "4PH1",
  colorKey: "physics",
  
  metaTitle: "IGCSE Physics – Past Papers, Topics & Questions | GradeMax",
  metaDescription: "Master IGCSE Physics with topic-wise past paper questions, mark schemes, and AI-powered practice. Forces, electricity, waves, and more.",
  h1: "IGCSE Physics: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IGCSE Physics with organized past paper questions and mark schemes.",
  longDescription: "GradeMax provides comprehensive IGCSE Physics revision with real past paper questions organized by topic. Practice forces and motion, electricity, waves, energy resources, and more with instant access to mark schemes.",
  keywords: [
    "IGCSE Physics",
    "Edexcel Physics past papers",
    "IGCSE Physics revision",
    "Physics exam questions",
    "4PH1 past papers",
    "IGCSE Physics topics"
  ],
  
  topics: [
    { code: "1", name: "Forces and Motion", slug: "forces-and-motion", description: "Speed, velocity, acceleration, Newton's laws, momentum, and stopping distances.", keywords: ["forces", "motion", "Newton's laws", "momentum", "acceleration"] },
    { code: "2", name: "Electricity", slug: "electricity", description: "Current, voltage, resistance, circuits, electrical power, and static electricity.", keywords: ["electricity", "circuits", "Ohm's law", "resistance", "current"] },
    { code: "3", name: "Waves", slug: "waves", description: "Sound waves, light, reflection, refraction, electromagnetic spectrum, and wave properties.", keywords: ["waves", "sound", "light", "reflection", "refraction", "EM spectrum"] },
    { code: "4", name: "Energy Resources and Energy Transfers", slug: "energy-resources", description: "Energy stores, transfers, efficiency, power stations, and renewable energy.", keywords: ["energy", "efficiency", "power", "renewable energy", "fossil fuels"] },
    { code: "5", name: "Solids, Liquids and Gases", slug: "solids-liquids-gases", description: "Particle model, density, pressure, gas laws, and thermal properties.", keywords: ["particles", "density", "pressure", "gas laws", "states of matter"] },
    { code: "6", name: "Magnetism and Electromagnetism", slug: "magnetism-electromagnetism", description: "Magnets, magnetic fields, electromagnets, motors, generators, and transformers.", keywords: ["magnetism", "electromagnets", "motors", "generators", "transformers"] },
    { code: "7", name: "Radioactivity and Particles", slug: "radioactivity", description: "Atomic structure, radioactive decay, alpha, beta, gamma radiation, and half-life.", keywords: ["radioactivity", "half-life", "alpha", "beta", "gamma", "nuclear"] },
    { code: "8", name: "Astrophysics", slug: "astrophysics", description: "The solar system, stars, galaxies, the universe, and space exploration.", keywords: ["astrophysics", "solar system", "stars", "galaxies", "universe"] },
  ],
  
  faqs: [
    { question: "What topics are covered in IGCSE Physics?", answer: "IGCSE Physics covers 8 main topics: Forces and Motion, Electricity, Waves, Energy Resources, Solids Liquids and Gases, Magnetism and Electromagnetism, Radioactivity and Particles, and Astrophysics." },
    { question: "How many papers are in IGCSE Physics?", answer: "Edexcel IGCSE Physics has two papers: Paper 1 (2 hours, 110 marks) and Paper 2 (1 hour 15 minutes, 70 marks). Both papers cover all topics." },
    { question: "What is the best way to revise for IGCSE Physics?", answer: "The most effective revision method is practicing past paper questions by topic. GradeMax organizes all questions by topic so you can focus on weak areas and build exam confidence." },
    { question: "Are calculators allowed in IGCSE Physics exams?", answer: "Yes, scientific calculators are allowed and recommended for IGCSE Physics exams. Make sure you're familiar with using it before the exam." },
    { question: "What grade boundaries are typical for IGCSE Physics?", answer: "Grade boundaries vary by session, but typically an A* requires around 80-85%, an A around 70-75%, and a C around 45-50%. Check the latest boundaries on the Edexcel website." },
  ],
  
  yearsAvailable: [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IGCSE MATHS B
// ============================================================================
export const igcseMathsB: SEOSubject = {
  slug: "maths-b",
  name: "Mathematics B",
  level: "igcse",
  levelDisplay: "IGCSE",
  examBoard: "Edexcel",
  examCode: "4MB1",
  colorKey: "maths",
  
  metaTitle: "IGCSE Maths B – Past Papers, Topics & Practice Questions | GradeMax",
  metaDescription: "Master IGCSE Mathematics B with topic-wise past papers, worked examples, and AI practice. Algebra, functions, calculus, matrices and more.",
  h1: "IGCSE Mathematics B: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IGCSE Maths B with organized past paper questions covering algebra, functions, and calculus.",
  longDescription: "GradeMax provides comprehensive IGCSE Mathematics B revision with real past paper questions organized by topic. Practice number, algebra, functions, matrices, geometry, and trigonometry with instant mark scheme access.",
  keywords: [
    "IGCSE Maths B",
    "IGCSE Mathematics B past papers",
    "Edexcel Maths B",
    "4MB1 past papers",
    "IGCSE Maths questions",
    "IGCSE algebra"
  ],
  
  topics: [
    { code: "1", name: "Number", slug: "number", description: "Integers, fractions, decimals, indices, surds, standard form, bounds, and ratio.", keywords: ["number", "fractions", "indices", "surds", "standard form"] },
    { code: "2", name: "Sets", slug: "sets", description: "Set notation, union, intersection, Venn diagrams, subsets, and complements.", keywords: ["sets", "Venn diagrams", "union", "intersection", "subsets"] },
    { code: "3", name: "Algebra", slug: "algebra", description: "Expressions, equations, inequalities, formulae, sequences, and factor theorem.", keywords: ["algebra", "equations", "inequalities", "sequences", "factorisation"] },
    { code: "4", name: "Functions", slug: "functions", description: "Function notation, domain, range, composite functions, inverse functions, and differentiation.", keywords: ["functions", "differentiation", "calculus", "domain", "range"] },
    { code: "5", name: "Matrices", slug: "matrices", description: "Matrix operations, multiplication, determinants, inverses, and transformations.", keywords: ["matrices", "determinants", "inverse matrix", "transformations"] },
    { code: "6", name: "Geometry", slug: "geometry", description: "Angles, polygons, congruence, similarity, circle theorems, and constructions.", keywords: ["geometry", "circle theorems", "congruence", "similarity", "angles"] },
    { code: "7", name: "Mensuration", slug: "mensuration", description: "Perimeter, area, volume, arc, sector, and similar shapes.", keywords: ["mensuration", "area", "volume", "arc", "sector"] },
    { code: "8", name: "Vectors and Transformations", slug: "vectors-transformations", description: "Vectors, position vectors, transformations, and enlargement.", keywords: ["vectors", "position vectors", "transformations", "enlargement"] },
    { code: "9", name: "Trigonometry", slug: "trigonometry", description: "Sin, cos, tan, sine rule, cosine rule, 3D trigonometry, and bearings.", keywords: ["trigonometry", "sine rule", "cosine rule", "bearings", "SOHCAHTOA"] },
    { code: "10", name: "Statistics and Probability", slug: "statistics-probability", description: "Data handling, averages, frequency diagrams, probability, and tree diagrams.", keywords: ["statistics", "probability", "mean", "median", "tree diagrams"] },
  ],
  
  faqs: [
    { question: "What is the difference between IGCSE Maths A and Maths B?", answer: "IGCSE Maths B (4MB1) is more challenging than Maths A (4MA1). Maths B includes additional topics like calculus (differentiation), matrices, and set theory. It's designed for students aiming for A-Level Mathematics." },
    { question: "What topics are in IGCSE Maths B?", answer: "IGCSE Maths B covers 10 topics: Number, Sets, Algebra, Functions (including differentiation), Matrices, Geometry, Mensuration, Vectors and Transformations, Trigonometry, and Statistics & Probability." },
    { question: "Is IGCSE Maths B harder than Maths A?", answer: "Yes, Maths B is more challenging. It includes calculus, matrices, and more advanced algebra. However, it provides better preparation for A-Level Mathematics and is preferred by top universities." },
    { question: "How many papers are in IGCSE Maths B?", answer: "Edexcel IGCSE Maths B has two papers: Paper 1 (2 hours, 100 marks) and Paper 2 (2 hours, 100 marks). Both are calculator papers covering all topics." },
    { question: "What calculator is allowed for IGCSE Maths B?", answer: "A scientific calculator is required for both papers. Graphing calculators are generally not allowed unless specified. Check the exam regulations for approved models." },
  ],
  
  yearsAvailable: [2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IAL MECHANICS 1
// ============================================================================
export const ialMechanics1: SEOSubject = {
  slug: "mechanics-1",
  name: "Mechanics 1 (M1)",
  level: "ial",
  levelDisplay: "A Level",
  examBoard: "Pearson Edexcel",
  examCode: "WME01",
  colorKey: "other",
  
  metaTitle: "A Level Mechanics 1 (M1) – Past Papers & Topic Questions | GradeMax",
  metaDescription: "Master A Level Mechanics 1 with SUVAT, dynamics, momentum, friction, and moments. Past papers organized by topic with mark schemes.",
  h1: "A Level Mechanics 1: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IAL Mechanics 1 with organized past paper questions and worked solutions.",
  longDescription: "GradeMax provides comprehensive A Level Mechanics 1 revision with real past paper questions organized by topic. Practice kinematics, dynamics, momentum, friction, statics, and moments with instant mark scheme access.",
  keywords: [
    "A Level Mechanics",
    "Mechanics 1 past papers",
    "WME01 past papers",
    "SUVAT questions",
    "A Level Maths Mechanics",
    "M1 revision"
  ],
  
  topics: [
    { code: "M1.1", name: "Modelling & Assumptions", slug: "modelling-assumptions", description: "Particle, lamina, rigid body, light strings/pulleys, smooth/rough surfaces, beads and wires.", keywords: ["modelling", "assumptions", "particle", "rigid body"] },
    { code: "M1.2", name: "Vectors in Mechanics", slug: "vectors-mechanics", description: "i,j notation, components, resultants, vector kinematics and forces.", keywords: ["vectors", "i j notation", "components", "resultants"] },
    { code: "M1.3", name: "Kinematics", slug: "kinematics", description: "Constant acceleration, SUVAT equations, displacement-time, velocity-time, and acceleration-time graphs.", keywords: ["kinematics", "SUVAT", "acceleration", "velocity-time graphs"] },
    { code: "M1.4", name: "Dynamics", slug: "dynamics", description: "Newton's second law (F=ma), tension, connected particles, inclined planes, and resolving forces.", keywords: ["dynamics", "F=ma", "Newton's laws", "connected particles", "inclines"] },
    { code: "M1.5", name: "Momentum & Impulse", slug: "momentum-impulse", description: "Momentum (p=mv), impulse (J=Ft), conservation of momentum in 1D collisions.", keywords: ["momentum", "impulse", "collisions", "conservation"] },
    { code: "M1.6", name: "Friction", slug: "friction", description: "Coefficient of friction (μ), limiting friction, F=μR, rough and smooth surfaces.", keywords: ["friction", "coefficient of friction", "limiting friction", "rough surfaces"] },
    { code: "M1.7", name: "Statics of a Particle", slug: "statics-particle", description: "Equilibrium (ΣF=0), resolving forces, tension, thrust, and reaction forces.", keywords: ["statics", "equilibrium", "resolving forces", "tension"] },
    { code: "M1.8", name: "Moments", slug: "moments", description: "Moment of a force (M=F×d), parallel coplanar forces, equilibrium about a point.", keywords: ["moments", "turning effect", "equilibrium", "parallel forces"] },
  ],
  
  faqs: [
    { question: "What is covered in A Level Mechanics 1?", answer: "Mechanics 1 covers: Modelling & Assumptions, Vectors in Mechanics, Kinematics (SUVAT), Dynamics (F=ma), Momentum & Impulse, Friction, Statics of a Particle, and Moments." },
    { question: "What is the SUVAT formula?", answer: "SUVAT equations relate displacement (s), initial velocity (u), final velocity (v), acceleration (a), and time (t): v=u+at, s=ut+½at², v²=u²+2as, s=½(u+v)t, s=vt-½at²." },
    { question: "How do you solve connected particles problems?", answer: "For connected particles: 1) Draw force diagrams for each particle, 2) Write F=ma for each particle, 3) Use the constraint that acceleration is the same, 4) Solve the simultaneous equations." },
    { question: "When do you use F=μR vs F≤μR?", answer: "Use F=μR when friction is at its limiting (maximum) value - when the object is about to move or moving. Use F≤μR when the object is stationary and friction hasn't reached its limit." },
    { question: "How long is the Mechanics 1 exam?", answer: "The Edexcel IAL Mechanics 1 (WME01) exam is 1 hour 30 minutes and worth 75 marks. It's a calculator paper." },
  ],
  
  yearsAvailable: [2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IAL PURE MATHEMATICS 1
// ============================================================================
export const ialPureMaths1: SEOSubject = {
  slug: "pure-mathematics-1",
  name: "Pure Mathematics 1 (P1)",
  level: "ial",
  levelDisplay: "A Level",
  examBoard: "Pearson Edexcel",
  examCode: "WMA11",
  colorKey: "maths",
  
  metaTitle: "A Level Pure Mathematics 1 (P1) – Past Papers & Questions | GradeMax",
  metaDescription: "Master A Level Pure Maths 1 with algebra, quadratics, coordinate geometry, and differentiation. Past papers organized by topic.",
  h1: "A Level Pure Mathematics 1: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IAL Pure Mathematics 1 with organized past paper questions and worked solutions.",
  longDescription: "GradeMax provides comprehensive A Level Pure Mathematics 1 revision with real past paper questions organized by topic. Practice algebra, quadratics, coordinate geometry, differentiation, and integration.",
  keywords: [
    "A Level Pure Maths",
    "Pure Mathematics 1",
    "P1 past papers",
    "WMA11 past papers",
    "A Level Maths revision",
    "differentiation"
  ],
  
  topics: [
    { code: "P1.1", name: "Algebra and Functions", slug: "algebra-functions", description: "Laws of indices, surds, quadratic equations, simultaneous equations, and inequalities.", keywords: ["algebra", "indices", "surds", "quadratics", "inequalities"] },
    { code: "P1.2", name: "Coordinate Geometry", slug: "coordinate-geometry", description: "Equations of lines, parallel and perpendicular lines, circles, and intersection points.", keywords: ["coordinate geometry", "straight lines", "circles", "gradients"] },
    { code: "P1.3", name: "Sequences and Series", slug: "sequences-series", description: "Arithmetic sequences, geometric sequences, sigma notation, and binomial expansion.", keywords: ["sequences", "series", "arithmetic", "geometric", "binomial"] },
    { code: "P1.4", name: "Differentiation", slug: "differentiation", description: "Differentiation from first principles, derivatives of polynomials, tangents, normals, and stationary points.", keywords: ["differentiation", "derivatives", "tangent", "normal", "stationary points"] },
    { code: "P1.5", name: "Integration", slug: "integration", description: "Indefinite integration, definite integration, and area under curves.", keywords: ["integration", "area under curve", "indefinite", "definite integral"] },
  ],
  
  faqs: [
    { question: "What topics are in Pure Mathematics 1?", answer: "Pure Maths 1 covers: Algebra and Functions, Coordinate Geometry (including circles), Sequences and Series (including binomial expansion), Differentiation, and Integration." },
    { question: "How do you differentiate from first principles?", answer: "Differentiation from first principles uses the limit: f'(x) = lim(h→0) [f(x+h) - f(x)]/h. You substitute f(x+h), simplify, and take the limit as h approaches 0." },
    { question: "What is the formula for arithmetic sequences?", answer: "For arithmetic sequences: nth term = a + (n-1)d, sum of n terms = n/2[2a + (n-1)d] or n/2(a + l), where a is first term, d is common difference, l is last term." },
    { question: "How do you find stationary points?", answer: "To find stationary points: 1) Differentiate to get dy/dx, 2) Set dy/dx = 0 and solve, 3) Find corresponding y-values, 4) Use second derivative to determine if max, min, or point of inflection." },
    { question: "What's the binomial expansion formula?", answer: "(a+b)ⁿ = Σ(r=0 to n) ⁿCᵣ × aⁿ⁻ʳ × bʳ. For (1+x)ⁿ, the general term is ⁿCᵣ × xʳ. Remember ⁿCᵣ = n!/(r!(n-r)!)." },
  ],
  
  yearsAvailable: [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IAL STATISTICS 1
// ============================================================================
export const ialStatistics1: SEOSubject = {
  slug: "statistics-1",
  name: "Statistics 1 (S1)",
  level: "ial",
  levelDisplay: "A Level",
  examBoard: "Pearson Edexcel",
  examCode: "WST01",
  colorKey: "other",
  
  metaTitle: "A Level Statistics 1 (S1) – Past Papers & Questions | GradeMax",
  metaDescription: "Master A Level Statistics 1 with probability, data representation, correlation, and regression. Past papers organized by topic.",
  h1: "A Level Statistics 1: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IAL Statistics 1 with organized past paper questions covering probability and data analysis.",
  longDescription: "GradeMax provides comprehensive A Level Statistics 1 revision with real past paper questions organized by topic. Practice probability, data representation, correlation, regression, and discrete random variables.",
  keywords: [
    "A Level Statistics",
    "Statistics 1 past papers",
    "S1 past papers",
    "WST01 past papers",
    "probability questions",
    "correlation regression"
  ],
  
  topics: [
    { code: "S1.1", name: "Data Representation", slug: "data-representation", description: "Histograms, stem and leaf diagrams, box plots, and cumulative frequency.", keywords: ["histograms", "box plots", "stem and leaf", "cumulative frequency"] },
    { code: "S1.2", name: "Measures of Location and Spread", slug: "measures-location-spread", description: "Mean, median, mode, range, IQR, variance, and standard deviation.", keywords: ["mean", "median", "variance", "standard deviation", "IQR"] },
    { code: "S1.3", name: "Probability", slug: "probability", description: "Addition and multiplication rules, conditional probability, and tree diagrams.", keywords: ["probability", "conditional probability", "tree diagrams", "Venn diagrams"] },
    { code: "S1.4", name: "Correlation and Regression", slug: "correlation-regression", description: "Scatter diagrams, correlation coefficient, and linear regression lines.", keywords: ["correlation", "regression", "scatter diagrams", "PMCC", "least squares"] },
    { code: "S1.5", name: "Discrete Random Variables", slug: "discrete-random-variables", description: "Probability distributions, expected value (E(X)), and variance (Var(X)).", keywords: ["discrete random variables", "expected value", "variance", "probability distribution"] },
  ],
  
  faqs: [
    { question: "What is the formula for standard deviation?", answer: "Standard deviation σ = √[Σ(x-μ)²/n] or σ = √[Σx²/n - (Σx/n)²]. For sample standard deviation, use (n-1) in the denominator instead of n." },
    { question: "How do you calculate correlation coefficient?", answer: "PMCC (r) = Sxy/√(Sxx × Syy), where Sxy = Σxy - (ΣxΣy)/n, Sxx = Σx² - (Σx)²/n, Syy = Σy² - (Σy)²/n. r ranges from -1 to +1." },
    { question: "What's the difference between correlation and regression?", answer: "Correlation measures the strength of linear relationship between two variables (-1 to +1). Regression finds the equation of the line of best fit to predict y from x (y = a + bx)." },
    { question: "How do you find E(X) and Var(X)?", answer: "E(X) = Σx×P(X=x) (sum of each value times its probability). Var(X) = E(X²) - [E(X)]² = Σx²×P(X=x) - [E(X)]²." },
    { question: "When do you use P(A∩B) vs P(A∪B)?", answer: "P(A∩B) = probability of A AND B both happening. P(A∪B) = probability of A OR B (or both). P(A∪B) = P(A) + P(B) - P(A∩B)." },
  ],
  
  yearsAvailable: [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IGCSE ICT
// ============================================================================
export const igcseICT: SEOSubject = {
  slug: "ict",
  name: "ICT",
  level: "igcse",
  levelDisplay: "IGCSE",
  examBoard: "Edexcel",
  examCode: "4IT1",
  colorKey: "ict",
  
  metaTitle: "IGCSE ICT – Past Papers, Theory Notes & Questions | GradeMax",
  metaDescription: "Master IGCSE ICT with theory notes, past paper questions, and practical skills. Hardware, software, networks, and more.",
  h1: "IGCSE ICT: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IGCSE ICT with organized theory notes and past paper questions.",
  longDescription: "GradeMax provides comprehensive IGCSE ICT revision covering both theory and practical components. Study hardware, software, networks, databases, spreadsheets, and web development with real exam questions.",
  keywords: [
    "IGCSE ICT",
    "IGCSE ICT past papers",
    "ICT theory notes",
    "4IT1 past papers",
    "IGCSE Computer Science",
    "ICT revision"
  ],
  
  topics: [
    { code: "1", name: "Digital Devices", slug: "digital-devices", description: "Types of computers, input devices, output devices, and storage devices.", keywords: ["computers", "input devices", "output devices", "storage"] },
    { code: "2", name: "Connectivity", slug: "connectivity", description: "Networks, internet, email, communication technologies, and network security.", keywords: ["networks", "internet", "LAN", "WAN", "security"] },
    { code: "3", name: "Operating Online", slug: "operating-online", description: "Online services, e-commerce, online safety, and digital citizenship.", keywords: ["online services", "e-commerce", "online safety", "digital citizenship"] },
    { code: "4", name: "Software Skills", slug: "software-skills", description: "Spreadsheets, databases, presentations, and word processing.", keywords: ["spreadsheets", "databases", "presentations", "word processing"] },
  ],
  
  faqs: [
    { question: "What is the difference between RAM and ROM?", answer: "RAM (Random Access Memory) is volatile - it loses data when power is off. It's used for running programs. ROM (Read Only Memory) is non-volatile and stores the BIOS/boot instructions permanently." },
    { question: "What are the different types of networks?", answer: "LAN (Local Area Network) covers a small area like a building. WAN (Wide Area Network) covers large geographical areas. MAN (Metropolitan Area Network) covers a city. PAN (Personal Area Network) is for personal devices." },
    { question: "What is the difference between SSD and HDD?", answer: "SSD (Solid State Drive) has no moving parts, is faster, more durable, but more expensive. HDD (Hard Disk Drive) uses spinning magnetic disks, is slower, but offers more storage per cost." },
    { question: "How many papers are in IGCSE ICT?", answer: "Edexcel IGCSE ICT has two papers: Paper 1 (Written, 2 hours) covers theory, and Paper 2 (Practical, 3 hours) tests practical software skills." },
    { question: "What practical skills are tested in IGCSE ICT?", answer: "IGCSE ICT practical tests spreadsheet skills (formulas, charts, data validation), database skills (queries, reports), and document production (mail merge, formatting)." },
  ],
  
  yearsAvailable: [2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IGCSE MATHS A
// ============================================================================
export const igcseMathsA: SEOSubject = {
  slug: "maths-a",
  name: "Mathematics A",
  level: "igcse",
  levelDisplay: "IGCSE",
  examBoard: "Edexcel",
  examCode: "4MA1",
  colorKey: "maths",
  
  metaTitle: "IGCSE Maths A – Past Papers, Topics & Questions | GradeMax",
  metaDescription: "Master IGCSE Mathematics A with topic-wise past papers and mark schemes. Algebra, geometry, statistics, and more.",
  h1: "IGCSE Mathematics A: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IGCSE Maths A with organized past paper questions and worked examples.",
  longDescription: "GradeMax provides comprehensive IGCSE Mathematics A revision with real past paper questions organized by topic. Practice number, algebra, geometry, and statistics with instant mark scheme access.",
  keywords: [
    "IGCSE Maths",
    "IGCSE Mathematics past papers",
    "Edexcel 4MA1",
    "IGCSE Maths revision",
    "IGCSE algebra",
    "IGCSE geometry"
  ],
  
  topics: [
    { code: "1", name: "Number", slug: "number", description: "Integers, fractions, decimals, percentages, ratio, and proportion.", keywords: ["number", "fractions", "percentages", "ratio", "proportion"] },
    { code: "2", name: "Algebra", slug: "algebra", description: "Expressions, equations, inequalities, sequences, and graphs.", keywords: ["algebra", "equations", "inequalities", "sequences"] },
    { code: "3", name: "Graphs", slug: "graphs", description: "Coordinates, linear graphs, quadratic graphs, and real-life graphs.", keywords: ["graphs", "coordinates", "linear", "quadratic"] },
    { code: "4", name: "Geometry", slug: "geometry", description: "Shapes, angles, transformations, and vectors.", keywords: ["geometry", "angles", "transformations", "vectors"] },
    { code: "5", name: "Mensuration", slug: "mensuration", description: "Perimeter, area, volume, and circle properties.", keywords: ["mensuration", "area", "volume", "circles"] },
    { code: "6", name: "Trigonometry", slug: "trigonometry", description: "Pythagoras' theorem, trigonometric ratios, and bearings.", keywords: ["trigonometry", "Pythagoras", "sin cos tan", "bearings"] },
    { code: "7", name: "Statistics and Probability", slug: "statistics-probability", description: "Data handling, averages, probability, and diagrams.", keywords: ["statistics", "probability", "averages", "diagrams"] },
  ],
  
  faqs: [
    { question: "What is IGCSE Maths A?", answer: "IGCSE Mathematics A (4MA1) is Edexcel's standard international GCSE mathematics qualification. It covers number, algebra, geometry, statistics, and probability at a level suitable for most students." },
    { question: "Is a calculator allowed in IGCSE Maths A?", answer: "Yes, IGCSE Maths A is a calculator exam. Both Paper 1 and Paper 2 allow the use of scientific calculators." },
    { question: "How many papers are in IGCSE Maths A?", answer: "IGCSE Maths A has two papers: Paper 1 (Higher/Foundation, 2 hours) and Paper 2 (Higher/Foundation, 2 hours). Each paper is worth 50% of the total mark." },
    { question: "What is the difference between Higher and Foundation tier?", answer: "Foundation tier (grades 5-1) has easier questions and a lower maximum grade. Higher tier (grades 9-4) has harder questions but allows access to the top grades. Choose based on your target grade." },
    { question: "What are the key formulas for IGCSE Maths?", answer: "Key formulas include: Area of triangle = ½bh, Area of circle = πr², Pythagoras = a²+b²=c², Quadratic formula = (-b±√(b²-4ac))/2a. A formula sheet is provided in the exam." },
  ],
  
  yearsAvailable: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IGCSE CHEMISTRY
// ============================================================================
export const igcseChemistry: SEOSubject = {
  slug: "chemistry",
  name: "Chemistry",
  level: "igcse",
  levelDisplay: "IGCSE",
  examBoard: "Edexcel",
  examCode: "4CH1",
  colorKey: "chemistry",
  
  metaTitle: "IGCSE Chemistry – Past Papers, Topics & Questions | GradeMax",
  metaDescription: "Master IGCSE Chemistry with topic-wise past papers and mark schemes. Atomic structure, bonding, organic chemistry, and more.",
  h1: "IGCSE Chemistry: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IGCSE Chemistry with organized past paper questions and detailed explanations.",
  longDescription: "GradeMax provides comprehensive IGCSE Chemistry revision with real past paper questions organized by topic. Practice principles of chemistry, organic chemistry, physical chemistry, and more.",
  keywords: [
    "IGCSE Chemistry",
    "IGCSE Chemistry past papers",
    "Edexcel Chemistry",
    "4CH1 past papers",
    "IGCSE Chemistry revision",
    "organic chemistry"
  ],
  
  topics: [
    { code: "1", name: "Principles of Chemistry", slug: "principles-chemistry", description: "States of matter, atoms, elements, compounds, and chemical formulas.", keywords: ["atoms", "elements", "compounds", "states of matter", "formulas"] },
    { code: "2", name: "Chemistry of the Elements", slug: "chemistry-elements", description: "Periodic table, groups, metals, non-metals, and reactivity series.", keywords: ["periodic table", "metals", "non-metals", "reactivity series", "groups"] },
    { code: "3", name: "Organic Chemistry", slug: "organic-chemistry", description: "Hydrocarbons, alkanes, alkenes, alcohols, and polymers.", keywords: ["organic chemistry", "alkanes", "alkenes", "alcohols", "polymers"] },
    { code: "4", name: "Physical Chemistry", slug: "physical-chemistry", description: "Energetics, rates of reaction, equilibrium, and electrolysis.", keywords: ["energetics", "rates", "equilibrium", "electrolysis"] },
    { code: "5", name: "Chemistry in Society", slug: "chemistry-society", description: "Industrial processes, atmosphere, earth materials, and environmental chemistry.", keywords: ["industrial chemistry", "atmosphere", "environment", "extraction"] },
  ],
  
  faqs: [
    { question: "What topics are in IGCSE Chemistry?", answer: "IGCSE Chemistry covers: Principles of Chemistry (atomic structure, bonding), Chemistry of the Elements (periodic table, reactivity), Organic Chemistry (hydrocarbons, polymers), Physical Chemistry (rates, equilibrium), and Chemistry in Society." },
    { question: "How do you balance chemical equations?", answer: "To balance equations: 1) Write the unbalanced equation, 2) Count atoms of each element on both sides, 3) Add coefficients to balance atoms (never change subscripts), 4) Check all atoms are balanced." },
    { question: "What is the reactivity series?", answer: "The reactivity series orders metals by reactivity: K, Na, Ca, Mg, Al, Zn, Fe, Pb, H, Cu, Ag, Au (most to least reactive). More reactive metals displace less reactive ones from solutions." },
    { question: "How many papers are in IGCSE Chemistry?", answer: "Edexcel IGCSE Chemistry has two papers: Paper 1 (2 hours, 110 marks) and Paper 2 (1 hour 15 minutes, 70 marks). Both are written exams covering all topics." },
    { question: "What equipment do I need for IGCSE Chemistry?", answer: "For the exam: pen, pencil, ruler, and calculator. You should know common lab equipment names and uses (beaker, conical flask, burette, etc.) for exam questions." },
  ],
  
  yearsAvailable: [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// IGCSE BIOLOGY
// ============================================================================
export const igcseBiology: SEOSubject = {
  slug: "biology",
  name: "Biology",
  level: "igcse",
  levelDisplay: "IGCSE",
  examBoard: "Edexcel",
  examCode: "4BI1",
  colorKey: "biology",
  
  metaTitle: "IGCSE Biology – Past Papers, Topics & Questions | GradeMax",
  metaDescription: "Master IGCSE Biology with topic-wise past papers and mark schemes. Cells, genetics, ecology, and human biology.",
  h1: "IGCSE Biology: Complete Study Guide & Past Papers",
  shortDescription: "Master Edexcel IGCSE Biology with organized past paper questions and detailed explanations.",
  longDescription: "GradeMax provides comprehensive IGCSE Biology revision with real past paper questions organized by topic. Practice cells, genetics, ecology, human biology, and plant biology with mark schemes.",
  keywords: [
    "IGCSE Biology",
    "IGCSE Biology past papers",
    "Edexcel Biology",
    "4BI1 past papers",
    "IGCSE Biology revision",
    "genetics"
  ],
  
  topics: [
    { code: "1", name: "Nature and Variety of Living Organisms", slug: "living-organisms", description: "Characteristics of life, classification, and variety of organisms.", keywords: ["classification", "characteristics of life", "organisms", "variety"] },
    { code: "2", name: "Structures and Functions in Living Organisms", slug: "structures-functions", description: "Cells, enzymes, nutrition, respiration, gas exchange, and transport.", keywords: ["cells", "enzymes", "nutrition", "respiration", "transport"] },
    { code: "3", name: "Reproduction and Inheritance", slug: "reproduction-inheritance", description: "Reproduction, cell division, genetics, and evolution.", keywords: ["reproduction", "genetics", "DNA", "evolution", "inheritance"] },
    { code: "4", name: "Ecology and the Environment", slug: "ecology", description: "Ecosystems, food chains, nutrient cycles, and human impact.", keywords: ["ecology", "ecosystems", "food chains", "environment"] },
    { code: "5", name: "Use of Biological Resources", slug: "biological-resources", description: "Food production, selective breeding, genetic modification, and cloning.", keywords: ["food production", "selective breeding", "genetic modification", "cloning"] },
  ],
  
  faqs: [
    { question: "What topics are in IGCSE Biology?", answer: "IGCSE Biology covers: Nature and Variety of Living Organisms, Structures and Functions (cells, enzymes, respiration), Reproduction and Inheritance (genetics), Ecology and Environment, and Use of Biological Resources." },
    { question: "How do you draw a Punnett square?", answer: "To draw a Punnett square: 1) Write parent genotypes, 2) Split alleles - one parent across top, one down side, 3) Fill in boxes by combining alleles, 4) Calculate phenotype ratios from results." },
    { question: "What is the difference between mitosis and meiosis?", answer: "Mitosis produces 2 identical diploid cells for growth/repair. Meiosis produces 4 different haploid cells (gametes) for sexual reproduction. Meiosis involves crossing over and creates genetic variation." },
    { question: "How many papers are in IGCSE Biology?", answer: "Edexcel IGCSE Biology has two papers: Paper 1 (2 hours, 110 marks) and Paper 2 (1 hour 15 minutes, 70 marks). Both are written exams covering all topics." },
    { question: "What equations do I need for IGCSE Biology?", answer: "Key equations: Photosynthesis (CO₂ + H₂O → glucose + O₂), Aerobic respiration (glucose + O₂ → CO₂ + H₂O + energy), Magnification = image size / actual size." },
  ],
  
  yearsAvailable: [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
}

// ============================================================================
// MASTER EXPORT
// ============================================================================
export const seoSubjects: SEOSubject[] = [
  // IGCSE
  igcsePhysics,
  igcseMathsA,
  igcseMathsB,
  igcseChemistry,
  igcseBiology,
  igcseICT,
  
  // IAL
  ialPureMaths1,
  ialMechanics1,
  ialStatistics1,
]

export const getSubjectBySlug = (level: Level, slug: string): SEOSubject | undefined => {
  return seoSubjects.find(s => s.level === level && s.slug === slug)
}

export const getSubjectsByLevel = (level: Level): SEOSubject[] => {
  return seoSubjects.filter(s => s.level === level)
}

export const getAllTopics = (): { subject: SEOSubject; topic: Topic }[] => {
  return seoSubjects.flatMap(subject => 
    subject.topics.map(topic => ({ subject, topic }))
  )
}

export const getLevelDisplay = (level: Level): string => {
  return level === "igcse" ? "IGCSE" : "A Level"
}
