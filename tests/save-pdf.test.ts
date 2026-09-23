import test from "node:test";
import assert from "node:assert/strict";
import {
  isIOS,
  supportsBlobDownloadAttribute,
  safePdfFilename,
  handlePdfDownloadClick,
  handlePdfPreviewClick,
} from "../src/lib/savePdf";

/**
 * These run under plain Node, so `navigator` is stubbed per-case. The helpers
 * are written to tolerate `navigator` being absent entirely (SSR), which is
 * the default state below.
 */
type NavStub = { userAgent: string; maxTouchPoints: number };

function withNavigator<T>(stub: NavStub | null, fn: () => T): T {
  const g = globalThis as unknown as { navigator?: unknown };
  const had = "navigator" in g;
  const previous = g.navigator;
  if (stub === null) {
    delete g.navigator;
  } else {
    Object.defineProperty(g, "navigator", {
      value: stub,
      configurable: true,
      writable: true,
    });
  }
  try {
    return fn();
  } finally {
    if (had) {
      Object.defineProperty(g, "navigator", {
        value: previous,
        configurable: true,
        writable: true,
      });
    } else {
      delete g.navigator;
    }
  }
}

const IPHONE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const IPAD_LEGACY =
  "Mozilla/5.0 (iPad; CPU OS 12_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Mobile/15E148 Safari/604.1";
// iPadOS 13+ lies and claims to be a desktop Mac.
const IPADOS_DESKTOP_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15";
const MAC_SAFARI = IPADOS_DESKTOP_UA;
const ANDROID_CHROME =
  "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36";
const WINDOWS_CHROME =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";
// The in-app browser people actually arrive from — still WebKit underneath.
const IOS_INSTAGRAM_WEBVIEW =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 335.0.0.30.98";

test("isIOS detects iPhone, legacy iPad and iOS in-app webviews", () => {
  for (const ua of [IPHONE, IPAD_LEGACY, IOS_INSTAGRAM_WEBVIEW]) {
    assert.equal(
      withNavigator({ userAgent: ua, maxTouchPoints: 5 }, isIOS),
      true,
      `expected iOS for ${ua.slice(0, 40)}…`,
    );
  }
});

test("isIOS detects iPadOS 13+ behind its desktop user-agent", () => {
  assert.equal(
    withNavigator({ userAgent: IPADOS_DESKTOP_UA, maxTouchPoints: 5 }, isIOS),
    true,
  );
});

test("isIOS does not misfire on desktop Safari, which shares that user-agent", () => {
  // Same UA string as iPadOS — only maxTouchPoints separates them.
  assert.equal(
    withNavigator({ userAgent: MAC_SAFARI, maxTouchPoints: 0 }, isIOS),
    false,
  );
});

test("isIOS is false on Android and Windows", () => {
  assert.equal(
    withNavigator({ userAgent: ANDROID_CHROME, maxTouchPoints: 5 }, isIOS),
    false,
  );
  assert.equal(
    withNavigator({ userAgent: WINDOWS_CHROME, maxTouchPoints: 0 }, isIOS),
    false,
  );
});

test("isIOS is false during SSR, where navigator does not exist", () => {
  assert.equal(withNavigator(null, isIOS), false);
});

test("supportsBlobDownloadAttribute is the inverse of isIOS", () => {
  assert.equal(
    withNavigator({ userAgent: IPHONE, maxTouchPoints: 5 }, supportsBlobDownloadAttribute),
    false,
  );
  assert.equal(
    withNavigator({ userAgent: WINDOWS_CHROME, maxTouchPoints: 0 }, supportsBlobDownloadAttribute),
    true,
  );
});

test("safePdfFilename strips unsafe characters and forces one .pdf suffix", () => {
  assert.equal(safePdfFilename("Physics Unit 1"), "Physics_Unit_1.pdf");
  assert.equal(safePdfFilename("Maths: Paper 2/3 <test>"), "Maths_Paper_23_test.pdf");
  assert.equal(safePdfFilename("already.pdf"), "already.pdf");
  assert.equal(safePdfFilename(""), "download.pdf");
  assert.equal(safePdfFilename("!!!", "worksheet"), "worksheet.pdf");
  assert.equal(safePdfFilename("a".repeat(200)).length, 84); // 80 + ".pdf"
});

test("handlePdfDownloadClick leaves the native download alone off iOS", () => {
  let prevented = false;
  const event = { preventDefault: () => { prevented = true; } };
  withNavigator({ userAgent: WINDOWS_CHROME, maxTouchPoints: 0 }, () =>
    handlePdfDownloadClick(event, new Blob(["x"]), "test.pdf", "blob:fake"),
  );
  assert.equal(prevented, false, "desktop must keep the browser's own download");
});

test("handlePdfDownloadClick intercepts the click on iOS and opens the PDF", async () => {
  let prevented = false;
  const event = { preventDefault: () => { prevented = true; } };

  // No navigator.share on this stub, so savePdf takes its last-resort path:
  // navigate to the blob in the same tab, where iOS renders the PDF and its
  // viewer offers "Save to Files".
  const g = globalThis as unknown as { window?: unknown };
  const location = { href: "" };
  Object.defineProperty(g, "window", { value: { location }, configurable: true, writable: true });
  try {
    withNavigator({ userAgent: IPHONE, maxTouchPoints: 5 }, () =>
      handlePdfDownloadClick(event, new Blob(["x"]), "test.pdf", "blob:fake"),
    );
    // savePdf is async; let its microtasks drain before asserting.
    await new Promise((resolve) => setTimeout(resolve, 0));
  } finally {
    delete g.window;
  }

  assert.equal(prevented, true, "iOS must not be allowed to follow the blob: href");
  assert.equal(location.href, "blob:fake", "should reuse the caller's object URL");
});

test("handlePdfDownloadClick falls through when the blob is missing", () => {
  let prevented = false;
  const event = { preventDefault: () => { prevented = true; } };
  withNavigator({ userAgent: IPHONE, maxTouchPoints: 5 }, () =>
    handlePdfDownloadClick(event, null, "test.pdf", "blob:fake"),
  );
  assert.equal(
    prevented,
    false,
    "with no blob to share, the href is a better bet than blocking the tap",
  );
});

test("handlePdfPreviewClick only intercepts on iOS, and only with a URL", () => {
  let prevented = false;
  const event = { preventDefault: () => { prevented = true; } };

  withNavigator({ userAgent: WINDOWS_CHROME, maxTouchPoints: 0 }, () =>
    handlePdfPreviewClick(event, "blob:fake"),
  );
  assert.equal(prevented, false, "target=_blank works fine off iOS");

  withNavigator({ userAgent: IPHONE, maxTouchPoints: 5 }, () =>
    handlePdfPreviewClick(event, null),
  );
  assert.equal(prevented, false, "nothing to open");
});
