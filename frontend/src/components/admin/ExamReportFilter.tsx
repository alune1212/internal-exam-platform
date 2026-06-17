import type { Exam } from "@/types/exam";

type ExamReportFilterProps = {
  exams: Exam[];
  value: string | null;
  onChange: (value: string | null) => void;
};

export function ExamReportFilter({ exams, value, onChange }: ExamReportFilterProps) {
  return (
    <label className="flex min-w-56 flex-col gap-2 text-caption uppercase tracking-[0.16em] text-muted">
      考试
      <select
        className="h-10 rounded-md border border-hairline bg-canvas px-3 text-body normal-case tracking-normal text-ink"
        value={value ?? "all"}
        onChange={(event) => onChange(event.target.value === "all" ? null : event.target.value)}
      >
        <option value="all">全部考试</option>
        {exams.map((exam) => (
          <option key={exam.id} value={String(exam.id)}>
            {exam.title}
          </option>
        ))}
      </select>
    </label>
  );
}
