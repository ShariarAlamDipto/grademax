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
  
  metaTitle: "Edexcel IGCSE Physics Past Papers (4PH1) – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel IGCSE Physics (4PH1) past papers, topic-wise questions, and mark schemes. Forces, electricity, waves, energy, and more. 2011–2025.",
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
  
  yearsAvailable: [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
  
  metaTitle: "Edexcel IGCSE Maths B Past Papers (4MB1) – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel IGCSE Mathematics B (4MB1) past papers, topic questions, and mark schemes. Algebra, functions, calculus, matrices and more. 2018–2025.",
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
  
  yearsAvailable: [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
  
  metaTitle: "Edexcel A Level Mechanics 1 (WME01) Past Papers – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel A Level Mechanics 1 (WME01/M1) past papers with mark schemes. SUVAT, dynamics, momentum, friction, moments. 2012–2025.",
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
  
  yearsAvailable: [2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
  
  metaTitle: "Edexcel A Level Pure Maths 1 (WMA11) Past Papers – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel A Level Pure Mathematics 1 (WMA11/P1) past papers with mark schemes. Algebra, quadratics, coordinate geometry, differentiation. 2014–2025.",
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
  
  yearsAvailable: [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
  
  metaTitle: "Edexcel A Level Statistics 1 (WST01) Past Papers – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel A Level Statistics 1 (WST01/S1) past papers with mark schemes. Probability, data representation, correlation, regression. 2014–2025.",
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
  
  yearsAvailable: [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
  
  metaTitle: "Edexcel IGCSE ICT Past Papers (4IT1) – Theory, Questions & Mark Schemes",
  metaDescription: "Free Edexcel IGCSE ICT (4IT1) past papers, theory notes, questions, and mark schemes. Hardware, software, networks, databases. 2018–2025.",
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
  
  yearsAvailable: [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
  
  metaTitle: "Edexcel IGCSE Maths A Past Papers (4MA1) – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel IGCSE Mathematics A (4MA1) past papers, topic-wise questions, and mark schemes. Algebra, geometry, statistics. 2015–2025.",
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
  
  yearsAvailable: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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

  metaTitle: "Edexcel IGCSE Chemistry Past Papers (4CH1) – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel IGCSE Chemistry (4CH1) past papers, topic-wise questions, and mark schemes. Atomic structure, bonding, organic chemistry. 2017–2025.",
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
    // Section 1: Principles of Chemistry
    { code: "1.1", name: "States of Matter", slug: "states-of-matter", description: "Particle model of solids, liquids and gases. Diffusion, melting and boiling points, separation techniques.", keywords: ["states of matter", "particles", "diffusion", "separation", "evaporation"] },
    { code: "1.2", name: "Atoms, Elements and Compounds", slug: "atoms-elements-compounds", description: "Atomic symbols, formulae of compounds, mixtures vs pure substances, relative atomic mass.", keywords: ["atoms", "elements", "compounds", "atomic symbol", "mixture"] },
    { code: "1.3", name: "Atomic Structure", slug: "atomic-structure", description: "Protons, neutrons and electrons; atomic number; mass number; isotopes; electron configuration.", keywords: ["atomic structure", "protons", "neutrons", "electrons", "isotopes", "electron configuration"] },
    { code: "1.4", name: "Relative Formula Masses and Moles", slug: "relative-formula-masses-moles", description: "Relative formula mass (Mr), mole calculations, reacting masses, percentage composition, molar volumes of gases.", keywords: ["moles", "relative formula mass", "reacting masses", "molar volume", "stoichiometry"] },
    { code: "1.5", name: "Chemical Formulae and Equations", slug: "chemical-formulae-equations", description: "Balancing equations, ionic equations, state symbols, empirical and molecular formulae, limiting reagents.", keywords: ["balancing equations", "ionic equations", "state symbols", "empirical formula", "limiting reagent"] },
    { code: "1.6", name: "Ionic Compounds", slug: "ionic-compounds", description: "Ionic bonding, formation of ions, lattice structure, properties of ionic compounds, testing for ions.", keywords: ["ionic bonding", "ions", "lattice", "ionic compounds", "electrostatic attraction"] },
    { code: "1.7", name: "Covalent Substances", slug: "covalent-substances", description: "Covalent bonding, dot-and-cross diagrams, molecular and giant covalent structures (diamond, graphite), properties.", keywords: ["covalent bonding", "dot and cross", "molecular structure", "diamond", "graphite", "giant covalent"] },
    { code: "1.8", name: "Metallic Crystals", slug: "metallic-crystals", description: "Metallic bonding, structure of metals, delocalized electrons, properties of metals and alloys.", keywords: ["metallic bonding", "delocalized electrons", "alloys", "metal structure", "conduction"] },
    { code: "1.9", name: "Electrolysis", slug: "electrolysis", description: "Electrolysis of molten and aqueous solutions, electrode reactions, half-equations, industrial electrolysis (brine, aluminium).", keywords: ["electrolysis", "electrodes", "half equations", "anode", "cathode", "brine", "aluminium extraction"] },
    // Section 2: Inorganic Chemistry
    { code: "2.1", name: "Group 1 – Alkali Metals", slug: "group-1-alkali-metals", description: "Properties and reactions of Li, Na, K with water and oxygen. Trend in reactivity down the group.", keywords: ["alkali metals", "group 1", "lithium", "sodium", "potassium", "reactivity trend"] },
    { code: "2.2", name: "Group 7 – Halogens", slug: "group-7-halogens", description: "Properties of F, Cl, Br, I; reactions with metals and hydrogen; displacement reactions; trend in reactivity.", keywords: ["halogens", "group 7", "chlorine", "bromine", "iodine", "displacement", "halide ions"] },
    { code: "2.3", name: "Oxygen and Oxides", slug: "oxygen-and-oxides", description: "Properties of oxygen; combustion; acidic, basic and amphoteric oxides; rusting and corrosion prevention.", keywords: ["oxygen", "oxides", "combustion", "rusting", "acidic oxides", "basic oxides", "corrosion"] },
    { code: "2.4", name: "Sulfur and Sulfur Dioxide", slug: "sulfur-and-sulfur-dioxide", description: "Properties of sulfur and SO₂; sulfuric acid manufacture (Contact process); acid rain.", keywords: ["sulfur", "sulfur dioxide", "SO2", "Contact process", "acid rain", "sulfuric acid"] },
    { code: "2.5", name: "Nitrogen and Ammonia", slug: "nitrogen-and-ammonia", description: "Haber process for ammonia manufacture; uses of ammonia; nitrogen cycle; fertilisers.", keywords: ["nitrogen", "ammonia", "Haber process", "fertilisers", "nitrogen cycle", "nitric acid"] },
    { code: "2.6", name: "Metals and Alloys", slug: "metals-and-alloys", description: "Physical and chemical properties of metals; structure and uses of steel, brass, bronze, and other alloys.", keywords: ["metals", "alloys", "steel", "brass", "bronze", "properties of metals"] },
    { code: "2.7", name: "Reactivity Series", slug: "reactivity-series", description: "Order of reactivity; displacement reactions; reactions of metals with water, acids and oxygen.", keywords: ["reactivity series", "displacement reactions", "metals", "reactions with acids", "reactions with water"] },
    { code: "2.8", name: "Extraction of Metals", slug: "extraction-of-metals", description: "Reduction with carbon, electrolysis; blast furnace for iron; extraction of aluminium; recycling metals.", keywords: ["extraction of metals", "blast furnace", "iron extraction", "aluminium extraction", "reduction", "recycling metals"] },
    { code: "2.9", name: "Making Salts", slug: "making-salts", description: "Acids and bases; neutralisation; methods of making soluble and insoluble salts; precipitation; pH scale.", keywords: ["salts", "neutralisation", "acids", "bases", "precipitation", "pH", "soluble salts"] },
    { code: "2.10", name: "Tests for Ions and Gases", slug: "tests-ions-gases", description: "Flame tests, precipitate tests, tests for anions; identifying gases (H₂, O₂, CO₂, Cl₂, NH₃).", keywords: ["flame tests", "ion tests", "gas tests", "anion tests", "cation tests", "identifying gases"] },
    // Section 3: Physical Chemistry
    { code: "3.1", name: "Energetics", slug: "energetics", description: "Exothermic and endothermic reactions; enthalpy changes (ΔH); bond energies; activation energy; energy profile diagrams.", keywords: ["energetics", "exothermic", "endothermic", "enthalpy", "bond energy", "activation energy", "energy diagrams"] },
    { code: "3.2", name: "Rates of Reaction", slug: "rates-of-reaction", description: "Factors affecting rate: concentration, temperature, surface area, catalysts; collision theory; measuring reaction rate.", keywords: ["rates of reaction", "concentration", "temperature", "surface area", "catalyst", "collision theory"] },
    { code: "3.3", name: "Reversible Reactions and Equilibria", slug: "reversible-reactions-equilibria", description: "Reversible reactions; dynamic equilibrium; Le Chatelier's principle; industrial applications (Haber, Contact).", keywords: ["reversible reactions", "equilibrium", "Le Chatelier", "dynamic equilibrium", "yield", "industrial processes"] },
    // Section 4: Organic Chemistry
    { code: "4.1", name: "Introduction to Organic Chemistry", slug: "introduction-organic-chemistry", description: "Homologous series; functional groups; naming organic compounds; structural isomers; crude oil and fractional distillation.", keywords: ["organic chemistry", "homologous series", "functional groups", "isomers", "crude oil", "fractional distillation"] },
    { code: "4.2", name: "Alkanes", slug: "alkanes", description: "Structure, properties and reactions of alkanes; complete and incomplete combustion; cracking; uses of alkanes.", keywords: ["alkanes", "methane", "ethane", "propane", "combustion", "cracking", "saturated hydrocarbons"] },
    { code: "4.3", name: "Alkenes", slug: "alkenes", description: "Structure and properties of alkenes; addition reactions; bromine water test; polymerisation; compared to alkanes.", keywords: ["alkenes", "ethene", "propene", "addition reactions", "bromine water", "unsaturated", "double bond"] },
    { code: "4.4", name: "Ethanol", slug: "ethanol", description: "Production by fermentation and hydration; properties; oxidation to ethanoic acid; uses and social impacts.", keywords: ["ethanol", "alcohol", "fermentation", "hydration", "ethanoic acid", "alcohols"] },
    { code: "4.5", name: "Carboxylic Acids and Esters", slug: "carboxylic-acids-esters", description: "Properties of carboxylic acids; esterification; hydrolysis; uses of esters; reactions with alkalis and metals.", keywords: ["carboxylic acids", "esters", "esterification", "ethanoic acid", "hydrolysis", "reactions of acids"] },
    { code: "4.6", name: "Polymerisation", slug: "polymerisation", description: "Addition polymerisation (alkenes); condensation polymerisation; structure and properties of polymers; environmental issues.", keywords: ["polymerisation", "addition polymerisation", "condensation polymerisation", "polymers", "monomers", "plastics"] },
    // Section 5: Chemistry in Society
    { code: "5.1", name: "Gases in the Atmosphere", slug: "gases-in-the-atmosphere", description: "Composition of air; history and evolution of the atmosphere; greenhouse effect; global warming; air pollution.", keywords: ["atmosphere", "greenhouse effect", "global warming", "carbon dioxide", "air pollution", "ozone layer"] },
    { code: "5.2", name: "Water", slug: "water", description: "Water treatment and purification; temporary and permanent hardness; removing hardness; water as a solvent.", keywords: ["water", "water treatment", "hard water", "soft water", "purification", "filtration", "chlorination"] },
    { code: "5.3", name: "Industrial Chemistry", slug: "industrial-chemistry", description: "Raw materials; economic factors in industrial processes; life cycle assessment; recycling; sustainability.", keywords: ["industrial chemistry", "raw materials", "economic factors", "life cycle assessment", "recycling", "sustainability"] },
  ],

  faqs: [
    { question: "What topics are in Edexcel IGCSE Chemistry (4CH1)?", answer: "Edexcel IGCSE Chemistry has 5 sections: Section 1 (Principles of Chemistry — states of matter, atomic structure, bonding, electrolysis), Section 2 (Inorganic Chemistry — groups 1 & 7, reactivity, extraction), Section 3 (Physical Chemistry — energetics, rates, equilibrium), Section 4 (Organic Chemistry — alkanes, alkenes, polymers), Section 5 (Chemistry in Society — atmosphere, water, industrial chemistry)." },
    { question: "How do you balance chemical equations?", answer: "To balance equations: 1) Write the unbalanced equation, 2) Count atoms of each element on both sides, 3) Add coefficients to balance atoms (never change subscripts), 4) Check all atoms are balanced." },
    { question: "What is the reactivity series?", answer: "The reactivity series orders metals by reactivity: K, Na, Ca, Mg, Al, C, Zn, Fe, Pb, H, Cu, Ag, Au (most to least reactive). More reactive metals displace less reactive ones from solutions and react more vigorously with acid and water." },
    { question: "How many papers are in IGCSE Chemistry?", answer: "Edexcel IGCSE Chemistry has two papers: Paper 1 (2 hours, 110 marks) and Paper 2 (1 hour 15 minutes, 70 marks). Both are written exams covering all topics." },
    { question: "What is the difference between ionic and covalent bonding?", answer: "Ionic bonding involves transfer of electrons between metals and non-metals, forming charged ions held by electrostatic attraction in a lattice. Covalent bonding involves sharing of electrons between non-metals, forming molecules or giant covalent structures." },
  ],

  yearsAvailable: [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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

  metaTitle: "Edexcel IGCSE Biology Past Papers (4BI1) – Topic Questions & Mark Schemes",
  metaDescription: "Free Edexcel IGCSE Biology (4BI1) past papers, topic-wise questions, and mark schemes. Cells, genetics, ecology, human biology. 2017–2025.",
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
    // Section 1: Nature and Variety of Living Organisms
    { code: "1.1", name: "Characteristics of Living Organisms", slug: "characteristics-living-organisms", description: "The seven characteristics of life (MRS GREN): movement, respiration, sensitivity, growth, reproduction, excretion, nutrition.", keywords: ["characteristics of life", "MRS GREN", "living organisms", "life processes"] },
    { code: "1.2", name: "Variety of Living Organisms", slug: "variety-living-organisms", description: "Classification into five kingdoms (animals, plants, fungi, bacteria, protists); features of viruses; dichotomous keys.", keywords: ["classification", "kingdoms", "animals", "plants", "fungi", "bacteria", "viruses", "dichotomous keys"] },
    // Section 2: Structures and Functions in Living Organisms
    { code: "2.1", name: "Cell Structure and Organisation", slug: "cell-structure-organisation", description: "Animal and plant cells; cell organelles (nucleus, mitochondria, chloroplast, cell wall, vacuole); cell, tissue, organ, system hierarchy; specialised cells.", keywords: ["cell structure", "organelles", "nucleus", "mitochondria", "chloroplast", "plant cell", "animal cell", "specialised cells"] },
    { code: "2.2", name: "Biological Molecules", slug: "biological-molecules", description: "Structure and function of carbohydrates, lipids, proteins and DNA; enzyme structure; food tests (Benedict's, iodine, biuret).", keywords: ["biological molecules", "carbohydrates", "lipids", "proteins", "DNA", "enzyme", "food tests", "Benedict's test"] },
    { code: "2.3", name: "Movement of Substances", slug: "movement-of-substances", description: "Diffusion, osmosis and active transport; factors affecting diffusion; water potential; turgid and plasmolysed cells.", keywords: ["diffusion", "osmosis", "active transport", "water potential", "turgid", "plasmolysis", "concentration gradient"] },
    { code: "2.4", name: "Nutrition in Plants", slug: "nutrition-in-plants", description: "Photosynthesis equation and process; limiting factors (light, CO₂, temperature); leaf structure; mineral ion requirements.", keywords: ["photosynthesis", "chlorophyll", "limiting factors", "light intensity", "leaf structure", "mineral ions", "nitrates"] },
    { code: "2.5", name: "Nutrition in Humans", slug: "nutrition-in-humans", description: "Balanced diet; digestive system; enzymes (amylase, protease, lipase); absorption in small intestine; villi; liver functions.", keywords: ["digestion", "digestive system", "enzymes", "amylase", "protease", "lipase", "villi", "absorption", "liver"] },
    { code: "2.6", name: "Respiration", slug: "respiration", description: "Aerobic and anaerobic respiration equations; ATP; fermentation; effects of exercise; mitochondria.", keywords: ["respiration", "aerobic respiration", "anaerobic respiration", "ATP", "fermentation", "glucose", "energy", "lactic acid"] },
    { code: "2.7", name: "Gas Exchange", slug: "gas-exchange", description: "Gas exchange in humans (alveoli, lungs); gas exchange in plants (stomata, guard cells); gas exchange in fish (gills).", keywords: ["gas exchange", "alveoli", "lungs", "breathing", "stomata", "guard cells", "gills", "ventilation"] },
    { code: "2.8", name: "Transport in Plants", slug: "transport-in-plants", description: "Xylem and phloem; transpiration; transpiration stream; factors affecting transpiration rate; translocation.", keywords: ["xylem", "phloem", "transpiration", "translocation", "water transport", "stomata", "wilting"] },
    { code: "2.9", name: "Transport in Humans", slug: "transport-in-humans", description: "Heart structure and function; circulatory system; blood composition (plasma, red cells, white cells, platelets); blood groups; coronary heart disease.", keywords: ["heart", "circulatory system", "blood", "red blood cells", "white blood cells", "platelets", "arteries", "veins", "capillaries"] },
    { code: "2.10", name: "Excretion", slug: "excretion", description: "Kidneys and urine formation; ultrafiltration and reabsorption; role of ADH; liver producing urea; lungs excreting CO₂.", keywords: ["excretion", "kidneys", "urea", "urine", "ultrafiltration", "reabsorption", "ADH", "osmoregulation"] },
    { code: "2.11", name: "Coordination and Response", slug: "coordination-and-response", description: "Nervous system (neurones, reflex arc, brain, spinal cord); hormonal system (hormones, endocrine glands); plant responses (tropisms, auxins).", keywords: ["nervous system", "neurones", "reflex arc", "hormones", "endocrine", "insulin", "adrenaline", "tropisms", "auxins"] },
    { code: "2.12", name: "Homeostasis", slug: "homeostasis", description: "Regulation of body temperature; blood glucose control (insulin, glucagon); ADH and water balance; negative feedback.", keywords: ["homeostasis", "thermoregulation", "blood glucose", "insulin", "glucagon", "negative feedback", "body temperature"] },
    // Section 3: Reproduction and Inheritance
    { code: "3.1", name: "Reproduction in Plants", slug: "reproduction-in-plants", description: "Sexual reproduction (flowers, pollination, fertilisation, seed dispersal); asexual reproduction (runners, tubers, bulbs, cuttings).", keywords: ["plant reproduction", "pollination", "fertilisation", "seed dispersal", "asexual reproduction", "flowers", "runners"] },
    { code: "3.2", name: "Reproduction in Humans", slug: "reproduction-in-humans", description: "Male and female reproductive systems; menstrual cycle; fertilisation; pregnancy; contraception; sexually transmitted infections.", keywords: ["human reproduction", "menstrual cycle", "fertilisation", "pregnancy", "contraception", "reproductive system", "ovulation"] },
    { code: "3.3", name: "Cell Division", slug: "cell-division", description: "Mitosis (growth and repair, produces 2 identical diploid cells); meiosis (produces 4 haploid gametes, genetic variation).", keywords: ["mitosis", "meiosis", "cell division", "diploid", "haploid", "chromosomes", "gametes", "genetic variation"] },
    { code: "3.4", name: "Inheritance", slug: "inheritance", description: "DNA structure; genes and alleles; dominant and recessive; Punnett squares; monohybrid and dihybrid crosses; codominance; sex linkage; mutations.", keywords: ["genetics", "DNA", "alleles", "dominant", "recessive", "Punnett square", "genotype", "phenotype", "codominance", "mutations"] },
    { code: "3.5", name: "Natural Selection and Evolution", slug: "natural-selection-evolution", description: "Natural selection; Darwin's theory; variation; adaptation; antibiotic resistance; speciation; fossil record.", keywords: ["natural selection", "evolution", "Darwin", "adaptation", "antibiotic resistance", "speciation", "variation", "survival of the fittest"] },
    // Section 4: Ecology and the Environment
    { code: "4.1", name: "Organisms and Their Environment", slug: "organisms-environment", description: "Ecosystems; habitats and niches; abiotic and biotic factors; population size; sampling techniques (quadrats, transects).", keywords: ["ecosystem", "habitat", "niche", "abiotic factors", "biotic factors", "population", "quadrats", "transects"] },
    { code: "4.2", name: "Feeding Relationships", slug: "feeding-relationships", description: "Food chains and food webs; producers, consumers and decomposers; energy transfer; trophic levels; pyramids of number, biomass and energy.", keywords: ["food chains", "food webs", "producers", "consumers", "decomposers", "trophic levels", "energy transfer", "biomass pyramids"] },
    { code: "4.3", name: "Nutrient Cycles", slug: "nutrient-cycles", description: "Carbon cycle (photosynthesis, respiration, decomposition, combustion); nitrogen cycle (fixation, nitrification, denitrification); water cycle.", keywords: ["carbon cycle", "nitrogen cycle", "water cycle", "decomposition", "nitrogen fixation", "nitrification", "denitrification"] },
    { code: "4.4", name: "Human Influences on the Environment", slug: "human-influences-environment", description: "Pollution (water, air, land); deforestation; habitat destruction; climate change; conservation; biodiversity; eutrophication.", keywords: ["pollution", "deforestation", "climate change", "conservation", "biodiversity", "eutrophication", "global warming", "human impact"] },
    // Section 5: Use of Biological Resources
    { code: "5.1", name: "Food Production", slug: "food-production", description: "Crop plants (pest control, fertilisers, irrigation); livestock farming; fish farming; glasshouses and hydroponics; food chains and efficiency.", keywords: ["food production", "farming", "crop production", "pest control", "fertilisers", "fish farming", "hydroponics", "food efficiency"] },
    { code: "5.2", name: "Selective Breeding", slug: "selective-breeding", description: "Artificial selection in plants and animals; examples (high-yield crops, disease-resistant varieties, dog breeds); advantages and risks.", keywords: ["selective breeding", "artificial selection", "high yield crops", "disease resistance", "genetic improvement"] },
    { code: "5.3", name: "Genetic Engineering", slug: "genetic-engineering", description: "Process of genetic modification; GM crops (pest resistance, herbicide tolerance); production of insulin and other proteins; ethical issues.", keywords: ["genetic engineering", "genetic modification", "GM crops", "insulin production", "recombinant DNA", "ethical issues"] },
    { code: "5.4", name: "Cloning", slug: "cloning", description: "Tissue culture; embryo transplanting; adult cell cloning (Dolly the sheep); stem cells; advantages and ethical considerations.", keywords: ["cloning", "tissue culture", "embryo transplant", "Dolly the sheep", "stem cells", "adult cell cloning", "ethics"] },
  ],

  faqs: [
    { question: "What topics are in Edexcel IGCSE Biology (4BI1)?", answer: "Edexcel IGCSE Biology has 5 sections with 27 chapters: Section 1 (Nature and Variety of Living Organisms), Section 2 (Structures and Functions — cells, nutrition, respiration, transport, coordination), Section 3 (Reproduction and Inheritance — genetics, evolution), Section 4 (Ecology and the Environment), and Section 5 (Use of Biological Resources)." },
    { question: "How do you draw a Punnett square?", answer: "To draw a Punnett square: 1) Write parent genotypes, 2) Split alleles — one parent across top, one down side, 3) Fill in boxes by combining alleles, 4) Calculate genotype and phenotype ratios from results." },
    { question: "What is the difference between mitosis and meiosis?", answer: "Mitosis produces 2 identical diploid cells for growth and repair. Meiosis produces 4 genetically different haploid cells (gametes) for sexual reproduction. Meiosis involves two divisions and creates genetic variation through crossing over and independent assortment." },
    { question: "How many papers are in IGCSE Biology?", answer: "Edexcel IGCSE Biology has two papers: Paper 1 (2 hours, 110 marks) and Paper 2 (1 hour 15 minutes, 70 marks). Both are written exams covering all topics." },
    { question: "What equations do I need for IGCSE Biology?", answer: "Key equations: Photosynthesis (6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂), Aerobic respiration (C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + energy), Anaerobic respiration in animals (glucose → lactic acid), Magnification = image size ÷ actual size." },
  ],

  yearsAvailable: [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
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
