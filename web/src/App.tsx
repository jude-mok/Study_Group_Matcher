import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  Check,
  Compass,
  LayoutDashboard,
  LogOut,
  MapPin,
  MessageCircle,
  Plus,
  Search,
  Settings2,
  Sparkles,
  Smartphone,
  Users,
  X,
} from "lucide-react";
import Auth from "./Auth";
import AppPreview from "./AppPreview";
import Chat from "./Chat";
import { api, getSession, setSession } from "./api";
import { demoUser } from "./demo";
import { createService } from "./service";
import {
  dateLabel,
  Empty,
  Heading,
  Logo,
  Modal,
  readText,
  Spinner,
  Submit,
  TimeFields,
  timeLabel,
  times,
} from "./ui";
import type { Course, Group, Snapshot, User } from "./types";

type Page =
  | "overview"
  | "discover"
  | "groups"
  | "courses"
  | "calendar"
  | "messages"
  | "profile";
const navigation = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "discover", label: "Find a group", icon: Compass },
  { id: "groups", label: "My groups", icon: Users },
  { id: "messages", label: "Messages", icon: MessageCircle },
  { id: "calendar", label: "Calendar", icon: CalendarDays },
  { id: "courses", label: "My courses", icon: BookOpen },
] as const;

export default function App() {
  const [appView, setAppView] = useState(
    () => new URLSearchParams(location.search).get("view") === "app",
  );
  const [appOpened, setAppOpened] = useState(appView);
  const showApp = () => {
    setAppOpened(true);
    setAppView(true);
  };
  const [mode, setMode] = useState<"live" | "demo" | null>(() =>
    getSession() ? "live" : null,
  );
  const [user, setUser] = useState<User | null>(
    () => getSession()?.user || null,
  );
  useEffect(() => {
    const changed = () => {
      const current = getSession();
      if (current) setUser(current.user);
      else if (mode === "live") {
        setMode(null);
        setUser(null);
      }
    };
    window.addEventListener("study-session", changed);
    return () => window.removeEventListener("study-session", changed);
  }, [mode]);
  const content =
    !mode || !user ? (
      <Auth
        showApp={showApp}
        enterDemo={() => {
          setUser({ ...demoUser });
          setMode("demo");
        }}
        enterLive={(value) => {
          setUser(value);
          setMode("live");
        }}
      />
    ) : (
      <Workspace
        key={`${mode}:${user.id}`}
        showApp={showApp}
        demo={mode === "demo"}
        user={user}
        updateUser={setUser}
        exit={() => {
          if (mode === "live") setSession(null);
          setMode(null);
          setUser(null);
        }}
      />
    );
  return (
    <>
      <div hidden={appView}>{content}</div>
      {appOpened && (
        <div hidden={!appView}>
          <AppPreview back={() => setAppView(false)} />
        </div>
      )}
    </>
  );
}

function Workspace({
  showApp,
  demo,
  user,
  updateUser,
  exit,
}: {
  showApp: () => void;
  demo: boolean;
  user: User;
  updateUser: (user: User) => void;
  exit: () => void;
}) {
  const service = useMemo(() => createService(demo), [demo]);
  const [page, setPage] = useState<Page>("overview");
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState<"create" | "schedule" | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [room, setRoom] = useState<string | null>(null);
  const [formError, setFormError] = useState("");
  const refresh = useCallback(async () => {
    setData(await service.snapshot());
  }, [service]);
  useEffect(() => {
    let active = true;
    service
      .snapshot()
      .then((value) => {
        if (active) setData(value);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [service]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(timer);
  }, [notice]);
  function go(next: Page) {
    setPage(next);
    setError("");
    setSearch("");
    setFilter("all");
  }
  async function act(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
      setNotice(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  async function submitModal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setFormError("");
    try {
      if (modal === "create")
        await service.create({
          name: readText(form, "name"),
          course_id: Number(form.get("course_id")),
          max_members: Number(form.get("max_members")),
          location: readText(form, "location"),
        });
      else
        await service.schedule({
          title: readText(form, "title"),
          ...times(form),
          location: readText(form, "location"),
          group_id: readText(form, "group_id") || null,
        });
      await refresh();
      setModal(null);
      setNotice(
        modal === "create"
          ? "Your group is ready. Start the conversation in Messages."
          : "Added to your calendar.",
      );
      setPage(modal === "create" ? "groups" : "calendar");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  const courseFor = (id: number) => data?.courses.find((c) => c.id === id);
  const openRoom = (group: Group) => {
    const next = data?.rooms.find((r) => r.group_id === group.id);
    if (next) {
      setRoom(next.id);
      go("messages");
    } else
      setError("The chat room is not available. Please refresh and try again.");
  };
  const upcoming =
    data?.schedules
      .filter((s) => Date.parse(s.end_time) >= Date.now())
      .sort((a, b) => Date.parse(a.start_time) - Date.parse(b.start_time)) ||
    [];
  const matched =
    data?.recommendations.filter(
      (g) =>
        (filter === "all" || g.course_id === Number(filter)) &&
        `${g.name} ${courseFor(g.course_id)?.course_name}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    ) || [];
  const addButton = (
    <button
      className="button primary"
      onClick={() => {
        setFormError("");
        setModal("create");
      }}
      disabled={!data?.courses.length}
    >
      <Plus size={17} /> Create a group
    </button>
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          className="brand-button"
          onClick={() => go("overview")}
          aria-label="Study Matcher home"
        >
          <Logo />
        </button>
        <span className="sidebar-caption">A LITTLE BETTER, TOGETHER</span>
        <nav aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={`nav-link ${page === item.id ? "active" : ""}`}
              onClick={() => go(item.id)}
              aria-current={page === item.id ? "page" : undefined}
            >
              <item.icon size={19} />
              {item.label}
              {item.id === "groups" && !!data?.groups.length && (
                <span className="nav-count">{data.groups.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="note-star">✳</span>
          <h3>
            Good company.
            <br />
            Better questions.
          </h3>
          <p>Make a little room for learning together.</p>
        </div>
        <div className="sidebar-bottom">
          <button
            className={`nav-link ${page === "profile" ? "active" : ""}`}
            onClick={() => go("profile")}
          >
            <Settings2 size={18} /> Study preferences
          </button>
          <button className="nav-link" onClick={exit}>
            <LogOut size={18} />
            {demo ? "Exit demo" : "Sign out"}
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="breadcrumb">
            Your campus <span>/</span>{" "}
            {navigation.find((n) => n.id === page)?.label || "Preferences"}
          </span>
          <div className="topbar-right">
            <button className="text-button" onClick={showApp}>
              <Smartphone size={16} />
              App version
            </button>
            <span className="mode-pill">
              <span className="small-dot" />
              {demo ? "Demo workspace" : "NYU community"}
            </span>
            <button
              className="avatar green"
              onClick={() => go("profile")}
              aria-label="Open profile"
            >
              {user.name.charAt(0).toUpperCase()}
            </button>
          </div>
        </header>
        {demo && (
          <div className="demo-banner">
            <Sparkles size={15} />
            <span>
              You’re exploring sample data. Changes last until you leave or
              refresh.
            </span>
            <button onClick={exit}>
              Use an account <ArrowUpRight size={13} />
            </button>
          </div>
        )}
        <main className="workspace-main" id="main-content">
          {error && (
            <div className="alert" role="alert">
              <span>{error}</span>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => void act(refresh, "Workspace refreshed.")}
              >
                Try again
              </button>
              <button
                className="icon-button"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <Check size={17} />
              {notice}
            </div>
          )}
          {loading ? (
            <div className="loading-state">
              <Spinner />
              <h2>Getting your workspace ready.</h2>
              <p>The server may need a moment to wake up.</p>
            </div>
          ) : !data ? (
            <Empty title="We couldn’t load your workspace.">
              Check your connection, then use Try again above.
            </Empty>
          ) : (
            <>
              {page === "overview" && (
                <>
                  <Heading
                    eyebrow="YOUR SPACE TO FIND YOUR PEOPLE"
                    title={`Good to see you, ${user.name.split(" ")[0]}.`}
                    action={addButton}
                  >
                    A shared class is a good place to start.
                  </Heading>
                  <section className="welcome-panel">
                    <div>
                      <span className="eyebrow">LESS STUDYING ALONE</span>
                      <h2>
                        A good group changes
                        <br />
                        <em>the whole semester.</em>
                      </h2>
                      <p>Find people who learn a little like you do.</p>
                      <button
                        className="button cream"
                        onClick={() => go("discover")}
                      >
                        Find your next group <ArrowUpRight size={18} />
                      </button>
                    </div>
                    <div className="welcome-drawing" aria-hidden="true">
                      <div className="draw-circle circle-a">you</div>
                      <div className="draw-circle circle-b">ideas</div>
                      <div className="draw-circle circle-c">people</div>
                      <span>
                        better,
                        <br />
                        together.
                      </span>
                    </div>
                  </section>
                  <div className="stats-row">
                    <button onClick={() => go("courses")}>
                      <BookOpen size={21} />
                      <strong>{data.enrollments.length}</strong>
                      <span>Courses on your list</span>
                      <ArrowUpRight size={16} />
                    </button>
                    <button onClick={() => go("groups")}>
                      <Users size={21} />
                      <strong>{data.groups.length}</strong>
                      <span>Groups to grow with</span>
                      <ArrowUpRight size={16} />
                    </button>
                    <button onClick={() => go("calendar")}>
                      <CalendarDays size={21} />
                      <strong>{upcoming.length}</strong>
                      <span>Plans to look forward to</span>
                      <ArrowUpRight size={16} />
                    </button>
                  </div>
                  <div className="section-title">
                    <div>
                      <span className="eyebrow">
                        A FEW GOOD STARTING POINTS
                      </span>
                      <h2>Groups you might click with</h2>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => go("discover")}
                    >
                      View all <ArrowRight size={16} />
                    </button>
                  </div>
                  <div className="cards-grid">
                    {data.recommendations.slice(0, 3).map((g, i) => (
                      <GroupCard
                        key={g.id}
                        group={g}
                        course={courseFor(g.course_id)}
                        index={i}
                        busy={busy}
                        onAction={() =>
                          void act(
                            () => service.join(g.id),
                            "You joined the group. Head to My groups to meet everyone.",
                          )
                        }
                      />
                    ))}
                  </div>
                  {!data.recommendations.length && (
                    <Empty title="Your next group starts with a course.">
                      Add your classes in My courses. If there are no matching
                      groups yet, start one.
                    </Empty>
                  )}
                  <div className="section-title">
                    <h2>Coming up</h2>
                    <button
                      className="text-button"
                      onClick={() => go("calendar")}
                    >
                      Open calendar <ArrowRight size={16} />
                    </button>
                  </div>
                  {upcoming.slice(0, 2).map((s) => (
                    <div className="event-row" key={s.id}>
                      <div className="date-square">
                        <span>
                          {new Date(s.start_time).toLocaleDateString("en-US", {
                            month: "short",
                          })}
                        </span>
                        <strong>{new Date(s.start_time).getDate()}</strong>
                      </div>
                      <div>
                        <h3>{s.title}</h3>
                        <p>
                          {timeLabel(s.start_time)} – {timeLabel(s.end_time)} ·{" "}
                          {s.location || "Location to be decided"}
                        </p>
                      </div>
                      <span className="subtle-pill">
                        {s.group_id ? "Group session" : "Personal"}
                      </span>
                    </div>
                  ))}
                  {!upcoming.length && (
                    <p className="muted">
                      A little breathing room. Make a plan in Calendar or
                      propose a group session in Messages.
                    </p>
                  )}
                </>
              )}
              {page === "discover" && (
                <>
                  <Heading
                    eyebrow="MAKE A CONNECTION"
                    title="Find your kind of group."
                    action={addButton}
                  >
                    Recommendations based on your courses and study preferences.
                  </Heading>
                  <div className="filter-bar">
                    <label className="search-field">
                      <Search size={18} />
                      <input
                        aria-label="Search recommended groups"
                        placeholder="Search groups or courses"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                    <select
                      aria-label="Filter by course"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    >
                      <option value="all">All your courses</option>
                      {data.courses
                        .filter((c) =>
                          data.enrollments.some((e) => e.course_id === c.id),
                        )
                        .map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.course_name}
                          </option>
                        ))}
                    </select>
                  </div>
                  <p className="result-count">
                    {matched.length} groups to get to know{" "}
                    {demo && "· illustrative match scores"}
                  </p>
                  <div className="cards-grid">
                    {matched.map((g, i) => (
                      <GroupCard
                        key={g.id}
                        group={g}
                        course={courseFor(g.course_id)}
                        index={i}
                        busy={busy}
                        onAction={() =>
                          void act(
                            () => service.join(g.id),
                            "You joined the group. Find it in My groups.",
                          )
                        }
                      />
                    ))}
                  </div>
                  {!matched.length && (
                    <Empty title="No groups here just yet.">
                      Try another search, add a course, or start a group of your
                      own.
                    </Empty>
                  )}
                </>
              )}
              {page === "groups" && (
                <>
                  <Heading
                    eyebrow="YOUR PEOPLE"
                    title="A place at the table."
                    action={addButton}
                  >
                    The groups you’re learning with.
                  </Heading>
                  <div className="cards-grid">
                    {data.groups.map((g, i) => (
                      <GroupCard
                        key={g.id}
                        group={g}
                        course={courseFor(g.course_id)}
                        index={i}
                        busy={busy}
                        member
                        onAction={() => openRoom(g)}
                      />
                    ))}
                  </div>
                  {!data.groups.length && (
                    <Empty title="Your first group is waiting.">
                      Find a group in your courses, or create one and invite
                      your classmates.
                    </Empty>
                  )}
                </>
              )}
              {page === "courses" && (
                <>
                  <Heading
                    eyebrow="YOUR SHARED STARTING POINT"
                    title="What are you learning?"
                  >
                    Add a course to discover groups studying the same things.
                  </Heading>
                  <label className="search-field standalone">
                    <Search size={18} />
                    <input
                      aria-label="Search courses"
                      placeholder="Search course name or code"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                  <div className="course-list">
                    {data.courses
                      .filter((c) =>
                        `${c.course_name} ${c.course_code}`
                          .toLowerCase()
                          .includes(search.toLowerCase()),
                      )
                      .map((c) => {
                        const enrolled = data.enrollments.some(
                          (e) => e.course_id === c.id,
                        );
                        return (
                          <div className="course-row" key={c.id}>
                            <div className="course-icon">
                              <BookOpen size={23} />
                            </div>
                            <div>
                              <span className="eyebrow">{c.course_code}</span>
                              <h3>{c.course_name}</h3>
                              {enrolled && (
                                <p>
                                  {data.enrollments
                                    .filter((e) => e.course_id === c.id)
                                    .map((e) => `${e.term} ${e.year}`)
                                    .join(" · ")}
                                </p>
                              )}
                            </div>
                            <button
                              className={`button ${enrolled ? "outline" : "primary"}`}
                              disabled={busy}
                              onClick={() =>
                                void act(
                                  () =>
                                    enrolled
                                      ? service.unenroll(c.id)
                                      : service.enroll(
                                          c.id,
                                          new Date().getMonth() < 5
                                            ? "Spring"
                                            : new Date().getMonth() < 8
                                              ? "Summer"
                                              : "Fall",
                                          new Date().getFullYear(),
                                        ),
                                  enrolled
                                    ? "Course removed from your list."
                                    : "Course added. Your recommendations are ready.",
                                )
                              }
                            >
                              {enrolled ? (
                                <>
                                  <Check size={16} /> Remove course
                                </>
                              ) : (
                                <>
                                  <Plus size={16} /> Add course
                                </>
                              )}
                            </button>
                          </div>
                        );
                      })}
                  </div>
                  {!data.courses.some((c) =>
                    `${c.course_name} ${c.course_code}`
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  ) && (
                    <Empty title="No courses found.">
                      Try a different course name or code.
                    </Empty>
                  )}
                </>
              )}
              {page === "calendar" && (
                <>
                  <Heading
                    eyebrow="MAKE TIME FOR IT"
                    title="Good plans start here."
                    action={
                      <button
                        className="button primary"
                        onClick={() => {
                          setFormError("");
                          setModal("schedule");
                        }}
                      >
                        <Plus size={17} /> Add a plan
                      </button>
                    }
                  >
                    Your personal plans and confirmed group sessions. Times are
                    shown in your timezone.
                  </Heading>
                  <div className="calendar-list">
                    {[...data.schedules]
                      .sort(
                        (a, b) =>
                          Date.parse(a.start_time) - Date.parse(b.start_time),
                      )
                      .map((s) => (
                        <div
                          className={`event-row ${Date.parse(s.end_time) < Date.now() ? "past-event" : ""}`}
                          key={s.id}
                        >
                          <div className="date-square">
                            <span>
                              {new Date(s.start_time).toLocaleDateString(
                                "en-US",
                                { month: "short" },
                              )}
                            </span>
                            <strong>{new Date(s.start_time).getDate()}</strong>
                          </div>
                          <div>
                            <span className="eyebrow">
                              {dateLabel(s.start_time)} ·{" "}
                              {s.group_id ? "Group session" : "Personal plan"}
                            </span>
                            <h3>{s.title}</h3>
                            <p>
                              {timeLabel(s.start_time)} –{" "}
                              {timeLabel(s.end_time)} ·{" "}
                              {s.location || "Location to be decided"}
                            </p>
                          </div>
                          {s.created_by === user.id && (
                            <button
                              className="icon-button"
                              aria-label={`Delete ${s.title}`}
                              disabled={busy}
                              onClick={() => {
                                if (window.confirm(`Delete “${s.title}”?`))
                                  void act(
                                    () => service.deleteSchedule(s.id),
                                    "Plan deleted.",
                                  );
                              }}
                            >
                              <X size={18} />
                            </button>
                          )}
                        </div>
                      ))}
                  </div>
                  {!data.schedules.length && (
                    <Empty title="A fresh page on your calendar.">
                      Add a personal plan, or vote on a group session in
                      Messages.
                    </Empty>
                  )}
                </>
              )}
              {page === "messages" && (
                <Chat
                  key={room || "default"}
                  demo={demo}
                  user={user}
                  service={service}
                  data={data}
                  initialRoom={room}
                  onChange={() =>
                    void refresh().catch((err) => setError(err.message))
                  }
                  onLeave={(id) =>
                    void act(async () => {
                      await service.leave(id);
                      setRoom(null);
                      go("groups");
                    }, "You left the group.")
                  }
                />
              )}
              {page === "profile" && (
                <>
                  <Heading
                    eyebrow="HOW YOU LIKE TO LEARN"
                    title="A little more about you."
                  >
                    Your preferences help find compatible study groups.
                  </Heading>
                  <form
                    className="profile-form form-stack"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void act(
                        async () => {
                          const input = {
                            name: readText(form, "name"),
                            major: readText(form, "major"),
                            academic_standing: Number(
                              form.get("academic_standing"),
                            ),
                            work_willingness: Number(
                              form.get("work_willingness"),
                            ),
                            preferred_location: readText(
                              form,
                              "preferred_location",
                            ),
                            time_preference: readText(form, "time_preference"),
                            ...(readText(form, "avg_gpa")
                              ? { avg_gpa: Number(form.get("avg_gpa")) }
                              : {}),
                          };
                          const updated = demo
                            ? { ...user, ...input }
                            : await api<User>("/users/me", "PUT", input);
                          if (!demo && getSession())
                            setSession({ ...getSession()!, user: updated });
                          updateUser(updated);
                        },
                        demo
                          ? "Demo preferences updated. Example match scores stay fixed."
                          : "Preferences updated.",
                      );
                    }}
                  >
                    <div className="form-grid">
                      <label>
                        Name
                        <input name="name" defaultValue={user.name} required />
                      </label>
                      <label>
                        Major
                        <input
                          name="major"
                          defaultValue={user.major}
                          required
                        />
                      </label>
                    </div>
                    <div className="form-grid">
                      <label>
                        Year in school
                        <select
                          name="academic_standing"
                          defaultValue={user.academic_standing}
                        >
                          {[1, 2, 3, 4].map((n) => (
                            <option key={n} value={n}>
                              Year {n}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Study intensity (1–10)
                        <input
                          name="work_willingness"
                          type="number"
                          min="1"
                          max="10"
                          defaultValue={user.work_willingness}
                          required
                        />
                      </label>
                      <label>
                        Preferred location
                        <select
                          name="preferred_location"
                          defaultValue={
                            user.preferred_location || "Bobst Library"
                          }
                        >
                          <option>Bobst Library</option>
                          <option>Kimmel Center</option>
                          <option>Off-campus</option>
                        </select>
                      </label>
                      <label>
                        Time preference
                        <select
                          name="time_preference"
                          defaultValue={user.time_preference || "afternoon"}
                        >
                          <option value="morning">Morning</option>
                          <option value="afternoon">Afternoon / evening</option>
                        </select>
                      </label>
                    </div>
                    <label>
                      GPA (optional)
                      <input
                        name="avg_gpa"
                        type="number"
                        min="0"
                        max="4"
                        step="0.01"
                        defaultValue={user.avg_gpa ?? ""}
                      />
                      <span className="fine-print">
                        Used in compatibility scoring. Leave blank to keep your
                        current value.
                      </span>
                    </label>
                    <Submit busy={busy}>Save preferences</Submit>
                  </form>
                  <button className="text-button profile-exit" onClick={exit}>
                    <LogOut size={16} />
                    {demo ? "Exit demo" : "Sign out"}
                  </button>
                </>
              )}
            </>
          )}
        </main>
        <footer className="workspace-footer">
          <span>Built for the way we learn together.</span>
          <span>Study Matcher · Student project</span>
        </footer>
      </div>
      {modal && (
        <Modal
          title={
            modal === "create"
              ? "Make room for your people."
              : "Put a little time aside."
          }
          busy={busy}
          close={() => setModal(null)}
        >
          <form className="form-stack" onSubmit={submitModal}>
            {modal === "create" ? (
              <>
                <label>
                  Group name
                  <input
                    name="name"
                    placeholder="e.g. Sunday problem solvers"
                    required
                    maxLength={100}
                  />
                </label>
                <label>
                  Course
                  <select name="course_id" required>
                    {data?.courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.course_name} · {c.course_code}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Maximum members
                  <input
                    name="max_members"
                    type="number"
                    min="2"
                    max="50"
                    defaultValue="5"
                    required
                  />
                </label>
              </>
            ) : (
              <>
                <label>
                  Plan title
                  <input
                    name="title"
                    required
                    maxLength={200}
                    placeholder="e.g. Midterm study session"
                  />
                </label>
                <label>
                  Who is it for?
                  <select name="group_id">
                    <option value="">Just me</option>
                    {data?.groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </label>
                <TimeFields />
              </>
            )}
            <label>
              Location
              <input
                name="location"
                placeholder="e.g. Bobst Library, floor 3"
                maxLength={200}
              />
            </label>
            {formError && (
              <p className="form-error" role="alert">
                {formError}
              </p>
            )}
            <Submit busy={busy}>
              {modal === "create" ? "Create group" : "Add to calendar"}
            </Submit>
          </form>
        </Modal>
      )}
    </div>
  );
}

function GroupCard({
  group,
  course,
  index,
  busy,
  member,
  onAction,
}: {
  group: Group;
  course?: Course;
  index: number;
  busy: boolean;
  member?: boolean;
  onAction: () => void;
}) {
  const full = (group.current_members || 0) >= group.max_members;
  return (
    <article className={`group-card tone-${index % 3}`}>
      <div className="card-top">
        <span className="course-pill">
          {course?.course_code || "STUDY GROUP"}
        </span>
        {!member && group.match_score !== undefined && (
          <span className="match-pill">
            <Sparkles size={12} />
            {Math.round(group.match_score)}% match
          </span>
        )}
      </div>
      <span className="card-course">
        {course?.course_name || "A shared course"}
      </span>
      <h3>{group.name}</h3>
      <p className="location">
        <MapPin size={15} />
        {group.location || "Choose a place together"}
      </p>
      {group.score_breakdown && (
        <details className="score-details">
          <summary>Why this match?</summary>
          <ul>
            {Object.entries(group.score_breakdown).map(([key, value]) => (
              <li key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <strong>{value} pts</strong>
              </li>
            ))}
          </ul>
        </details>
      )}
      <div className="card-bottom">
        <span>
          <Users size={16} />
          {group.current_members || 0} / {group.max_members} members
        </span>
        <button
          className="text-button"
          disabled={busy || (!member && full)}
          onClick={onAction}
        >
          {member ? "Open group" : full ? "Full" : "Join group"}
          <ArrowUpRight size={16} />
        </button>
      </div>
    </article>
  );
}
