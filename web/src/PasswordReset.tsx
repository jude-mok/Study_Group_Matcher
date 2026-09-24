import { useState, type FormEvent } from "react";
import {
  ApiError,
  requestPasswordReset,
  confirmPasswordReset,
  setSession,
} from "./api";
import { Submit } from "./ui";

export function readRecoveryLink(url: URL) {
  const hash = new URLSearchParams(url.hash.slice(1));
  const active =
    url.searchParams.get("reset") === "1" || hash.get("type") === "recovery";
  if (!active) return null;
  return {
    token: hash.get("type") === "recovery" ? hash.get("access_token") : null,
  };
}

export default function PasswordReset({
  token,
  recovery = false,
  onDone,
}: {
  token?: string | null;
  recovery?: boolean;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [complete, setComplete] = useState(false);
  const [invalid, setInvalid] = useState(recovery && !token);
  const [requestAgain, setRequestAgain] = useState(false);
  const changing = recovery && !requestAgain;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    const password = String(form.get("password") || "");
    if (changing && password !== form.get("confirm")) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      if (changing) {
        await confirmPasswordReset(password, token!);
        setSession(null);
        setComplete(true);
      } else {
        await requestPasswordReset(String(form.get("email") || "").trim());
        setSent(true);
      }
    } catch (err) {
      if (
        changing &&
        err instanceof ApiError &&
        [401, 403].includes(err.status)
      ) {
        setInvalid(true);
      } else setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Password reset">
      <h2>
        {complete
          ? "Password updated"
          : changing
            ? "Choose a new password"
            : "Reset your password"}
      </h2>
      {complete ? (
        <p role="status">
          Your password has been updated. Sign in with your new password.
        </p>
      ) : invalid && changing ? (
        <>
          <p role="alert">
            This reset link is invalid or has expired. Request a new email to
            continue.
          </p>
          <button
            className="button primary"
            onClick={() => {
              setRequestAgain(true);
              setInvalid(false);
              setError("");
            }}
          >
            Request a new link
          </button>
        </>
      ) : sent ? (
        <p role="status">
          If an account exists for that email, a reset link will arrive shortly.
          Check your inbox and spam folder.
        </p>
      ) : (
        <form className="form-stack" onSubmit={submit}>
          <p>
            {changing
              ? "Use at least 8 characters."
              : "Enter your NYU email and we’ll send you a reset link."}
          </p>
          {changing ? (
            <>
              <label>
                New password
                <input
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  disabled={busy}
                />
              </label>
              <label>
                Confirm new password
                <input
                  name="confirm"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  disabled={busy}
                />
              </label>
            </>
          ) : (
            <label>
              NYU email
              <input
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@nyu.edu"
                required
                disabled={busy}
              />
            </label>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <Submit busy={busy}>
            {changing ? "Update password" : "Send reset link"}
          </Submit>
        </form>
      )}
      <button className="text-button" disabled={busy} onClick={onDone}>
        {complete ? "Continue to sign in" : "Back to sign in"}
      </button>
    </section>
  );
}
