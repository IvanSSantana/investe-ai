import { useState, type SubmitEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRegister } from "../../queries/useAuth";
import { ApiError } from "../../api/client";

const MIN_PASSWORD_LENGTH = 8; 

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const navigate = useNavigate();
  const registerMutation = useRegister();

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (password.length < MIN_PASSWORD_LENGTH) {
      setValidationError(`A senha deve ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres.`);
      return;
    }

    if (password !== confirmPassword) {
      setValidationError("As senhas não coincidem.");
      return;
    }

    registerMutation.mutate(
      { email, password },
      { onSuccess: () => navigate("/dashboard", { replace: true }) },
    );
  };

  const errorMessage =
    validationError ??
    (registerMutation.error instanceof ApiError
      ? registerMutation.error.detail
      : registerMutation.isError
        ? "Falha ao criar conta. Tente novamente."
        : null);

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 320, margin: "80px auto" }}>
      <h1>Criar conta</h1>

      <input
        type="email"
        placeholder="E-mail"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        autoComplete="email"
      />

      <input
        type="password"
        placeholder={`Senha (mínimo ${MIN_PASSWORD_LENGTH} caracteres)`}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        minLength={MIN_PASSWORD_LENGTH}
      />

      <input
        type="password"
        placeholder="Confirme a senha"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
        minLength={MIN_PASSWORD_LENGTH}
      />

      <button type="submit" disabled={registerMutation.isPending}>
        {registerMutation.isPending ? "Criando conta…" : "Criar conta"}
      </button>

      {errorMessage && <p style={{ color: "crimson" }}>{errorMessage}</p>}

      <p style={{ fontSize: 14, marginTop: 16 }}>
        Já tem conta?{" "}
        <Link to="/login">Entrar</Link>
      </p>
    </form>
  );
}