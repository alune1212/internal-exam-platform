import { Suspense, lazy, type ComponentType } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";

import { AdminLayout } from "@/components/layout/AdminLayout";
import { CandidateLayout } from "@/components/layout/CandidateLayout";

function lazyNamed<T extends ComponentType<object>>(
  loader: () => Promise<Record<string, T>>,
  exportName: string,
) {
  return lazy(async () => ({ default: (await loader())[exportName] }));
}

function routeElement(Component: ComponentType) {
  return (
    <Suspense
      fallback={
        <div className="p-6 text-caption uppercase tracking-[0.16em] text-muted" role="status">
          Loading
        </div>
      }
    >
      <Component />
    </Suspense>
  );
}

const LoginPage = lazyNamed(() => import("@/pages/LoginPage"), "LoginPage");
const PracticePage = lazyNamed(() => import("@/pages/PracticePage"), "PracticePage");
const ExamListPage = lazyNamed(() => import("@/pages/ExamListPage"), "ExamListPage");
const ExamStartPage = lazyNamed(() => import("@/pages/ExamStartPage"), "ExamStartPage");
const ExamTakingPage = lazyNamed(() => import("@/pages/ExamTakingPage"), "ExamTakingPage");
const ExamResultPage = lazyNamed(() => import("@/pages/ExamResultPage"), "ExamResultPage");
const AdminLoginPage = lazyNamed(() => import("@/pages/admin/AdminLoginPage"), "AdminLoginPage");
const AdminDashboardPage = lazyNamed(
  () => import("@/pages/admin/AdminDashboardPage"),
  "AdminDashboardPage",
);
const QuestionListPage = lazyNamed(
  () => import("@/pages/admin/QuestionListPage"),
  "QuestionListPage",
);
const QuestionImportPage = lazyNamed(
  () => import("@/pages/admin/QuestionImportPage"),
  "QuestionImportPage",
);
const AdminExamListPage = lazyNamed(
  () => import("@/pages/admin/ExamListPage"),
  "AdminExamListPage",
);
const ExamEditPage = lazyNamed(() => import("@/pages/admin/ExamEditPage"), "ExamEditPage");
const ExamCandidatesPage = lazyNamed(
  () => import("@/pages/admin/ExamCandidatesPage"),
  "ExamCandidatesPage",
);
const ScoreReportPage = lazyNamed(() => import("@/pages/admin/ScoreReportPage"), "ScoreReportPage");
const QuestionAccuracyPage = lazyNamed(
  () => import("@/pages/admin/QuestionAccuracyPage"),
  "QuestionAccuracyPage",
);
const WrongQuestionPage = lazyNamed(
  () => import("@/pages/admin/WrongQuestionPage"),
  "WrongQuestionPage",
);
const AbsentCandidatePage = lazyNamed(
  () => import("@/pages/admin/AbsentCandidatePage"),
  "AbsentCandidatePage",
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <CandidateLayout />,
    children: [
      { index: true, element: <Navigate to="/login" replace /> },
      { path: "login", element: routeElement(LoginPage) },
      { path: "practice", element: routeElement(PracticePage) },
      { path: "exams", element: routeElement(ExamListPage) },
      { path: "exams/:examId/start", element: routeElement(ExamStartPage) },
      { path: "exams/:examId/taking", element: routeElement(ExamTakingPage) },
      { path: "exams/:examId/result", element: routeElement(ExamResultPage) },
    ],
  },
  { path: "/admin/login", element: routeElement(AdminLoginPage) },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: "dashboard", element: routeElement(AdminDashboardPage) },
      { path: "questions", element: routeElement(QuestionListPage) },
      { path: "questions/import", element: routeElement(QuestionImportPage) },
      { path: "exams", element: routeElement(AdminExamListPage) },
      { path: "exams/:examId/edit", element: routeElement(ExamEditPage) },
      { path: "exams/:examId/candidates", element: routeElement(ExamCandidatesPage) },
      { path: "reports/scores", element: routeElement(ScoreReportPage) },
      { path: "reports/questions", element: routeElement(QuestionAccuracyPage) },
      { path: "reports/wrong", element: routeElement(WrongQuestionPage) },
      { path: "reports/absent", element: routeElement(AbsentCandidatePage) },
    ],
  },
]);
