/**
 * Saving a generated PDF to the user's device, on every platform.
 *
 * Background:
 *   Both generators (Worksheet Generator and Test Builder) merge their PDF in
 *   the browser with pdf-lib and hand the user a `blob:` object URL on an
 *   `<a download="…">`. That works on desktop and Android, but it is a dead
 *   end on iOS:
 *
 *     - WebKit does not honour the `download` attribute on `blob:` URLs. In
 *       Safari the tap navigates instead of saving: the PDF opens inline, the
 *       filename is discarded, and the user is bounced off the page.
 *     - Inside the WKWebView browsers people actually arrive from (Instagram,
 *       Facebook, Messenger, Gmail, TikTok), `blob:` navigation is blocked
 *       outright, so the tap does nothing at all — the reported symptom.
 *     - `target="_blank"` on a `blob:` URL is unreliable in the same way, so
 *       the "Preview" / "Open in viewer" links break for the same reason.
 *
 *   The supported route on iOS is the Web Share API with a `File` payload,
 *   which raises the native share sheet with "Save to Files". It has one hard
 *   requirement: `navigator.share()` must be called during the user gesture,
 *   so nothing may be awaited before it. Every entry point below therefore
 *   takes an already-built `Blob` and calls `share()` synchronously.
 *
 * Everywhere else the native `download` attribute is left completely alone —
 * it works, and it keeps right-click "Save link as" intact on desktop.
 */

export type SaveOutcome =
  /** Native `download` attribute handled it (desktop / Android). */
  | 'download'
  /** Handed to the OS share sheet — iOS "Save to Files", AirDrop, etc. */
  | 'shared'
  /** Share sheet was dismissed by the user. */
  | 'cancelled'
  /** Fell back to opening the PDF inline so the user can save from there. */
  | 'opened';

/**
 * True on iPhone/iPad/iPod, including iPadOS 13+ which masquerades as
 * "Macintosh" and can only be told apart by its touch support.
 *
 * Note this deliberately matches *all* iOS browsers, not just Safari: Chrome,
 * Firefox and Edge on iOS are all WKWebView skins and inherit the exact same
 * `download`-attribute limitation.
 */
export function isIOS(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(ua)) return true;
  // iPadOS 13+ reports a desktop UA string; touch points give it away.
  return ua.includes('Macintosh') && navigator.maxTouchPoints > 1;
}

/** Whether this platform can be trusted with `<a download>` on a blob: URL. */
export function supportsBlobDownloadAttribute(): boolean {
  return !isIOS();
}

/** Can we hand this file to the OS share sheet? */
function canShareFile(file: File): boolean {
  return (
    typeof navigator !== 'undefined' &&
    typeof navigator.canShare === 'function' &&
    typeof navigator.share === 'function' &&
    navigator.canShare({ files: [file] })
  );
}

/** Strip characters that break filenames, and guarantee a .pdf extension. */
export function safePdfFilename(name: string, fallback = 'download'): string {
  const base =
    (name || '')
      .replace(/\.pdf$/i, '')
      .replace(/[^a-zA-Z0-9 _-]/g, '')
      .replace(/\s+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 80) || fallback;
  return `${base}.pdf`;
}

/**
 * Save a generated PDF.
 *
 * MUST be called synchronously from a user-gesture handler (a click), or iOS
 * will reject the share sheet with a NotAllowedError.
 *
 * @param blob     The PDF, already built. Never fetched here — awaiting a
 *                 fetch first would spend the user gesture.
 * @param filename Suggested name; sanitised before use.
 * @param blobUrl  An existing object URL for `blob`, if the caller already
 *                 holds one. Saves allocating (and leaking) a second one.
 */
export async function savePdf(
  blob: Blob,
  filename: string,
  blobUrl?: string,
): Promise<SaveOutcome> {
  const name = safePdfFilename(filename);

  if (isIOS()) {
    const file = new File([blob], name, { type: 'application/pdf' });

    if (canShareFile(file)) {
      try {
        // Synchronous within the gesture — do not await anything above this.
        await navigator.share({ files: [file], title: name });
        return 'shared';
      } catch (err) {
        // The user dismissing the sheet is a normal outcome, not a failure.
        if (err instanceof DOMException && err.name === 'AbortError') {
          return 'cancelled';
        }
        // Anything else (older WebKit, share disabled in a webview) falls
        // through to opening the PDF inline below.
        console.warn('[savePdf] share sheet unavailable, opening inline', err);
      }
    }

    // No share sheet: open the PDF in the same tab. iOS renders it in the
    // native PDF viewer, where the built-in share button can save it to Files.
    // Same tab rather than a new one because `target="_blank"` on a blob: URL
    // is what produces "Safari cannot open the page because the address is
    // invalid".
    const url = blobUrl ?? URL.createObjectURL(blob);
    window.location.href = url;
    return 'opened';
  }

  // Desktop / Android: the native download attribute works.
  const url = blobUrl ?? URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.rel = 'noopener';
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  // Only revoke a URL we minted ourselves — the caller's is still on screen.
  if (!blobUrl) {
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }
  return 'download';
}

/**
 * `onClick` handler for a real `<a href={blobUrl} download={name}>`.
 *
 * On desktop and Android this does nothing at all — the browser's native
 * download runs untouched, right-click "Save link as" still works, and the
 * markup stays semantic. On iOS it cancels the doomed navigation and routes
 * through {@link savePdf} instead.
 */
export function handlePdfDownloadClick(
  event: { preventDefault: () => void },
  blob: Blob | null,
  filename: string,
  blobUrl?: string,
): void {
  if (supportsBlobDownloadAttribute()) return;
  // Without the Blob we cannot build a File for the share sheet; let the
  // browser try the href rather than blocking the tap outright.
  if (!blob) return;

  event.preventDefault();
  void savePdf(blob, filename, blobUrl);
}

/**
 * `onClick` handler for a "Preview" / "Open in viewer" link pointing at a
 * blob: URL.
 *
 * `target="_blank"` to a blob: URL fails on iOS, so open it in the same tab
 * there. Untouched on every other platform.
 */
export function handlePdfPreviewClick(
  event: { preventDefault: () => void },
  blobUrl: string | null,
): void {
  if (!isIOS() || !blobUrl) return;
  event.preventDefault();
  window.location.href = blobUrl;
}
