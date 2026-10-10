-- Migration 24: Store — downloads are entitlements, not stored bearer tokens
-- =============================================================================
-- `store_downloads` was designed around a permanent token whose SHA-256 hash
-- was stored. In practice the buyer-facing flow never needs one: the order
-- tracking page proves who they are (order number + phone) and mints a signed
-- grant that lasts thirty minutes, and every redemption re-reads this row to
-- confirm payment is still verified and access has not been revoked.
--
-- A permanent token would have been a credential to forward, and it could not
-- be shown on the tracking page anyway, because a hash cannot be reversed.
--
-- The column is kept, but nullable, so a future "permanent link in an email"
-- feature has somewhere to put one.
-- =============================================================================

BEGIN;

ALTER TABLE store_downloads ALTER COLUMN token_hash DROP NOT NULL;

-- Record where each download actually went. Useful when one order's file shows
-- up in a hundred different places.
CREATE TABLE IF NOT EXISTS store_download_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entitlement_id UUID NOT NULL REFERENCES store_downloads(id) ON DELETE CASCADE,
  order_id      UUID NOT NULL REFERENCES store_orders(id) ON DELETE CASCADE,
  ip            TEXT,
  user_agent    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS store_download_log_ent ON store_download_log (entitlement_id, created_at DESC);

ALTER TABLE store_download_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role only" ON store_download_log;
CREATE POLICY "Service role only" ON store_download_log FOR ALL
  USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

-- Spend one download from an entitlement, atomically.
-- The guarded UPDATE is what enforces `max_downloads`: reading the count and
-- then writing it back would let parallel requests both pass the check.
CREATE OR REPLACE FUNCTION store_consume_download(p_entitlement UUID, p_ip TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE v_rows INTEGER; v_row RECORD;
BEGIN
  UPDATE store_downloads d
     SET download_count = d.download_count + 1,
         last_used_at = NOW(),
         last_ip = COALESCE(p_ip, d.last_ip)
    FROM store_orders o
   WHERE d.id = p_entitlement
     AND o.id = d.order_id
     AND d.revoked_at IS NULL
     AND d.expires_at > NOW()
     AND d.download_count < d.max_downloads
     -- Re-checked at redemption, so revoking or refunding an order kills a
     -- grant that has already been handed out.
     AND o.payment_status = 'verified'
     AND o.order_status <> 'cancelled';
  GET DIAGNOSTICS v_rows = ROW_COUNT;

  IF v_rows <> 1 THEN
    RETURN jsonb_build_object('ok', FALSE);
  END IF;

  SELECT d.order_id, d.download_count, d.max_downloads, i.variant_id, i.product_title
    INTO v_row
    FROM store_downloads d
    JOIN store_order_items i ON i.id = d.order_item_id
   WHERE d.id = p_entitlement;

  INSERT INTO store_download_log (entitlement_id, order_id, ip)
  VALUES (p_entitlement, v_row.order_id, p_ip);

  RETURN jsonb_build_object(
    'ok', TRUE,
    'variant_id', v_row.variant_id,
    'product_title', v_row.product_title,
    'download_count', v_row.download_count,
    'max_downloads', v_row.max_downloads
  );
END;
$$;

REVOKE ALL ON FUNCTION store_consume_download(UUID, TEXT) FROM PUBLIC, anon, authenticated;

COMMIT;
