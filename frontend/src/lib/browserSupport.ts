export type BrowserSupport = {
  supported: boolean;
  browser:
    | "edge"
    | "chrome"
    | "android-chrome"
    | "ios-safari"
    | "macos-chrome"
    | "macos-safari"
    | "embedded"
    | "unknown";
  reason?: string;
};

const MIN_CHROMIUM_MAJOR = 120;
const MIN_IOS_SAFARI_MAJOR = 17;
const MIN_MACOS_SAFARI_MAJOR = 17;
const EMBEDDED_PATTERN = /MicroMessenger|FBAN|FBAV|Instagram|Line\/|; wv\)|\bwv\b|WebView/i;
const UNSUPPORTED_CHROMIUM_VARIANT_PATTERN =
  /Edg[A-Z]*\/|OPR\/|Opera Mini|SamsungBrowser\/|CriOS\/|FxiOS\//i;

function major(userAgent: string, pattern: RegExp): number | null {
  const match = userAgent.match(pattern);
  return match ? Number(match[1]) : null;
}

function isIOS(userAgent: string): boolean {
  return (
    /(iPhone|iPad|iPod)/i.test(userAgent) ||
    (/Macintosh/i.test(userAgent) && /Mobile/i.test(userAgent))
  );
}

function isMacOS(userAgent: string): boolean {
  return /Macintosh|Mac OS X/i.test(userAgent) && !isIOS(userAgent);
}

function isSafari(userAgent: string): boolean {
  return (
    /Safari/i.test(userAgent) &&
    !/(Chrome|Chromium|CriOS|Edg|OPR|SamsungBrowser|FxiOS|Firefox)/i.test(userAgent)
  );
}

export function detectBrowserSupport(userAgent: string): BrowserSupport {
  if (EMBEDDED_PATTERN.test(userAgent)) {
    return {
      supported: false,
      browser: "embedded",
      reason: "内嵌浏览器不支持正式考试，请在系统浏览器中打开。",
    };
  }
  const edgeMajor = major(userAgent, /Edg\/(\d+)/);
  if (/Windows/i.test(userAgent) && edgeMajor !== null) {
    return edgeMajor >= MIN_CHROMIUM_MAJOR
      ? { supported: true, browser: "edge" }
      : { supported: false, browser: "edge", reason: "Edge 版本过旧，请先更新。" };
  }
  const chromeMajor = major(userAgent, /Chrome\/(\d+)/);
  if (
    /Android/i.test(userAgent) &&
    chromeMajor !== null &&
    !UNSUPPORTED_CHROMIUM_VARIANT_PATTERN.test(userAgent)
  ) {
    return chromeMajor >= MIN_CHROMIUM_MAJOR
      ? { supported: true, browser: "android-chrome" }
      : { supported: false, browser: "android-chrome", reason: "Android Chrome 版本过旧。" };
  }
  if (
    /Windows/i.test(userAgent) &&
    chromeMajor !== null &&
    !UNSUPPORTED_CHROMIUM_VARIANT_PATTERN.test(userAgent)
  ) {
    return chromeMajor >= MIN_CHROMIUM_MAJOR
      ? { supported: true, browser: "chrome" }
      : { supported: false, browser: "chrome", reason: "Chrome 版本过旧，请先更新。" };
  }
  if (
    isMacOS(userAgent) &&
    chromeMajor !== null &&
    !UNSUPPORTED_CHROMIUM_VARIANT_PATTERN.test(userAgent)
  ) {
    return chromeMajor >= MIN_CHROMIUM_MAJOR
      ? { supported: true, browser: "macos-chrome" }
      : {
          supported: false,
          browser: "macos-chrome",
          reason: `macOS Chrome 版本过旧，请更新至 ${MIN_CHROMIUM_MAJOR} 或更高版本。`,
        };
  }
  const safariMajor = major(userAgent, /Version\/(\d+)/);
  if (isIOS(userAgent) && isSafari(userAgent) && safariMajor !== null) {
    return safariMajor >= MIN_IOS_SAFARI_MAJOR
      ? { supported: true, browser: "ios-safari" }
      : { supported: false, browser: "ios-safari", reason: "iOS Safari 版本过旧，请先更新系统。" };
  }
  if (isMacOS(userAgent) && isSafari(userAgent) && safariMajor !== null) {
    return safariMajor >= MIN_MACOS_SAFARI_MAJOR
      ? { supported: true, browser: "macos-safari" }
      : {
          supported: false,
          browser: "macos-safari",
          reason: `macOS Safari 版本过旧，请更新至 ${MIN_MACOS_SAFARI_MAJOR} 或更高版本。`,
        };
  }
  return {
    supported: false,
    browser: "unknown",
    reason:
      "当前浏览器不在支持范围内，请使用 Windows Edge/Chrome、macOS Chrome/Safari、Android Chrome 或 iOS Safari。",
  };
}
