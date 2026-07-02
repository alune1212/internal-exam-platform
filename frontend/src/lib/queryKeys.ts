// Centralised query-key factories. Every cache key in the app must be
// constructed through these helpers so cross-identity cache leaks are
// impossible and invalidations can target a whole namespace via `.all`.

import { getCurrentCandidate } from "@/lib/candidateSession";

export const adminKeys = {
  all: ["admin"] as const,
  exams: () => [...adminKeys.all, "exams"] as const,
  exam: (id: number) => [...adminKeys.exams(), id] as const,
  examCandidates: (id: number) => [...adminKeys.exam(id), "candidates"] as const,
  examRetake: (id: number) => [...adminKeys.exam(id), "retake"] as const,
  questions: () => [...adminKeys.all, "questions"] as const,
  question: (id: number) => [...adminKeys.questions(), id] as const,
  reports: () => [...adminKeys.all, "reports"] as const,
  learning: () => [...adminKeys.all, "learning"] as const,
  learningVideos: () => [...adminKeys.learning(), "videos"] as const,
  learningReport: (videoId: string | null, status: string | null) =>
    [...adminKeys.learning(), "report", videoId, status] as const,
  scoreReport: (examId: number | null) => [...adminKeys.reports(), "score", examId] as const,
  accuracyReport: (examId: number | null) => [...adminKeys.reports(), "accuracy", examId] as const,
  wrongReport: (examId: number | null) => [...adminKeys.reports(), "wrong", examId] as const,
  absentReport: (examId: number | null) => [...adminKeys.reports(), "absent", examId] as const,
  absentCandidates: (examId: number | null, status: string) =>
    [...adminKeys.reports(), "absent", examId, status] as const,
  imports: () => [...adminKeys.all, "imports"] as const,
};

export const candidateKeys = {
  all: ["candidate"] as const,
  id: () => getCurrentCandidate()?.id ?? "anonymous",
  activeExams: () => [...candidateKeys.all, candidateKeys.id(), "active-exams"] as const,
  attempt: (id: number) => [...candidateKeys.all, candidateKeys.id(), "attempt", id] as const,
  result: (id: number) => [...candidateKeys.all, candidateKeys.id(), "result", id] as const,
  practice: () => [...candidateKeys.all, candidateKeys.id(), "practice"] as const,
  learningVideos: () => [...candidateKeys.all, candidateKeys.id(), "learning-videos"] as const,
  learningVideo: (id: number) =>
    [...candidateKeys.all, candidateKeys.id(), "learning-video", id] as const,
};
