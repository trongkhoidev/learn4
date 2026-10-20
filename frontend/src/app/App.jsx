import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import PublicLayout from "../layouts/PublicLayout.jsx";
import SpeakingLayout from "../layouts/SpeakingLayout.jsx";
import StudentLayout from "../layouts/StudentLayout.jsx";
import TeacherLayout from "../layouts/TeacherLayout.jsx";

const ClassDetail = lazy(() => import("../features/classes/pages/ClassDetail.jsx"));
const Dashboard = lazy(() => import("../features/classes/pages/TeacherDashboard.jsx"));
const StudentHome = lazy(() => import("../features/classes/pages/StudentHome.jsx"));
const AssignmentBuilder = lazy(() => import("../features/assignments/pages/AssignmentBuilder.jsx"));
const DoAssignment = lazy(() => import("../features/assignments/pages/DoAssignment.jsx"));
const Join = lazy(() => import("../features/access/pages/Join.jsx"));
const SpeakingDashboard = lazy(() => import("../features/speaking/pages/SpeakingDashboard.jsx"));
const SpeakingPractice = lazy(() => import("../features/speaking/pages/SpeakingPractice.jsx"));
const SpeakingMockTest = lazy(() => import("../features/speaking/pages/SpeakingMockTest.jsx"));
const SpeakingHistory = lazy(() => import("../features/speaking/pages/SpeakingHistory.jsx"));

export default function App() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-gray-500">Đang tải...</div>}>
      <Routes>
        <Route path="/" element={<Navigate to="/speaking" replace />} />
        <Route path="/student" element={<Navigate to="/speaking" replace />} />
        <Route element={<PublicLayout />}>
          <Route path="/join" element={<Join />} />
        </Route>
        <Route element={<TeacherLayout />}>
          <Route path="/teacher" element={<Dashboard />} />
          <Route path="/teacher/class/:classId" element={<ClassDetail />} />
          <Route path="/teacher/class/:classId/new" element={<AssignmentBuilder />} />
          <Route path="/teacher/class/:classId/edit/:assignmentId" element={<AssignmentBuilder />} />
        </Route>
        <Route element={<StudentLayout />}>
          <Route path="/student/:classId" element={<StudentHome />} />
          <Route path="/student/:classId/assignment/:assignmentId" element={<DoAssignment />} />
        </Route>
        <Route element={<SpeakingLayout />}>
          <Route path="/speaking" element={<SpeakingDashboard />} />
          <Route path="/speaking/practice" element={<SpeakingPractice />} />
          <Route path="/speaking/practice/:topicId" element={<SpeakingPractice />} />
          <Route path="/speaking/mock-test" element={<SpeakingMockTest />} />
          <Route path="/speaking/mock-test/:testId" element={<SpeakingMockTest />} />
          <Route path="/speaking/history" element={<SpeakingHistory />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
