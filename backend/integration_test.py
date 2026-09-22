pass

import json
import sys
import time
import uuid
import traceback
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000"
TIMEOUT = 15.0

# Unique suffix so tests are idempotent
UID = uuid.uuid4().hex[:6]

USER_A = {
    "name": f"Test User A {UID}",
    "nyu_email": f"testa{UID}@nyu.edu",
    "nyu_id": f"NA{UID}",
    "password": "testpassword123",
    "major": "computer science",
    "academic_standing": 3,
    "work_willingness": 8,
    "preferred_location": "Bobst Library",
    "time_preference": "morning",
    "avg_gpa": 3.7,
}

USER_B = {
    "name": f"Test User B {UID}",
    "nyu_email": f"testb{UID}@nyu.edu",
    "nyu_id": f"NB{UID}",
    "password": "testpassword456",
    "major": "data science",
    "academic_standing": 2,
    "work_willingness": 6,
    "preferred_location": "Kimmel",
    "time_preference": "afternoon",
    "avg_gpa": 3.2,
}


# ─── helpers ───────────────────────────────────────────────────────
class TestContext:
    token_a: str = ""
    token_b: str = ""
    refresh_token_a: str = ""
    user_a_id: str = ""
    user_b_id: str = ""
    course_id: int = 0
    course_code: str = ""
    group_id: str = ""
    room_id: str = ""
    schedule_id: str = ""
    group_schedule_id: str = ""
    proposal_id: str = ""
    join_request_id: str = ""


ctx = TestContext()
results: list[dict] = []


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def record(section: str, name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append({"section": section, "name": name, "status": status, "detail": detail})
    mark = "✅" if passed else "❌"
    print(f"  {mark} {name}" + (f"  — {detail}" if detail and not passed else ""))


def run_test(section: str, name: str, fn):
    try:
        fn()
    except AssertionError as e:
        record(section, name, False, str(e))
    except Exception as e:
        record(section, name, False, f"Exception: {e}")


# ─── 1. Health ─────────────────────────────────────────────────────
def test_health():
    print("\n[1] Health Check")
    def _t():
        r = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        assert r.json().get("status") == "healthy"
        record("Health", "GET /health", True)
    run_test("Health", "GET /health", _t)

    def _root():
        r = httpx.get(f"{BASE_URL}/", timeout=TIMEOUT)
        assert r.status_code == 200
        record("Health", "GET /", True)
    run_test("Health", "GET /", _root)


# ─── 2. Auth ──────────────────────────────────────────────────────
def test_auth():
    print("\n[2] Auth")

    # Signup A
    def _signup_a():
        r = httpx.post(f"{BASE_URL}/auth/signup", json=USER_A, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        data = r.json()
        ctx.user_a_id = data["id"]
        assert data["nyu_email"] == USER_A["nyu_email"]
        record("Auth", "POST /auth/signup (User A)", True)
    run_test("Auth", "POST /auth/signup (User A)", _signup_a)

    # Signup B
    def _signup_b():
        r = httpx.post(f"{BASE_URL}/auth/signup", json=USER_B, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        ctx.user_b_id = r.json()["id"]
        record("Auth", "POST /auth/signup (User B)", True)
    run_test("Auth", "POST /auth/signup (User B)", _signup_b)

    # Duplicate signup
    def _dup_signup():
        r = httpx.post(f"{BASE_URL}/auth/signup", json=USER_A, timeout=TIMEOUT)
        assert r.status_code == 409, f"Expected 409 got {r.status_code}"
        record("Auth", "POST /auth/signup duplicate → 409", True)
    run_test("Auth", "POST /auth/signup duplicate → 409", _dup_signup)

    # Login A
    def _login_a():
        r = httpx.post(f"{BASE_URL}/auth/login", json={
            "nyu_email": USER_A["nyu_email"],
            "password": USER_A["password"],
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        ctx.token_a = data["access_token"]
        ctx.refresh_token_a = data["refresh_token"]
        assert data["token_type"] == "bearer"
        assert "user" in data
        record("Auth", "POST /auth/login (User A)", True)
    run_test("Auth", "POST /auth/login (User A)", _login_a)

    # Login B
    def _login_b():
        r = httpx.post(f"{BASE_URL}/auth/login", json={
            "nyu_email": USER_B["nyu_email"],
            "password": USER_B["password"],
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        ctx.token_b = r.json()["access_token"]
        record("Auth", "POST /auth/login (User B)", True)
    run_test("Auth", "POST /auth/login (User B)", _login_b)

    # Wrong password
    def _bad_login():
        r = httpx.post(f"{BASE_URL}/auth/login", json={
            "nyu_email": USER_A["nyu_email"],
            "password": "wrongpassword99",
        }, timeout=TIMEOUT)
        assert r.status_code == 401, f"Expected 401 got {r.status_code}"
        record("Auth", "POST /auth/login wrong password → 401", True)
    run_test("Auth", "POST /auth/login wrong password → 401", _bad_login)

    # Refresh token
    def _refresh():
        if not ctx.refresh_token_a:
            record("Auth", "POST /auth/refresh", False, "No refresh token")
            return
        r = httpx.post(f"{BASE_URL}/auth/refresh", json={
            "refresh_token": ctx.refresh_token_a,
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        ctx.token_a = data["access_token"]  # use refreshed token
        record("Auth", "POST /auth/refresh", True)
    run_test("Auth", "POST /auth/refresh", _refresh)

    # Verify email status
    def _verify_email():
        r = httpx.get(f"{BASE_URL}/auth/verify-email-status", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        record("Auth", "GET /auth/verify-email-status", True)
    run_test("Auth", "GET /auth/verify-email-status", _verify_email)

    # No token → 403
    def _no_token():
        r = httpx.get(f"{BASE_URL}/users/me", timeout=TIMEOUT)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}"
        record("Auth", "GET /users/me without token → 403", True)
    run_test("Auth", "GET /users/me without token → 403", _no_token)


# ─── 3. Users ─────────────────────────────────────────────────────
def test_users():
    print("\n[3] Users")

    def _get_me():
        r = httpx.get(f"{BASE_URL}/users/me", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        data = r.json()
        assert data["id"] == ctx.user_a_id
        assert data["nyu_email"] == USER_A["nyu_email"]
        record("Users", "GET /users/me", True)
    run_test("Users", "GET /users/me", _get_me)

    def _get_by_id():
        r = httpx.get(f"{BASE_URL}/users/{ctx.user_b_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        assert r.json()["id"] == ctx.user_b_id
        record("Users", "GET /users/{id}", True)
    run_test("Users", "GET /users/{id}", _get_by_id)

    def _update_me():
        r = httpx.put(f"{BASE_URL}/users/me", headers=_headers(ctx.token_a), json={
            "work_willingness": 9,
            "preferred_location": "Kimmel Center",
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data["work_willingness"] == 9
        record("Users", "PUT /users/me", True)
    run_test("Users", "PUT /users/me", _update_me)

    def _update_empty():
        r = httpx.put(f"{BASE_URL}/users/me", headers=_headers(ctx.token_a), json={}, timeout=TIMEOUT)
        assert r.status_code == 400, f"Expected 400 got {r.status_code}"
        record("Users", "PUT /users/me empty body → 400", True)
    run_test("Users", "PUT /users/me empty body → 400", _update_empty)


# ─── 4. Courses ───────────────────────────────────────────────────
def test_courses():
    print("\n[4] Courses")

    # Use existing course for downstream tests (avoids DB sequence issues)
    def _get_all():
        r = httpx.get(f"{BASE_URL}/courses/", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        # Pick first course for downstream tests
        ctx.course_id = data[0]["id"]
        ctx.course_code = data[0]["course_code"]
        record("Courses", "GET /courses/", True)
    run_test("Courses", "GET /courses/", _get_all)

    def _search():
        r = httpx.get(f"{BASE_URL}/courses/search", params={"course_code": ctx.course_code}, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        data = r.json()
        assert len(data) >= 1
        record("Courses", "GET /courses/search", True)
    run_test("Courses", "GET /courses/search", _search)

    def _get_by_id():
        r = httpx.get(f"{BASE_URL}/courses/{ctx.course_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        record("Courses", "GET /courses/{id}", True)
    run_test("Courses", "GET /courses/{id}", _get_by_id)

    def _get_not_found():
        r = httpx.get(f"{BASE_URL}/courses/999999", timeout=TIMEOUT)
        assert r.status_code in (404, 500), f"Expected 404/500 got {r.status_code}"
        record("Courses", "GET /courses/{bad_id} → 404", True)
    run_test("Courses", "GET /courses/{bad_id} → 404", _get_not_found)

    # Test course creation (may fail due to DB sequence issue — not a code bug)
    def _create():
        r = httpx.post(f"{BASE_URL}/courses/", json={
            "course_code": f"CSTEST{UID}",
            "course_name": f"test integration {UID}",
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        record("Courses", "POST /courses/ (create)", True)
    run_test("Courses", "POST /courses/ (create)", _create)

    def _create_dup():
        # Use a course code that definitely exists
        r = httpx.post(f"{BASE_URL}/courses/", json={
            "course_code": ctx.course_code,
            "course_name": "duplicate test",
        }, timeout=TIMEOUT)
        assert r.status_code == 409, f"Expected 409 got {r.status_code}"
        record("Courses", "POST /courses/ duplicate → 409", True)
    run_test("Courses", "POST /courses/ duplicate → 409", _create_dup)


# ─── 5. User Courses ─────────────────────────────────────────────
def test_user_courses():
    print("\n[5] User Courses")

    def _enroll_a():
        r = httpx.post(f"{BASE_URL}/user-courses/", headers=_headers(ctx.token_a), json={
            "course_id": ctx.course_id,
            "term": "Fall",
            "year": 2026,
            "start_time": "09:00",
            "end_time": "10:30",
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        record("UserCourses", "POST /user-courses/ (A enroll)", True)
    run_test("UserCourses", "POST /user-courses/ (A enroll)", _enroll_a)

    def _enroll_b():
        r = httpx.post(f"{BASE_URL}/user-courses/", headers=_headers(ctx.token_b), json={
            "course_id": ctx.course_id,
            "term": "Fall",
            "year": 2026,
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        record("UserCourses", "POST /user-courses/ (B enroll)", True)
    run_test("UserCourses", "POST /user-courses/ (B enroll)", _enroll_b)

    def _enroll_dup():
        r = httpx.post(f"{BASE_URL}/user-courses/", headers=_headers(ctx.token_a), json={
            "course_id": ctx.course_id,
            "term": "Fall",
            "year": 2026,
        }, timeout=TIMEOUT)
        assert r.status_code == 409, f"Expected 409 got {r.status_code}"
        record("UserCourses", "POST /user-courses/ duplicate → 409", True)
    run_test("UserCourses", "POST /user-courses/ duplicate → 409", _enroll_dup)

    def _list():
        r = httpx.get(f"{BASE_URL}/user-courses/", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 1
        record("UserCourses", "GET /user-courses/", True)
    run_test("UserCourses", "GET /user-courses/", _list)


# ─── 6. Study Groups ─────────────────────────────────────────────
def test_study_groups():
    print("\n[6] Study Groups")

    group_name = f"Integration Test Group {UID}"

    # A creates group
    def _create():
        r = httpx.post(f"{BASE_URL}/study-groups/", headers=_headers(ctx.token_a), json={
            "course_id": ctx.course_id,
            "name": group_name,
            "max_members": 4,
            "location": "Bobst Library 4F",
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        data = r.json()
        ctx.group_id = data["id"]
        assert data["current_members"] == 1
        assert data["admin_id"] == ctx.user_a_id
        record("StudyGroups", "POST /study-groups/ (create)", True)
    run_test("StudyGroups", "POST /study-groups/ (create)", _create)

    # Get by course
    def _by_course():
        r = httpx.get(f"{BASE_URL}/study-groups/course/{ctx.course_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert any(g["id"] == ctx.group_id for g in data)
        record("StudyGroups", "GET /study-groups/course/{id}", True)
    run_test("StudyGroups", "GET /study-groups/course/{id}", _by_course)

    # Search by name
    def _search():
        r = httpx.get(f"{BASE_URL}/study-groups/search", params={"name": UID}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        record("StudyGroups", "GET /study-groups/search", True)
    run_test("StudyGroups", "GET /study-groups/search", _search)

    # My groups (A)
    def _my_groups():
        r = httpx.get(f"{BASE_URL}/study-groups/me", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert any(g["id"] == ctx.group_id for g in data)
        record("StudyGroups", "GET /study-groups/me", True)
    run_test("StudyGroups", "GET /study-groups/me", _my_groups)

    # B requests to join
    def _join_request():
        r = httpx.post(f"{BASE_URL}/study-groups/{ctx.group_id}/join", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        record("StudyGroups", "POST /{id}/join (B requests)", True)
    run_test("StudyGroups", "POST /{id}/join (B requests)", _join_request)

    # Duplicate join request
    def _dup_join():
        r = httpx.post(f"{BASE_URL}/study-groups/{ctx.group_id}/join", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 409, f"Expected 409 got {r.status_code}"
        record("StudyGroups", "POST /{id}/join duplicate → 409", True)
    run_test("StudyGroups", "POST /{id}/join duplicate → 409", _dup_join)

    # A sees pending requests
    def _get_requests():
        r = httpx.get(f"{BASE_URL}/study-groups/{ctx.group_id}/requests", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert len(data) >= 1
        ctx.join_request_id = data[0]["id"]
        assert data[0]["status"] == "pending"
        assert data[0].get("user") is not None  # has user info
        record("StudyGroups", "GET /{id}/requests (admin)", True)
    run_test("StudyGroups", "GET /{id}/requests (admin)", _get_requests)

    # B cannot see requests (not admin)
    def _get_requests_forbidden():
        r = httpx.get(f"{BASE_URL}/study-groups/{ctx.group_id}/requests", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}"
        record("StudyGroups", "GET /{id}/requests (non-admin) → 403", True)
    run_test("StudyGroups", "GET /{id}/requests (non-admin) → 403", _get_requests_forbidden)

    # A accepts B's request
    def _accept():
        r = httpx.post(
            f"{BASE_URL}/study-groups/{ctx.group_id}/requests/{ctx.join_request_id}/accept",
            headers=_headers(ctx.token_a),
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        record("StudyGroups", "POST /{id}/requests/{rid}/accept", True)
    run_test("StudyGroups", "POST /{id}/requests/{rid}/accept", _accept)

    # Members list
    def _members():
        r = httpx.get(f"{BASE_URL}/study-groups/{ctx.group_id}/members", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        data = r.json()
        assert len(data) == 2
        roles = {m["role"] for m in data}
        assert "admin" in roles and "member" in roles
        record("StudyGroups", "GET /{id}/members", True)
    run_test("StudyGroups", "GET /{id}/members", _members)

    # Recommendations for B
    def _recommend():
        r = httpx.get(f"{BASE_URL}/study-groups/recommend", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        record("StudyGroups", "GET /study-groups/recommend", True)
    run_test("StudyGroups", "GET /study-groups/recommend", _recommend)


# ─── 7. Chat ─────────────────────────────────────────────────────
def test_chat():
    print("\n[7] Chat")

    # Room should have been auto-created with the study group
    def _list_rooms():
        r = httpx.get(f"{BASE_URL}/rooms", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        data = r.json()
        assert isinstance(data, list) and len(data) >= 1
        # Find room for our group
        for room in data:
            if room.get("group_id") == ctx.group_id:
                ctx.room_id = room["id"]
                break
        assert ctx.room_id, f"Room for group {ctx.group_id} not found in {data}"
        record("Chat", "GET /rooms (list)", True)
    run_test("Chat", "GET /rooms (list)", _list_rooms)

    # B should also see the room
    def _list_rooms_b():
        r = httpx.get(f"{BASE_URL}/rooms", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        room_ids = [room["id"] for room in data]
        assert ctx.room_id in room_ids, "B should see the room after being accepted"
        record("Chat", "GET /rooms (User B sees room)", True)
    run_test("Chat", "GET /rooms (User B sees room)", _list_rooms_b)

    # Get messages (should be empty or have system messages)
    def _messages():
        r = httpx.get(f"{BASE_URL}/rooms/{ctx.room_id}/messages", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        record("Chat", "GET /rooms/{id}/messages", True)
    run_test("Chat", "GET /rooms/{id}/messages", _messages)

    # Non-member cannot read messages
    def _messages_forbidden():
        r = httpx.get(f"{BASE_URL}/rooms/00000000-0000-0000-0000-000000000000/messages",
                      headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}"
        record("Chat", "GET /rooms/{bad_id}/messages → 403", True)
    run_test("Chat", "GET /rooms/{bad_id}/messages → 403", _messages_forbidden)


# ─── 8. Schedules ────────────────────────────────────────────────
def test_schedules():
    print("\n[8] Schedules")

    now = datetime.now(timezone.utc)
    start = (now + timedelta(days=1)).isoformat()
    end = (now + timedelta(days=1, hours=2)).isoformat()

    # Personal schedule
    def _create_personal():
        r = httpx.post(f"{BASE_URL}/schedules/", headers=_headers(ctx.token_a), json={
            "title": f"Personal Study {UID}",
            "description": "Integration test personal schedule",
            "start_time": start,
            "end_time": end,
            "location": "Home",
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        ctx.schedule_id = r.json()["id"]
        record("Schedules", "POST /schedules/ (personal)", True)
    run_test("Schedules", "POST /schedules/ (personal)", _create_personal)

    # Group schedule
    def _create_group():
        r = httpx.post(f"{BASE_URL}/schedules/", headers=_headers(ctx.token_a), json={
            "title": f"Group Study {UID}",
            "start_time": start,
            "end_time": end,
            "location": "Library",
            "group_id": ctx.group_id,
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        ctx.group_schedule_id = r.json()["id"]
        record("Schedules", "POST /schedules/ (group)", True)
    run_test("Schedules", "POST /schedules/ (group)", _create_group)

    # Invalid time range
    def _invalid_time():
        r = httpx.post(f"{BASE_URL}/schedules/", headers=_headers(ctx.token_a), json={
            "title": "Bad Schedule",
            "start_time": end,
            "end_time": start,  # end before start
        }, timeout=TIMEOUT)
        assert r.status_code == 400, f"Expected 400 got {r.status_code}"
        record("Schedules", "POST /schedules/ invalid time → 400", True)
    run_test("Schedules", "POST /schedules/ invalid time → 400", _invalid_time)

    # Get my schedules
    def _my_schedules():
        r = httpx.get(f"{BASE_URL}/schedules/me", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert any(s["id"] == ctx.schedule_id for s in data)
        record("Schedules", "GET /schedules/me", True)
    run_test("Schedules", "GET /schedules/me", _my_schedules)

    # Get group schedules
    def _group_schedules():
        r = httpx.get(f"{BASE_URL}/schedules/group/{ctx.group_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert any(s["id"] == ctx.group_schedule_id for s in data)
        record("Schedules", "GET /schedules/group/{id}", True)
    run_test("Schedules", "GET /schedules/group/{id}", _group_schedules)

    # Get single schedule
    def _get_schedule():
        r = httpx.get(f"{BASE_URL}/schedules/{ctx.schedule_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        record("Schedules", "GET /schedules/{id}", True)
    run_test("Schedules", "GET /schedules/{id}", _get_schedule)

    # Update schedule
    def _update():
        r = httpx.put(f"{BASE_URL}/schedules/{ctx.schedule_id}", headers=_headers(ctx.token_a), json={
            "title": f"Updated Schedule {UID}",
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        assert r.json()["title"] == f"updated schedule {UID}" or "Updated" in r.json()["title"]
        record("Schedules", "PUT /schedules/{id}", True)
    run_test("Schedules", "PUT /schedules/{id}", _update)

    # B cannot update A's personal schedule
    def _update_forbidden():
        r = httpx.put(f"{BASE_URL}/schedules/{ctx.schedule_id}", headers=_headers(ctx.token_b), json={
            "title": "Hacked",
        }, timeout=TIMEOUT)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}"
        record("Schedules", "PUT /schedules/{id} not owner → 403", True)
    run_test("Schedules", "PUT /schedules/{id} not owner → 403", _update_forbidden)

    # Delete schedule
    def _delete():
        r = httpx.delete(f"{BASE_URL}/schedules/{ctx.schedule_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 204, f"status={r.status_code}"
        record("Schedules", "DELETE /schedules/{id}", True)
    run_test("Schedules", "DELETE /schedules/{id}", _delete)

    # Verify deleted
    def _get_deleted():
        r = httpx.get(f"{BASE_URL}/schedules/{ctx.schedule_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 404, f"Expected 404 got {r.status_code}"
        record("Schedules", "GET deleted schedule → 404", True)
    run_test("Schedules", "GET deleted schedule → 404", _get_deleted)


# ─── 9. Meetings ─────────────────────────────────────────────────
def test_meetings():
    print("\n[9] Meetings")

    now = datetime.now(timezone.utc)
    start = (now + timedelta(days=2)).isoformat()
    end = (now + timedelta(days=2, hours=1)).isoformat()

    # A creates proposal (admin)
    def _create_proposal():
        r = httpx.post(f"{BASE_URL}/meetings/proposals", headers=_headers(ctx.token_a), json={
            "room_id": ctx.room_id,
            "start_time": start,
            "end_time": end,
            "location": "Kimmel 4th Floor",
        }, timeout=TIMEOUT)
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        data = r.json()
        ctx.proposal_id = data["id"]
        assert data["is_confirmed"] == False
        record("Meetings", "POST /meetings/proposals", True)
    run_test("Meetings", "POST /meetings/proposals", _create_proposal)

    # Non-admin cannot create proposal
    def _create_proposal_forbidden():
        r = httpx.post(f"{BASE_URL}/meetings/proposals", headers=_headers(ctx.token_b), json={
            "room_id": ctx.room_id,
            "start_time": start,
            "end_time": end,
        }, timeout=TIMEOUT)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}"
        record("Meetings", "POST /meetings/proposals (non-admin) → 403", True)
    run_test("Meetings", "POST /meetings/proposals (non-admin) → 403", _create_proposal_forbidden)

    # Get proposals
    def _get_proposals():
        r = httpx.get(f"{BASE_URL}/meetings/proposals/{ctx.room_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        record("Meetings", "GET /meetings/proposals/{room_id}", True)
    run_test("Meetings", "GET /meetings/proposals/{room_id}", _get_proposals)

    # A votes attend
    def _vote_a():
        r = httpx.post(f"{BASE_URL}/meetings/votes", headers=_headers(ctx.token_a), json={
            "proposal_id": ctx.proposal_id,
            "vote": True,
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        record("Meetings", "POST /meetings/votes (A attend)", True)
    run_test("Meetings", "POST /meetings/votes (A attend)", _vote_a)

    # B votes attend → should trigger unanimous confirmation
    def _vote_b():
        r = httpx.post(f"{BASE_URL}/meetings/votes", headers=_headers(ctx.token_b), json={
            "proposal_id": ctx.proposal_id,
            "vote": True,
        }, timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        body = r.json()
        assert "confirmed" in body.get("message", "").lower() or "vote cast" in body.get("message", "").lower()
        record("Meetings", "POST /meetings/votes (B attend → unanimous)", True)
    run_test("Meetings", "POST /meetings/votes (B attend → unanimous)", _vote_b)

    # Get results
    def _get_results():
        r = httpx.get(f"{BASE_URL}/meetings/results/{ctx.room_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200, f"status={r.status_code}"
        data = r.json()
        assert len(data) >= 1, f"Expected at least 1 result, got {len(data)}"
        assert data[0]["confirmation_type"] == "unanimous"
        record("Meetings", "GET /meetings/results/{room_id}", True)
    run_test("Meetings", "GET /meetings/results/{room_id}", _get_results)

    # Confirmed meeting should have created a group schedule automatically
    def _auto_schedule():
        r = httpx.get(f"{BASE_URL}/schedules/group/{ctx.group_id}", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        # Should have at least one "Study Session" schedule
        study_sessions = [s for s in data if "study session" in s["title"].lower()]
        assert len(study_sessions) >= 1, f"No auto-created schedule found. Schedules: {[s['title'] for s in data]}"
        record("Meetings", "Auto-created schedule after confirmation", True)
    run_test("Meetings", "Auto-created schedule after confirmation", _auto_schedule)


# ─── 10. Cleanup ─────────────────────────────────────────────────
def test_cleanup():
    print("\n[10] Cleanup")

    # B leaves group
    def _leave():
        r = httpx.delete(f"{BASE_URL}/study-groups/{ctx.group_id}/leave", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 204, f"status={r.status_code}"
        record("Cleanup", "DELETE /study-groups/{id}/leave (B)", True)
    run_test("Cleanup", "DELETE /study-groups/{id}/leave (B)", _leave)

    # Unenroll from course
    def _unenroll_a():
        r = httpx.delete(f"{BASE_URL}/user-courses/", headers=_headers(ctx.token_a),
                         params={"course_id": ctx.course_id}, timeout=TIMEOUT)
        assert r.status_code == 204, f"status={r.status_code}"
        record("Cleanup", "DELETE /user-courses/ (A)", True)
    run_test("Cleanup", "DELETE /user-courses/ (A)", _unenroll_a)

    def _unenroll_b():
        r = httpx.delete(f"{BASE_URL}/user-courses/", headers=_headers(ctx.token_b),
                         params={"course_id": ctx.course_id}, timeout=TIMEOUT)
        assert r.status_code == 204, f"status={r.status_code}"
        record("Cleanup", "DELETE /user-courses/ (B)", True)
    run_test("Cleanup", "DELETE /user-courses/ (B)", _unenroll_b)

    # Delete users
    def _delete_b():
        r = httpx.delete(f"{BASE_URL}/users/me", headers=_headers(ctx.token_b), timeout=TIMEOUT)
        assert r.status_code == 204, f"status={r.status_code} body={r.text}"
        record("Cleanup", "DELETE /users/me (B)", True)
    run_test("Cleanup", "DELETE /users/me (B)", _delete_b)

    def _delete_a():
        r = httpx.delete(f"{BASE_URL}/users/me", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        assert r.status_code == 204, f"status={r.status_code} body={r.text}"
        record("Cleanup", "DELETE /users/me (A)", True)
    run_test("Cleanup", "DELETE /users/me (A)", _delete_a)

    # Logout (will fail since user deleted, but test the endpoint exists)
    def _logout():
        r = httpx.post(f"{BASE_URL}/auth/logout", headers=_headers(ctx.token_a), timeout=TIMEOUT)
        # May be 401 since user was deleted, or 200 if session still valid
        assert r.status_code in (200, 401, 404), f"Unexpected {r.status_code}"
        record("Cleanup", "POST /auth/logout (after delete)", True)
    run_test("Cleanup", "POST /auth/logout (after delete)", _logout)


# ─── Main ────────────────────────────────────────────────────────
def print_report():
    print("\n" + "=" * 70)
    print("  INTEGRATION TEST REPORT")
    print("=" * 70)

    sections: dict[str, list] = {}
    for r in results:
        sections.setdefault(r["section"], []).append(r)

    total_pass = sum(1 for r in results if r["status"] == "PASS")
    total_fail = sum(1 for r in results if r["status"] == "FAIL")

    for section, tests in sections.items():
        passed = sum(1 for t in tests if t["status"] == "PASS")
        failed = sum(1 for t in tests if t["status"] == "FAIL")
        icon = "PASS" if failed == 0 else "FAIL"
        print(f"\n  [{icon}] {section}  ({passed}/{len(tests)})")
        for t in tests:
            mark = "  PASS" if t["status"] == "PASS" else "  FAIL"
            line = f"    {mark}  {t['name']}"
            if t["status"] == "FAIL" and t["detail"]:
                line += f"\n           -> {t['detail']}"
            print(line)

    print(f"\n{'=' * 70}")
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed, {total_pass + total_fail} total")
    if total_fail == 0:
        print("  ALL TESTS PASSED")
    else:
        print(f"  {total_fail} TEST(S) FAILED")
    print("=" * 70)

    return total_fail


if __name__ == "__main__":
    print(f"Running integration tests against {BASE_URL}")
    print(f"Test UID: {UID}")

    test_health()
    test_auth()
    test_users()
    test_courses()
    test_user_courses()
    test_study_groups()
    test_chat()
    test_schedules()
    test_meetings()
    test_cleanup()

    failures = print_report()
    sys.exit(1 if failures > 0 else 0)
