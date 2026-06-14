import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, Save, X } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const STATUS_OPTIONS = [
  { value: "draft", label: "DRAFT · 草稿", variant: "default" },
  { value: "active", label: "LIVE · 进行中", variant: "success" },
  { value: "archived", label: "ENDED · 已结束", variant: "warning" },
] as const;

const schema = z.object({
  title: z.string().min(1, "请输入考试名称"),
  duration_minutes: z.coerce.number().int().min(1, "时长必须 >= 1 分钟"),
  status: z.enum(["draft", "active", "archived"]),
  question_rule_json: z.string().min(2, "抽题规则不能为空"),
});

type ExamEditForm = z.infer<typeof schema>;

function StatusDropdown({
  value,
  onChange,
}: {
  value: ExamEditForm["status"];
  onChange: (next: ExamEditForm["status"]) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = STATUS_OPTIONS.find((status) => status.value === value) ?? STATUS_OPTIONS[0];

  return (
    <div className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        className="flex h-11 w-full items-center justify-between gap-2 rounded-md border border-hairline bg-canvas px-4 text-body text-ink hover:border-ink"
      >
        <span className="flex items-center gap-2">
          <StatusPill variant={current.variant as StatusPillVariant}>{current.value}</StatusPill>
          {current.label}
        </span>
        <ChevronDown className="h-4 w-4 text-muted" data-icon="inline-end" />
      </button>
      {open ? (
        <ul
          role="listbox"
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-hairline bg-surface-elev shadow-pop"
        >
          {STATUS_OPTIONS.map((option) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={option.value === value}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-4 py-2 text-left text-body hover:bg-surface-card",
                  option.value === value && "bg-surface-card",
                )}
              >
                <StatusPill variant={option.variant as StatusPillVariant}>
                  {option.value}
                </StatusPill>
                {option.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ExamEditPage() {
  const { examId } = useParams();
  const form = useForm<ExamEditForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "临时考试",
      duration_minutes: 60,
      status: "draft",
      question_rule_json: JSON.stringify({ counts: [5, 5, 2], total_score: 100 }, null, 2),
    },
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-3">
          <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
          <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
            编辑考试 #{examId ?? "-"}
          </h1>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/admin/exams">
              <X data-icon="inline-start" />
              取消
            </Link>
          </Button>
          <Button type="button" size="sm" onClick={form.handleSubmit(() => undefined)}>
            <Save data-icon="inline-start" />
            保存配置
          </Button>
        </div>
      </header>

      <section className="grid gap-6 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:grid-cols-2 lg:p-8">
        <div className="flex flex-col gap-2">
          <Label htmlFor="title">考试名称 · Title</Label>
          <Input id="title" {...form.register("title")} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="duration_minutes">时长（分钟）· Duration</Label>
          <Input
            id="duration_minutes"
            type="number"
            min={1}
            {...form.register("duration_minutes", { valueAsNumber: true })}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="status">状态 · Status</Label>
          <Controller
            control={form.control}
            name="status"
            render={({ field }) => <StatusDropdown value={field.value} onChange={field.onChange} />}
          />
        </div>
        <div className="flex flex-col gap-2 lg:col-span-2">
          <Label htmlFor="question_rule_json">抽题规则 · JSON</Label>
          <textarea
            id="question_rule_json"
            rows={8}
            spellCheck={false}
            className="w-full resize-y rounded-md border border-hairline bg-footer p-4 font-mono text-[12px] leading-relaxed text-footer-soft focus:border-ink focus:outline-none"
            {...form.register("question_rule_json")}
          />
        </div>
        <div className="flex flex-col gap-3 rounded-md bg-surface-card p-4 md:flex-row md:items-center md:justify-between lg:col-span-2">
          <div className="flex flex-col gap-1">
            <span className="text-caption uppercase tracking-[0.16em] text-muted">CANDIDATES</span>
            <span className="text-body text-ink">应考人员 · 在此页维护本场名单</span>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to={`/admin/exams/${examId ?? "1"}/candidates`}>管理应考</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
