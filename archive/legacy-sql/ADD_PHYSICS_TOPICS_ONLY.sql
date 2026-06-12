-- ============================================================================
-- RUN THIS IN SUPABASE SQL EDITOR
-- This will add 24 Physics topics to your database
-- ============================================================================

-- First, verify Physics subject exists
DO $$
DECLARE
  physics_id UUID;
  topic_count INT;
BEGIN
  -- Get Physics subject ID
  SELECT id INTO physics_id 
  FROM subjects 
  WHERE code = '4PH1' AND level = 'IGCSE' 
  LIMIT 1;

  IF physics_id IS NULL THEN
    RAISE EXCEPTION '❌ Physics subject (4PH1) not found! Please run COMPLETE_FIX.sql first to seed subjects.';
  END IF;

  RAISE NOTICE '✅ Found Physics subject ID: %', physics_id;

  -- Check if topics already exist
  SELECT COUNT(*) INTO topic_count 
  FROM topics 
  WHERE subject_id = physics_id;

  IF topic_count > 0 THEN
    RAISE NOTICE '⚠️  Found % existing Physics topics. Deleting them first...', topic_count;
    DELETE FROM topics WHERE subject_id = physics_id;
    RAISE NOTICE '✅ Deleted old topics';
  END IF;

  -- Insert all 24 Physics topics
  INSERT INTO topics (subject_id, code, name, spec_ref, content) VALUES
  -- Topic 1: Forces and motion
  (physics_id, '1a', 'Units', 'p6', 'Use SI units: kg, m, s, A, K, mol, cd'),
  (physics_id, '1b', 'Movement and position', 'p7', 'Plot and explain distance-time graphs; calculate average speed'),
  (physics_id, '1c', 'Forces, movement, shape and momentum', 'p9', 'Identify forces, calculate momentum, apply Newtons laws'),
  (physics_id, '1d', 'Energy and work', 'p12', 'Calculate work done, kinetic energy, gravitational potential energy, efficiency'),
  
  -- Topic 2: Electricity
  (physics_id, '2a', 'Mains electricity', 'p14', 'Understand AC/DC, voltage, current, resistance; use Ohms law'),
  (physics_id, '2b', 'Energy and voltage in circuits', 'p16', 'Calculate power and energy; series and parallel circuits'),
  (physics_id, '2c', 'Electric charge', 'p18', 'Describe charge, current as flow of charge, static electricity'),
  
  -- Topic 3: Waves
  (physics_id, '3a', 'Properties of waves', 'p20', 'Define wavelength, frequency, amplitude; wave equation; transverse vs longitudinal'),
  (physics_id, '3b', 'The electromagnetic spectrum', 'p22', 'Order EM waves by wavelength/frequency; applications and dangers'),
  (physics_id, '3c', 'Light and sound', 'p24', 'Reflection, refraction, diffraction, interference; speed of sound'),
  
  -- Topic 4: Energy resources and energy transfers
  (physics_id, '4a', 'Energy resources and electricity generation', 'p26', 'Compare fossil fuels, nuclear, renewables; efficiency of power stations'),
  (physics_id, '4b', 'Work and power', 'p28', 'Calculate work and power, efficiency calculations'),
  
  -- Topic 5: Solids, liquids and gases
  (physics_id, '5a', 'Density and pressure', 'p30', 'Calculate density, pressure, pressure in fluids'),
  (physics_id, '5b', 'Change of state', 'p32', 'Describe melting, boiling, evaporation, condensation; latent heat'),
  (physics_id, '5c', 'Ideal gas molecules', 'p34', 'Kinetic theory, Brownian motion, absolute zero, gas laws'),
  
  -- Topic 6: Magnetism and electromagnetism
  (physics_id, '6a', 'Magnetism', 'p36', 'Magnetic fields, poles, plotting field lines, induced magnetism'),
  (physics_id, '6b', 'Electromagnetism', 'p38', 'Motor effect, Flemings left-hand rule, electromagnetic induction, transformers'),
  
  -- Topic 7: Radioactivity and particles
  (physics_id, '7a', 'Radioactivity', 'p40', 'Alpha, beta, gamma radiation; properties, uses, dangers; half-life; nuclear equations'),
  (physics_id, '7b', 'Fission and fusion', 'p42', 'Nuclear fission, chain reactions, fusion in stars'),
  
  -- Topic 8: Astrophysics
  (physics_id, '8a', 'Motion in the Universe', 'p44', 'Orbital motion, gravity, satellites, planets, moons'),
  (physics_id, '8b', 'Stellar evolution', 'p46', 'Life cycle of stars: main sequence, red giant, white dwarf, supernova, neutron star, black hole');

  -- Verify insertion
  SELECT COUNT(*) INTO topic_count 
  FROM topics 
  WHERE subject_id = physics_id;

  RAISE NOTICE '';
  RAISE NOTICE '============================================================';
  RAISE NOTICE '✅ SUCCESS! Inserted % Physics topics', topic_count;
  RAISE NOTICE '============================================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Topics added:';
  RAISE NOTICE '  1a - Units';
  RAISE NOTICE '  1b - Movement and position';
  RAISE NOTICE '  1c - Forces, movement, shape and momentum';
  RAISE NOTICE '  1d - Energy and work';
  RAISE NOTICE '  2a - Mains electricity';
  RAISE NOTICE '  2b - Energy and voltage in circuits';
  RAISE NOTICE '  2c - Electric charge';
  RAISE NOTICE '  3a - Properties of waves';
  RAISE NOTICE '  3b - The electromagnetic spectrum';
  RAISE NOTICE '  3c - Light and sound';
  RAISE NOTICE '  4a - Energy resources and electricity generation';
  RAISE NOTICE '  4b - Work and power';
  RAISE NOTICE '  5a - Density and pressure';
  RAISE NOTICE '  5b - Change of state';
  RAISE NOTICE '  5c - Ideal gas molecules';
  RAISE NOTICE '  6a - Magnetism';
  RAISE NOTICE '  6b - Electromagnetism';
  RAISE NOTICE '  7a - Radioactivity';
  RAISE NOTICE '  7b - Fission and fusion';
  RAISE NOTICE '  8a - Motion in the Universe';
  RAISE NOTICE '  8b - Stellar evolution';
  RAISE NOTICE '';
  RAISE NOTICE '👉 Next: Go to http://localhost:3001/worksheets';
  RAISE NOTICE '   Select "Edexcel IGCSE Physics (4PH1)"';
  RAISE NOTICE '   You should see 24 topics appear!';
  RAISE NOTICE '============================================================';

END $$;
