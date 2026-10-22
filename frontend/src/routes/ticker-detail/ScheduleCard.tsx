import { useState, type SubmitEvent } from "react";
import { Card } from "../../components/ui/Card";
import { useScheduleEmail } from "../../queries/useFii";
import { errorMessage } from "../../helpers/errors";

export function ScheduleCard({ ticker }: { ticker: string }) {
  const [email, setEmail] = useState("");
  const [day, setDay] = useState(1);
  const [hour, setHour] = useState(9);
  const scheduleMutation = useScheduleEmail();

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    scheduleMutation.mutate(
      { ticker, email_to: email, day_of_month: day, hour },
      { onSuccess: () => setEmail("") },
    );
  };

  return (
    <Card title="Agendar envio mensal">
      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}
      >
        <input
          type="email"
          placeholder="E-mail de destino"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{ flex: "1 1 240px", padding: 8 }}
        />
        <label>
          Dia&nbsp;
          <input
            type="number"
            min={1}
            max={31}
            value={day}
            onChange={(e) => setDay(Number(e.target.value))}
            required
            style={{ width: 64, padding: 8 }}
          />
        </label>
        <label>
          Hora&nbsp;
          <input
            type="number"
            min={0}
            max={23}
            value={hour}
            onChange={(e) => setHour(Number(e.target.value))}
            required
            style={{ width: 64, padding: 8 }}
          />
        </label>
        <button type="submit" disabled={scheduleMutation.isPending}>
          {scheduleMutation.isPending ? "Agendando…" : "Agendar"}
        </button>
      </form>

      {scheduleMutation.isError && (
        <p style={{ color: "crimson", marginTop: 8 }}>
          {errorMessage(scheduleMutation.error, "Falha ao agendar.")}
        </p>
      )}
      {scheduleMutation.isSuccess && (
        <p style={{ color: "#065f46", marginTop: 8 }}>{scheduleMutation.data.message}</p>
      )}
    </Card>
  );
}