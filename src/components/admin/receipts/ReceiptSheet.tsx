import { formatBdt } from "@/lib/store/format"
import { paymentStamp, takaInWords, type ReceiptDraft, type ReceiptTotals } from "@/lib/receipts/receiptMath"

/** The printable A4 receipt. Pure markup: every figure comes from computeTotals. */

function formatDay(value: string): string {
  if (!value) return "—"
  const d = new Date(`${value}T00:00:00`)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

export default function ReceiptSheet({ draft, totals }: { draft: ReceiptDraft; totals: ReceiptTotals }) {
  const stamp = paymentStamp(totals)
  const note = draft.note.trim()

  return (
    <article className="gmr-sheet" aria-label="A4 receipt">
      <div className="gmr-head">
        <div>
          <div className="gmr-brand">{draft.shop || "Your print shop"}</div>
          {draft.shopSub ? <div className="gmr-shopsub">{draft.shopSub}</div> : null}
        </div>
        <div className="gmr-doc">
          <h2>RECEIPT</h2>
          <div className="gmr-kind">Booklet printing</div>
          <dl>
            <dt>Receipt no.</dt><dd className="gmr-mono">{draft.no || "—"}</dd>
            <dt>Date</dt><dd>{formatDay(draft.date)}</dd>
          </dl>
        </div>
      </div>

      <div className="gmr-parties">
        <div>
          <span className="gmr-u">Received from</span>
          <strong>{draft.cust || "—"}</strong>
          {draft.phone ? <span className="gmr-mono">{draft.phone}</span> : null}
          {draft.addr ? <span>{draft.addr}</span> : null}
        </div>
        <div>
          <span className="gmr-u">Order</span>
          <span>{plural(totals.lines.length, "title", "titles")} · {plural(totals.copies, "copy", "copies")}</span>
          {draft.ready ? <span>Ready by {formatDay(draft.ready)}</span> : null}
          <span>Paid by {draft.method || "Cash"}{draft.txn ? ` · Txn ${draft.txn}` : ""}</span>
        </div>
      </div>

      <table className="gmr-items">
        <thead>
          <tr>
            <th className="gmr-idx">#</th>
            <th>Booklet &amp; specification</th>
            <th className="gmr-num">Copies</th>
            <th className="gmr-num">Rate</th>
            <th className="gmr-num">Amount</th>
          </tr>
        </thead>
        <tbody>
          {totals.lines.length ? totals.lines.map((line, i) => (
            <tr key={i}>
              <td className="gmr-idx">{String(i + 1).padStart(2, "0")}</td>
              <td>
                <span className="gmr-name">{line.name || "Booklet"}</span>
                {line.spec ? <span className="gmr-spec">{line.spec}</span> : null}
              </td>
              <td className="gmr-num">{line.qty.toLocaleString("en-US")}</td>
              <td className="gmr-num">{formatBdt(line.rate)}</td>
              <td className="gmr-num">{formatBdt(line.amount)}</td>
            </tr>
          )) : (
            <tr><td colSpan={5} className="gmr-empty">Add a booklet to start.</td></tr>
          )}
        </tbody>
      </table>

      <div className="gmr-bottom">
        <div className="gmr-left">
          <div className="gmr-words">Total payable in words: Taka {takaInWords(totals.total)} only.</div>
          {note ? <div className="gmr-note">{note}</div> : null}
        </div>
        <div className="gmr-sums">
          {stamp ? (
            <div className={`gmr-stamp gmr-stamp-${stamp}`}>{stamp === "paid" ? "PAID" : "PARTLY PAID"}</div>
          ) : null}
          <div className="gmr-line"><span>Subtotal</span><span>{formatBdt(totals.subtotal)}</span></div>
          {totals.discount ? <div className="gmr-line gmr-neg"><span>Discount</span><span>{formatBdt(totals.discount)}</span></div> : null}
          {totals.delivery ? <div className="gmr-line"><span>Delivery</span><span>{formatBdt(totals.delivery)}</span></div> : null}
          <div className="gmr-total">
            <span className="gmr-total-lbl">Total payable</span>
            <span className="gmr-total-amt">{formatBdt(totals.total)}</span>
          </div>
          <div className="gmr-line"><span>Paid ({draft.method || "Cash"})</span><span>{formatBdt(totals.paid)}</span></div>
          <div className="gmr-line gmr-due">
            <span>{totals.balance < 0 ? "Change returned" : "Balance due"}</span>
            <span>{formatBdt(Math.abs(totals.balance))}</span>
          </div>
        </div>
      </div>

      <div className="gmr-foot">
        <div className="gmr-signs"><span>Customer signature</span><span>Authorised signature</span></div>
        <div className="gmr-terms">
          <span>Goods once printed cannot be returned. Please check your booklets on collection.</span>
          <span className="gmr-thanks">Thank you · Study well</span>
        </div>
      </div>
    </article>
  )
}
