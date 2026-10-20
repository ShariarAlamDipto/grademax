# Store — setup and operation

The shop at `/store` sells the printed workbooks and booklets, **delivered
anywhere in Bangladesh**, with cash on delivery available. Buyers need an
account. Each title shows a **30-page preview** before anyone has to pay.

PDF downloads are built but **switched off**. Nothing about them is deleted —
flipping one setting brings them back.

The store ships **switched off** and every product ships **inactive**, so
nothing can be sold before the steps below are done.

---

## 1. Set the prices and stock

**Admin → Store → Products & prices.**

| Product | Price | Stock |
|---|---|---|
| Mathematics B — Part 1 | 600 | set it |
| Mathematics B — Part 2 | 600 | set it |
| Further Pure Mathematics | 800 | set it |
| IGCSE Accounting formats | **not set** | set it |

Everything seeds at **0 stock**, so nothing can be ordered until you say how
many copies you have. Accounting has no price yet and is blocked from going on
sale until you give it one.

## 2. Set your payment numbers and open the shop

Same screen, lower down.

1. Fill in **bkash number** and/or **nagad number**. The shop will not open
   without at least one, because buyers who choose to pay ahead need somewhere
   to send it. Cash on delivery works regardless.
2. Check **delivery bdt metro** (70, inside Dhaka) and **delivery bdt outside** (130).
3. Tick **On sale** on each product you want listed.
4. Tick **The shop is open**, then save.

No Cloudflare or R2 setup is needed. Previews are already uploaded, and because
no paid file is ever served, there is no private bucket to configure.

---

## 3. How an order flows

```
Buyer signs in (required)
  → adds to cart (browser only — no prices stored client side)
  → /api/store/cart reprices from the database
  → /api/store/checkout creates the order in ONE transaction:
      prices re-read, stock reserved, order + items written
  → cash on delivery:  order sits at "Cash on delivery" until the courier collects
  → bKash / Nagad:     buyer sends money, submits the Transaction ID,
                       YOU verify it in Admin → Store → Orders
  → Confirmed → Packed → Shipped → Delivered
```

### Rules the system enforces for you

- **An account is required**, checked inside the order function itself, so no
  code path can write an order that belongs to nobody.
- **Email and house number are required.** A Bangladeshi courier works from
  house and road number, area and a landmark, so those are captured separately
  *and* composed into one printable line for the delivery label.
- **Print stock is reserved when the order is placed**, not when it is paid, and
  released automatically if the order is cancelled. Two buyers cannot both take
  the last copy — this is tested with real concurrent connections.
- **Unpaid orders hold stock for 48 hours.** Run
  `SELECT store_expire_reservations();` periodically (a cron job) to release
  abandoned checkouts. Nothing breaks without it; copies just look sold.
- **At most 10 copies of one title per order**, and splitting it across two cart
  lines does not get round it.
- **Verifying twice does nothing twice.** Every transition is guarded.
- **A rejected Transaction ID can be resubmitted.** Rejecting sends the order
  back to "awaiting payment" with your reason.
- **Prices are never taken from the browser.** Totals are computed in the
  database from the catalogue, every time.

---

## 4. Where orders are coming from

**Admin → Store** shows, for a chosen period:

- revenue — verified and cash-on-delivery-collected only, never unchecked claims,
- how many payments are waiting on you and how many parcels are waiting to ship,
- **orders by district and by division**, which is the demand map,
- which page the buyer was on before they checked out,
- orders per day, bucketed in Dhaka time.

Districts come from a fixed list of all 64, so the breakdown never splits
"Dhaka" from "dhaka".

---

## 5. Previews

### M1, S1 and P4 yearwise question booklets

Published on the Books page (`/store`) on 13 October 2026, with 50 printed
copies initially available for each title:

| Product | Price (BDT) | Question-book pages | URL |
|---|---|---|---|
| Mechanics M1 | 550 | 341 | `/store/m1-yearwise` |
| Statistics S1 | 350 | 226 | `/store/s1-yearwise` |
| Pure Mathematics P4 | 350 | 212 | `/store/p4-yearwise` |

The cover and 30-page preview are derived from each finished GradeMax edition
in `data/workbook/{m1,s1,p4}_yearwise/final/`. These are printed question
booklets; the separate mark-scheme volumes are excluded from the product.
Full PDFs remain local, consistent with the print-only shop.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/publish_yearwise_store_products.py
.\.venv\Scripts\python.exe -X utf8 scripts/publish_yearwise_store_products.py --commit
```

The first command prepares and checks every cover and preview without writing
to the live catalogue. The second uploads the assets and creates or updates
only these three listings at their configured prices. Existing stock is
preserved; new listings start at zero. Use `--stock 50` only when intentionally
setting all three stock quantities to 50. Prices and stock can also be edited
in Admin → Store → Products & prices.

Three titles have a live 30-page preview, rendered in the browser from a
separate small PDF. The rest of the book is not in that file at all, so there is
nothing to unlock or bypass — it is 30 pages, not a locked 1,000-page document.

```bash
python scripts/publish_store_assets.py previews              # 30 pages
python scripts/publish_store_assets.py previews --pages 40   # longer samples
```

The builder refuses to publish a preview whose pages render blank. That guard
exists because of the problem below.

### ⚠ The Accounting booklet is broken and has no preview

`data/workbook/accounting/IGCSE_Accounting_Chapterwise_Formats.pdf` — the file
`scripts/rebuild_accounting_format_booklet.py` produced on 16 September —
**renders completely blank on every page**. Both MuPDF and pdf.js agree. Page 6
has a 4-byte empty content stream where the draft has 14,029 bytes:

| File | Pages | Page 6 content stream | Page 6 text |
|---|---|---|---|
| `IGCSE Acc fomat booklet draft (1) (1).pdf` | 157 | 14,029 bytes | 1,869 chars |
| `IGCSE_Accounting_Chapterwise_Formats.pdf` | 156 | **4 bytes** | **0 chars** |

The rebuild script is dropping the page content. Until it is fixed, Accounting
has no preview and should not be sold as a printed book either — the print
master is the same blank file. The draft still renders correctly, so the content
is not lost.

---

## 6. Turning PDF downloads back on

Everything is still there: `store_variant_files`, the download entitlements, the
signed-grant redemption route and the admin guards. To sell downloads:

1. Create a **private** R2 bucket (Cloudflare → R2 → Create bucket). Do **not**
   enable public access or an `r2.dev` domain on it. The existing
   `grademax-papers` bucket is world-readable through its `pub-*.r2.dev` domain
   — verified by fetching a paper anonymously and getting HTTP 200 — so a paid
   PDF placed there would simply be published.
2. Set `R2_STORE_BUCKET=grademax-store` (plus `R2_STORE_ACCESS_KEY_ID` /
   `R2_STORE_SECRET_ACCESS_KEY` if you make a separate token).
3. `python scripts/publish_store_assets.py files` — uploads each workbook and
   mark-scheme volume and registers them.
4. In `store_settings`, set `digital_sales_enabled` to `true`, and reactivate
   the digital variants in Admin → Store → Products & prices.

Note the digital variants are seeded at the **same price as print** (600/600/800),
because that is the figure that was given. A PDF has no printing or delivery
cost, so decide a real figure before switching them on.

---

## 7. Verifying it still works

```bash
node --env-file=.env.local scripts/verify-store-schema.mjs   # 33 checks
node --env-file=.env.local scripts/verify-store-orders.mjs   # 29 checks
# with a dev server running on :3949
E2E_BASE=http://localhost:3949 node --env-file=.env.local scripts/verify-store-e2e.mjs   # 42 checks
```

The e2e suite creates a throwaway product, walks a full purchase, then attacks
it — guest checkout, tampered prices, forged download links, stolen Transaction
IDs, orders looked up with the wrong phone number — and deletes everything
afterwards, restoring your settings.

`verify-store-orders.mjs` needs at least one real account to exist, because
orders now require an owner.

---

## 8. Things deliberately left out

- **No email or SMS.** `RESEND_API_KEY` is already configured, so an order
  confirmation and a "payment verified" message is a small addition — and worth
  doing, because a buyer's only feedback channel today is the tracking page.
- **No automated payment gateway.** The schema is ready for one.
- **No courier API.** `courier_name` and `tracking_code` are free text.
- **No refund button.** Cancelling an order restocks it and revokes any digital
  access, but there is no separate refund flow.
