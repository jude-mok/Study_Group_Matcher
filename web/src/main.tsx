import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import PasswordReset, { readRecoveryLink } from "./PasswordReset";
import "./styles.css";

const recovery = readRecoveryLink(new URL(window.location.href));
if (recovery) {
  // Consume credentials once and remove them from the address bar/history.
  history.replaceState(null, "", location.pathname + "?reset=1");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {recovery ? (
      <main className="recovery-page">
        <PasswordReset
          recovery
          token={recovery.token}
          onDone={() => {
            window.location.replace(location.pathname + "?signin=1");
          }}
        />
      </main>
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
