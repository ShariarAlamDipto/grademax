-- Physics IGCSE Topics Seed SQL (Edexcel 4PH1)
-- Run this in Supabase SQL Editor after creating the subjects table

-- First, ensure Physics subject exists
INSERT INTO subjects (board, level, code, name, color)
VALUES ('Edexcel', 'IGCSE', '4PH1', 'Physics', '#3b82f6')
ON CONFLICT DO NOTHING;

-- Get the subject_id (adjust if needed)
DO $$
DECLARE
  physics_id bigint;
BEGIN
  SELECT id INTO physics_id FROM subjects WHERE code = '4PH1' AND level = 'IGCSE' LIMIT 1;

  -- Topic 1: Forces and motion
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '1a', 'Units', 'p6', 'Use SI units: kg, m, s, A, K, mol, cd'),
  (physics_id, '1b', 'Movement and position', 'p7', 'Plot and explain distance–time graphs; calculate average speed = distance ÷ time'),
  (physics_id, '1c', 'Forces, movement, shape and momentum', 'p9', 'Identify forces, calculate momentum = mass × velocity, apply Newton's laws'),
  (physics_id, '1d', 'Energy and work', 'p12', 'Calculate work done = force × distance, kinetic energy, gravitational potential energy, efficiency');

  -- Topic 2: Electricity
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '2a', 'Mains electricity', 'p14', 'Understand AC/DC, voltage, current, resistance; use V = I × R'),
  (physics_id, '2b', 'Energy and voltage in circuits', 'p16', 'Calculate power = V × I, energy transferred = V × I × t; series and parallel circuits'),
  (physics_id, '2c', 'Electric charge', 'p18', 'Describe charge, current as flow of charge, static electricity');

  -- Topic 3: Waves
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '3a', 'Properties of waves', 'p20', 'Define wavelength, frequency, amplitude; use v = f × λ; transverse vs longitudinal'),
  (physics_id, '3b', 'The electromagnetic spectrum', 'p22', 'Order EM waves by wavelength/frequency; applications and dangers'),
  (physics_id, '3c', 'Light and sound', 'p24', 'Reflection, refraction, diffraction, interference; speed of sound');

  -- Topic 4: Energy resources and energy transfers
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '4a', 'Energy resources and electricity generation', 'p26', 'Compare fossil fuels, nuclear, renewables; efficiency of power stations'),
  (physics_id, '4b', 'Work and power', 'p28', 'Calculate work = F × d, power = work ÷ time, efficiency = useful output ÷ total input');

  -- Topic 5: Solids, liquids and gases
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '5a', 'Density and pressure', 'p30', 'Calculate density = mass ÷ volume, pressure = force ÷ area, pressure in fluids'),
  (physics_id, '5b', 'Change of state', 'p32', 'Describe melting, boiling, evaporation, condensation; latent heat'),
  (physics_id, '5c', 'Ideal gas molecules', 'p34', 'Kinetic theory, Brownian motion, absolute zero, pressure–volume–temperature relationships');

  -- Topic 6: Magnetism and electromagnetism
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '6a', 'Magnetism', 'p36', 'Magnetic fields, poles, plotting field lines, induced magnetism'),
  (physics_id, '6b', 'Electromagnetism', 'p38', 'Motor effect, Fleming's left-hand rule, electromagnetic induction, transformers');

  -- Topic 7: Radioactivity and particles
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '7a', 'Radioactivity', 'p40', 'Alpha, beta, gamma radiation; properties, uses, dangers; half-life; nuclear equations'),
  (physics_id, '7b', 'Fission and fusion', 'p42', 'Nuclear fission, chain reactions, fusion in stars');

  -- Topic 8: Astrophysics
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  (physics_id, '8a', 'Motion in the Universe', 'p44', 'Orbital motion, gravity, satellites, planets, moons'),
  (physics_id, '8b', 'Stellar evolution', 'p46', 'Life cycle of stars: main sequence, red giant, white dwarf, supernova, neutron star, black hole; cosmology');

END $$;
