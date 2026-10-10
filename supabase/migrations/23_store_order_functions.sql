-- Migration 23: Store — atomic order creation and payment transitions
-- =============================================================================
-- WHY THESE ARE SQL FUNCTIONS AND NOT TYPESCRIPT
-- ----------------------------------------------
-- Creating an order means: read prices, reserve stock on several rows, insert
-- the order, insert its items. The Supabase JS client issues each of those as a
-- separate HTTP request, so a failure half way leaves stock reserved against an
-- order that does not exist, and a compensating "undo" in application code is
-- itself just another request that can fail.
--
-- Doing it in one function makes it one transaction: either the order exists
-- with its stock reserved, or nothing happened at all.
--
-- Prices are re-read from `store_variants` INSIDE the transaction rather than
-- passed in. The caller cannot set a price even by mistake, and a price edited
-- between the cart being priced and the order being placed cannot produce an
-- order whose stored total disagrees with what was charged.
--
-- Every transition is guarded on the status it expects, so clicking Verify
-- twice performs the action once.
-- =============================================================================

BEGIN;

-- ── Create an order ──────────────────────────────────────────────────────────
-- p_items: [{"variant_id": "...", "quantity": 2}, ...]
-- Raises with a machine-readable ERRCODE so the API can map failures to fields.
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
  p_items           JSONB
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
  v_order_id      UUID;
  v_payment_status TEXT;
  v_reserve_hours INTEGER := 48;
BEGIN
  IF jsonb_array_length(p_items) = 0 THEN
    RAISE EXCEPTION 'cart is empty' USING ERRCODE = 'P0001';
  END IF;

  -- Pass 1: validate every line, reserve print stock, accumulate the subtotal.
  -- FOR UPDATE serialises two buyers racing for the last copy; the guarded
  -- UPDATE below is what actually refuses the loser.
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

    IF v_variant.kind = 'print' THEN
      v_has_print := TRUE;
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

  -- Payment method rules, enforced here as well as by the table constraint so
  -- the caller gets a useful message instead of a raw constraint violation.
  IF p_payment_method = 'cod' AND v_has_digital THEN
    RAISE EXCEPTION 'cash on delivery cannot be used for a download' USING ERRCODE = 'P0005';
  END IF;
  IF v_has_print AND (p_district_id IS NULL OR p_address IS NULL) THEN
    RAISE EXCEPTION 'a delivery address is required' USING ERRCODE = 'P0006';
  END IF;

  -- Delivery, computed from settings inside the transaction.
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
    v_has_print, v_has_digital,
    v_subtotal, v_delivery, 0, v_subtotal + v_delivery,
    p_payment_method, v_payment_status, 'pending',
    p_source_path, p_source_referrer,
    CASE WHEN v_has_print AND p_payment_method <> 'cod'
         THEN NOW() + make_interval(hours => v_reserve_hours) ELSE NULL END
  ) RETURNING id INTO v_order_id;

  -- Pass 2: snapshot the lines.
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

-- ── Verify a manual payment ──────────────────────────────────────────────────
-- Idempotent by construction: the UPDATE is guarded on payment_status, so a
-- second click matches no row and reports that it was already done rather than
-- transitioning again, double-confirming the order or re-issuing downloads.
CREATE OR REPLACE FUNCTION store_verify_payment(
  p_order UUID, p_admin UUID, p_admin_email TEXT, p_note TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_rows INTEGER; v_status TEXT;
BEGIN
  UPDATE store_orders
     SET payment_status = 'verified',
         order_status   = CASE WHEN order_status = 'pending' THEN 'confirmed' ELSE order_status END,
         reserved_until = NULL,
         updated_at     = NOW()
   WHERE id = p_order
     AND payment_status = 'submitted';
  GET DIAGNOSTICS v_rows = ROW_COUNT;

  IF v_rows <> 1 THEN
    SELECT payment_status INTO v_status FROM store_orders WHERE id = p_order;
    RETURN jsonb_build_object('changed', FALSE, 'payment_status', v_status);
  END IF;

  UPDATE store_payments
     SET status = 'verified', verified_by = p_admin, verified_at = NOW(),
         admin_note = COALESCE(p_note, admin_note)
   WHERE order_id = p_order AND status = 'submitted';

  INSERT INTO store_order_events (order_id, field, from_value, to_value, actor_id, actor_email, note)
  VALUES (p_order, 'payment_status', 'submitted', 'verified', p_admin, p_admin_email, p_note);

  RETURN jsonb_build_object('changed', TRUE, 'payment_status', 'verified');
END;
$$;

-- ── Reject a manual payment ──────────────────────────────────────────────────
-- The order returns to `awaiting_payment` so the buyer can submit a corrected
-- Transaction ID. Stock stays reserved: the buyer is still trying to pay, and
-- releasing it here would sell their copy out from under them mid-correction.
CREATE OR REPLACE FUNCTION store_reject_payment(
  p_order UUID, p_admin UUID, p_admin_email TEXT, p_reason TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_rows INTEGER; v_status TEXT;
BEGIN
  UPDATE store_orders
     SET payment_status = 'awaiting_payment', updated_at = NOW()
   WHERE id = p_order AND payment_status = 'submitted';
  GET DIAGNOSTICS v_rows = ROW_COUNT;

  IF v_rows <> 1 THEN
    SELECT payment_status INTO v_status FROM store_orders WHERE id = p_order;
    RETURN jsonb_build_object('changed', FALSE, 'payment_status', v_status);
  END IF;

  UPDATE store_payments
     SET status = 'rejected', verified_by = p_admin, verified_at = NOW(),
         rejection_reason = p_reason
   WHERE order_id = p_order AND status = 'submitted';

  INSERT INTO store_order_events (order_id, field, from_value, to_value, actor_id, actor_email, note)
  VALUES (p_order, 'payment_status', 'submitted', 'rejected', p_admin, p_admin_email, p_reason);

  RETURN jsonb_build_object('changed', TRUE, 'payment_status', 'awaiting_payment');
END;
$$;

-- ── Cancel an order and give the stock back ──────────────────────────────────
-- Guarded so a double-click cannot restock twice, which would invent inventory.
CREATE OR REPLACE FUNCTION store_cancel_order(
  p_order UUID, p_admin UUID, p_admin_email TEXT, p_reason TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_rows INTEGER;
BEGIN
  UPDATE store_orders
     SET order_status = 'cancelled', reserved_until = NULL, updated_at = NOW()
   WHERE id = p_order AND order_status <> 'cancelled';
  GET DIAGNOSTICS v_rows = ROW_COUNT;

  IF v_rows <> 1 THEN
    RETURN jsonb_build_object('changed', FALSE);
  END IF;

  PERFORM store_release_order_stock(p_order);

  -- Revoke any digital access this order had already been granted.
  UPDATE store_downloads SET revoked_at = NOW()
   WHERE order_id = p_order AND revoked_at IS NULL;

  INSERT INTO store_order_events (order_id, field, from_value, to_value, actor_id, actor_email, note)
  VALUES (p_order, 'order_status', NULL, 'cancelled', p_admin, p_admin_email, p_reason);

  RETURN jsonb_build_object('changed', TRUE);
END;
$$;

-- ── Expire abandoned reservations ────────────────────────────────────────────
-- An unpaid order holds print stock for 48 hours. Without this, a handful of
-- abandoned checkouts would show the last copies as sold forever.
CREATE OR REPLACE FUNCTION store_expire_reservations()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_order RECORD; v_count INTEGER := 0;
BEGIN
  FOR v_order IN
    SELECT id FROM store_orders
     WHERE reserved_until IS NOT NULL
       AND reserved_until < NOW()
       AND payment_status = 'awaiting_payment'
       AND order_status = 'pending'
  LOOP
    PERFORM store_cancel_order(v_order.id, NULL, 'system', 'Reservation expired — payment not received');
    v_count := v_count + 1;
  END LOOP;
  RETURN v_count;
END;
$$;

REVOKE ALL ON FUNCTION store_create_order(TEXT,UUID,TEXT,TEXT,TEXT,INTEGER,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_verify_payment(UUID,UUID,TEXT,TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_reject_payment(UUID,UUID,TEXT,TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_cancel_order(UUID,UUID,TEXT,TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION store_expire_reservations() FROM PUBLIC, anon, authenticated;

COMMIT;
