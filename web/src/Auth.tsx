import PasswordReset from "./PasswordReset";
import { useState, type FormEvent } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  BookOpen,
  CalendarDays,
  MessageCircle,
  Smartphone,
  Users,
  Sparkles,
} from "lucide-react";
import { API_URL, login, signup } from "./api";
import { Logo, Modal, readText, Submit } from "./ui";
import type { User } from "./types";

export default function Auth({
  enterDemo,
  enterLive,
  showApp,
}: {
  enterDemo: () => void;
  enterLive: (user: User) => void;
  showApp: () => void;
}) {
  const [mode, setMode] = useState<"login" | "signup" | "reset" | null>(() =>
    new URLSearchParams(location.search).get("signin") === "1" ? "login" : null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const nyu_email = readText(form, "email");
      const password = String(form.get("password") || "");
      if (mode === "signup") {
        await signup({
          nyu_email,
          password,
          name: readText(form, "name"),
          nyu_id: readText(form, "nyu_id"),
          major: readText(form, "major"),
          academic_standing: Number(form.get("year")),
          work_willingness: Number(form.get("effort")),
          preferred_location: readText(form, "location"),
          time_preference: readText(form, "time"),
        });
        setMode("login");
        setNotice("Account created. Sign in to find your group.");
      } else enterLive(await login(nyu_email, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo />
        <nav className="landing-links" aria-label="Website navigation">
          <a href="#how-it-works">How it works</a>
          <button className="app-version-link" onClick={showApp}>
            <Smartphone size={17} /> App version
          </button>
          <button
            className="button soft"
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            Sign in
          </button>
        </nav>
      </header>
      <main>
        <section className="landing-main">
          <div className="hero-copy">
            <span className="intro-pill">
              <span className="small-dot" /> A better way to study at NYU
            </span>
            <h1>
              Your people.
              <br />
              Your pace.
              <br />
              <span>Better together.</span>
            </h1>
            <p className="hero-description">
              Find a group that gets you.
              <br />
              Turn shared classes into shared progress.
            </p>
            <div className="hero-actions">
              <button className="button primary large" onClick={enterDemo}>
                Try the web demo <ArrowRight size={20} />
              </button>
              <button className="button soft large" onClick={showApp}>
                <Smartphone size={19} /> View app version
              </button>
            </div>
            <p className="fine-print">
              <Check size={14} /> No account or download needed
            </p>
          </div>
          <div
            className="hero-visual"
            aria-label="Example of a recommended study group"
          >
            <div className="visual-halo" />
            <div className="floating-symbol book-symbol">
              <BookOpen strokeWidth={1.8} />
            </div>
            <div className="floating-symbol chat-symbol">
              <MessageCircle strokeWidth={1.8} />
            </div>
            <div className="match-preview">
              <div className="preview-heading">
                <span className="preview-icon">
                  <Users size={25} />
                </span>
                <div>
                  <strong>Your next study group</strong>
                  <span>Made for the way you learn</span>
                </div>
                <Sparkles size={22} />
              </div>
              <div className="match-preview-body">
                <span className="course-pill">DATA STRUCTURES</span>
                <h2>The problem-solving club</h2>
                <div className="compatibility">
                  <span>Study compatibility</span>
                  <strong>
                    94<span>%</span>
                  </strong>
                </div>
                <div className="match-track">
                  <span />
                </div>
                <div className="match-tags">
                  <span>
                    <Check size={13} /> Same course
                  </span>
                  <span>
                    <Check size={13} /> Shared goals
                  </span>
                </div>
              </div>
              <div className="match-preview-footer">
                <div className="avatar-row">
                  <span className="avatar peach">M</span>
                  <span className="avatar green">S</span>
                  <span className="avatar lavender">J</span>
                </div>
                <span>3 people. One shared goal.</span>
                <ArrowUpRight size={19} />
              </div>
            </div>
            <div className="session-preview">
              <span className="session-check">
                <Check size={20} strokeWidth={3} />
              </span>
              <div>
                <strong>It’s a plan.</strong>
                <span>Study session · Tomorrow, 4 PM</span>
              </div>
              <CalendarDays size={20} />
            </div>
            <span className="visual-caption">
              A LOOK INSIDE THE DEMO · SAMPLE DATA
            </span>
          </div>
        </section>
        <section className="benefit-strip">
          <span>
            <BookOpen size={20} /> Your courses, your community
          </span>
          <span>
            <Users size={20} /> A group that fits your style
          </span>
          <span>
            <CalendarDays size={20} /> Plans that come together
          </span>
        </section>
        <section className="how-section" id="how-it-works">
          <p className="section-kicker">LESS COORDINATING. MORE LEARNING.</p>
          <h2>
            From “anyone want to study?”
            <br />
            to “see you there.”
          </h2>
          <p className="section-description">
            Everything you need to find your group and make it happen.
          </p>
          <div className="feature-grid">
            <article className="feature-card">
              <span className="feature-icon mint">
                <BookOpen size={28} />
              </span>
              <span className="feature-step">01 · FIND YOUR PEOPLE</span>
              <h3>
                Start with what
                <br />
                you have in common.
              </h3>
              <p>
                Add your classes. Discover groups with similar goals, habits,
                and study preferences.
              </p>
              <div className="feature-mini">
                <span className="mini-book">DS</span>
                <div>
                  <strong>Data Structures</strong>
                  <span>Same class. New connections.</span>
                </div>
                <Check size={18} />
              </div>
            </article>
            <article className="feature-card">
              <span className="feature-icon lilac">
                <MessageCircle size={28} />
              </span>
              <span className="feature-step">02 · BREAK THE ICE</span>
              <h3>
                A quick hello.
                <br />A better study session.
              </h3>
              <p>
                Join a group and jump into the conversation. Questions are
                always welcome.
              </p>
              <div className="mini-chat">
                <span>Working on the graph problems?</span>
                <span>Let’s figure it out together 👋</span>
              </div>
            </article>
            <article className="feature-card">
              <span className="feature-icon apricot">
                <CalendarDays size={28} />
              </span>
              <span className="feature-step">03 · MAKE IT HAPPEN</span>
              <h3>
                Pick a time.
                <br />
                We’ll save your spot.
              </h3>
              <p>
                Propose a session, vote on a time, and keep the plan on your
                shared calendar.
              </p>
              <div className="mini-vote">
                <span>
                  <Check size={16} /> Everyone’s in
                </span>
                <strong>Added to your calendar</strong>
              </div>
            </article>
          </div>
        </section>
        <section className="app-callout">
          <div>
            <span className="section-kicker">
              ONE PROJECT. TWO WAYS TO EXPLORE.
            </span>
            <h2>
              Made for the web.
              <br />
              Started on mobile.
            </h2>
            <p>
              Explore the original app screens, or try the new web experience.
            </p>
          </div>
          <button className="button soft" onClick={showApp}>
            <Smartphone size={19} /> View app version <ArrowUpRight size={18} />
          </button>
        </section>
        <section className="final-cta">
          <span className="cta-mark">
            <Users size={35} />
          </span>
          <h2>
            Your next group
            <br />
            is a good place to start.
          </h2>
          <p>Take a look around. No sign-up needed.</p>
          <button className="button primary large" onClick={enterDemo}>
            Explore the web demo <ArrowRight size={20} />
          </button>
        </section>
      </main>
      <footer className="landing-footer">
        <Logo />
        <span>A student-built project. Not affiliated with NYU.</span>
        <button className="text-button" onClick={showApp}>
          Original app <ArrowUpRight size={15} />
        </button>
      </footer>
      {mode && (
        <Modal
          title={
            mode === "login"
              ? "Welcome back."
              : mode === "reset"
                ? "Account recovery"
                : "Find your study people."
          }
          busy={busy}
          close={() => setMode(null)}
        >
          {!API_URL ? (
            <div className="connection-notice">
              <h3>Account mode is coming next.</h3>
              <p>
                This preview is ready to explore with sample data. Live accounts
                need the study server to be connected.
              </p>
              <button className="button primary" onClick={enterDemo}>
                Explore the demo <ArrowRight size={16} />
              </button>
            </div>
          ) : mode === "reset" ? (
            <PasswordReset
              onDone={() => {
                setMode("login");
                setError("");
              }}
            />
          ) : (
            <form onSubmit={submit} className="form-stack">
              {mode === "signup" && (
                <>
                  <div className="form-grid">
                    <label>
                      Name
                      <input
                        name="name"
                        autoComplete="name"
                        required
                        maxLength={80}
                      />
                    </label>
                    <label>
                      NYU ID
                      <input name="nyu_id" required />
                    </label>
                  </div>
                  <label>
                    Major
                    <input name="major" required />
                  </label>
                  <div className="form-grid">
                    <label>
                      Year
                      <select name="year">
                        <option value="1">First year</option>
                        <option value="2">Sophomore</option>
                        <option value="3">Junior</option>
                        <option value="4">Senior</option>
                      </select>
                    </label>
                    <label>
                      Study intensity (1–10)
                      <input
                        name="effort"
                        type="number"
                        min="1"
                        max="10"
                        defaultValue="7"
                        required
                      />
                    </label>
                  </div>
                  <div className="form-grid">
                    <label>
                      Preferred place
                      <select name="location">
                        <option>Bobst Library</option>
                        <option>Kimmel Center</option>
                        <option>Off-campus</option>
                      </select>
                    </label>
                    <label>
                      Best time
                      <select name="time">
                        <option value="morning">Morning</option>
                        <option value="afternoon">Afternoon / evening</option>
                      </select>
                    </label>
                  </div>
                </>
              )}
              <label>
                NYU email
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@nyu.edu"
                  pattern="[^@\s]+@nyu\.edu"
                  required
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  minLength={8}
                  required
                />
              </label>
              {mode === "login" && (
                <button
                  type="button"
                  className="text-button"
                  disabled={busy}
                  onClick={() => {
                    setMode("reset");
                    setError("");
                  }}
                >
                  Forgot password?
                </button>
              )}
              {error && (
                <p role="alert" className="form-error">
                  {error}
                </p>
              )}
              {notice && (
                <p role="status" className="form-success">
                  {notice}
                </p>
              )}
              {busy && (
                <p className="fine-print" role="status">
                  Connecting… the server may need a moment to wake up.
                </p>
              )}
              <Submit busy={busy}>
                {mode === "login" ? "Sign in" : "Create account"}
              </Submit>
              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() => {
                  setMode(mode === "login" ? "signup" : "login");
                  setError("");
                  setNotice("");
                }}
              >
                {mode === "login"
                  ? "New here? Create an account"
                  : "Already have an account? Sign in"}
              </button>
            </form>
          )}
        </Modal>
      )}
    </div>
  );
}
