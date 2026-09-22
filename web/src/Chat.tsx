import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  CalendarDays,
  Check,
  MessageCircle,
  Plus,
  Send,
  Users,
} from "lucide-react";
import { refreshSession, socketUrl } from "./api";
import type { Service } from "./service";
import type { Member, Message, Proposal, Snapshot, User } from "./types";
import {
  dateLabel,
  Empty,
  Heading,
  Modal,
  readText,
  Spinner,
  Submit,
  TimeFields,
  timeLabel,
  times,
} from "./ui";

export function mergeMessages(previous: Message[], incoming: Message[]) {
  return [
    ...new Map(
      [...previous, ...incoming].map((message) => [message.id, message]),
    ).values(),
  ].sort(
    (a, b) =>
      Date.parse(a.created_at) - Date.parse(b.created_at) ||
      a.id.localeCompare(b.id),
  );
}

export default function Chat({
  demo,
  user,
  service,
  data,
  initialRoom,
  onChange,
  onLeave,
}: {
  demo: boolean;
  user: User;
  service: Service;
  data: Snapshot;
  initialRoom: string | null;
  onChange: () => void;
  onLeave: (id: string) => void;
}) {
  const [roomId, setRoomId] = useState(initialRoom || data.rooms[0]?.id || "");
  const [messages, setMessages] = useState<Message[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [status, setStatus] = useState("Connecting");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [modal, setModal] = useState(false);
  const [hasOlder, setHasOlder] = useState(false);
  const [retry, setRetry] = useState(0);
  const [formError, setFormError] = useState("");
  const socket = useRef<WebSocket | null>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);
  const activeRoom = useRef(roomId);
  const selected = data.rooms.find((r) => r.id === roomId);
  const group = data.groups.find((g) => g.id === selected?.group_id);
  const admin = members.some(
    (m) => m.user_id === user.id && m.role === "admin",
  );
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  activeRoom.current = roomId;

  const updateProposals = useCallback(async () => {
    const value = await service.proposals(roomId);
    if (activeRoom.current === roomId) setProposals(value);
  }, [roomId, service]);

  // The existing API broadcasts votes, but not newly created proposals.
  useEffect(() => {
    if (demo || !roomId) return;
    const timer = setInterval(() => {
      if (document.visibilityState === "visible")
        void updateProposals().catch(() => {});
    }, 15_000);
    return () => clearInterval(timer);
  }, [demo, roomId, updateProposals]);

  useEffect(() => {
    if (!selected) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let failures = 0;
    let localSocket: WebSocket | null = null;
    setMessages([]);
    setMembers([]);
    setProposals([]);
    setDraft("");
    setError("");
    setHasOlder(false);
    setLoading(true);
    atBottom.current = true;
    Promise.all([
      service.messages(roomId),
      service.members(selected.group_id),
      service.proposals(roomId),
    ])
      .then(([history, people, votes]) => {
        if (!disposed) {
          setMessages((prev) => mergeMessages(prev, history));
          setMembers(people);
          setProposals(votes);
          setHasOlder(!demo && history.length === 50);
        }
      })
      .catch((err) => {
        if (!disposed) setError(err.message);
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    async function connect() {
      if (demo) {
        setStatus("Demo chat");
        return;
      }
      try {
        setStatus(failures ? "Reconnecting" : "Connecting");
        const url = await socketUrl(roomId);
        if (disposed) return;
        localSocket = new WebSocket(url);
        socket.current = localSocket;
        localSocket.onopen = () => {
          if (disposed) return;
          failures = 0;
          setStatus("Connected");
          // Recover messages and votes missed while the connection was down.
          service
            .messages(roomId)
            .then((history) => {
              if (!disposed)
                setMessages((prev) => mergeMessages(prev, history));
            })
            .catch((err) => {
              if (!disposed) setError(err.message);
            });
          updateProposals().catch((err) => {
            if (!disposed) setError(err.message);
          });
        };
        localSocket.onmessage = (event) => {
          if (disposed) return;
          try {
            const value = JSON.parse(event.data);
            if (
              value.type === "vote_update" ||
              value.type === "meeting_confirmed"
            ) {
              updateProposals().catch((err) => {
                if (!disposed) setError(err.message);
              });
              onChangeRef.current();
            } else if (
              typeof value.id === "string" &&
              typeof value.content === "string" &&
              value.room_id === roomId
            )
              setMessages((prev) => mergeMessages(prev, [value]));
          } catch {
            setError(
              "A message could not be read. Reconnect to refresh the conversation.",
            );
          }
        };
        localSocket.onerror = () => {
          if (!disposed) setStatus("Connection interrupted");
        };
        localSocket.onclose = async (event) => {
          if (disposed) return;
          if (event.code === 4003) {
            setStatus("Access denied");
            setError("You no longer have access to this group.");
            return;
          }
          if (event.code === 4001) {
            try {
              await refreshSession();
            } catch (err) {
              if (!disposed) {
                setStatus("Sign in required");
                setError(
                  err instanceof Error ? err.message : "Please sign in again.",
                );
              }
              return;
            }
          }
          if (!disposed) reconnect();
        };
      } catch (err) {
        if (!disposed) {
          setError(
            err instanceof Error ? err.message : "Could not connect to chat.",
          );
          reconnect();
        }
      }
    }
    function reconnect() {
      failures++;
      setStatus("Reconnecting");
      timer = setTimeout(
        () => void connect(),
        Math.min(1000 * 2 ** Math.min(failures, 5), 30_000),
      );
    }
    void connect();
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      if (localSocket) {
        localSocket.onclose = null;
        localSocket.close();
      }
      socket.current = null;
    };
  }, [roomId, selected?.group_id, service, demo, retry, updateProposals]);
  useEffect(() => {
    if (atBottom.current)
      scroll.current?.scrollTo({ top: scroll.current.scrollHeight });
  }, [messages]);

  function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) return;
    try {
      if (demo)
        setMessages((prev) =>
          mergeMessages(prev, [service.sendDemo(roomId, content)]),
        );
      else {
        if (socket.current?.readyState !== WebSocket.OPEN)
          throw new Error("Wait for the chat to reconnect before sending.");
        socket.current.send(JSON.stringify({ content }));
      }
      atBottom.current = true;
      setDraft("");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message not sent.");
    }
  }
  async function vote(id: string, attend: boolean) {
    setBusy(true);
    setError("");
    try {
      await service.vote(id, attend);
      await updateProposals();
      onChangeRef.current();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vote could not be saved.");
    } finally {
      setBusy(false);
    }
  }
  async function propose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setFormError("");
    try {
      await service.propose({
        room_id: roomId,
        ...times(form),
        location: readText(form, "location"),
      });
      await updateProposals();
      setModal(false);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Could not propose a time.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function older() {
    if (!messages[0]) return;
    setBusy(true);
    try {
      const history = await service.messages(roomId, messages[0].created_at);
      setMessages((prev) => mergeMessages(prev, history));
      setHasOlder(history.length === 50);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load older messages.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        eyebrow="THE CONVERSATION STARTS HERE"
        title="Meet your study people."
      >
        A place for questions, quick hellos, and making a plan.
      </Heading>
      {!data.rooms.length ? (
        <Empty title="No conversations yet.">
          Join or create a group to open its chat room.
        </Empty>
      ) : (
        <>
          <div
            className="room-tabs"
            role="group"
            aria-label="Choose a chat room"
          >
            {data.rooms.map((r) => (
              <button
                className={r.id === roomId ? "selected" : ""}
                key={r.id}
                onClick={() => setRoomId(r.id)}
              >
                <MessageCircle size={16} />
                {r.name || "Study group"}
              </button>
            ))}
          </div>
          {error && (
            <div className="alert" role="alert">
              <span>{error}</span>
              <button
                className="text-button"
                onClick={() => setRetry((value) => value + 1)}
              >
                Reconnect
              </button>
            </div>
          )}
          <div className="chat-layout">
            <section className="chat-panel">
              <header className="chat-header">
                <div>
                  <h2>{selected?.name || group?.name || "Group chat"}</h2>
                  <span className="chat-status">
                    <span className="small-dot" />
                    {status}
                    {demo && " · only you are here"}
                  </span>
                </div>
                <Users size={20} />
              </header>
              <div
                className="message-list"
                ref={scroll}
                role="log"
                aria-label="Conversation"
                aria-live="polite"
                onScroll={() => {
                  const el = scroll.current;
                  if (el)
                    atBottom.current =
                      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
                }}
              >
                {loading && <Spinner />}
                {hasOlder && (
                  <button
                    className="button outline"
                    disabled={busy}
                    onClick={() => void older()}
                  >
                    Load earlier messages
                  </button>
                )}
                {!loading && !messages.length && (
                  <Empty title="Break the ice.">
                    Say hello and share what you’re working on.
                  </Empty>
                )}
                {messages.map((m) => (
                  <div
                    className={`message ${m.sender_id === user.id ? "mine" : ""}`}
                    key={m.id}
                  >
                    <span className="message-meta">
                      {m.sender_id === user.id
                        ? "You"
                        : members.find(
                            (member) => member.user_id === m.sender_id,
                          )?.name || "Group member"}{" "}
                      · {dateLabel(m.created_at)}, {timeLabel(m.created_at)}
                    </span>
                    <div className="message-bubble">{m.content}</div>
                  </div>
                ))}
              </div>
              <form className="message-composer" onSubmit={send}>
                <input
                  aria-label="Message"
                  placeholder="A question, an idea, a quick hello…"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  maxLength={4000}
                  autoComplete="off"
                />
                <button
                  className="button primary"
                  type="submit"
                  aria-label="Send message"
                  disabled={!draft.trim() || (!demo && status !== "Connected")}
                >
                  <Send size={18} />
                </button>
              </form>
            </section>
            <aside className="group-detail">
              <section className="detail-box">
                <div className="section-title compact">
                  <h3>Your study circle</h3>
                  <Users size={18} />
                </div>
                {members.map((m) => (
                  <div className="member-row" key={m.user_id}>
                    <span className="avatar green">
                      {m.name?.charAt(0).toUpperCase()}
                    </span>
                    <div>
                      <strong>
                        {m.user_id === user.id ? `${user.name} (you)` : m.name}
                      </strong>
                      <span>{m.role === "admin" ? "Group host" : m.major}</span>
                    </div>
                  </div>
                ))}
                {group && !admin && (
                  <button
                    className="text-button danger"
                    disabled={busy}
                    onClick={() => {
                      if (window.confirm(`Leave “${group.name}”?`))
                        onLeave(group.id);
                    }}
                  >
                    Leave group
                  </button>
                )}
              </section>
              <section className="detail-box">
                <div className="section-title compact">
                  <h3>Find a time</h3>
                  <CalendarDays size={18} />
                </div>
                <p className="fine-print">
                  When everyone votes yes, the session goes on your calendar.
                  Expired votes are processed when the server is awake.
                </p>
                {proposals.map((p) => {
                  const chosen = p.votes.find((v) => v.user_id === user.id);
                  const expired = Date.parse(p.expires_at) < Date.now();
                  return (
                    <div className="proposal" key={p.id}>
                      <strong>{dateLabel(p.start_time)}</strong>
                      <p>
                        {timeLabel(p.start_time)} – {timeLabel(p.end_time)}
                        <br />
                        {p.location || "Location to be decided"}
                      </p>
                      <span className="fine-print">
                        {p.attend_count} of {p.total_members} can make it
                        {expired ? " · Voting closed" : ""}
                      </span>
                      <div className="vote-buttons">
                        <button
                          disabled={busy || expired}
                          className={chosen?.vote === true ? "selected" : ""}
                          onClick={() => void vote(p.id, true)}
                        >
                          <Check size={14} /> I’m in
                        </button>
                        <button
                          disabled={busy || expired}
                          className={chosen?.vote === false ? "selected" : ""}
                          onClick={() => void vote(p.id, false)}
                        >
                          Can’t make it
                        </button>
                      </div>
                    </div>
                  );
                })}
                {!proposals.length && (
                  <p className="muted">
                    No open proposals. Confirmed sessions appear in Calendar.
                  </p>
                )}
                {admin && (
                  <button
                    className="button outline full"
                    onClick={() => {
                      setFormError("");
                      setModal(true);
                    }}
                  >
                    <Plus size={16} /> Propose a time
                  </button>
                )}
              </section>
            </aside>
          </div>
        </>
      )}
      {modal && (
        <Modal
          title="When should we meet?"
          close={() => setModal(false)}
          busy={busy}
        >
          <form className="form-stack" onSubmit={propose}>
            <TimeFields />
            <label>
              Location
              <input name="location" defaultValue={group?.location || ""} />
            </label>
            {formError && (
              <p className="form-error" role="alert">
                {formError}
              </p>
            )}
            <Submit busy={busy}>Propose time</Submit>
          </form>
        </Modal>
      )}
    </>
  );
}
