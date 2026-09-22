import { describe, expect, it } from "vitest";
import { createDemo, demoUser } from "./demo";
import { mergeMessages } from "./Chat";
import { times } from "./ui";

describe("demo workspace journeys", () => {
  it("reveals recommendations for a newly added course", () => {
    const demo = createDemo();
    expect(demo.snapshot().recommendations.some((g) => g.course_id === 3)).toBe(
      false,
    );
    demo.enroll(3, "Fall", 2026);
    expect(demo.snapshot().recommendations.some((g) => g.course_id === 3)).toBe(
      true,
    );
    demo.unenroll(3);
    expect(demo.snapshot().recommendations.some((g) => g.course_id === 3)).toBe(
      false,
    );
  });
  it("joining moves a group out of recommendations and creates a usable chat", () => {
    const demo = createDemo();
    demo.join("g1");
    const snapshot = demo.snapshot();
    expect(snapshot.recommendations.some((g) => g.id === "g1")).toBe(false);
    expect(snapshot.groups.find((g) => g.id === "g1")?.current_members).toBe(4);
    const room = snapshot.rooms.find((r) => r.group_id === "g1")!;
    demo.send(room.id, "Can we review trees?");
    expect(demo.messages(room.id)[0].content).toBe("Can we review trees?");
    expect(() => demo.join("g1")).toThrow(/already belong/);
    demo.leave("g1");
    expect(
      demo.snapshot().recommendations.find((g) => g.id === "g1")
        ?.current_members,
    ).toBe(3);
  });
  it("creates a group with an admin and a chat room", () => {
    const demo = createDemo();
    demo.create({
      name: "CS practice",
      course_id: 1,
      max_members: 4,
      location: "Library",
    });
    const group = demo.snapshot().groups.find((g) => g.name === "CS practice")!;
    expect(demo.members(group.id)[0]).toMatchObject({
      user_id: demoUser.id,
      role: "admin",
    });
    expect(demo.snapshot().rooms.some((r) => r.group_id === group.id)).toBe(
      true,
    );
  });
  it("updating a vote does not double-count and unanimity creates one calendar event", () => {
    const demo = createDemo();
    demo.vote("p0", false);
    demo.vote("p0", false);
    expect(demo.proposals("r0")[0].votes).toHaveLength(3);
    expect(demo.proposals("r0")[0].attend_count).toBe(2);
    demo.vote("p0", true);
    expect(demo.proposals("r0")).toHaveLength(0);
    expect(demo.snapshot().schedules).toHaveLength(2);
    expect(() => demo.vote("p0", true)).toThrow(/no longer open/);
    expect(demo.snapshot().schedules).toHaveLength(2);
  });
  it("separate visitors do not share sample mutations", () => {
    const first = createDemo();
    first.join("g1");
    expect(
      createDemo()
        .snapshot()
        .groups.some((g) => g.id === "g1"),
    ).toBe(false);
  });
});

describe("chat recovery and date validation", () => {
  it("deduplicates a message received both in history and through the socket", () => {
    const message = {
      id: "m1",
      room_id: "r0",
      sender_id: "alex",
      content: "Hello",
      created_at: "2026-09-22T12:00:00Z",
    };
    const older = { ...message, id: "m0", created_at: "2026-09-22T11:00:00Z" };
    expect(mergeMessages([message], [older, message]).map((m) => m.id)).toEqual(
      ["m0", "m1"],
    );
  });
  it("rejects reversed times instead of sending an invalid proposal", () => {
    const form = new FormData();
    form.set("start_time", "2026-09-22T16:00");
    form.set("end_time", "2026-09-22T15:00");
    expect(() => times(form)).toThrow(/end time after/);
    form.set("end_time", "2026-09-22T17:00");
    expect(
      Date.parse(times(form).end_time) - Date.parse(times(form).start_time),
    ).toBe(3600_000);
  });
});
