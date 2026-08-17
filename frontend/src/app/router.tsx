import { Suspense, lazy, type ComponentType } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";

import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { CANDIDATE_PRESENTATION_HANDLE } from "@/components/layout/candidate-presentation-mode";
import { RouteErrorPage } from "@/components/page";

function lazyNamed<T extends ComponentType<object>>(
  loader: () => Promise<Record<string, T>>,
  exportName: string,
) {
  return lazy(async () => ({ default: (await loader())[exportName] }));
}

function routeElement(Component: ComponentType) {
  return (
    <Suspense fallback={<ContentSkeleton rows={2} showCaption variant="page" />}>
      <Component />
    </Suspense>
  );
}

const LoginPage = lazyNamed(() => import("@/pages/LoginPage"), "LoginPage");
const RegistrationPage = lazyNamed(() => import("@/pages/RegistrationPage"), "RegistrationPage");
const ProfilePage = lazyNamed(() => import("@/pages/ProfilePage"), "ProfilePage");
const LearningListPage = lazyNamed(() => import("@/pages/LearningListPage"), "LearningListPage");
const LearningVideoPage = lazyNamed(() => import("@/pages/LearningVideoPage"), "LearningVideoPage");
const PracticePage = lazyNamed(() => import("@/pages/PracticePage"), "PracticePage");
const WrongQuestionReviewPage = lazyNamed(
  () => import("@/pages/WrongQuestionReviewPage"),
  "WrongQuestionReviewPage",
);
const ExamListPage = lazyNamed(() => import("@/pages/ExamListPage"), "ExamListPage");
const ExamStartPage = lazyNamed(() => import("@/pages/ExamStartPage"), "ExamStartPage");
const ExamTakingPage = lazyNamed(() => import("@/pages/ExamTakingPage"), "ExamTakingPage");
const ExamResultPage = lazyNamed(() => import("@/pages/ExamResultPage"), "ExamResultPage");
const AdminLoginPage = lazyNamed(() => import("@/pages/admin/AdminLoginPage"), "AdminLoginPage");
const AdminDashboardPage = lazyNamed(
  () => import("@/pages/admin/AdminDashboardPage"),
  "AdminDashboardPage",
);
const AccountDirectoryPage = lazyNamed(
  () => import("@/pages/admin/AccountDirectoryPage"),
  "AccountDirectoryPage",
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
const AdminExamWorkspacePage = lazyNamed(
  () => import("@/pages/admin/ExamWorkspacePage"),
  "ExamWorkspacePage",
);
const ExamEditPage = lazyNamed(() => import("@/pages/admin/ExamEditPage"), "ExamEditPage");
const ExamCandidatesPage = lazyNamed(
  () => import("@/pages/admin/ExamCandidatesPage"),
  "ExamCandidatesPage",
);
const AdminLearningVideoPage = lazyNamed(
  () => import("@/pages/admin/LearningVideoPage"),
  "AdminLearningVideoPage",
);
const AdminLearningReportPage = lazyNamed(
  () => import("@/pages/admin/LearningReportPage"),
  "AdminLearningReportPage",
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
const OperationsPage = lazyNamed(() => import("@/pages/admin/OperationsPage"), "OperationsPage");
const AbsentCandidatePage = lazyNamed(
  () => import("@/pages/admin/AbsentCandidatePage"),
  "AbsentCandidatePage",
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <CandidateLayout />,
    errorElement: <RouteErrorPage safePath="/login" />,
    children: [
      { index: true, element: <Navigate to="/login" replace /> },
      { path: "login", element: routeElement(LoginPage) },
      { path: "register", element: routeElement(RegistrationPage) },
      { path: "profile", element: routeElement(ProfilePage) },
      { path: "learning", element: routeElement(LearningListPage) },
      { path: "learning/:videoId", element: routeElement(LearningVideoPage) },
      { path: "practice", element: routeElement(PracticePage) },
      { path: "practice/wrong-questions", element: routeElement(WrongQuestionReviewPage) },
      { path: "exams", element: routeElement(ExamListPage) },
      { path: "exams/:examId/start", element: routeElement(ExamStartPage) },
      {
        path: "exams/:examId/taking",
        element: routeElement(ExamTakingPage),
        handle: { [CANDIDATE_PRESENTATION_HANDLE]: "focus" },
      },
      { path: "exams/:examId/result", element: routeElement(ExamResultPage) },
    ],
  },
  {
    path: "/admin/login",
    element: routeElement(AdminLoginPage),
    errorElement: <RouteErrorPage safePath="/admin/login" />,
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    errorElement: <RouteErrorPage safePath="/admin/dashboard" />,
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: "dashboard", element: routeElement(AdminDashboardPage) },
      { path: "accounts", element: routeElement(AccountDirectoryPage) },
      { path: "questions", element: routeElement(QuestionListPage) },
      { path: "questions/import", element: routeElement(QuestionImportPage) },
      { path: "exams", element: routeElement(AdminExamListPage) },
      { path: "exams/:examId", element: routeElement(AdminExamWorkspacePage) },
      { path: "exams/:examId/edit", element: routeElement(ExamEditPage) },
      { path: "exams/:examId/candidates", element: routeElement(ExamCandidatesPage) },
      { path: "learning", element: routeElement(AdminLearningVideoPage) },
      { path: "learning/reports", element: routeElement(AdminLearningReportPage) },
      { path: "reports/scores", element: routeElement(ScoreReportPage) },
      { path: "reports/questions", element: routeElement(QuestionAccuracyPage) },
      { path: "reports/wrong", element: routeElement(WrongQuestionPage) },
      { path: "reports/absent", element: routeElement(AbsentCandidatePage) },
      { path: "operations", element: routeElement(OperationsPage) },
    ],
  },
]);
