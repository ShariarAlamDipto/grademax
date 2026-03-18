-- ============================================================================
-- Migration 005: Expand Chemistry and Biology to spec-aligned chapters
-- Edexcel IGCSE Chemistry (4CH1): 31 chapters (codes 1.1 – 5.3)
-- Edexcel IGCSE Biology  (4BI1): 27 chapters (codes 1.1 – 5.4)
--
-- Steps:
--   1. Archive old broad topic codes on pages (so we can roll back if needed)
--   2. Delete old 5-topic entries from topics table for chem and bio
--   3. Insert granular chapter entries
--   4. Reset pages.topics for chem/bio (requires re-classification run)
-- ============================================================================

BEGIN;

-- ─── STEP 1: Archive old topic codes ────────────────────────────────────────
-- Add column if it doesn't exist yet
ALTER TABLE pages
  ADD COLUMN IF NOT EXISTS topics_v1 TEXT[];

-- Back up current topics array for chem and bio pages before we reset
UPDATE pages p
SET    topics_v1 = p.topics
FROM   papers pa
JOIN   subjects s ON pa.subject_id = s.id
WHERE  pa.id = p.paper_id
  AND  s.code IN ('4CH1', '4BI1')
  AND  p.topics_v1 IS NULL;

-- ─── STEP 2: Remove old broad topics ────────────────────────────────────────
DELETE FROM topics
WHERE subject_id = (SELECT id FROM subjects WHERE code = '4CH1')
  AND code IN ('1','2','3','4','5');

DELETE FROM topics
WHERE subject_id = (SELECT id FROM subjects WHERE code = '4BI1')
  AND code IN ('1','2','3','4','5');

-- ─── STEP 3: Insert Chemistry chapters (4CH1) ────────────────────────────────
INSERT INTO topics (subject_id, code, name, description, keywords) VALUES

-- Section 1: Principles of Chemistry
((SELECT id FROM subjects WHERE code = '4CH1'), '1.1', 'States of Matter',
 'Particle model, states of matter, diffusion, separation techniques',
 ARRAY['solid','liquid','gas','diffusion','filtration','distillation','chromatography','crystallisation']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.2', 'Atoms, Elements and Compounds',
 'Elements, compounds, mixtures, chemical symbols, formulae, relative atomic mass',
 ARRAY['element','compound','mixture','symbol','formula','relative atomic mass','Ar']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.3', 'Atomic Structure',
 'Protons, neutrons, electrons, atomic number, mass number, isotopes, electron configuration',
 ARRAY['proton','neutron','electron','atomic number','mass number','isotope','electron configuration','shell']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.4', 'Relative Formula Masses and Moles',
 'Mr, moles, molar mass, Avogadro, reacting masses, percentage composition, molar volumes',
 ARRAY['mole','molar mass','Mr','Avogadro','reacting mass','percentage composition','molar volume','stoichiometry']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.5', 'Chemical Formulae and Equations',
 'Balancing equations, ionic equations, state symbols, empirical and molecular formulae',
 ARRAY['balance','equation','ionic equation','state symbol','empirical formula','molecular formula','half equation']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.6', 'Ionic Compounds',
 'Ionic bonding, ion formation, lattice structure, properties of ionic compounds',
 ARRAY['ionic bond','ionic compound','ion','cation','anion','lattice','electrostatic attraction','dot-and-cross']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.7', 'Covalent Substances',
 'Covalent bonding, molecular and giant covalent structures (diamond, graphite, SiO2)',
 ARRAY['covalent bond','shared electron','molecule','diamond','graphite','silicon dioxide','giant covalent','van der Waals']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.8', 'Metallic Crystals',
 'Metallic bonding, delocalized electrons, properties of metals and alloys',
 ARRAY['metallic bond','delocalized electron','sea of electrons','metal structure','metallic crystal','alloy']),

((SELECT id FROM subjects WHERE code = '4CH1'), '1.9', 'Electrolysis',
 'Electrolysis of molten and aqueous solutions, electrode reactions, half-equations, industrial electrolysis',
 ARRAY['electrolysis','electrolyte','electrode','anode','cathode','discharge','half equation','brine','aluminium','copper sulfate']),

-- Section 2: Inorganic Chemistry
((SELECT id FROM subjects WHERE code = '4CH1'), '2.1', 'Group 1 – Alkali Metals',
 'Properties and reactions of Li, Na, K with water and oxygen; trend in reactivity',
 ARRAY['alkali metal','group 1','lithium','sodium','potassium','react with water','hydroxide','hydrogen','vigorous']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.2', 'Group 7 – Halogens',
 'Properties of F, Cl, Br, I; displacement reactions; halide tests; trend in reactivity',
 ARRAY['halogen','group 7','chlorine','bromine','iodine','fluorine','displacement','halide','bleach','silver nitrate']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.3', 'Oxygen and Oxides',
 'Combustion, rusting, types of oxides, corrosion prevention',
 ARRAY['oxygen','oxide','combustion','burning','rusting','oxidation','corrosion','acidic oxide','basic oxide','amphoteric']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.4', 'Sulfur and Sulfur Dioxide',
 'Properties of sulfur and SO2; Contact process; acid rain; sulfuric acid',
 ARRAY['sulfur','sulphur','sulfur dioxide','SO2','sulfuric acid','H2SO4','Contact process','acid rain']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.5', 'Nitrogen and Ammonia',
 'Haber process, manufacture of ammonia, fertilisers, nitric acid, nitrogen cycle',
 ARRAY['nitrogen','ammonia','Haber process','fertiliser','nitrate','nitric acid','nitrogen fixation','nitrogen cycle','urea']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.6', 'Metals and Alloys',
 'Physical and chemical properties of metals; alloys (steel, brass, bronze)',
 ARRAY['alloy','steel','brass','bronze','stainless steel','duralumin','properties of metals','carbon steel']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.7', 'Reactivity Series',
 'Order of reactivity, displacement reactions, reactions with water, dilute acids and oxygen',
 ARRAY['reactivity series','displacement','reactivity','potassium','sodium','calcium','magnesium','aluminium','zinc','iron','copper']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.8', 'Extraction of Metals',
 'Blast furnace, iron extraction, aluminium extraction, reduction with carbon, recycling',
 ARRAY['blast furnace','iron extraction','aluminium extraction','bauxite','cryolite','haematite','coke','limestone','slag','reduction','ore']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.9', 'Making Salts',
 'Acids and bases, neutralisation, preparation of soluble and insoluble salts, titration, pH',
 ARRAY['salt','neutralisation','acid','alkali','base','titration','precipitation','soluble salt','insoluble salt','pH','indicator']),

((SELECT id FROM subjects WHERE code = '4CH1'), '2.10', 'Tests for Ions and Gases',
 'Flame tests, precipitate tests, silver nitrate, barium chloride, gas tests',
 ARRAY['flame test','precipitate','silver nitrate','barium chloride','limewater','gas test','identify','anion test','cation test']),

-- Section 3: Physical Chemistry
((SELECT id FROM subjects WHERE code = '4CH1'), '3.1', 'Energetics',
 'Exothermic and endothermic reactions, enthalpy, bond energies, activation energy, energy profiles',
 ARRAY['exothermic','endothermic','enthalpy','delta H','bond energy','activation energy','energy profile','Hess']),

((SELECT id FROM subjects WHERE code = '4CH1'), '3.2', 'Rates of Reaction',
 'Factors affecting rate, collision theory, measuring rate',
 ARRAY['rate of reaction','concentration','surface area','temperature','catalyst','collision theory','frequency of collision']),

((SELECT id FROM subjects WHERE code = '4CH1'), '3.3', 'Reversible Reactions and Equilibria',
 'Reversible reactions, dynamic equilibrium, Le Chatelier''s principle',
 ARRAY['reversible reaction','equilibrium','dynamic equilibrium','Le Chatelier','yield','forward reaction','backward reaction']),

-- Section 4: Organic Chemistry
((SELECT id FROM subjects WHERE code = '4CH1'), '4.1', 'Introduction to Organic Chemistry',
 'Homologous series, functional groups, naming, isomers, crude oil, fractional distillation',
 ARRAY['organic chemistry','homologous series','functional group','isomer','crude oil','fractional distillation','hydrocarbon']),

((SELECT id FROM subjects WHERE code = '4CH1'), '4.2', 'Alkanes',
 'Structure and properties of alkanes, combustion, cracking',
 ARRAY['alkane','methane','ethane','propane','butane','saturated','complete combustion','incomplete combustion','cracking']),

((SELECT id FROM subjects WHERE code = '4CH1'), '4.3', 'Alkenes',
 'Structure of alkenes, addition reactions, bromine water test, polymerisation',
 ARRAY['alkene','ethene','propene','unsaturated','double bond','addition reaction','bromine water','decolourise','polymerisation']),

((SELECT id FROM subjects WHERE code = '4CH1'), '4.4', 'Ethanol',
 'Production by fermentation and hydration, oxidation to ethanoic acid, uses',
 ARRAY['ethanol','alcohol','fermentation','glucose','yeast','hydration of ethene','ethanoic acid','biofuel']),

((SELECT id FROM subjects WHERE code = '4CH1'), '4.5', 'Carboxylic Acids and Esters',
 'Properties of carboxylic acids, esterification, hydrolysis, uses of esters',
 ARRAY['carboxylic acid','ethanoic acid','ester','esterification','hydrolysis','vinegar','COOH','fruity smell']),

((SELECT id FROM subjects WHERE code = '4CH1'), '4.6', 'Polymerisation',
 'Addition and condensation polymerisation, structure of polymers, environmental issues',
 ARRAY['polymer','monomer','addition polymerisation','condensation polymerisation','polyethene','nylon','polyester','plastic']),

-- Section 5: Chemistry in Society
((SELECT id FROM subjects WHERE code = '4CH1'), '5.1', 'Gases in the Atmosphere',
 'Composition of air, history of atmosphere, greenhouse effect, global warming, air pollution',
 ARRAY['atmosphere','greenhouse effect','global warming','carbon dioxide','methane','air pollution','ozone','nitrogen','oxygen']),

((SELECT id FROM subjects WHERE code = '4CH1'), '5.2', 'Water',
 'Water treatment, hardness of water, removing hardness, water as a solvent',
 ARRAY['hard water','soft water','temporary hardness','permanent hardness','calcium carbonate','limescale','water treatment','chlorination']),

((SELECT id FROM subjects WHERE code = '4CH1'), '5.3', 'Industrial Chemistry',
 'Economic factors, raw materials, life cycle assessment, recycling, sustainability',
 ARRAY['industrial chemistry','raw material','economic factor','life cycle assessment','recycling','sustainability','atom economy']);


-- ─── STEP 4: Insert Biology chapters (4BI1) ──────────────────────────────────
INSERT INTO topics (subject_id, code, name, description, keywords) VALUES

-- Section 1: Nature and Variety of Living Organisms
((SELECT id FROM subjects WHERE code = '4BI1'), '1.1', 'Characteristics of Living Organisms',
 'MRS GREN: movement, respiration, sensitivity, growth, reproduction, excretion, nutrition',
 ARRAY['characteristics of life','MRS GREN','movement','sensitivity','growth','reproduction','excretion','nutrition','living organism']),

((SELECT id FROM subjects WHERE code = '4BI1'), '1.2', 'Variety of Living Organisms',
 'Classification into 5 kingdoms; viruses; dichotomous keys; binomial nomenclature',
 ARRAY['classification','kingdom','animal','plant','fungi','bacteria','protist','virus','dichotomous key','binomial','species','eukaryote','prokaryote']),

-- Section 2: Structures and Functions in Living Organisms
((SELECT id FROM subjects WHERE code = '4BI1'), '2.1', 'Cell Structure and Organisation',
 'Animal and plant cells, organelles, specialised cells, tissue, organ, organ system',
 ARRAY['cell structure','organelle','nucleus','mitochondria','chloroplast','cell wall','vacuole','cell membrane','ribosome','cytoplasm','animal cell','plant cell','specialised cell','magnification']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.2', 'Biological Molecules',
 'Carbohydrates, lipids, proteins, DNA, enzymes, food tests',
 ARRAY['carbohydrate','lipid','protein','DNA','enzyme','starch','glucose','amino acid','polypeptide','Benedict','iodine test','biuret','food test','active site','denatured']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.3', 'Movement of Substances',
 'Diffusion, osmosis, active transport, concentration gradient, water potential',
 ARRAY['diffusion','osmosis','active transport','concentration gradient','water potential','turgid','plasmolysis','plasmolysed','partially permeable membrane','facilitated diffusion']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.4', 'Nutrition in Plants',
 'Photosynthesis, limiting factors, leaf structure, mineral ion requirements',
 ARRAY['photosynthesis','chlorophyll','light intensity','carbon dioxide','glucose','starch','limiting factor','stomata','guard cell','chloroplast','mineral ion','nitrate','magnesium']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.5', 'Nutrition in Humans',
 'Digestive system, enzymes (amylase, protease, lipase), bile, villi, liver',
 ARRAY['digestion','digestive system','stomach','small intestine','amylase','protease','lipase','bile','villi','villus','absorption','peristalsis','balanced diet','liver','pancreas']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.6', 'Respiration',
 'Aerobic and anaerobic respiration, ATP, fermentation, effects of exercise',
 ARRAY['aerobic respiration','anaerobic respiration','respiration','ATP','mitochondria','glucose','oxygen','lactic acid','fermentation','yeast','ethanol','oxygen debt','exercise']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.7', 'Gas Exchange',
 'Alveoli, ventilation, gas exchange in plants (stomata) and fish (gills)',
 ARRAY['alveoli','alveolus','lung','breathing','diaphragm','intercostal muscle','stomata','guard cell','gill','ventilation','gas exchange','inhale','exhale']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.8', 'Transport in Plants',
 'Xylem, phloem, transpiration, translocation, factors affecting transpiration rate',
 ARRAY['xylem','phloem','transpiration','translocation','water transport','mineral transport','root hair','transpiration stream','wilting','potometer','humidity']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.9', 'Transport in Humans',
 'Heart structure, circulatory system, blood composition, coronary heart disease',
 ARRAY['heart','atrium','ventricle','valve','artery','vein','capillary','blood','plasma','red blood cell','white blood cell','platelet','haemoglobin','coronary heart disease','double circulation']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.10', 'Excretion',
 'Kidneys, urine formation, ultrafiltration, selective reabsorption, ADH, liver, deamination',
 ARRAY['excretion','kidney','urine','urea','ultrafiltration','selective reabsorption','nephron','glomerulus','Bowman','ADH','osmoregulation','deamination']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.11', 'Coordination and Response',
 'Nervous system, reflex arc, hormones, plant tropisms, auxins, eye',
 ARRAY['nervous system','neurone','synapse','reflex arc','receptor','effector','brain','spinal cord','hormone','insulin','glucagon','adrenaline','oestrogen','auxin','phototropism','geotropism','tropism','pupil reflex']),

((SELECT id FROM subjects WHERE code = '4BI1'), '2.12', 'Homeostasis',
 'Temperature regulation, blood glucose control (insulin, glucagon), ADH, negative feedback',
 ARRAY['homeostasis','thermoregulation','body temperature','blood glucose','insulin','glucagon','negative feedback','vasodilation','vasoconstriction','shivering','sweating','ADH','diabetes']),

-- Section 3: Reproduction and Inheritance
((SELECT id FROM subjects WHERE code = '4BI1'), '3.1', 'Reproduction in Plants',
 'Flowers, pollination, fertilisation, seed dispersal; asexual reproduction',
 ARRAY['plant reproduction','pollination','fertilisation','seed dispersal','pollen','stigma','ovule','flower structure','anther','stamen','carpel','asexual reproduction','runner','bulb','tuber','cutting']),

((SELECT id FROM subjects WHERE code = '4BI1'), '3.2', 'Reproduction in Humans',
 'Reproductive systems, menstrual cycle, fertilisation, pregnancy, contraception, STIs',
 ARRAY['menstrual cycle','ovulation','fertilisation','implantation','pregnancy','uterus','ovary','testes','sperm','egg','FSH','LH','oestrogen','progesterone','contraception','STI','placenta']),

((SELECT id FROM subjects WHERE code = '4BI1'), '3.3', 'Cell Division',
 'Mitosis (2 diploid identical cells) and meiosis (4 haploid gametes, genetic variation)',
 ARRAY['mitosis','meiosis','chromosome','diploid','haploid','gamete','DNA replication','crossing over','genetic variation','cell cycle','binary fission']),

((SELECT id FROM subjects WHERE code = '4BI1'), '3.4', 'Inheritance',
 'Genes, alleles, dominant, recessive, Punnett squares, codominance, sex linkage, mutations',
 ARRAY['genetics','allele','dominant','recessive','genotype','phenotype','homozygous','heterozygous','Punnett square','monohybrid','codominance','sex-linked','mutation','carrier','inheritance']),

((SELECT id FROM subjects WHERE code = '4BI1'), '3.5', 'Natural Selection and Evolution',
 'Natural selection, Darwin, variation, adaptation, antibiotic resistance, speciation, fossils',
 ARRAY['natural selection','evolution','Darwin','variation','adaptation','survival of the fittest','antibiotic resistance','speciation','fossil','extinction','selective pressure']),

-- Section 4: Ecology and the Environment
((SELECT id FROM subjects WHERE code = '4BI1'), '4.1', 'Organisms and Their Environment',
 'Ecosystems, habitats, niches, abiotic and biotic factors, population sampling',
 ARRAY['ecosystem','habitat','niche','abiotic factor','biotic factor','population','community','quadrat','transect','sampling','distribution','abundance','competition']),

((SELECT id FROM subjects WHERE code = '4BI1'), '4.2', 'Feeding Relationships',
 'Food chains, food webs, producers, consumers, decomposers, energy transfer, biomass pyramids',
 ARRAY['food chain','food web','producer','consumer','decomposer','herbivore','carnivore','predator','prey','trophic level','pyramid of numbers','pyramid of biomass','energy transfer']),

((SELECT id FROM subjects WHERE code = '4BI1'), '4.3', 'Nutrient Cycles',
 'Carbon cycle, nitrogen cycle, water cycle, decomposition, nitrogen fixation, nitrification',
 ARRAY['carbon cycle','nitrogen cycle','water cycle','decomposition','nitrogen fixation','nitrification','denitrification','Rhizobium','combustion','transpiration','nutrient recycling']),

((SELECT id FROM subjects WHERE code = '4BI1'), '4.4', 'Human Influences on the Environment',
 'Pollution, deforestation, habitat loss, climate change, eutrophication, conservation',
 ARRAY['pollution','deforestation','habitat destruction','climate change','global warming','eutrophication','sewage','fertiliser runoff','pesticide','conservation','biodiversity','endangered']),

-- Section 5: Use of Biological Resources
((SELECT id FROM subjects WHERE code = '4BI1'), '5.1', 'Food Production',
 'Crop plants, livestock, fish farming, glasshouses, hydroponics, food chain efficiency',
 ARRAY['food production','farming','crop','livestock','pest control','fertiliser','fish farming','hydroponics','intensive farming','food chain efficiency']),

((SELECT id FROM subjects WHERE code = '4BI1'), '5.2', 'Selective Breeding',
 'Artificial selection in plants and animals; high-yield crops; disease resistance; risks',
 ARRAY['selective breeding','artificial selection','breeding program','high yield crop','disease resistance','trait selection','domestication','inbreeding']),

((SELECT id FROM subjects WHERE code = '4BI1'), '5.3', 'Genetic Engineering',
 'GM crops, insulin production, restriction enzymes, plasmid vector, ethical issues',
 ARRAY['genetic engineering','genetic modification','GM crop','recombinant DNA','insulin','plasmid','restriction enzyme','DNA ligase','host cell','ethics','Bt cotton']),

((SELECT id FROM subjects WHERE code = '4BI1'), '5.4', 'Cloning',
 'Tissue culture, embryo transplanting, adult cell cloning (Dolly), stem cells',
 ARRAY['cloning','tissue culture','embryo transplant','adult cell cloning','Dolly','stem cell','therapeutic cloning','somatic cell','nuclear transfer','micropropagation']);


-- ─── STEP 5: Reset pages.topics for chem/bio (flag for re-classification) ────
-- We reset to empty array so the classifier picks them up as unclassified.
-- The backup is in topics_v1 for rollback purposes.
UPDATE pages p
SET    topics = '{}',
       confidence = NULL
FROM   papers pa
JOIN   subjects s ON pa.subject_id = s.id
WHERE  pa.id = p.paper_id
  AND  s.code IN ('4CH1', '4BI1');

COMMIT;

-- ─── ROLLBACK SCRIPT (run manually if needed) ────────────────────────────────
-- To undo this migration:
--
-- BEGIN;
-- DELETE FROM topics
-- WHERE subject_id IN (SELECT id FROM subjects WHERE code IN ('4CH1','4BI1'));
--
-- INSERT INTO topics (subject_id, code, name, description)
-- SELECT s.id, t.code, t.name, ''
-- FROM (VALUES
--   ('4CH1','1','Principles of Chemistry'),
--   ('4CH1','2','Chemistry of the Elements'),
--   ('4CH1','3','Organic Chemistry'),
--   ('4CH1','4','Physical Chemistry'),
--   ('4CH1','5','Chemistry in Society'),
--   ('4BI1','1','Nature and Variety of Living Organisms'),
--   ('4BI1','2','Structures and Functions in Living Organisms'),
--   ('4BI1','3','Reproduction and Inheritance'),
--   ('4BI1','4','Ecology and the Environment'),
--   ('4BI1','5','Use of Biological Resources')
-- ) AS t(code_subj, code, name)
-- JOIN subjects s ON s.code = t.code_subj;
--
-- UPDATE pages p SET topics = p.topics_v1
-- FROM papers pa JOIN subjects s ON pa.subject_id = s.id
-- WHERE pa.id = p.paper_id AND s.code IN ('4CH1','4BI1');
-- COMMIT;
