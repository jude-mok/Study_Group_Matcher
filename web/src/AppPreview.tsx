import { Monitor, Smartphone } from "lucide-react";
import { Logo } from "./ui";
export default function AppPreview({ back }: { back: () => void }) {
  return (
    <section className="app-preview-page" aria-label="App version">
      <header className="preview-toolbar">
        <Logo />
        <div className="view-switch">
          <button onClick={back}>
            <Monitor size={16} />
            Web
          </button>
          <button className="selected" aria-pressed="true">
            <Smartphone size={16} />
            App
          </button>
        </div>
      </header>
      <div className="preview-stage">
        <div className="preview-intro">
          <span className="eyebrow">THE ORIGINAL APP</span>
          <h1>
            Same idea.
            <br />A familiar view.
          </h1>
          <p>
            Explore the original Study Matcher app. Find a group, open a chat,
            and make plans together.
          </p>
          <button className="button primary" onClick={back}>
            Back to web version
          </button>
        </div>
        <div className="preview-device">
          <iframe
            title="Original Study Matcher app — interactive demo"
            src="/app-version/index.html"
          />
        </div>
      </div>
      <div className="preview-note">
        Interactive app demo · Sample data · App and web demos are separate;
        refreshing resets changes.
      </div>
    </section>
  );
}
