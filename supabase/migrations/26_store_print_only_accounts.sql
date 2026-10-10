-- Migration 26: Store — printed books only, delivered in Bangladesh, account required
-- =============================================================================
-- Three changes, all driven by how the shop is actually going to run for now:
--
-- 1. DIGITAL SALES ARE SWITCHED OFF. The PDF variants stay in the database and
--    every line of code that serves them stays in place, but they are
--    deactivated and hidden behind `digital_sales_enabled`. Flipping that
--    setting back to 'true' and reactivating the variants is all it takes to
--    sell downloads later. Nothing is deleted.
--
--    A useful consequence: with no PDF being sold, no paid file is ever served,
--    so the private R2 bucket is no longer needed to open the shop.
--
-- 2. AN ACCOUNT IS REQUIRED. Guest checkout is refused inside the order
--    function itself, not just in the API route, so there is no path that can
--    write an order with no owner. The column stays nullable so the historical
--    guest orders a future change might allow are still representable.
--
-- 3. A FULLER DELIVERY ADDRESS. A Bangladeshi courier needs the house and road
--    number and, in practice, a landmark — "Road 5, Dhanmondi" alone loses
--    parcels. These are stored as separate columns AND composed into
--    `address_line`, which stays the one printable line for a delivery label.
-- =============================================================================

BEGIN;

-- ── 1. Structured address parts ──────────────────────────────────────────────
ALTER TABLE store_orders ADD COLUMN IF NOT EXISTS house_no  TEXT;
ALTER TABLE store_orders ADD COLUMN IF NOT EXISTS road_no   TEXT;
ALTER TABLE store_orders ADD COLUMN IF NOT EXISTS landmark  TEXT;
ALTER TABLE store_orders ADD COLUMN IF NOT EXISTS alt_phone TEXT;

-- ── 2. Settings ──────────────────────────────────────────────────────────────
INSERT INTO store_settings (key, value, description) VALUES
  ('digital_sales_enabled','false','Sell PDF downloads as well as printed copies. Off: only printed books are listed.'),
  ('require_account','true','Buyers must sign in to order. Off would allow guest checkout.')
ON CONFLICT (key) DO NOTHING;

-- Printed copies are the only thing on sale, so the shop is Bangladesh-only
-- delivery and cash on delivery is available on every order.
UPDATE store_settings SET value = 'false' WHERE key = 'digital_sales_enabled';
UPDATE store_settings SET value = 'true'  WHERE key = 'require_account';

-- ── 3. Hide the digital variants ─────────────────────────────────────────────
-- Deactivated, not deleted. store_variant_files, the download entitlements and
-- the grant machinery all remain intact and dormant.
UPDATE store_variants SET is_active = FALSE, updated_at = NOW() WHERE kind = 'digital';

-- ── 4. Order creation: account required, no digital, structured address ──────
CREATE OR REPLACE FUNCTION store_create_order(
  p_order_number    TEXT,
  p_user_id         UUID,
  p_name            TEXT,
  p_phone           TEXT,
  p_email           TEXT,
  p_district_id     INTEGER,
  p_city            TEXT,
  p_area            TEXT,
  p_address         TEXT,
  p_postcode        TEXT,
  p_notes           TEXT,
  p_payment_method  TEXT,
  p_source_path     TEXT,
  p_source_referrer TEXT,
  p_items           JSONB,
  p_house_no        TEXT DEFAULT NULL,
  p_road_no         TEXT DEFAULT NULL,
  p_landmark        TEXT DEFAULT NULL,
  p_alt_phone       TEXT DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_item          JSONB;
  v_variant       RECORD;
  v_qty           INTEGER;
  v_rows          INTEGER;
  v_subtotal      INTEGER := 0;
  v_has_print     BOOLEAN := FALSE;
  v_has_digital   BOOLEAN := FALSE;
  v_is_metro      BOOLEAN := FALSE;
  v_delivery      INTEGER := 0;
  v_free_over     INTEGER := 0;
  v_max_units     INTEGER := 10;
  v_digital_on    BOOLEAN := FALSE;
  v_need_account  BOOLEAN := TRUE;
  v_order_id      UUID;
  v_payment_status TEXT;
  v_reserve_hours INTEGER := 48;
  v_totals        JSONB;
BEGIN
  IF jsonb_array_length(p_items) = 0 THEN
    RAISE EXCEPTION 'cart is empty' USING ERRCODE = 'P0001';
  END IF;

  SELECT COALESCE((SELECT value::INTEGER FROM store_settings WHERE key = 'max_units_per_order'), 10)
    INTO v_max_units;
  SELECT COALESCE((SELECT lower(value) = 'true' FROM store_settings WHERE key = 'digital_sales_enabled'), FALSE)
    INTO v_digital_on;
  SELECT COALESCE((SELECT lower(value) = 'true' FROM store_settings WHERE key = 'require_account'), TRUE)
    INTO v_need_account;

  -- An account is required. Enforced here so no code path, present or future,
  -- can create an order that belongs to nobody.
  IF v_need_account AND p_user_id IS NULL THEN
    RAISE EXCEPTION 'an account is required to order' USING ERRCODE = 'P0008';
  END IF;

  IF p_email IS NULL OR btrim(p_email) = '' THEN
    RAISE EXCEPTION 'an email address is required' USING ERRCODE = 'P0009';
  END IF;

  -- Collapse duplicate lines before the per-line cap is applied.
  SELECT jsonb_agg(jsonb_build_object('variant_id', variant_id, 'quantity', qty))
    INTO v_totals
    FROM (
      SELECT (item->>'variant_id')::UUID AS variant_id,
             SUM((item->>'quantity')::INTEGER) AS qty
        FROM jsonb_array_elements(p_items) AS item
       GROUP BY 1
    ) collapsed;
  p_items := v_totals;

  FOR v_item IN SELECT * FROM jsonb_array_elements(p_items) LOOP
    v_qty := (v_item->>'quantity')::INTEGER;
    IF v_qty IS NULL OR v_qty < 1 THEN
      RAISE EXCEPTION 'invalid quantity' USING ERRCODE = 'P0001';
    END IF;

    SELECT v.id, v.kind, v.label, v.price_bdt, v.stock_qty, v.is_active,
           p.id AS product_id, p.title, p.is_active AS product_active
      INTO v_variant
      FROM store_variants v
      JOIN store_products p ON p.id = v.product_id
     WHERE v.id = (v_item->>'variant_id')::UUID
     FOR UPDATE OF v;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'variant not found' USING ERRCODE = 'P0002';
    END IF;
    IF NOT v_variant.is_active OR NOT v_variant.product_active THEN
      RAISE EXCEPTION 'variant not on sale: %', v_variant.title USING ERRCODE = 'P0003';
    END IF;

    IF v_variant.kind = 'digital' AND NOT v_digital_on THEN
      RAISE EXCEPTION 'digital downloads are not on sale' USING ERRCODE = 'P0010';
    END IF;

    IF v_variant.kind = 'print' THEN
      v_has_print := TRUE;
      IF v_qty > v_max_units THEN
        RAISE EXCEPTION 'at most % copies of one title per order', v_max_units
          USING ERRCODE = 'P0007';
      END IF;

      UPDATE store_variants
         SET stock_qty = stock_qty - v_qty, updated_at = NOW()
       WHERE id = v_variant.id AND stock_qty >= v_qty;
      GET DIAGNOSTICS v_rows = ROW_COUNT;
      IF v_rows <> 1 THEN
        RAISE EXCEPTION 'out of stock: %', v_variant.title USING ERRCODE = 'P0004';
      END IF;
    ELSE
      v_has_digital := TRUE;
      IF v_qty <> 1 THEN
        RAISE EXCEPTION 'digital quantity must be 1' USING ERRCODE = 'P0001';
      END IF;
    END IF;

    v_subtotal := v_subtotal + (v_variant.price_bdt * v_qty);
  END LOOP;

  IF p_payment_method = 'cod' AND v_has_digital THEN
    RAISE EXCEPTION 'cash on delivery cannot be used for a download' USING ERRCODE = 'P0005';
  END IF;
  IF v_has_print AND (p_district_id IS NULL OR p_address IS NULL OR btrim(p_address) = '') THEN
    RAISE EXCEPTION 'a delivery address is required' USING ERRCODE = 'P0006';
  END IF;
  IF v_has_print AND (p_house_no IS NULL OR btrim(p_house_no) = '') THEN
    RAISE EXCEPTION 'a house number is required' USING ERRCODE = 'P0006';
  END IF;

  IF v_has_print THEN
    SELECT is_metro INTO v_is_metro FROM store_districts WHERE id = p_district_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'unknown district' USING ERRCODE = 'P0006';
    END IF;
    SELECT COALESCE((SELECT value::INTEGER FROM store_settings WHERE key = 'free_delivery_over_bdt'), 0)
      INTO v_free_over;
    IF v_free_over > 0 AND v_subtotal >= v_free_over THEN
      v_delivery := 0;
    ELSIF v_is_metro THEN
      SELECT COALESCE((SELECT value::INTEGER FROM store_settings WHERE key = 'delivery_bdt_metro'), 70)
        INTO v_delivery;
    ELSE
      SELECT COALESCE((SELECT value::INTEGER FROM store_settings WHERE key = 'delivery_bdt_outside'), 130)
        INTO v_delivery;
    END IF;
  END IF;

  v_payment_status := CASE WHEN p_payment_method = 'cod' THEN 'cod_pending' ELSE 'awaiting_payment' END;

  INSERT INTO store_orders (
    order_number, user_id, customer_name, customer_phone, customer_email,
    district_id, city, area, address_line, postcode, notes,
    house_no, road_no, landmark, alt_phone,
    has_print, has_digital,
    subtotal_bdt, delivery_bdt, discount_bdt, total_bdt,
    payment_method, payment_status, order_status,
    source_path, source_referrer, reserved_until
  ) VALUES (
    p_order_number, p_user_id, p_name, p_phone, p_email,
    CASE WHEN v_has_print THEN p_district_id ELSE NULL END,
    CASE WHEN v_has_print THEN p_city ELSE NULL END,
    CASE WHEN v_has_print THEN p_area ELSE NULL END,
    CASE WHEN v_has_print THEN p_address ELSE NULL END,
    CASE WHEN v_has_print THEN p_postcode ELSE NULL END,
    p_notes,
    CASE WHEN v_has_print THEN p_house_no ELSE NULL END,
    CASE WHEN v_has_print THEN p_road_no ELSE NULL END,
    CASE WHEN v_has_print THEN p_landmark ELSE NULL END,
    p_alt_phone,
    v_has_print, v_has_digital,
    v_subtotal, v_delivery, 0, v_subtotal + v_delivery,
    p_payment_method, v_payment_status, 'pending',
    p_source_path, p_source_referrer,
    CASE WHEN v_has_print AND p_payment_method <> 'cod'
         THEN NOW() + make_interval(hours => v_reserve_hours) ELSE NULL END
  ) RETURNING id INTO v_order_id;

  FOR v_item IN SELECT * FROM jsonb_array_elements(p_items) LOOP
    v_qty := (v_item->>'quantity')::INTEGER;
    INSERT INTO store_order_items (
      order_id, variant_id, product_title, variant_label, variant_kind,
      unit_price_bdt, quantity, line_total_bdt
    )
    SELECT v_order_id, v.id, p.title, v.label, v.kind,
           v.price_bdt, v_qty, v.price_bdt * v_qty
      FROM store_variants v
      JOIN store_products p ON p.id = v.product_id
     WHERE v.id = (v_item->>'variant_id')::UUID;
  END LOOP;

  INSERT INTO store_order_events (order_id, field, from_value, to_value, note)
  VALUES (v_order_id, 'created', NULL, 'pending', 'Order placed');

  RETURN jsonb_build_object(
    'order_id', v_order_id,
    'order_number', p_order_number,
    'subtotal_bdt', v_subtotal,
    'delivery_bdt', v_delivery,
    'total_bdt', v_subtotal + v_delivery,
    'has_print', v_has_print,
    'has_digital', v_has_digital,
    'payment_status', v_payment_status
  );
END;
$$;

-- The old 15-argument signature is replaced by the 19-argument one above.
-- Postgres treats them as separate functions, so the stale one must go or
-- PostgREST could still resolve a call to it and skip the new rules.
DROP FUNCTION IF EXISTS store_create_order(
  TEXT,UUID,TEXT,TEXT,TEXT,INTEGER,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,JSONB);

REVOKE ALL ON FUNCTION store_create_order(
  TEXT,UUID,TEXT,TEXT,TEXT,INTEGER,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,JSONB,TEXT,TEXT,TEXT,TEXT
) FROM PUBLIC, anon, authenticated;

COMMIT;
