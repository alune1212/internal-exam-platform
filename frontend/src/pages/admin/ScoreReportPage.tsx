import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getRanking, getScoreReport } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { adminPageCopy, adminPageText, adminTableCopy } from "@/lib/pageCopy";
import type { ScoreReportRow } from "@/types/report";

type ScoreReportDisplayRow = ScoreReportRow & { rank: number | null };

const columns: ColumnDef<ScoreReportDisplayRow>[] = [
  {
    accessorKey: "rank",
    header: "RANK · 名次",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.rank ?? "-"}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "名次" },
  },
  {
    accessorKey: "roster_name",
    header: "ROSTER NAME · 名单姓名",
    cell: ({ row }) => <span className="font-medium">{row.original.roster_name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "名单姓名" },
  },
  {
    accessorKey: "roster_email",
    header: "ROSTER EMAIL · 名单邮箱",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.roster_email}</span>,
    meta: { mobileLabel: "名单邮箱" },
  },
  {
    accessorKey: "department",
    header: adminTableCopy.department,
    cell: ({ row }) => row.original.department ?? "-",
    meta: { mobileLabel: adminTableCopy.department },
  },
  {
    accessorKey: "exam_title",
    header: adminTableCopy.exam,
    meta: { mobileLabel: adminTableCopy.exam },
  },
  {
    accessorKey: "score",
    header: adminTableCopy.score,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {row.original.score} / {row.original.total_score}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.score },
  },
  {
    accessorKey: "total_score",
    header: adminTableCopy.totalScore,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_score}</span>
    ),
    meta: { mobilePriority: false },
  },
];

export function ScoreReportPage() {
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });
  const [selectedExamId, setSelectedExamId] = useState<string | null | undefined>(undefined);
  const examsLoadError = exams.isError && !exams.data;
  const examsPending = selectedExamId === undefined && !examsLoadError;

  useEffect(() => {
    if (selectedExamId !== undefined || !exams.data) {
      return;
    }
    setSelectedExamId(exams.data[0] ? String(exams.data[0].id) : null);
  }, [exams.data, selectedExamId]);

  return (
    <ReportPage
      title={adminPageText.reports.score.title}
      chapterLabel={adminPageCopy.reports}
      description={adminPageText.reports.score.description}
      queryKey={[
        "admin",
        "score-report",
        selectedExamId,
        examsLoadError ? "exams-error" : examsPending ? "exams-loading" : "exams-ready",
      ]}
      queryEnabled={!examsPending}
      isLoading={examsPending}
      queryFn={async () => {
        if (examsLoadError) {
          throw new Error("考试列表加载失败");
        }
        const scores = await getScoreReport(selectedExamId ?? null);
        if (!selectedExamId) {
          return scores.map((row) => ({ ...row, rank: null }));
        }
        const ranking = await getRanking(selectedExamId);
        const rankByCandidate = new Map(ranking.map((row) => [row.candidate_id, row.rank]));
        return scores.map((row) => ({
          ...row,
          rank: rankByCandidate.get(row.candidate_id) ?? null,
        }));
      }}
      columns={columns}
      actions={
        examsLoadError || examsPending ? null : (
          <>
            <ExamReportFilter
              exams={exams.data ?? []}
              value={selectedExamId ?? null}
              onChange={setSelectedExamId}
            />
            <ReportExportButton examId={selectedExamId ?? null} />
          </>
        )
      }
    />
  );
}
