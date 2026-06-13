import { Wordmark } from "@/components/editorial/Wordmark";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-footer text-footer-soft">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 md:flex-row md:items-start md:justify-between md:px-8 md:py-12">
        <div className="flex flex-col gap-3">
          <Wordmark size="sm" tone="dark" subtitle="internal exam platform" />
          <p className="max-w-sm text-body-sm">内部临时考试与刷题平台 · 轻量、可信、留有纸感。</p>
        </div>
        <div className="flex flex-col gap-2 text-body-sm md:items-end">
          <p className="text-caption tracking-[0.16em]">CONTACT</p>
          <a href="mailto:internal-exam@example.com" className="transition-colors hover:text-white">
            internal-exam@example.com
          </a>
          <p className="text-caption">© {year} ZHISHI</p>
        </div>
      </div>
    </footer>
  );
}
