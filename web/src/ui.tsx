import { useEffect, useRef, type ReactNode } from "react";
import { ArrowUpRight, BookOpen, LoaderCircle, X } from "lucide-react";

export function Logo() {
  return (
    <span className="brand">
      <span className="brand-mark">
        <BookOpen size={21} />
      </span>
      study<span className="brand-light">matcher</span>
      <span className="brand-dot">.</span>
    </span>
  );
}
export function Spinner() {
  return <LoaderCircle className="spin" size={18} aria-label="Loading" />;
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <BookOpen size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Heading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <p className="muted">{children}</p>}
      </div>
      {action}
    </div>
  );
}
export function Modal({
  title,
  children,
  close,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    const el = ref.current;
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby="modal-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) close();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) close();
      }}
    >
      <div className="modal-head">
        <h2 id="modal-title">{title}</h2>
        <button
          className="icon-button"
          disabled={busy}
          onClick={close}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Submit({
  busy,
  children,
}: {
  busy: boolean;
  children: ReactNode;
}) {
  return (
    <button className="button primary" type="submit" disabled={busy}>
      {busy ? <Spinner /> : children}
      {!busy && <ArrowUpRight size={17} />}
    </button>
  );
}
export const dateLabel = (value: string) =>
  new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    weekday: "short",
  });
export const timeLabel = (value: string) =>
  new Date(value).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
export function readText(form: FormData, key: string) {
  return String(form.get(key) || "").trim();
}
export function times(form: FormData) {
  const start = new Date(readText(form, "start_time"));
  const end = new Date(readText(form, "end_time"));
  if (!Number.isFinite(+start) || !Number.isFinite(+end) || end <= start)
    throw new Error("Choose an end time after the start time.");
  return { start_time: start.toISOString(), end_time: end.toISOString() };
}
export function TimeFields() {
  return (
    <div className="form-grid">
      <label>
        Starts
        <input name="start_time" type="datetime-local" required />
      </label>
      <label>
        Ends
        <input name="end_time" type="datetime-local" required />
      </label>
    </div>
  );
}
