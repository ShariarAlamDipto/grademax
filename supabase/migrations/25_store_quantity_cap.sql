-- Migration 25: Store — enforce the per-line quantity cap where it counts
-- =============================================================================
-- `max_units_per_order` was only checked in priceCart(), which backs the cart
-- preview. Nothing forces a buyer to call that endpoint: POST straight to
-- /api/store/checkout and the cap never ran, so a single guest request could
-- reserve up to 50 copies (the Zod ceiling) of a limited print run.
--
-- No money was at risk — the price was always correct — but the guard exists to
-- stop one person hoarding a short print run, and a guard that can be skipped
-- by not calling the optional endpoint is not a guard.
--
-- It belongs here, in the same transaction that reserves the stock, so every
-- path to an order goes through it.
-- =============================================================================

BEGIN;

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
  v_max_units     INTEGER := 10;
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

  -- Duplicate lines for the same variant are summed first. Sending the same
  -- variant ten times at quantity 1 must not slip past a per-line cap.
  SELECT jsonb_agg(jsonb_build_object('variant_id', variant_id, 'quantity', qty))
    INTO v_totals
    FROM (
      SELECT (item->>'variant_id')::UUID AS variant_id,
             SUM((item->>'quantity')::INTEGER) AS qty
        FROM jsonb_array_elements(p_items) AS item
       GROUP BY 1
    ) collapsed;
  p_items := v_totals;

  -- Pass 1: validate every line, reserve print stock, accumulate the subtotal.
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
  IF v_has_print AND (p_district_id IS NULL OR p_address IS NULL) THEN
    RAISE EXCEPTION 'a delivery address is required' USING ERRCODE = 'P0006';
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

REVOKE ALL ON FUNCTION store_create_order(TEXT,UUID,TEXT,TEXT,TEXT,INTEGER,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,TEXT,JSONB) FROM PUBLIC, anon, authenticated;

COMMIT;
