export interface User {
  id: string;
  name: string;
  nyu_email: string;
  nyu_id: string;
  major: string;
  academic_standing: number;
  work_willingness: number;
  preferred_location?: string | null;
  time_preference?: string | null;
  avg_gpa?: number | null;
}
export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: User;
}
export interface Course {
  id: number;
  course_code: string;
  course_name: string;
}
export interface Enrollment {
  course_id: number;
  term: string;
  year: number;
}
export interface Group {
  id: string;
  course_id: number;
  name: string;
  max_members: number;
  current_members?: number;
  location?: string | null;
  admin_id?: string;
  match_score?: number;
  score_breakdown?: Record<string, number>;
}
export interface Member {
  user_id: string;
  name: string;
  role: string;
  major: string;
}
export interface Room {
  id: string;
  group_id: string;
  name?: string;
}
export interface Message {
  id: string;
  room_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}
export interface Proposal {
  id: string;
  room_id: string;
  start_time: string;
  end_time: string;
  location?: string | null;
  expires_at: string;
  is_confirmed: boolean;
  attend_count: number;
  total_members: number;
  votes: { user_id: string; vote: boolean }[];
}
export interface Schedule {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  location?: string | null;
  group_id?: string | null;
  created_by: string;
}
export interface Snapshot {
  courses: Course[];
  enrollments: Enrollment[];
  groups: Group[];
  recommendations: Group[];
  rooms: Room[];
  schedules: Schedule[];
}
export interface GroupInput {
  name: string;
  course_id: number;
  max_members: number;
  location: string;
}
export interface ProposalInput {
  room_id: string;
  start_time: string;
  end_time: string;
  location: string;
}
export interface SignupInput extends Omit<User, "id"> {
  password: string;
}
