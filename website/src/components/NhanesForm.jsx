import { useState } from "react";
import { Activity } from "lucide-react";
import { NHANES_GROUPS, emptyNhanes, toNhanesPayload } from "../data/nhanes";
import { Button, Field, Input, Select, Spinner } from "./ui";

export function NhanesForm({ onSubmit, submitLabel = "Get Prediction", dense = true }) {
  const [values, setValues] = useState(emptyNhanes);
  const [busy, setBusy] = useState(false);

  const set = (key, value) => setValues((prev) => ({ ...prev, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await onSubmit(toNhanesPayload(values));
    } finally {
      setBusy(false);
    }
  };

  const grid = dense
    ? "grid-cols-1 sm:grid-cols-2 xl:grid-cols-3"
    : "grid-cols-2";

  return (
    <form onSubmit={submit} className="space-y-5">
      {NHANES_GROUPS.map((group) => (
        <fieldset key={group.title} className="space-y-3">
          <legend className="w-full border-b border-outline-variant pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
            {group.title}
          </legend>
          <div className={`grid gap-3 ${grid}`}>
            {group.fields.map((field) => (
              <Field key={field.key} label={field.label} htmlFor={field.key}>
                {field.options ? (
                  <Select
                    id={field.key}
                    value={values[field.key]}
                    onChange={(e) => set(field.key, e.target.value)}
                  >
                    <option value="">Not recorded</option>
                    {field.options.map(([code, label]) => (
                      <option key={code} value={code}>
                        {code} — {label}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Input
                    id={field.key}
                    type="number"
                    step="any"
                    inputMode="decimal"
                    placeholder={field.unit ? `— ${field.unit}` : "—"}
                    value={values[field.key]}
                    onChange={(e) => set(field.key, e.target.value)}
                  />
                )}
              </Field>
            ))}
          </div>
        </fieldset>
      ))}

      <div className="flex items-center justify-between gap-3 border-t border-outline-variant pt-4">
        <p className="text-[11px] leading-tight text-on-surface-variant">
          Blank fields are sent as <span className="font-mono">null</span> and imputed by the
          serving pipeline.
        </p>
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? <Spinner /> : <Activity className="size-4" />}
          {busy ? "Running inference…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
