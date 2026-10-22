import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Login from "./routes/login/Login";
import Register from "./routes/register/Register";
import TickerDetail from "./routes/ticker-detail/TickerDetail";
import { RequireAuth } from "./components/RequireAuth";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/fiis/:ticker"
            element={
              <RequireAuth>
                <TickerDetail />
              </RequireAuth>
            }
          />
          <Route path="/" element={<Navigate to="/fiis/mxrf11" replace />} />
          <Route path="*" element={<Navigate to="/fiis/mxrf11" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}