import { PageState } from "@/components/page";
import type { BrowserSupport } from "@/lib/browserSupport";

export function UnsupportedBrowserNotice({ support }: { support: BrowserSupport }) {
  return (
    <main
      data-testid="unsupported-browser"
      data-browser={support.browser}
      className="flex min-h-screen items-center justify-center bg-canvas-warm px-page-inline py-page-block md:px-page-inline-lg"
    >
      <div className="w-full max-w-xl rounded-lg border border-error bg-canvas p-8 shadow-pop">
        <PageState
          state="error"
          surface="inherit"
          eyebrow="浏览器限制"
          title="请更换受支持的系统浏览器。"
          description={support.reason}
        />
        <p className="mt-4 text-body-sm text-muted">
          支持 Windows Edge/Chrome（120 及以上）、macOS Chrome（120 及以上）/Safari（17
          及以上）、Android Chrome（120 及以上）和 iOS Safari（17
          及以上）；微信等内嵌浏览器不能用于正式考试。
        </p>
      </div>
    </main>
  );
}
