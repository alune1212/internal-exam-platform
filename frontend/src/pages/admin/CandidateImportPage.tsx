import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { importCandidates } from "@/api/imports";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ImportFailure } from "@/types/imports";

export function CandidateImportPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (selected: File) => importCandidates(examId, selected),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["absent-candidates"] });
    },
  });

  return (
    <div data-stagger className="flex max-w-3xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold italic tracking-[-0.04em] text-ink lg:text-display-xl">
          应考人员导入
        </h1>
        <p className="text-body-lg">
          未参加人员名单 = 应考人员 - 已提交考试人员。导入前请按模板填写。
        </p>
      </header>

      <section className="flex flex-col gap-5 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
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
          {mutation.isPending ? "正在导入..." : "上传应考人员"}
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
