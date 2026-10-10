-- Migration 21: Store — catalogue, checkout, manual payments, fulfilment
-- =============================================================================
-- Sells the printed workbooks and the booklets (Mathematics B Part 1/Part 2,
-- Further Pure Mathematics, IGCSE Accounting formats) as either a PRINT copy
-- that ships or a DIGITAL PDF that unlocks once payment is verified.
--
-- WHY MONEY IS AN INTEGER
-- -----------------------
-- Prices are whole Taka. FLOAT money is a classic rounding bug and NUMERIC
-- invites accidental fractional pricing, so every amount here is INTEGER BDT.
--
-- WHY ORDER ITEMS SNAPSHOT THE PRICE
-- ----------------------------------
-- `store_order_items` copies the title, variant kind and unit price at the
-- moment of ordering. Editing a price in the admin portal must never silently
-- rewrite what a past buyer agreed to pay — an order is a historical record,
-- not a live join against the catalogue.
--
-- WHY THE TRANSACTION-ID UNIQUE INDEX IS PARTIAL
-- ----------------------------------------------
-- bKash/Nagad payments are verified by hand, so a buyer may mistype a TrxID,
-- get rejected, and resubmit. A plain UNIQUE(method, transaction_id) would burn
-- the real TrxID forever the first time it was typed against the wrong order.
-- The index therefore ignores rejected rows. A second partial index keeps one
-- order from carrying two live claims at once.
--
-- WHY RLS DENIES EVERYONE
-- -----------------------
-- Migration 11 established that the anon PostgREST surface is directly
-- reachable from the internet. `store_variants.r2_key` points at the paid PDF
-- and `store_orders` holds customer names, phones and addresses, so NO anon or
-- authenticated role may read any table here. The app reads them server-side
-- with the service key only, and the public catalogue is served through
-- /api/store/products, which selects an explicit, safe column list.
--
-- Everything here is idempotent and safe to re-run.
-- =============================================================================

BEGIN;

-- ── Reference: Bangladesh districts ──────────────────────────────────────────
-- A lookup table, not free text. "Where are orders coming from" is only
-- answerable if Dhaka, dhaka and DHK are the same row. `is_metro` drives the
-- inside/outside-Dhaka delivery charge.
CREATE TABLE IF NOT EXISTS store_districts (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  division   TEXT NOT NULL,
  is_metro   BOOLEAN NOT NULL DEFAULT FALSE,
  is_active  BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 100
);

INSERT INTO store_districts (name, division, is_metro, sort_order) VALUES
  ('Dhaka','Dhaka',TRUE,1),('Gazipur','Dhaka',FALSE,2),('Narayanganj','Dhaka',FALSE,3),
  ('Chattogram','Chattogram',FALSE,4),('Sylhet','Sylhet',FALSE,5),('Rajshahi','Rajshahi',FALSE,6),
  ('Khulna','Khulna',FALSE,7),('Barishal','Barishal',FALSE,8),('Rangpur','Rangpur',FALSE,9),
  ('Mymensingh','Mymensingh',FALSE,10),
  ('Bagerhat','Khulna',FALSE,100),('Bandarban','Chattogram',FALSE,100),('Barguna','Barishal',FALSE,100),
  ('Bhola','Barishal',FALSE,100),('Bogura','Rajshahi',FALSE,100),('Brahmanbaria','Chattogram',FALSE,100),
  ('Chandpur','Chattogram',FALSE,100),('Chapainawabganj','Rajshahi',FALSE,100),('Chuadanga','Khulna',FALSE,100),
  ('Coxs Bazar','Chattogram',FALSE,100),('Cumilla','Chattogram',FALSE,100),('Dinajpur','Rangpur',FALSE,100),
  ('Faridpur','Dhaka',FALSE,100),('Feni','Chattogram',FALSE,100),('Gaibandha','Rangpur',FALSE,100),
  ('Gopalganj','Dhaka',FALSE,100),('Habiganj','Sylhet',FALSE,100),('Jamalpur','Mymensingh',FALSE,100),
  ('Jashore','Khulna',FALSE,100),('Jhalokati','Barishal',FALSE,100),('Jhenaidah','Khulna',FALSE,100),
  ('Joypurhat','Rajshahi',FALSE,100),('Khagrachhari','Chattogram',FALSE,100),('Kishoreganj','Dhaka',FALSE,100),
  ('Kurigram','Rangpur',FALSE,100),('Kushtia','Khulna',FALSE,100),('Lakshmipur','Chattogram',FALSE,100),
  ('Lalmonirhat','Rangpur',FALSE,100),('Madaripur','Dhaka',FALSE,100),('Magura','Khulna',FALSE,100),
  ('Manikganj','Dhaka',FALSE,100),('Meherpur','Khulna',FALSE,100),('Moulvibazar','Sylhet',FALSE,100),
  ('Munshiganj','Dhaka',FALSE,100),('Naogaon','Rajshahi',FALSE,100),('Narail','Khulna',FALSE,100),
  ('Narsingdi','Dhaka',FALSE,100),('Natore','Rajshahi',FALSE,100),('Netrokona','Mymensingh',FALSE,100),
  ('Nilphamari','Rangpur',FALSE,100),('Noakhali','Chattogram',FALSE,100),('Pabna','Rajshahi',FALSE,100),
  ('Panchagarh','Rangpur',FALSE,100),('Patuakhali','Barishal',FALSE,100),('Pirojpur','Barishal',FALSE,100),
  ('Rajbari','Dhaka',FALSE,100),('Rangamati','Chattogram',FALSE,100),('Satkhira','Khulna',FALSE,100),
  ('Shariatpur','Dhaka',FALSE,100),('Sherpur','Mymensingh',FALSE,100),('Sirajganj','Rajshahi',FALSE,100),
  ('Sunamganj','Sylhet',FALSE,100),('Tangail','Dhaka',FALSE,100),('Thakurgaon','Rangpur',FALSE,100)
ON CONFLICT (name) DO NOTHING;

-- ── Settings: no hardcoded prices or wallet numbers in source ────────────────
CREATE TABLE IF NOT EXISTS store_settings (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  description TEXT,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO store_settings (key, value, description) VALUES
  ('delivery_bdt_metro','70','Delivery charge inside Dhaka city, in Taka'),
  ('delivery_bdt_outside','130','Delivery charge outside Dhaka, in Taka'),
  ('free_delivery_over_bdt','0','Order subtotal above which delivery is free. 0 disables it.'),
  ('bkash_number','','bKash number buyers send money to'),
  ('nagad_number','','Nagad number buyers send money to'),
  ('payment_instructions','Send the exact total using Send Money, then enter the Transaction ID below.','Shown on the payment step'),
  ('verification_sla_hours','12','Promised manual verification window, shown to the buyer'),
  ('store_enabled','true','Master switch for the public store'),
  ('max_units_per_order','10','Per-line quantity cap — an abuse guard on an unauthenticated endpoint')
ON CONFLICT (key) DO NOTHING;

-- ── Catalogue ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS store_products (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            TEXT NOT NULL UNIQUE,
  title           TEXT NOT NULL,
  subtitle        TEXT,
  description     TEXT,
  subject_code    TEXT,
  spec_summary    TEXT,
  cover_image_url TEXT,
  preview_r2_key  TEXT,
  preview_pages   INTEGER,
  is_active       BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order      INTEGER NOT NULL DEFAULT 100,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One product, two ways to buy it.
CREATE TABLE IF NOT EXISTS store_variants (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id     UUID NOT NULL REFERENCES store_products(id) ON DELETE CASCADE,
  kind           TEXT NOT NULL CHECK (kind IN ('print','digital')),
  label          TEXT NOT NULL,
  price_bdt      INTEGER NOT NULL CHECK (price_bdt >= 0),
  compare_at_bdt INTEGER CHECK (compare_at_bdt IS NULL OR compare_at_bdt >= 0),
  stock_qty      INTEGER CHECK (stock_qty IS NULL OR stock_qty >= 0),
  r2_key         TEXT,
  file_bytes     BIGINT,
  page_count     INTEGER,
  weight_grams   INTEGER,
  allow_cod      BOOLEAN NOT NULL DEFAULT TRUE,
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (product_id, kind),
  -- Cash on delivery makes no sense for a download, and print stock must be
  -- finite. Encoded as a row constraint so the rule cannot be forgotten in code.
  CONSTRAINT store_variants_digital_shape CHECK (
    (kind = 'digital' AND stock_qty IS NULL AND allow_cod = FALSE) OR
    (kind = 'print'   AND stock_qty IS NOT NULL)
  )
);
CREATE INDEX IF NOT EXISTS store_variants_product ON store_variants (product_id);

-- A digital purchase is usually MORE than one PDF: every workbook ships with a
-- separate mark-scheme volume, and the two are far too large to merge. So the
-- deliverable is a list of files, not a single key. `store_variants.r2_key` is
-- left for the trivial one-file case; anything here takes precedence.
CREATE TABLE IF NOT EXISTS store_variant_files (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  variant_id  UUID NOT NULL REFERENCES store_variants(id) ON DELETE CASCADE,
  label       TEXT NOT NULL,          -- "Questions", "Mark schemes"
  r2_key      TEXT NOT NULL,          -- PRIVATE bucket (R2_STORE_BUCKET)
  file_name   TEXT NOT NULL,          -- what the buyer's browser saves it as
  file_bytes  BIGINT,
  page_count  INTEGER,
  sort_order  INTEGER NOT NULL DEFAULT 1,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (variant_id, r2_key)
);
CREATE INDEX IF NOT EXISTS store_variant_files_variant ON store_variant_files (variant_id, sort_order);

-- ── Orders ───────────────────────────────────────────────────────────────────
-- A human order number that is NOT guessable. A bare sequence would let anyone
-- walk GM-000124 -> GM-000125 against the guest lookup, so a short random
-- suffix is appended. The sequence keeps it collision-free under concurrency;
-- SELECT max()+1 would not.
CREATE SEQUENCE IF NOT EXISTS store_order_number_seq START 1001;

CREATE TABLE IF NOT EXISTS store_orders (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_number     TEXT NOT NULL UNIQUE,
  user_id          UUID REFERENCES auth.users(id) ON DELETE SET NULL,

  customer_name    TEXT NOT NULL,
  customer_phone   TEXT NOT NULL,              -- normalised to 01XXXXXXXXX
  customer_email   TEXT,

  -- Delivery. NULL for a digital-only order, which ships nothing.
  district_id      INTEGER REFERENCES store_districts(id) ON DELETE RESTRICT,
  city             TEXT,
  area             TEXT,
  address_line     TEXT,
  postcode         TEXT,
  notes            TEXT,

  -- Derived once at creation, then indexed. Answers "does this ship?" and
  -- "does this unlock?" without joining the items on every listing query.
  has_print        BOOLEAN NOT NULL DEFAULT FALSE,
  has_digital      BOOLEAN NOT NULL DEFAULT FALSE,

  subtotal_bdt     INTEGER NOT NULL CHECK (subtotal_bdt >= 0),
  delivery_bdt     INTEGER NOT NULL DEFAULT 0 CHECK (delivery_bdt >= 0),
  discount_bdt     INTEGER NOT NULL DEFAULT 0 CHECK (discount_bdt >= 0),
  total_bdt        INTEGER NOT NULL CHECK (total_bdt >= 0),

  payment_method   TEXT NOT NULL CHECK (payment_method IN ('bkash','nagad','cod')),
  payment_status   TEXT NOT NULL DEFAULT 'awaiting_payment'
                     CHECK (payment_status IN ('awaiting_payment','submitted','verified',
                                               'rejected','cod_pending','paid_on_delivery','refunded')),
  order_status     TEXT NOT NULL DEFAULT 'pending'
                     CHECK (order_status IN ('pending','confirmed','packed','shipped',
                                             'delivered','cancelled')),

  courier_name     TEXT,
  tracking_code    TEXT,

  -- Where the buyer came from. Captured at checkout for attribution only.
  source_path      TEXT,
  source_referrer  TEXT,

  -- Reserved stock is released when this passes with the order still unpaid.
  reserved_until   TIMESTAMPTZ,
  admin_note       TEXT,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- The arithmetic must hold. A mismatch here means a pricing bug, and it
  -- should fail loudly at write time rather than quietly bill the wrong amount.
  CONSTRAINT store_orders_total_adds_up
    CHECK (total_bdt = subtotal_bdt + delivery_bdt - discount_bdt),
  -- A shipped order needs somewhere to ship to.
  CONSTRAINT store_orders_print_needs_address
    CHECK (has_print = FALSE OR (district_id IS NOT NULL AND address_line IS NOT NULL)),
  -- COD cannot collect cash for a download.
  CONSTRAINT store_orders_cod_is_print_only
    CHECK (payment_method <> 'cod' OR has_digital = FALSE)
);

CREATE INDEX IF NOT EXISTS store_orders_created    ON store_orders (created_at DESC);
CREATE INDEX IF NOT EXISTS store_orders_district   ON store_orders (district_id);
CREATE INDEX IF NOT EXISTS store_orders_pay_status ON store_orders (payment_status);
CREATE INDEX IF NOT EXISTS store_orders_status     ON store_orders (order_status);
CREATE INDEX IF NOT EXISTS store_orders_user       ON store_orders (user_id);
CREATE INDEX IF NOT EXISTS store_orders_phone      ON store_orders (customer_phone);

-- Line items. RESTRICT, never CASCADE: deleting a catalogue row must not
-- silently erase what somebody already paid for.
CREATE TABLE IF NOT EXISTS store_order_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id        UUID NOT NULL REFERENCES store_orders(id) ON DELETE CASCADE,
  variant_id      UUID NOT NULL REFERENCES store_variants(id) ON DELETE RESTRICT,
  product_title   TEXT NOT NULL,     -- snapshot
  variant_label   TEXT NOT NULL,     -- snapshot
  variant_kind    TEXT NOT NULL CHECK (variant_kind IN ('print','digital')),
  unit_price_bdt  INTEGER NOT NULL CHECK (unit_price_bdt >= 0),
  quantity        INTEGER NOT NULL CHECK (quantity > 0),
  line_total_bdt  INTEGER NOT NULL CHECK (line_total_bdt >= 0),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT store_order_items_line_adds_up
    CHECK (line_total_bdt = unit_price_bdt * quantity)
);
CREATE INDEX IF NOT EXISTS store_order_items_order ON store_order_items (order_id);

-- ── Manual payment claims ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS store_payments (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id         UUID NOT NULL REFERENCES store_orders(id) ON DELETE CASCADE,
  method           TEXT NOT NULL CHECK (method IN ('bkash','nagad','cod')),
  sender_msisdn    TEXT,
  transaction_id   TEXT,
  -- Normalised form the uniqueness rule actually compares. bKash TrxIDs are
  -- case-insensitive alphanumeric and buyers paste them with stray spaces;
  -- without this, "  ab12cd  " and "AB12CD" would both be accepted as new.
  transaction_key  TEXT GENERATED ALWAYS AS (upper(regexp_replace(coalesce(transaction_id,''), '\s', '', 'g'))) STORED,
  amount_bdt       INTEGER CHECK (amount_bdt IS NULL OR amount_bdt >= 0),
  status           TEXT NOT NULL DEFAULT 'submitted'
                     CHECK (status IN ('submitted','verified','rejected','refunded')),
  verified_by      UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  verified_at      TIMESTAMPTZ,
  rejection_reason TEXT,
  admin_note       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS store_payments_order ON store_payments (order_id);

-- A live TrxID belongs to exactly one order. Rejected rows are excluded so a
-- buyer whose first attempt was rejected can resubmit the same real TrxID.
CREATE UNIQUE INDEX IF NOT EXISTS store_payments_live_trx
  ON store_payments (method, transaction_key)
  WHERE status IN ('submitted','verified') AND transaction_key <> '';

-- One live claim per order, so a double-submit cannot create two rows for an
-- admin to verify twice.
CREATE UNIQUE INDEX IF NOT EXISTS store_payments_one_live_per_order
  ON store_payments (order_id)
  WHERE status IN ('submitted','verified');

-- ── Status audit trail ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS store_order_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    UUID NOT NULL REFERENCES store_orders(id) ON DELETE CASCADE,
  field       TEXT NOT NULL,
  from_value  TEXT,
  to_value    TEXT,
  actor_id    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_email TEXT,
  note        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS store_order_events_order ON store_order_events (order_id, created_at DESC);

-- ── Digital entitlements ─────────────────────────────────────────────────────
-- The token is stored as a SHA-256 hash, like a password. The plaintext exists
-- only in the link handed to the buyer, so a database leak does not hand over
-- every paid PDF.
CREATE TABLE IF NOT EXISTS store_downloads (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_item_id  UUID NOT NULL REFERENCES store_order_items(id) ON DELETE CASCADE,
  order_id       UUID NOT NULL REFERENCES store_orders(id) ON DELETE CASCADE,
  token_hash     TEXT NOT NULL UNIQUE,
  expires_at     TIMESTAMPTZ NOT NULL,
  max_downloads  INTEGER NOT NULL DEFAULT 10 CHECK (max_downloads > 0),
  download_count INTEGER NOT NULL DEFAULT 0 CHECK (download_count >= 0),
  last_ip        TEXT,
  last_used_at   TIMESTAMPTZ,
  revoked_at     TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (order_item_id)
);
CREATE INDEX IF NOT EXISTS store_downloads_order ON store_downloads (order_id);

-- ── Rate limiting ────────────────────────────────────────────────────────────
-- Postgres-backed on purpose. Vercel runs many short-lived serverless
-- instances, so an in-process counter resets constantly and protects nothing.
CREATE TABLE IF NOT EXISTS store_rate_limits (
  bucket      TEXT PRIMARY KEY,
  hits        INTEGER NOT NULL DEFAULT 0,
  window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  blocked_until TIMESTAMPTZ
);

-- Atomic fixed-window counter. Returns TRUE when the caller is allowed.
-- Doing this in SQL keeps read-modify-write in one statement, so two
-- simultaneous requests cannot both observe the same pre-increment count.
CREATE OR REPLACE FUNCTION store_rate_limit_hit(
  p_bucket TEXT, p_limit INTEGER, p_window_seconds INTEGER
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_hits INTEGER; v_start TIMESTAMPTZ;
BEGIN
  INSERT INTO store_rate_limits (bucket, hits, window_start)
  VALUES (p_bucket, 1, NOW())
  ON CONFLICT (bucket) DO UPDATE SET
    hits = CASE WHEN store_rate_limits.window_start < NOW() - make_interval(secs => p_window_seconds)
                THEN 1 ELSE store_rate_limits.hits + 1 END,
    window_start = CASE WHEN store_rate_limits.window_start < NOW() - make_interval(secs => p_window_seconds)
                THEN NOW() ELSE store_rate_limits.window_start END
  RETURNING hits, window_start INTO v_hits, v_start;
  RETURN v_hits <= p_limit;
END;
$$;

-- Hand out the next order sequence value. Exposed as an RPC because the app
-- talks to the database through PostgREST, which cannot call nextval directly.
CREATE OR REPLACE FUNCTION store_next_order_seq()
RETURNS INTEGER
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$ SELECT nextval('store_order_number_seq')::INTEGER $$;

-- ── Atomic stock reservation ─────────────────────────────────────────────────
-- Manual verification means an order can sit unpaid for hours, so stock is
-- reserved at creation and released on cancel/reject/expiry. The decrement is a
-- single guarded UPDATE: a read-then-write in TypeScript would let two buyers
-- both take the last copy.
CREATE OR REPLACE FUNCTION store_reserve_stock(p_variant UUID, p_qty INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_rows INTEGER;
BEGIN
  UPDATE store_variants
     SET stock_qty = stock_qty - p_qty, updated_at = NOW()
   WHERE id = p_variant
     AND kind = 'print'
     AND is_active = TRUE
     AND stock_qty >= p_qty;
  GET DIAGNOSTICS v_rows = ROW_COUNT;
  RETURN v_rows = 1;
END;
$$;

CREATE OR REPLACE FUNCTION store_release_stock(p_variant UUID, p_qty INTEGER)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE store_variants
     SET stock_qty = stock_qty + p_qty, updated_at = NOW()
   WHERE id = p_variant AND kind = 'print';
END;
$$;

-- Release every print reservation on an order, exactly once. Guarded on the
-- order's current state so a double-click cannot restock twice.
CREATE OR REPLACE FUNCTION store_release_order_stock(p_order UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE store_variants v
     SET stock_qty = v.stock_qty + i.quantity, updated_at = NOW()
    FROM store_order_items i
   WHERE i.order_id = p_order
     AND i.variant_id = v.id
     AND i.variant_kind = 'print'
     AND v.stock_qty IS NOT NULL;
END;
$$;

-- ── updated_at maintenance ───────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION store_touch_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['store_products','store_variants','store_orders'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_touch ON public.%I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_touch BEFORE UPDATE ON public.%I
                    FOR EACH ROW EXECUTE FUNCTION store_touch_updated_at()', t, t);
  END LOOP;
END $$;

-- ── RLS: service role only, on every table ───────────────────────────────────
-- No policy is created for anon or authenticated, so with RLS enabled and no
-- permissive policy, PostgREST returns nothing to them. The service key used by
-- the server bypasses RLS entirely, so the application is unaffected.
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['store_districts','store_settings','store_products','store_variants',
                           'store_variant_files','store_orders','store_order_items','store_payments',
                           'store_order_events','store_downloads','store_rate_limits'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS "Service role only" ON public.%I', t);
    EXECUTE format('CREATE POLICY "Service role only" ON public.%I FOR ALL
                    USING (auth.role() = ''service_role'')
                    WITH CHECK (auth.role() = ''service_role'')', t);
  END LOOP;
END $$;

-- The rate limiter and stock helpers are SECURITY DEFINER; make sure the
-- untrusted PostgREST roles cannot call them directly.
REVOKE ALL ON FUNCTION store_rate_limit_hit(TEXT, INTEGER, INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_next_order_seq() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_reserve_stock(UUID, INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_release_stock(UUID, INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_release_order_stock(UUID) FROM PUBLIC, anon, authenticated;

COMMIT;
