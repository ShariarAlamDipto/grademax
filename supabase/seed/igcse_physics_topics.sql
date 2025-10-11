-- Seed IGCSE Physics Topics (Idempotent)
-- Run this AFTER schema.sql

insert into subjects (board, level, code, name, color)
values ('Edexcel','IGCSE','4PH1','Physics','#3b82f6')
on conflict (board, level, code) do nothing;

with s as (
  select id from subjects
  where board='Edexcel' and level='IGCSE' and code='4PH1' limit 1
)
insert into topics (subject_id, code, name, spec_ref, content)
select s.id, v.code, v.name, v.spec_ref, v.content
from s cross join (
  values
    ('1a','Units','p6','Use SI units: kg, m, s, A, K, mol, cd'),
    ('1b','Movement and position','p7','Plot/explain distance–time graphs; average speed = distance ÷ time'),
    ('1c','Forces, movement, shape and momentum','p9','Forces; Newton''s laws; momentum = mass × velocity'),
    ('1d','Energy and work','p12','Work = force × distance; KE & GPE; efficiency'),
    ('2a','Mains electricity','p14','AC vs DC; V, I, R; V = I × R'),
    ('2b','Energy and voltage in circuits','p16','Power = V × I; energy = V × I × t; series vs parallel'),
    ('2c','Electric charge','p18','Charge; current as flow of charge; static electricity'),
    ('3a','Properties of waves','p20','λ, f, A; v = f × λ; transverse vs longitudinal'),
    ('3b','Electromagnetic spectrum','p22','Order EM by λ/f; uses & hazards'),
    ('3c','Light and sound','p24','Reflection, refraction, diffraction; speed of sound'),
    ('4a','Energy resources & generation','p26','Fossil, nuclear, renewables; efficiency comparisons'),
    ('4b','Work and power','p28','Work = F × d; power = work ÷ time; efficiency'),
    ('5a','Density and pressure','p30','ρ = m ÷ V; p = F ÷ A; fluids'),
    ('5b','Change of state','p32','Melting, boiling, evaporation, condensation; latent heat'),
    ('5c','Ideal gas molecules','p34','Kinetic theory; Brownian motion; p–V–T'),
    ('6a','Magnetism','p36','Fields, poles, field lines, induced magnetism'),
    ('6b','Electromagnetism','p38','Motor effect; FLHR; induction; transformers'),
    ('7a','Radioactivity','p40','α, β, γ; uses & hazards; half-life; nuclear equations'),
    ('7b','Fission and fusion','p42','Fission, chain reactions; fusion in stars'),
    ('8a','Motion in the Universe','p44','Orbits, gravity, satellites, planets, moons'),
    ('8b','Stellar evolution','p46','Lifecycle; supernova; neutron star; black hole; cosmology')
) as v(code, name, spec_ref, content)
on conflict (subject_id, code) do nothing;

-- Verification
select code, name from topics 
where subject_id = (select id from subjects where code='4PH1' and level='IGCSE')
order by code;
