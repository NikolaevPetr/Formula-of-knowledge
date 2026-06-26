import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";

import Login from "./pages/teacher/Login";
import Dashboard from "./pages/teacher/Dashboard";
import BankEditor from "./pages/teacher/BankEditor";
import RoomCreate from "./pages/teacher/RoomCreate";
import TeacherRoom from "./pages/teacher/TeacherRoom";
import Report from "./pages/teacher/Report";

import Join from "./pages/student/Join";
import StudentRoom from "./pages/student/StudentRoom";

function RequireTeacher({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/teacher/login" replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Студент */}
      <Route path="/" element={<Navigate to="/teacher/login" replace />} />
      <Route path="/join" element={<Join />} />
      <Route path="/join/:code" element={<Join />} />
      <Route path="/play/:code" element={<StudentRoom />} />

      {/* Преподаватель */}
      <Route path="/teacher/login" element={<Login />} />
      <Route
        path="/teacher"
        element={
          <RequireTeacher>
            <Dashboard />
          </RequireTeacher>
        }
      />
      <Route
        path="/teacher/banks/:bankId"
        element={
          <RequireTeacher>
            <BankEditor />
          </RequireTeacher>
        }
      />
      <Route
        path="/teacher/rooms/new"
        element={
          <RequireTeacher>
            <RoomCreate />
          </RequireTeacher>
        }
      />
      <Route
        path="/teacher/rooms/:roomId/manage/:code"
        element={
          <RequireTeacher>
            <TeacherRoom />
          </RequireTeacher>
        }
      />
      <Route
        path="/teacher/rooms/:roomId/report"
        element={
          <RequireTeacher>
            <Report />
          </RequireTeacher>
        }
      />
      <Route path="*" element={<Navigate to="/teacher/login" replace />} />
    </Routes>
  );
}
