import { describe, expect, it } from "vitest";

import { detectBrowserSupport } from "@/lib/browserSupport";

describe("detectBrowserSupport", () => {
  it.each([
    ["Windows Edge", "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Edg/140.0.0.0", "edge"],
    [
      "Windows Chrome",
      "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
      "chrome",
    ],
    [
      "Android Chrome",
      "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140.0.0.0 Mobile Safari/537.36",
      "android-chrome",
    ],
    [
      "iOS Safari",
      "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) Version/19.0 Mobile/15E148 Safari/604.1",
      "ios-safari",
    ],
    [
      "macOS Chrome",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
      "macos-chrome",
    ],
    [
      "macOS Safari",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
      "macos-safari",
    ],
  ])("accepts supported %s", (_name, userAgent, browser) => {
    expect(detectBrowserSupport(userAgent)).toMatchObject({ supported: true, browser });
  });

  it.each([
    [
      "legacy Windows Chrome",
      "Mozilla/5.0 (Windows NT 10.0) Chrome/100.0.0.0 Safari/537.36",
      "chrome",
    ],
    [
      "legacy Windows Edge",
      "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Edg/119.0.0.0",
      "edge",
    ],
    [
      "legacy Android Chrome",
      "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/119.0.0.0 Mobile Safari/537.36",
      "android-chrome",
    ],
    [
      "legacy iOS Safari",
      "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) Version/16.0 Mobile/15E148 Safari/604.1",
      "ios-safari",
    ],
    [
      "obsolete macOS Chrome",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
      "macos-chrome",
    ],
    [
      "obsolete macOS Safari",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
      "macos-safari",
    ],
    [
      "Windows Opera",
      "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36 OPR/120.0.0.0",
      "unknown",
    ],
    [
      "Android Samsung Internet",
      "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140.0.0.0 Mobile Safari/537.36 SamsungBrowser/28.0",
      "unknown",
    ],
    [
      "macOS Edge",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
      "unknown",
    ],
    [
      "iOS Chrome",
      "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 CriOS/140.0.0.0 Mobile/15E148 Safari/604.1",
      "unknown",
    ],
    [
      "embedded WeChat",
      "Mozilla/5.0 (Linux; Android 15) MicroMessenger/8.0 Chrome/140.0.0.0 Mobile",
      "embedded",
    ],
    ["unknown desktop", "Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0", "unknown"],
  ])("blocks %s", (_name, userAgent, browser) => {
    const result = detectBrowserSupport(userAgent);
    expect(result).toMatchObject({ supported: false, browser });
    expect(result.reason).toBeTruthy();
  });

  it("explains the supported desktop and mobile browsers for unknown clients", () => {
    const result = detectBrowserSupport("Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0");

    expect(result.reason).toContain("macOS Chrome/Safari");
    expect(result.reason).toContain("Windows Edge/Chrome");
    expect(result.reason).toContain("Android Chrome");
    expect(result.reason).toContain("iOS Safari");
  });

  it("keeps embedded detection ahead of otherwise supported Chrome", () => {
    const result = detectBrowserSupport(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MicroMessenger/8.0 Chrome/140.0.0.0 Safari/537.36",
    );

    expect(result).toMatchObject({ supported: false, browser: "embedded" });
    expect(result.reason).toContain("内嵌浏览器");
  });

  it("does not treat macOS Edge as Chrome", () => {
    const result = detectBrowserSupport(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    );

    expect(result).toMatchObject({ supported: false, browser: "unknown" });
  });
});
