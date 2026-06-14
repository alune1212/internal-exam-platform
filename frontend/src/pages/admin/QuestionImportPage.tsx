import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { useState } from "react";

import { importQuestions } from "@/api/imports";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ImportFailure } from "@/types/imports";

export function QuestionImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: importQuestions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-questions"] });
    },
  });

  return (
    <div className="flex max-w-3xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 03 · LIBRARY</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold tracking-[-0.04em] text-ink lg:text-[40px]">
          题库导入
        </h1>
        <p className="text-body text-body-lg">
          仅支持标准 Excel（.xlsx / .xls），不解析 Word。导入前请先下载模板，按列填写题目。
        </p>
      </header>

      <section className="flex flex-col gap-5 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
        <p className="text-caption italic text-muted">
          模板格式见 docs/import-templates.md · Template format lives in the docs.
        </p>

        <Input
          type="file"
          accept=".xlsx,.xls"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          aria-label="选择 Excel 文件"
        />

        <Button
          type="button"
          size="lg"
          className="self-start"
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate(file)}
        >
          <FileUp data-icon="inline-start" />
          {mutation.isPending ? "正在导入..." : "上传并校验"}
        </Button>
      </section>

      {mutation.data ? (
        <section className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-6 shadow-card">
          <p className="text-body text-ink">
            成功 <span className="font-mono">{mutation.data.success_count}</span> 行，失败{" "}
            <span className="font-mono text-error">{mutation.data.failed_count}</span> 行
          </p>
          {mutation.data.failures.length ? (
            <ul className="flex flex-col gap-1 border-t border-hairline-soft pt-3 text-caption text-muted">
              {mutation.data.failures.map((failure: ImportFailure) => (
                <li key={failure.row_number} className="font-mono">
                  行 {failure.row_number} · {failure.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
