import { useState, type SubmitEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLogin } from "../../queries/useAuth";
import { ApiError } from "../../api/client";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const loginMutation = useLogin();

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    loginMutation.mutate(
      { email, password },
      { onSuccess: () => navigate("/dashboard", { replace: true }) },
    );
  };

  const errorMessage =
    loginMutation.error instanceof ApiError
      ? loginMutation.error.detail
      : loginMutation.isError
        ? "Falha no login."
        : null;

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 320, margin: "80px auto" }}>
      <h1>Entrar</h1>
      <input
        type="email"
        placeholder="Digite seu e-mail..."
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        autoComplete="email"
      />
      <input
        type="password"
        placeholder="Digite sua senha..."
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit" disabled={loginMutation.isPending}>
        {loginMutation.isPending ? "Entrando…" : "Entrar"}
      </button>
      
      {errorMessage && <p style={{ color: "crimson" }}>{errorMessage}</p>}

      <p style={{ fontSize: 14, marginTop: 16 }}>
        Não tem uma conta?{" "}
        <Link to="/register">Criar conta</Link>
      </p>
    </form>
  );
}