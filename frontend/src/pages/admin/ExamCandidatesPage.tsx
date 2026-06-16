import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import {
  createRetakeGrant,
  getAdminExams,
  getExamCandidates,
  importExamCandidates,
  removeExamCandidate,
} from "@/api/exams";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { StatusPill } from "@/components/editorial/StatusPill";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ExamCandidateRow } from "@/types/exam";
import type { ImportFailure } from "@/types/imports";

function scoreText(row: ExamCandidateRow) {
  if (row.latest_score == null || row.latest_total_score == null) {
    return "-";
  }
  return `${row.latest_score} / ${row.latest_total_score}`;
}

function statusVariant(status?: string | null) {
  if (status === "submitted" || status === "auto_submitted") return "success";
  if (status === "in_progress") return "warning";
  return "default";
}

export function ExamCandidatesPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();
  const candidatesKey = ["exam-candidates", examId];
  const exams = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });
  const currentExam = exams.data?.find((exam) => String(exam.id) === examId);
  const isFrozen = currentExam?.status === "active";
  const candidates = useQuery({
    queryKey: candidatesKey,
    queryFn: () => getExamCandidates(examId),
  });
  const importMutation = useMutation({
    mutationFn: (selected: File) => importExamCandidates(examId, selected),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
      void queryClient.invalidateQueries({ queryKey: ["absent-candidates"] });
    },
  });
  const retakeMutation = useMutation({
    mutationFn: (candidateId: number) => createRetakeGrant(examId, candidateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
    },
  });
  const removeMutation = useMutation({
    mutationFn: (candidateId: number) => removeExamCandidate(examId, candidateId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
    },
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
          应考人员名单
        </h1>
        <p className="text-body text-body-lg">
          本名单决定谁可以进入这场考试。考试发布后名单冻结，只保留补考授权操作。
        </p>
      </header>

      <section className="flex flex-col gap-4 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-caption uppercase tracking-[0.16em] text-muted">IMPORT</p>
            <p className="text-body text-ink">
              {isFrozen ? "考试已发布，不能再修改应考名单。" : "上传 Excel 后写入本场应考名单。"}
            </p>
          </div>
          <StatusPill variant={isFrozen ? "success" : "default"}>
            {currentExam?.status ?? "loading"}
          </StatusPill>
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <Input
            type="file"
            accept=".xlsx,.xls"
            disabled={isFrozen}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            aria-label="选择 Excel 文件"
          />
          <Button
            type="button"
            className="self-start"
            disabled={!file || importMutation.isPending || isFrozen}
            onClick={() => file && importMutation.mutate(file)}
          >
            <FileUp data-icon="inline-start" />
            {importMutation.isPending ? "正在导入..." : "上传应考人员"}
          </Button>
        </div>
        {importMutation.data ? (
          <p className="text-body-sm text-muted">
            成功 <span className="font-mono text-ink">{importMutation.data.success_count}</span>{" "}
            行，失败{" "}
            <span className="font-mono text-error">{importMutation.data.failed_count}</span> 行
          </p>
        ) : null}
        {importMutation.data?.failures.length ? (
          <ul className="flex flex-col gap-1 text-caption text-muted">
            {importMutation.data.failures.map((failure: ImportFailure) => (
              <li key={failure.row_number} className="font-mono">
                行 {failure.row_number} · {failure.reason}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="overflow-hidden rounded-lg border border-hairline bg-canvas shadow-card">
        <table className="w-full text-left text-body-sm">
          <thead className="border-b border-hairline bg-surface-card text-caption uppercase tracking-[0.16em] text-muted">
            <tr>
              <th className="px-4 py-3">NAME</th>
              <th className="px-4 py-3">DEPT</th>
              <th className="px-4 py-3">ATTEMPT</th>
              <th className="px-4 py-3">SCORE</th>
              <th className="px-4 py-3 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody>
            {(candidates.data ?? []).map((row) => (
              <tr key={row.candidate_id} className="border-b border-hairline-soft">
                <td className="px-4 py-3">
                  <span className="font-medium text-ink">{row.candidate_name}</span>
                  <span className="ml-2 font-mono text-caption text-muted">
                    {row.employee_no ?? "-"}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted">{row.department ?? "-"}</td>
                <td className="px-4 py-3">
                  <StatusPill variant={statusVariant(row.latest_attempt_status)}>
                    {row.latest_attempt_status ?? "not_started"}
                  </StatusPill>
                  {row.attempt_no ? (
                    <span className="ml-2 font-mono text-caption text-muted">
                      #{row.attempt_no} {row.attempt_kind}
                    </span>
                  ) : null}
                </td>
                <td className="px-4 py-3 font-mono tabular-nums">{scoreText(row)}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    {row.latest_attempt_status === "submitted" ||
                    row.latest_attempt_status === "auto_submitted" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant={row.has_unused_retake_grant ? "outline" : "default"}
                        disabled={row.has_unused_retake_grant || retakeMutation.isPending}
                        onClick={() => retakeMutation.mutate(row.candidate_id)}
                      >
                        <RotateCcw data-icon="inline-start" />
                        {row.has_unused_retake_grant ? "已授权" : "授权补考"}
                      </Button>
                    ) : null}
                    {!isFrozen ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={removeMutation.isPending}
                        onClick={() => removeMutation.mutate(row.candidate_id)}
                      >
                        <Trash2 data-icon="inline-start" />
                        移除
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!candidates.isLoading && !candidates.data?.length ? (
          <p className="p-6 text-body text-muted">暂无应考人员。</p>
        ) : null}
      </section>
    </div>
  );
}
