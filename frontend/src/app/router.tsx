import { Navigate, createBrowserRouter } from "react-router-dom";

import { AdminLayout } from "@/components/layout/AdminLayout";
import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { ExamListPage } from "@/pages/ExamListPage";
import { ExamResultPage } from "@/pages/ExamResultPage";
import { ExamStartPage } from "@/pages/ExamStartPage";
import { ExamTakingPage } from "@/pages/ExamTakingPage";
import { LoginPage } from "@/pages/LoginPage";
import { PracticePage } from "@/pages/PracticePage";
import { RankingPage } from "@/pages/RankingPage";
import { AbsentCandidatePage } from "@/pages/admin/AbsentCandidatePage";
import { AdminDashboardPage } from "@/pages/admin/AdminDashboardPage";
import { AdminExamListPage } from "@/pages/admin/ExamListPage";
import { AdminLoginPage } from "@/pages/admin/AdminLoginPage";
import { CandidateImportPage } from "@/pages/admin/CandidateImportPage";
import { ExamEditPage } from "@/pages/admin/ExamEditPage";
import { QuestionAccuracyPage } from "@/pages/admin/QuestionAccuracyPage";
import { QuestionImportPage } from "@/pages/admin/QuestionImportPage";
import { QuestionListPage } from "@/pages/admin/QuestionListPage";
import { ScoreReportPage } from "@/pages/admin/ScoreReportPage";
import { WrongQuestionPage } from "@/pages/admin/WrongQuestionPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <CandidateLayout />,
    children: [
      { index: true, element: <Navigate to="/login" replace /> },
      { path: "login", element: <LoginPage /> },
      { path: "practice", element: <PracticePage /> },
      { path: "exams", element: <ExamListPage /> },
      { path: "exams/:examId/start", element: <ExamStartPage /> },
      { path: "exams/:examId/taking", element: <ExamTakingPage /> },
      { path: "exams/:examId/result", element: <ExamResultPage /> },
      { path: "exams/:examId/ranking", element: <RankingPage /> },
    ],
  },
  { path: "/admin/login", element: <AdminLoginPage /> },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: "dashboard", element: <AdminDashboardPage /> },
      { path: "questions", element: <QuestionListPage /> },
      { path: "questions/import", element: <QuestionImportPage /> },
      { path: "exams", element: <AdminExamListPage /> },
      { path: "exams/:examId/edit", element: <ExamEditPage /> },
      { path: "exams/:examId/candidates", element: <CandidateImportPage /> },
      { path: "reports/scores", element: <ScoreReportPage /> },
      { path: "reports/questions", element: <QuestionAccuracyPage /> },
      { path: "reports/wrong", element: <WrongQuestionPage /> },
      { path: "reports/absent", element: <AbsentCandidatePage /> },
    ],
  },
]);
