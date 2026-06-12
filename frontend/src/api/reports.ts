import { apiRequest } from "@/api/client";
import type {
  AbsentCandidateRow,
  QuestionAccuracyRow,
  ScoreReportRow,
  WrongQuestionRow,
} from "@/types/report";

export function getScoreReport() {
  return apiRequest<ScoreReportRow[]>("/api/admin/reports/scores");
}

export function getQuestionAccuracy() {
  return apiRequest<QuestionAccuracyRow[]>("/api/admin/reports/question-accuracy");
}

export function getWrongQuestions() {
  return apiRequest<WrongQuestionRow[]>("/api/admin/reports/wrong-questions");
}

export function getAbsentCandidates() {
  return apiRequest<AbsentCandidateRow[]>("/api/admin/reports/absent-candidates");
}
