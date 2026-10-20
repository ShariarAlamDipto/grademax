# GradeMax SEO audit

Date: 15 October 2026 (Asia/Dhaka). Scope: full-site sampled audit of https://www.grademax.me and the local Next.js implementation. This is an inspection; application files were not changed or deployed. Existing local edits mean source observations and production behavior are identified separately.

## A. Audit summary

Overall rating: **Needs improvement**, with a healthy basic sitemap and several confirmed canonical and feature-consistency defects. Numeric overall score: **Insufficient data**. Core Web Vitals, private Search Console data and a complete URL-status crawl are unavailable, so a precise weighted health score would be misleading.

The three highest priorities are (1) homepage canonicals on store/product and informational pages, (2) practice links that do not preselect the requested subject/topic, and (3) worksheet promises for unsupported subjects. The fastest opportunities are correcting route metadata, removing the repeated brand from the past-papers title, and matching worksheet CTAs to actual availability.

### Evidence coverage

- Parsed every sitemap entry: **15,094 URLs, all unique and HTTPS on the canonical www host**.
- Fetched **106 distinct requested URLs**, including **95 sitemap URLs** sampled across hubs, subjects/topics, QP pages, store, years, sessions and individual papers. Samples were stratified and seeded with 42; see audit_live.py.
- All **95 sampled sitemap URLs returned 200 without redirect chains**; **9 had homepage canonical mismatches**. None of those 95 emitted noindex.
- Sample composition: all core hubs and all current store URLs; 8 subjects/topic URLs; 8 QP URLs; 14 each of past-paper subject, year, session and paper URLs; plus selected explicit checks.
- The bundled homepage link checker tested 41 unique links: 37 healthy, 4 redirected, 0 broken, 0 timed out. Its TLS verification was disabled, so the direct verified requests in crawl.json are stronger evidence for sampled internal URLs.
- Bundled checks attempted: robots, llms.txt, PageSpeed mobile, security headers, broken links, redirects, social metadata, internal links, HTML parsing, readability, schema parsing, and finding verification.

### Sitemap result

| Check | Result |
|---|---|
| Fetch | HTTP 200 at /sitemap.xml |
| XML root / namespace | Valid urlset; standard sitemaps.org namespace |
| URL count | 15,094 / 50,000 maximum per sitemap |
| Size | 3,096,088 bytes (about 3.1 MB), below 50 MB. Raw response bytes retained in sitemap.xml. |
| Duplicated URL strings | 0 |
| Non-HTTPS or wrong host | 0 |
| robots.txt reference | Correct www sitemap URL present |
| lastmod coverage | 14,606 present; 488 omitted |
| Sampled HTTP status | 95/95 sitemap URLs return 200 |
| Sampled canonical alignment | 86/95 self-canonical; 9 point to homepage |
| Entire sitemap HTTP status / file health | Unknown; not all 15,094 URLs or their PDFs were fetched |

The sitemap contains 1,022 year URLs, 2,115 session URLs, 11,469 individual paper URLs, 282 subject/topic/level URLs, 86 QP URLs, 99 subject-or-Cambridge-index URLs at past-papers depth 2, and the remaining core/store URLs. A single sitemap is permitted at this size; splitting it by content type would be an operational option, not an urgent requirement. Missing lastmod on evergreen pages is acceptable. priority and changefreq are ignored by Google and need not be treated as faults. [Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).

## B. Findings table

| ID | Area | Severity | Confidence | Finding | Evidence | Fix |
|---|---|---|---|---|---|---|
| F01 | Canonical URLs | Warning | Confirmed | Nine sitemap URLs incorrectly canonicalize to the homepage. | Live crawl.json: /contact, /privacy, /terms, /store, /store/mathematics-b, /store/further-pure-mathematics, /store/m1-yearwise, /store/s1-yearwise and /store/p4-yearwise all return 200 with rel=canonical https://www.grademax.me. Root src/app/layout.tsx:209 supplies a homepage canonical; these routes omit an override. /improvements has the same issue outside the sitemap. | Give every intended indexable route a self-referencing canonical, including generateMetadata for each product. Keep homepage canonical on the homepage. Verify emitted HTML across the entire route inventory. |
| F02 | Topic links / tool behavior | Warning | Confirmed | Subject and topic practice links do not initialize the requested worksheet filters. | src/app/subjects/[level]/[slug]/[topic]/page.tsx:166 and :230 link to /generate?subject={slug}&level={level}&topic={code}; src/app/generate/page.tsx:11 accepts no searchParams; src/components/generate/WorksheetGenerator.tsx:115 initializes selectedSubject to the first subject and has no query parameter reader. Live query URLs return 200 and canonicalize to /generate. | Resolve subject slugs and topic codes into supported database IDs on the server; pass validated initial selection into the generator. Show a useful fallback when the request is unsupported. |
| F03 | Content / feature accuracy | Warning | Confirmed | Topic pages promote worksheet generation for unsupported subjects. | Live /subjects/ial/ial-english-literature/unit-1 advertises a custom worksheet for English Literature. Live /generate subject options contain Physics, Maths A/B, Chemistry, Biology, Human Biology, Further Pure Maths and selected IAL mathematics units; English Literature is absent. The shared topic template promotes the generator without checking tool coverage. | Gate worksheet CTAs against actual tool coverage. For unsupported subjects, link to their available past papers and remove unfulfilled generation promises. |
| F04 | Store structured data | Warning | Confirmed | The five live book detail pages have no Product structured data. | All five store product responses in crawl.json contain only the shared root JSON-LD graph. src/app/store/[slug]/page.tsx provides title/description but no Product/Offer JSON-LD. | After canonical fixes, add JSON-LD Product with real Offer priceCurrency BDT, price, URL, availability, seller and applicable shipping/returns details. Use only real identifiers and reviews; validate with Google Rich Results Test. |
| F05 | Structured data accuracy | Warning | Confirmed | Homepage-specific schema and artificial modification dates are emitted across unrelated routes. | src/app/layout.tsx:62-73 defines a homepage WebPage with @id /#webpage, homepage URL/name and dateModified=new Date().toISOString(); the same root graph appears on product and paper pages. Captured home dateModified is 2026-10-13T06:43:29.322Z; a product response has 2026-10-15T04:13:41.284Z for that same homepage entity. | Keep Organization/WebSite shared; emit homepage WebPage and homepage ItemList only on the homepage. Emit route-specific page entities with actual content update timestamps, or omit optional modification dates. |
| F06 | Topic content quality | Warning | Likely | Some topic landing pages provide little useful topic-specific content beyond repeated prompts. | Live English Literature Unit 1 page has 148 main-content words and generic text such as Unit 1 examination content; the keyword card repeats Practice ... questions. Physics forces-and-motion has 169 main-content words, mostly navigation and calls to action. Source topic template repeats the same sentence for each keyword. | Add actual worked examples, relevant downloadable or browsable questions, syllabus points, topic-specific guidance and honest coverage. Merge or temporarily noindex pages that offer no independent value until improved. |
| F07 | On-page title | Warning | Confirmed | The past-papers index repeats the brand in its title. | Live /past-papers title: Free Edexcel Past Papers – IGCSE & A Level by Year / GradeMax / GradeMax. src/app/past-papers/page.tsx:8 includes the brand and root title template at src/app/layout.tsx:130 adds it again. | Remove the explicit suffix from the child title, or use an absolute title deliberately. Apply a single brand suffix consistently. |
| F08 | Sitemap coverage / tool policy | Warning | Confirmed | The sitemap exclusion reason for the worksheet generator is obsolete. | src/app/sitemap.ts:58 says /generate is auth-gated with 307 to /login and excludes it. Live /generate returns 200, index/follow, with a self-canonical and public worksheet controls. /edexcel-worksheets is separately indexable and included. | Decide the intended relationship: retain a distinct public tool and add its canonical URL to the sitemap, or deliberately consolidate overlapping intent into one route. Update the obsolete comment. |
| F09 | Content authority / trust | Warning | Likely | The About page offers few verifiable people or editorial-quality signals. | src/app/about/page.tsx describes founders only as students, with generic mission text and no named creators, qualifications, resource checking process or update policy. | Add truthful team/maintainer details, exam-board independence, sourcing and checking process, correction/reporting route, and resource update policy. Avoid invented credentials. |
| F10 | Sitemap freshness | Warning | Likely | Paper sitemap lastmod is based on insertion time rather than verified content update time. | src/app/sitemap.ts:167 selects created_at; :203 and :221 derive lastModified from it. The sitemap has 14,606 lastmod values. Existing file replacement or correction after insertion would not be represented unless its creation timestamp is also changed. | Track substantive page/PDF updated_at, aggregate the latest relevant change for year/session pages, and use that for lastmod; omit lastmod where trustworthy update time is unavailable. |
| F11 | SEO monitoring | Info | Confirmed | Package SEO monitoring commands reference missing scripts. | package.json declares index:pages, gsc:monitor and check:errors pointing to scripts/google-indexing-api.ts, scripts/gsc-monitoring.ts and scripts/fix-google-errors.ts. These files are absent in this checkout. | Restore useful Search Console read-only monitoring or remove stale package commands. Ordinary study pages are not eligible for Google Indexing API; use sitemap submission and Search Console instead. |
| F12 | AI discovery information | Info | Confirmed | llms.txt links use the redirecting non-www host and describe a narrower/staler catalog. | public/llms.txt has fourteen links using https://grademax.me and describes only Edexcel, years through 2025. Live site includes Cambridge hubs and 2026 entries; https://grademax.me redirects to https://www.grademax.me/. | Use canonical www URLs and accurately summarize current boards, years and feature access. No need to create llms-full.txt solely to satisfy a checker. |

### Detailed findings and impact

#### F01: Nine sitemap URLs incorrectly canonicalize to the homepage.

- Severity: Warning; confidence: Confirmed; priority: P1 - high impact, low effort.
- Evidence: Live crawl.json: /contact, /privacy, /terms, /store, /store/mathematics-b, /store/further-pure-mathematics, /store/m1-yearwise, /store/s1-yearwise and /store/p4-yearwise all return 200 with rel=canonical https://www.grademax.me. Root src/app/layout.tsx:209 supplies a homepage canonical; these routes omit an override. /improvements has the same issue outside the sitemap.
- Impact: Conflicts with sitemap inclusion and asks Google to consolidate distinct pages into the homepage. Whether Google accepted this signal is unknown without URL Inspection.
- Fix: Give every intended indexable route a self-referencing canonical, including generateMetadata for each product. Keep homepage canonical on the homepage. Verify emitted HTML across the entire route inventory.

#### F02: Subject and topic practice links do not initialize the requested worksheet filters.

- Severity: Warning; confidence: Confirmed; priority: P1 - high impact, medium effort.
- Evidence: src/app/subjects/[level]/[slug]/[topic]/page.tsx:166 and :230 link to /generate?subject={slug}&level={level}&topic={code}; src/app/generate/page.tsx:11 accepts no searchParams; src/components/generate/WorksheetGenerator.tsx:115 initializes selectedSubject to the first subject and has no query parameter reader. Live query URLs return 200 and canonicalize to /generate.
- Impact: A student arriving on a specific topic page is sent to a generic generator rather than the advertised practice selection. This is a confirmed source behavior defect; browser hydration was not separately tested.
- Fix: Resolve subject slugs and topic codes into supported database IDs on the server; pass validated initial selection into the generator. Show a useful fallback when the request is unsupported.

#### F03: Topic pages promote worksheet generation for unsupported subjects.

- Severity: Warning; confidence: Confirmed; priority: P1 - high impact, low/medium effort.
- Evidence: Live /subjects/ial/ial-english-literature/unit-1 advertises a custom worksheet for English Literature. Live /generate subject options contain Physics, Maths A/B, Chemistry, Biology, Human Biology, Further Pure Maths and selected IAL mathematics units; English Literature is absent. The shared topic template promotes the generator without checking tool coverage.
- Impact: Public landing pages promise functionality visitors cannot use for that subject.
- Fix: Gate worksheet CTAs against actual tool coverage. For unsupported subjects, link to their available past papers and remove unfulfilled generation promises.

#### F04: The five live book detail pages have no Product structured data.

- Severity: Warning; confidence: Confirmed; priority: P2 - medium/high impact, medium effort.
- Evidence: All five store product responses in crawl.json contain only the shared root JSON-LD graph. src/app/store/[slug]/page.tsx provides title/description but no Product/Offer JSON-LD.
- Impact: Misses an opportunity to communicate book name, image, BDT price, availability and shipping details for eligible product search appearances. Rich results are not guaranteed.
- Fix: After canonical fixes, add JSON-LD Product with real Offer priceCurrency BDT, price, URL, availability, seller and applicable shipping/returns details. Use only real identifiers and reviews; validate with Google Rich Results Test.

#### F05: Homepage-specific schema and artificial modification dates are emitted across unrelated routes.

- Severity: Warning; confidence: Confirmed; priority: P2 - medium impact, low/medium effort.
- Evidence: src/app/layout.tsx:62-73 defines a homepage WebPage with @id /#webpage, homepage URL/name and dateModified=new Date().toISOString(); the same root graph appears on product and paper pages. Captured home dateModified is 2026-10-13T06:43:29.322Z; a product response has 2026-10-15T04:13:41.284Z for that same homepage entity.
- Impact: Adds irrelevant page identity and unreliable freshness claims to unrelated documents. No structured-data penalty is established.
- Fix: Keep Organization/WebSite shared; emit homepage WebPage and homepage ItemList only on the homepage. Emit route-specific page entities with actual content update timestamps, or omit optional modification dates.

#### F06: Some topic landing pages provide little useful topic-specific content beyond repeated prompts.

- Severity: Warning; confidence: Likely; priority: P2 - high potential impact, higher effort.
- Evidence: Live English Literature Unit 1 page has 148 main-content words and generic text such as Unit 1 examination content; the keyword card repeats Practice ... questions. Physics forces-and-motion has 169 main-content words, mostly navigation and calls to action. Source topic template repeats the same sentence for each keyword.
- Impact: These pages may satisfy topic-practice intent poorly, especially where the advertised tool is unsupported. Low word count alone is not an indexing or ranking violation.
- Fix: Add actual worked examples, relevant downloadable or browsable questions, syllabus points, topic-specific guidance and honest coverage. Merge or temporarily noindex pages that offer no independent value until improved.

#### F07: The past-papers index repeats the brand in its title.

- Severity: Warning; confidence: Confirmed; priority: P2 - quick win, low effort.
- Evidence: Live /past-papers title: Free Edexcel Past Papers – IGCSE & A Level by Year | GradeMax | GradeMax. src/app/past-papers/page.tsx:8 includes the brand and root title template at src/app/layout.tsx:130 adds it again.
- Impact: Wastes title space and makes the search title less concise.
- Fix: Remove the explicit suffix from the child title, or use an absolute title deliberately. Apply a single brand suffix consistently.

#### F08: The sitemap exclusion reason for the worksheet generator is obsolete.

- Severity: Warning; confidence: Confirmed; priority: P2 - medium impact, low effort.
- Evidence: src/app/sitemap.ts:58 says /generate is auth-gated with 307 to /login and excludes it. Live /generate returns 200, index/follow, with a self-canonical and public worksheet controls. /edexcel-worksheets is separately indexable and included.
- Impact: The sitemap policy no longer reflects actual public behavior. Omission alone does not prevent indexing because internal links exist.
- Fix: Decide the intended relationship: retain a distinct public tool and add its canonical URL to the sitemap, or deliberately consolidate overlapping intent into one route. Update the obsolete comment.

#### F09: The About page offers few verifiable people or editorial-quality signals.

- Severity: Warning; confidence: Likely; priority: P3 - strategic, medium effort.
- Evidence: src/app/about/page.tsx describes founders only as students, with generic mission text and no named creators, qualifications, resource checking process or update policy.
- Impact: Visitors have little evidence of who checks classifications and study materials. The audit establishes missing visible detail, not a Google trust score.
- Fix: Add truthful team/maintainer details, exam-board independence, sourcing and checking process, correction/reporting route, and resource update policy. Avoid invented credentials.

#### F10: Paper sitemap lastmod is based on insertion time rather than verified content update time.

- Severity: Warning; confidence: Likely; priority: P3 - maintenance, medium effort.
- Evidence: src/app/sitemap.ts:167 selects created_at; :203 and :221 derive lastModified from it. The sitemap has 14,606 lastmod values. Existing file replacement or correction after insertion would not be represented unless its creation timestamp is also changed.
- Impact: Potentially fails to signal real corrections and replaced PDFs. Actual timestamp staleness is not confirmed without database update history.
- Fix: Track substantive page/PDF updated_at, aggregate the latest relevant change for year/session pages, and use that for lastmod; omit lastmod where trustworthy update time is unavailable.

#### F11: Package SEO monitoring commands reference missing scripts.

- Severity: Info; confidence: Confirmed; priority: P3 - maintenance, low/medium effort.
- Evidence: package.json declares index:pages, gsc:monitor and check:errors pointing to scripts/google-indexing-api.ts, scripts/gsc-monitoring.ts and scripts/fix-google-errors.ts. These files are absent in this checkout.
- Impact: The advertised local monitoring commands cannot currently run. This does not establish a live indexing problem.
- Fix: Restore useful Search Console read-only monitoring or remove stale package commands. Ordinary study pages are not eligible for Google Indexing API; use sitemap submission and Search Console instead.

#### F12: llms.txt links use the redirecting non-www host and describe a narrower/staler catalog.

- Severity: Info; confidence: Confirmed; priority: P3 - optional maintenance, low effort.
- Evidence: public/llms.txt has fourteen links using https://grademax.me and describes only Edexcel, years through 2025. Live site includes Cambridge hubs and 2026 entries; https://grademax.me redirects to https://www.grademax.me/.
- Impact: Minor information consistency and redirect overhead. llms.txt is optional and is not a Google indexing requirement.
- Fix: Use canonical www URLs and accurately summarize current boards, years and feature access. No need to create llms-full.txt solely to satisfy a checker.

### What is working

- robots.txt permits public crawling, excludes API/admin/debug paths, and advertises the correct sitemap. Consecutive user-agent lines share one rules group; the checker incorrectly reports zero rules for some AI bots in that group. There is no confirmed AI-bot rule defect.
- Non-www and HTTP homepage requests reach the canonical HTTPS www homepage.
- Tested nonexistent URLs return 404 and noindex; the existing /login?next= variant is noindex. /lectures redirects to sign-in and is absent from the sitemap.
- Main navigation, subject/year/session hierarchy, breadcrumbs and crawlable links exist. Paper samples have individual canonical URLs and resource markup.
- HTTPS, HSTS, CSP, X-Frame-Options, nosniff, Referrer-Policy and Permissions-Policy are present. A header presence score is not a security assessment.
- Homepage Open Graph and large-image Twitter card essentials exist. Optional twitter:site/creator absence is not a defect; do not invent account handles.
- All 10 image elements in the 95 sitemap-page sample had an alt attribute. Image byte sizes, visual suitability and layout stability were not tested.
- Shared JSON-LD parses as JSON. The root uses @graph, whose nodes have @type. The bundled schema checker warning that the root lacks @type is a false positive, not a JSON-LD syntax failure.
- llms.txt exists. It is optional; absence of llms-full.txt is not a Google SEO fault.

### Additional opportunities and caveats

- Some /qp and /subjects pages use identical titles (for example WMA11 and WMA12). Similar search intent may warrant clearer differentiation, but title reuse alone does not prove duplicate content, cannibalization or ranking loss. Inspect Search Console query/page data before merging useful pages.
- Homepage has two h1 elements splitting one slogan. Combining them into one semantic heading would improve clarity; this is not a demonstrated indexing blocker. Keep the visual styling and make the page topic clear near the headline.
- Some text/metadata describes coverage through 2025 while there are 2026 routes. Reconcile claims with actual available sessions per board/subject; do not mechanically claim 2026 coverage everywhere.
- Topic content recommendations are about fulfilling user intent, not meeting an arbitrary word-count minimum. Similarly, long titles/descriptions are not automatically invalid because of a fixed character count. [Google title guidance](https://developers.google.com/search/docs/appearance/title-link).
- FAQ rich results are restricted to eligible authoritative government/health sites. No FAQ rich-result strategy is recommended here, and unused valid FAQ markup is not automatically harmful. [Google FAQ guidance](https://developers.google.com/search/blog/2023/08/howto-faq-changes).
- Product schema should describe real visible offers. [Google product structured data](https://developers.google.com/search/docs/appearance/structured-data/product).
- Canonicals are signals, not guarantees that Google has removed these pages. A sitemap should agree with canonical annotations. [Google canonical guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).
- Ordinary past-paper pages cannot use Google's job/livestream-only Indexing API. [Google Indexing API eligibility](https://developers.google.com/search/apis/indexing-api/v3/quickstart).

## C. Prioritized action plan

1. **P1, quick win:** Correct the nine sitemap canonical mismatches and audit other routes inheriting homepage metadata. Validate rendered tags before any deployment.
2. **P1:** Fix topic/subject deep-link initialization and gate practice CTAs by supported subject/topic availability. Verify at least one supported physics topic, one supported maths topic and one unsupported subject.
3. **P2, quick win:** Remove the repeated brand from /past-papers and decide /generate sitemap/indexing policy based on its actual public behavior.
4. **P2:** Add product-specific metadata and truthful Product/Offer JSON-LD after canonical fixes. Separate global identity from route-specific page schema.
5. **P2, strategic:** Improve the weakest topic pages with genuinely useful examples and available resources; avoid expanding the template footprint before fixing capability gaps.
6. **P3:** Add truthful team/source-quality detail; improve lastmod tracking; repair monitoring commands and llms.txt consistency.
7. **Verification:** After deploying reviewed fixes, inspect representative URLs in Search Console, compare declared and Google-selected canonical, check sitemap processing, and measure mobile Core Web Vitals.

## D. Unknowns and follow-ups

- **Private Google Search Console was not accessed.** Sitemap submission status, Google's last read, discovered versus indexed totals, page exclusions, selected canonicals, query impressions/clicks and manual actions are unknown. Public sitemap success does not prove submission or indexing.
- The remaining sitemap URLs and PDF/download destinations have not all been checked. Current sample findings must not be extrapolated into a full-site broken-link percentage.
- No mobile visual/browser interaction test was completed. Tool parameter behavior is established from code; hydrated UI behavior and console errors remain a follow-up.
- No CrUX/field or Lighthouse LCP, INP or CLS values are available. Measure before making performance claims. Check key page templates, not only the homepage.
- No backlink/competitor or ranking/traffic analysis was performed. No penalty or traffic-loss claim is made.
- Product rich-result eligibility requires Google validation against final live markup and policies. Product image quality, shipping/returns detail and availability must match the actual shop.

### Environment limitations and evidence reconciliation

- The web reader could not open sitemap.xml/robots.txt; direct HTTPS requests succeeded. Those reader failures are not site defects.
- Google PageSpeed API returned rate limiting, including on the bounded retry. Performance remains unscored.
- The shallow internal-link checker labels pages with one incoming link as potential orphans. Its 1,061 labels are not confirmed orphan pages; the crawl is incomplete and those pages already have links.
- Baseline runner initially hit Windows console encoding output errors; saved check outputs were retained and the runner was repeated using UTF-8. No application fault is inferred.
- Bundled source reference freshness was not treated as authoritative. Current Google primary documentation was checked for sitemap, canonical, title, product and Indexing API recommendations.
- The finding verifier deduplicated the findings; it is not independent Google validation. Manual reconciliation suppressed checker false positives described above.

## Artifacts

- FULL-AUDIT-REPORT.md - this report.
- ACTION-PLAN.md - implementation order and acceptance checks.
- output/seo-audit-2026-10-15/VALIDATION-REPORT.md - sitemap summary.
- output/seo-audit-2026-10-15/sitemap.xml and sitemap-summary.json - captured sitemap evidence.
- output/seo-audit-2026-10-15/crawl.json - per-URL status, redirects, metadata, headings, schema, links and headers.
- output/seo-audit-2026-10-15/verified-findings.json - final findings with evidence/confidence labels.
- Other files in that directory contain script outputs and reproducible collection code. No HTML dashboard was generated.
