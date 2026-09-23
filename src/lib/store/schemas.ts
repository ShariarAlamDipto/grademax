/**
 * Validation at the system boundary.
 *
 * Every public store endpoint is unauthenticated, so nothing arriving from a
 * browser is trusted: shapes, lengths and formats are all checked here before
 * a single value reaches the database. Lengths are capped deliberately — an
 * unbounded `notes` field on an open endpoint is a free write-amplification
 * primitive.
 */
import { z } from "zod"
import { normalizeBdPhone } from "./phone"

const uuid = z.string().uuid()

export const cartLineSchema = z.object({
  variantId: uuid,
  quantity: z.number().int().min(1).max(50),
})

/** A cap on distinct lines, so one request cannot ask us to price 10,000 rows. */
export const cartSchema = z.array(cartLineSchema).min(1).max(20)

/** Normalises as it validates, so callers always receive `01XXXXXXXXX`. */
export const bdPhoneSchema = z
  .string()
  .min(6)
  .max(20)
  .transform(v => normalizeBdPhone(v))
  .refine((v): v is string => v !== null, {
    message: "Enter a valid Bangladeshi mobile number, for example 01712345678.",
  })

/**
 * The delivery address, structured.
 *
 * A Bangladeshi courier works from house and road number, area, and very often
 * a landmark. A single free-text line loses parcels, so the parts are captured
 * separately; the server composes them into one printable line as well.
 */
export const deliveryAddressSchema = z.object({
  districtId: z.number().int().positive({ message: "Choose your district." }),
  city: z.string().trim().min(2, "Enter your city, upazila or thana.").max(120),
  area: z.string().trim().min(2, "Enter your area.").max(160),
  houseNo: z.string().trim().min(1, "Enter your house or flat number.").max(80),
  roadNo: z.string().trim().max(80).optional().transform(v => v || null),
  landmark: z.string().trim().max(160).optional().transform(v => v || null),
  postcode: z.string().trim().max(12).optional().transform(v => v || null),
  /** Anything the parts above do not capture. */
  addressLine: z.string().trim().max(400).optional().transform(v => v || null),
})

export const checkoutSchema = z.object({
  items: cartSchema,
  customer: z.object({
    name: z.string().trim().min(2, "Enter your full name.").max(120),
    phone: bdPhoneSchema,
    // Required now: it is how a receipt and any delivery problem reach the
    // buyer, and an account already carries one.
    email: z.string().trim().email("Enter a valid email address.").max(200),
    altPhone: z.string().trim().max(20).optional().transform(v => v || null),
  }),
  delivery: deliveryAddressSchema.optional(),
  paymentMethod: z.enum(["bkash", "nagad", "cod"]),
  notes: z.string().trim().max(500).optional().transform(v => v || null),
  /** Attribution only. Never used for access control. */
  source: z
    .object({
      path: z.string().max(300).optional(),
      referrer: z.string().max(300).optional(),
    })
    .optional(),
  /**
   * Honeypot. A real person never fills a field they cannot see; a naive bot
   * fills every input on the form.
   *
   * Deliberately NOT constrained to an empty string here. If validation
   * rejected it, the bot would get a 400 and simply retry without the field —
   * which teaches it how to get through. The route accepts the request, answers
   * as though it succeeded, and writes nothing.
   */
  website: z.string().max(200).optional(),
})

export type CheckoutInput = z.infer<typeof checkoutSchema>

export const paymentSubmitSchema = z.object({
  orderNumber: z.string().trim().min(4).max(40),
  phone: bdPhoneSchema,
  method: z.enum(["bkash", "nagad"]),
  senderMsisdn: bdPhoneSchema,
  /**
   * bKash TrxIDs are 10 alphanumeric characters; Nagad's are longer. Kept
   * permissive within a sane range rather than rejecting a valid receipt on a
   * format guess — the admin verifies it by eye anyway.
   */
  transactionId: z
    .string()
    .trim()
    .min(4, "Enter the Transaction ID from your payment receipt.")
    .max(40)
    .regex(/^[A-Za-z0-9]+$/, "A Transaction ID contains only letters and numbers."),
  amountBdt: z.number().int().min(0).max(1_000_000).optional(),
})

export const orderLookupSchema = z.object({
  orderNumber: z.string().trim().min(4).max(40),
  phone: bdPhoneSchema,
})

// ── Admin-side schemas ───────────────────────────────────────────────────────

export const adminVariantUpdateSchema = z.object({
  variantId: uuid,
  priceBdt: z.number().int().min(0).max(1_000_000).optional(),
  stockQty: z.number().int().min(0).max(100_000).nullable().optional(),
  isActive: z.boolean().optional(),
  label: z.string().trim().min(2).max(120).optional(),
})

export const adminProductUpdateSchema = z.object({
  productId: uuid,
  isActive: z.boolean().optional(),
  title: z.string().trim().min(2).max(200).optional(),
  subtitle: z.string().trim().max(200).nullable().optional(),
  description: z.string().trim().max(4000).nullable().optional(),
  sortOrder: z.number().int().min(0).max(9999).optional(),
})

export const adminOrderUpdateSchema = z.object({
  orderId: uuid,
  orderStatus: z.enum(["pending", "confirmed", "packed", "shipped", "delivered", "cancelled"]).optional(),
  courierName: z.string().trim().max(80).nullable().optional(),
  trackingCode: z.string().trim().max(80).nullable().optional(),
  adminNote: z.string().trim().max(1000).nullable().optional(),
})

export const adminPaymentDecisionSchema = z.object({
  orderId: uuid,
  decision: z.enum(["verify", "reject"]),
  reason: z.string().trim().max(400).optional(),
})

export const adminSettingsSchema = z.object({
  updates: z.record(z.string().min(1).max(60), z.string().max(1000)),
})
