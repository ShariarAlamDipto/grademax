-- 35: `questions` becomes an exact, automatic mirror of `pages`.
--
-- Why: worksheet_items.question_id references questions(id), and saved-worksheet
-- re-downloads (/api/worksheets/[id]/download, /pdf) read the PDF URLs from
-- `questions`. But the tools pick from `pages`, and only ~1/3 of pages rows had a
-- questions row (all IAL, most of 4PH1/4MB1/4PM1 had none). For those, the
-- generator's worksheet_items insert failed silently on the FK, so the saved
-- worksheet re-downloaded as "No PDFs found". 2,013 older questions rows (no
-- pages row any more) still pointed at the pre-2026-10 per-question cuts, whose
-- mark schemes were the ones found wrong -- 251 saved worksheets used them.
--
-- After this migration:
--   * every pages row has a questions row with the same id and the same URLs;
--   * a trigger keeps them identical on every insert/update of pages;
--   * stale rows are re-pointed at the verified cut for the same paper and
--     question number (rows with no such question keep their URLs).
--   * questions.difficulty only accepts easy/medium/hard/NULL
--     (questions_difficulty_check); any other pages value (2 rows hold the
--     text 'None') is mirrored as NULL.

create or replace function public.sync_question_mirror()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.questions (id, paper_id, question_number, difficulty,
                                page_pdf_url, ms_pdf_url, has_diagram, text_excerpt)
  values (new.id, new.paper_id, new.question_number,
          case when new.difficulty in ('easy', 'medium', 'hard') then new.difficulty end,
          new.qp_page_url, new.ms_page_url, coalesce(new.has_diagram, false), new.text_excerpt)
  on conflict (id) do update set
    paper_id        = excluded.paper_id,
    question_number = excluded.question_number,
    difficulty      = excluded.difficulty,
    page_pdf_url    = excluded.page_pdf_url,
    ms_pdf_url      = excluded.ms_pdf_url,
    has_diagram     = excluded.has_diagram,
    text_excerpt    = excluded.text_excerpt;
  return new;
end;
$$;

drop trigger if exists pages_sync_question_mirror on public.pages;
create trigger pages_sync_question_mirror
  after insert or update of paper_id, question_number, difficulty, qp_page_url,
                            ms_page_url, has_diagram, text_excerpt
  on public.pages
  for each row execute function public.sync_question_mirror();

-- Backfill: one mirror row per pages row, URLs identical.
insert into public.questions (id, paper_id, question_number, difficulty,
                              page_pdf_url, ms_pdf_url, has_diagram, text_excerpt)
select p.id, p.paper_id, p.question_number,
       case when p.difficulty in ('easy', 'medium', 'hard') then p.difficulty end,
       p.qp_page_url, p.ms_page_url, coalesce(p.has_diagram, false), p.text_excerpt
from public.pages p
on conflict (id) do update set
  paper_id        = excluded.paper_id,
  question_number = excluded.question_number,
  difficulty      = excluded.difficulty,
  page_pdf_url    = excluded.page_pdf_url,
  ms_pdf_url      = excluded.ms_pdf_url,
  has_diagram     = excluded.has_diagram,
  text_excerpt    = excluded.text_excerpt;

-- Stale rows (no pages row): take the verified cut of the same paper + number.
update public.questions q
set page_pdf_url = m.qp_page_url,
    ms_pdf_url   = m.ms_page_url
from (
  select distinct on (p.paper_id, p.question_number)
         p.paper_id, p.question_number, p.qp_page_url, p.ms_page_url
  from public.pages p
  where p.qp_page_url is not null
  order by p.paper_id, p.question_number, p.page_number
) m
where not exists (select 1 from public.pages p2 where p2.id = q.id)
  and m.paper_id = q.paper_id
  and m.question_number = q.question_number;
