import { VERSION } from "@sns-calendar/shared-types";
import { Button } from "@sns-calendar/ui";
import type { HealthResponse } from "../generated";

const dummyHealthResponse: HealthResponse = { status: "ok", version: "0.1.0" };

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-sand px-6">
      <div className="w-full max-w-xl rounded-2xl border border-brand-ink/10 bg-white p-10 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-brand-ocean">
          WEB-001 Scaffold
        </p>
        <h1 className="mt-4 text-4xl font-semibold text-brand-ink">
          Hello SNS Calendar
        </h1>
        <p className="mt-4 text-base text-slate-600">
          Shared types version: <span className="font-mono">{VERSION}</span>
        </p>
        <p className="mt-2 text-base text-slate-600">
          OpenAPI health version:{" "}
          <span className="font-mono">{dummyHealthResponse.version}</span>
        </p>
        <div className="mt-8">
          <Button type="button">UI Package Button</Button>
        </div>
      </div>
    </main>
  );
}
