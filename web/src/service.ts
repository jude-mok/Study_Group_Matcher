import { api } from "./api";
import { createDemo } from "./demo";
import type {
  Course,
  Enrollment,
  Group,
  GroupInput,
  Member,
  Message,
  Proposal,
  ProposalInput,
  Room,
  Schedule,
  Snapshot,
} from "./types";

export function createService(demo: boolean) {
  const sample = createDemo();
  return {
    async snapshot(): Promise<Snapshot> {
      if (demo) return sample.snapshot();
      const [courses, enrollments, groups, recommendations, rooms, personal] =
        await Promise.all([
          api<Course[]>("/courses/"),
          api<Enrollment[]>("/user-courses/"),
          api<Group[]>("/study-groups/me"),
          api<Group[]>("/study-groups/recommend?limit=50"),
          api<Room[]>("/rooms"),
          api<Schedule[]>("/schedules/me"),
        ]);
      const groupSchedules = await Promise.all(
        groups.map((g) => api<Schedule[]>(`/schedules/group/${g.id}`)),
      );
      return {
        courses,
        enrollments,
        groups,
        recommendations,
        rooms,
        schedules: [...personal, ...groupSchedules.flat()],
      };
    },
    async enroll(course_id: number, term: string, year: number) {
      if (demo) sample.enroll(course_id, term, year);
      else await api("/user-courses/", "POST", { course_id, term, year });
    },
    async unenroll(id: number) {
      if (demo) sample.unenroll(id);
      else await api(`/user-courses/?course_id=${id}`, "DELETE");
    },
    async join(id: string) {
      if (demo) sample.join(id);
      else await api(`/study-groups/${id}/join`, "POST");
    },
    async create(input: GroupInput) {
      if (demo) sample.create(input);
      else await api("/study-groups/", "POST", input);
    },
    async leave(id: string) {
      if (demo) sample.leave(id);
      else await api(`/study-groups/${id}/leave`, "DELETE");
    },
    async members(id: string) {
      return demo
        ? sample.members(id)
        : api<Member[]>(`/study-groups/${id}/members`);
    },
    async messages(id: string, before?: string) {
      return demo
        ? sample.messages(id)
        : api<Message[]>(
            `/rooms/${id}/messages?limit=50${before ? `&before=${encodeURIComponent(before)}` : ""}`,
          );
    },
    sendDemo(room: string, content: string) {
      return sample.send(room, content);
    },
    async proposals(room: string) {
      return demo
        ? sample.proposals(room)
        : api<Proposal[]>(`/meetings/proposals/${room}`);
    },
    async propose(input: ProposalInput) {
      if (demo) sample.propose(input);
      else await api("/meetings/proposals", "POST", input);
    },
    async vote(id: string, vote: boolean) {
      if (demo) sample.vote(id, vote);
      else await api("/meetings/votes", "POST", { proposal_id: id, vote });
    },
    async schedule(input: Omit<Schedule, "id" | "created_by">) {
      if (demo) sample.schedule(input);
      else await api("/schedules/", "POST", input);
    },
    async deleteSchedule(id: string) {
      if (demo) sample.deleteSchedule(id);
      else await api(`/schedules/${id}`, "DELETE");
    },
  };
}
export type Service = ReturnType<typeof createService>;
