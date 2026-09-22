import type {
  Group,
  GroupInput,
  Member,
  Message,
  Proposal,
  ProposalInput,
  Schedule,
  Snapshot,
  User,
} from "./types";

export const demoUser: User = {
  id: "demo-you",
  name: "Alex",
  nyu_email: "alex@example.invalid",
  nyu_id: "DEMO",
  major: "Computer Science",
  academic_standing: 3,
  work_willingness: 8,
  preferred_location: "Bobst Library",
  time_preference: "afternoon",
  avg_gpa: 3.5,
};
const later = (days: number, hour: number) => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  date.setHours(hour, 0, 0, 0);
  return date.toISOString();
};

export function createDemo() {
  const courses = [
    { id: 1, course_code: "CSCI-UA 102", course_name: "Data Structures" },
    { id: 2, course_code: "MATH-UA 123", course_name: "Calculus III" },
    { id: 3, course_code: "CSCI-UA 310", course_name: "Basic Algorithms" },
    {
      id: 4,
      course_code: "PSYCH-UA 1",
      course_name: "Introduction to Psychology",
    },
  ];
  const candidates: Group[] = [
    {
      id: "g1",
      course_id: 1,
      name: "The problem-solving club",
      max_members: 5,
      current_members: 3,
      location: "Bobst Library",
      admin_id: "maya",
      match_score: 94,
      score_breakdown: {
        work_willingness: 45,
        gpa: 30,
        location: 10,
        time_preference: 9,
      },
    },
    {
      id: "g2",
      course_id: 2,
      name: "A little less lost in calculus",
      max_members: 4,
      current_members: 2,
      location: "Kimmel Center",
      admin_id: "sam",
      match_score: 87,
      score_breakdown: {
        work_willingness: 40,
        gpa: 30,
        location: 7,
        time_preference: 10,
      },
    },
    {
      id: "g3",
      course_id: 1,
      name: "Coffee, code & conversation",
      max_members: 6,
      current_members: 4,
      location: "Off-campus café",
      admin_id: "jo",
      match_score: 78,
      score_breakdown: {
        work_willingness: 40,
        gpa: 25,
        location: 3,
        time_preference: 10,
      },
    },
    {
      id: "g4",
      course_id: 3,
      name: "One algorithm at a time",
      max_members: 5,
      current_members: 2,
      location: "Bobst Library",
      admin_id: "lee",
      match_score: 85,
      score_breakdown: {
        work_willingness: 40,
        gpa: 25,
        location: 10,
        time_preference: 10,
      },
    },
  ];
  const data: Snapshot = {
    courses,
    enrollments: [
      { course_id: 1, term: "Fall", year: new Date().getFullYear() },
      { course_id: 2, term: "Fall", year: new Date().getFullYear() },
    ],
    groups: [
      {
        id: "g0",
        course_id: 3,
        name: "Tuesday whiteboard sessions",
        max_members: 5,
        current_members: 3,
        location: "Bobst Library",
        admin_id: demoUser.id,
      },
    ],
    recommendations: [],
    rooms: [{ id: "r0", group_id: "g0", name: "Tuesday whiteboard sessions" }],
    schedules: [
      {
        id: "s0",
        title: "Algorithms · whiteboard session",
        start_time: later(1, 16),
        end_time: later(1, 17),
        location: "Bobst Library",
        group_id: "g0",
        created_by: demoUser.id,
      },
    ],
  };
  const messages: Record<string, Message[]> = {
    r0: [
      {
        id: "m1",
        room_id: "r0",
        sender_id: "maya",
        content: "Anyone up for working through the graph problems together?",
        created_at: later(-1, 15),
      },
      {
        id: "m2",
        room_id: "r0",
        sender_id: "sam",
        content:
          "Yes! I can bring my notes. Let’s try the whiteboards at Bobst.",
        created_at: later(-1, 16),
      },
    ],
  };
  const proposals: Proposal[] = [
    {
      id: "p0",
      room_id: "r0",
      start_time: later(2, 15),
      end_time: later(2, 16),
      location: "Bobst Library",
      expires_at: new Date(Date.now() + 12 * 3600_000).toISOString(),
      is_confirmed: false,
      attend_count: 2,
      total_members: 3,
      votes: [
        { user_id: "maya", vote: true },
        { user_id: "sam", vote: true },
      ],
    },
  ];
  const members: Record<string, Member[]> = {
    g0: [
      {
        user_id: demoUser.id,
        name: "Alex",
        role: "admin",
        major: "Computer Science",
      },
      {
        user_id: "maya",
        name: "Maya",
        role: "member",
        major: "Computer Science",
      },
      { user_id: "sam", name: "Sam", role: "member", major: "Mathematics" },
    ],
  };
  return {
    snapshot() {
      return structuredClone({
        ...data,
        recommendations: candidates
          .filter(
            (g) =>
              data.enrollments.some((e) => e.course_id === g.course_id) &&
              !data.groups.some((m) => m.id === g.id) &&
              (g.current_members || 0) < g.max_members,
          )
          .sort((a, b) => (b.match_score || 0) - (a.match_score || 0)),
      });
    },
    enroll(course_id: number, term: string, year: number) {
      if (!data.enrollments.some((e) => e.course_id === course_id))
        data.enrollments.push({ course_id, term, year });
    },
    unenroll(course_id: number) {
      data.enrollments = data.enrollments.filter(
        (e) => e.course_id !== course_id,
      );
    },
    join(id: string) {
      if (data.groups.some((g) => g.id === id))
        throw new Error("You already belong to this group.");
      const group = candidates.find((g) => g.id === id);
      if (!group || (group.current_members || 0) >= group.max_members)
        throw new Error("This group is full.");
      group.current_members = (group.current_members || 0) + 1;
      data.groups.push({ ...group });
      data.rooms.push({ id: `r-${id}`, group_id: id, name: group.name });
      members[id] = [
        {
          user_id: group.admin_id!,
          name: "Group host",
          role: "admin",
          major: "Computer Science",
        },
        {
          user_id: demoUser.id,
          name: demoUser.name,
          role: "member",
          major: demoUser.major,
        },
      ];
    },
    create(input: GroupInput) {
      const id = crypto.randomUUID();
      data.groups.push({
        ...input,
        id,
        current_members: 1,
        admin_id: demoUser.id,
      });
      data.rooms.push({ id: `r-${id}`, group_id: id, name: input.name });
      members[id] = [
        {
          user_id: demoUser.id,
          name: demoUser.name,
          role: "admin",
          major: demoUser.major,
        },
      ];
    },
    leave(id: string) {
      data.groups = data.groups.filter((g) => g.id !== id);
      data.rooms = data.rooms.filter((r) => r.group_id !== id);
      data.schedules = data.schedules.filter((s) => s.group_id !== id);
      const candidate = candidates.find((g) => g.id === id);
      if (candidate) candidate.current_members!--;
    },
    members(id: string) {
      return structuredClone(members[id] || []);
    },
    messages(room: string) {
      return structuredClone(messages[room] || []);
    },
    send(room: string, content: string) {
      const message = {
        id: crypto.randomUUID(),
        room_id: room,
        sender_id: demoUser.id,
        content,
        created_at: new Date().toISOString(),
      };
      (messages[room] ||= []).push(message);
      return message;
    },
    proposals(room: string) {
      return structuredClone(
        proposals.filter((p) => p.room_id === room && !p.is_confirmed),
      );
    },
    propose(input: ProposalInput) {
      if (
        proposals.filter(
          (p) =>
            p.room_id === input.room_id &&
            !p.is_confirmed &&
            Date.parse(p.expires_at) > Date.now(),
        ).length >= 3
      )
        throw new Error("There are already three active proposals.");
      const group = data.groups.find((g) =>
        data.rooms.some((r) => r.group_id === g.id && r.id === input.room_id),
      );
      proposals.push({
        ...input,
        id: crypto.randomUUID(),
        is_confirmed: false,
        expires_at: new Date(Date.now() + 12 * 3600_000).toISOString(),
        attend_count: 0,
        total_members: group?.current_members || 1,
        votes: [],
      });
    },
    vote(id: string, vote: boolean) {
      const p = proposals.find((p) => p.id === id);
      if (!p || p.is_confirmed || Date.parse(p.expires_at) < Date.now())
        throw new Error("This proposal is no longer open.");
      p.votes = [
        ...p.votes.filter((v) => v.user_id !== demoUser.id),
        { user_id: demoUser.id, vote },
      ];
      p.attend_count = p.votes.filter((v) => v.vote).length;
      if (p.attend_count === p.total_members) {
        p.is_confirmed = true;
        const room = data.rooms.find((r) => r.id === p.room_id)!;
        data.schedules.push({
          id: crypto.randomUUID(),
          title: `Study session · ${room.name}`,
          start_time: p.start_time,
          end_time: p.end_time,
          location: p.location,
          group_id: room.group_id,
          created_by: demoUser.id,
        });
      }
    },
    schedule(input: Omit<Schedule, "id" | "created_by">) {
      data.schedules.push({
        ...input,
        id: crypto.randomUUID(),
        created_by: demoUser.id,
      });
    },
    deleteSchedule(id: string) {
      data.schedules = data.schedules.filter((s) => s.id !== id);
    },
  };
}
