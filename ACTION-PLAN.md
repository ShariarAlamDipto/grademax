# GradeMax SEO action plan

Metadata follow-up (15 October 2026): canonical, social metadata, title, route-specific schema and /generate sitemap fixes are implemented and verified locally. See [fix summary](output/seo-metadata-fix-2026-10-15/FIX-SUMMARY.md). Deployment and Google recrawling remain outstanding.

15 October 2026 (Asia/Dhaka). Audit complete; no application changes or deployment performed. See FULL-AUDIT-REPORT.md for scope, evidence, impact and limitations.

| Order | Priority | Task | Effort | Acceptance check |
|---|---|---|---|---|
| 1 | P1 / quick win | Correct store, five product pages, Contact, Privacy and Terms canonicals; review Improvements and other root-metadata inheritors. | Low | Every intended indexable page emits exactly its intended canonical; sitemap and canonical agree. Confirm in response HTML and Google URL Inspection after deployment. |
| 2 | P1 | Consume validated subject/topic URL parameters in the worksheet generator. | Medium | A Physics radioactivity link selects Physics and its topic; a Maths B link selects Maths B; unknown inputs receive a useful fallback. |
| 3 | P1 | Gate subject/topic worksheet CTAs on actual tool support. | Low/medium | Unsupported English Literature Unit 1 and Mechanics 3 pages lead to available papers rather than promising unavailable worksheets. |
| 4 | P2 / quick win | Remove duplicate GradeMax suffix from /past-papers. | Low | Live title contains the brand once. |
| 5 | P2 / quick win | Decide /generate public-indexing policy and update sitemap/comment. | Low | The sitemap reflects the real public route and intentional canonical policy; no auth-only URL is advertised. |
| 6 | P2 | Add product Open Graph metadata and Product/Offer JSON-LD. | Medium | Correct self-canonical first; real BDT price/stock, images and policies; Google Rich Results Test has no required-field errors. |
| 7 | P2 | Move homepage-only WebPage/ItemList schema out of root layout; use real dates. | Low/medium | Paper/product pages identify themselves accurately; no request-time invented update timestamp. |
| 8 | P2 / strategic | Improve low-value topic pages and deliver actual relevant practice resources. | Higher | Topic pages answer specific needs, link to supported resources and contain subject-specific examples instead of generic keyword prompts. |
| 9 | P3 | Add truthful team, sourcing, editorial checks and corrections detail. | Medium | About/resources explain who maintains materials and how errors are handled. |
| 10 | P3 | Derive sitemap lastmod from substantive update timestamps. | Medium | Correcting a paper/PDF changes the relevant URL and aggregate lastmod; unchanged content retains its date. |
| 11 | P3 | Restore/remove missing npm SEO monitoring commands; update llms.txt host and coverage. | Low/medium | Declared scripts exist and run; canonical www links and truthful board/year descriptions. |

## Verification still needed

1. Read Search Console sitemap processing, Page indexing exclusions and representative URL Inspection results. Record both user-declared and Google-selected canonicals. Public sitemap retrieval alone cannot establish indexing.
2. Measure mobile LCP, INP and CLS through PageSpeed/CrUX or Search Console; the API was rate-limited during this audit.
3. Crawl the remaining sitemap URLs and test actual PDF links with a bounded, rate-limited process. This audit sampled 95 sitemap URLs, all returning 200; it did not validate all 15,094 destinations.
4. Verify browser behavior, console and mobile layout for core tools; source inspection established the ignored query parameter defect.

Do not spend priority effort on sitemap priority/changefreq, arbitrary word-count targets, optional Twitter handles, llms-full.txt or FAQ rich-result markup. No evidence currently establishes a Google penalty, ranking loss or a site-wide indexing block.
