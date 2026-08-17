import type { Exam } from "@/types/exam";

import { Field, FieldLabel } from "@/components/ui/field";
import { Select } from "@/components/ui/select";

export type ExamReportFilterProps = {
  exams: Exam[];
  value: string | null;
  onChange: (value: string | null) => void;
};

export function ExamReportFilter({ exams, value, onChange }: ExamReportFilterProps) {
  return (
    <Field data-report-filter="" className="w-full min-w-0 sm:w-auto sm:min-w-56">
      <FieldLabel htmlFor="exam-report-filter">考试</FieldLabel>
      <Select
        id="exam-report-filter"
        value={value ?? "all"}
        onChange={(event) => onChange(event.target.value === "all" ? null : event.target.value)}
      >
        <option value="all">全部考试</option>
        {exams.map((exam) => (
          <option key={exam.id} value={String(exam.id)}>
            {exam.title}
          </option>
        ))}
      </Select>
    </Field>
  );
}
