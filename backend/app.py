# app.py — SkillForge backend (single file, no blueprints, no extra config)
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
import jwt, datetime, os

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Config ────────────────────────────────────────────────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 3306)}"
    f"/{os.getenv('DB_NAME')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "changeme")

db = SQLAlchemy(app)


# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(100), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    bio        = db.Column(db.String(300), default="")
    avatar_url = db.Column(db.String(300), default="")
    xp         = db.Column(db.Integer, default=0)
    streak     = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    daily_goal = db.Column(db.Float, default=2.0)   # hours per day

    courses      = db.relationship("Course",     backref="owner",    lazy=True)
    activity_logs = db.relationship("ActivityLog", backref="owner",   lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "bio":        self.bio,
            "avatar_url": self.avatar_url,
            "xp":         self.xp,
            "streak":     self.streak,
        }


class Course(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title    = db.Column(db.String(200), nullable=False)
    level    = db.Column(db.String(50),  default="Beginner")
    progress = db.Column(db.Integer,     default=0)   # 0-100
    status   = db.Column(db.String(20),  default="active")  # active | completed

    def to_dict(self):
        return {
            "id":          self.id,
            "course_id":   self.id,        # some pages use course_id
            "course_title": self.title,    # matches what courses.html expects
            "title":       self.title,
            "level":       self.level,
            "progress":    self.progress,
            "status":      self.status,
        }


class ActivityLog(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    log_date = db.Column(db.Date,    nullable=False)
    hours    = db.Column(db.Float,   default=0.0)


# ══════════════════════════════════════════════════════════════════════════════
# AUTH HELPER
# ══════════════════════════════════════════════════════════════════════════════

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Authorization header missing"}), 401
        token = header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        g.user = User.query.get(payload["user_id"])
        if not g.user:
            return jsonify({"error": "User not found"}), 401
        return f(*args, **kwargs)
    return decorated


def make_token(user_id):
    exp = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(os.getenv("JWT_EXPIRES", 3600)))
    return jwt.encode({"user_id": user_id, "exp": exp}, app.config["SECRET_KEY"], algorithm="HS256")


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES  /api/auth
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/register")
def register():
    data     = request.get_json(silent=True) or {}
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(name=name, email=email, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    return jsonify({"token": make_token(user.id), "user": user.to_dict()}), 201


@app.post("/api/auth/login")
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Update streak
    today = datetime.date.today()
    if user.last_login:
        diff = today - user.last_login.date()
        if diff.days == 1:
            user.streak += 1
        elif diff.days > 1:
            user.streak = 1
    else:
        user.streak = 1

    user.last_login = datetime.datetime.utcnow()
    db.session.commit()

    return jsonify({"token": make_token(user.id), "user": user.to_dict()}), 200


# ══════════════════════════════════════════════════════════════════════════════
# USER ROUTES  /api/users
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/users/me")
@token_required
def get_profile():
    u = g.user
    data = u.to_dict()
    data["daily_goal_hours"] = u.daily_goal
    return jsonify(data), 200


@app.put("/api/users/me")
@token_required
def update_profile():
    u    = g.user
    data = request.get_json(silent=True) or {}

    if "name"       in data: u.name       = data["name"].strip()
    if "bio"        in data: u.bio        = data["bio"].strip()
    if "avatar_url" in data: u.avatar_url = data["avatar_url"].strip()
    if "password"   in data and data["password"]:
        u.password = generate_password_hash(data["password"])
    if "daily_goal_hours" in data:
        u.daily_goal = float(data["daily_goal_hours"])

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": u.to_dict()}), 200


@app.get("/api/users/me/dashboard")
@token_required
def dashboard():
    u = g.user

    courses   = Course.query.filter_by(user_id=u.id).all()
    active    = [c for c in courses if c.status != "completed"]
    completed = [c for c in courses if c.status == "completed"]
    avg_prog  = round(sum(c.progress for c in active) / len(active)) if active else 0

    today_log = ActivityLog.query.filter_by(
        user_id=u.id, log_date=datetime.date.today()
    ).first()

    return jsonify({
        "courses_enrolled":  len(courses),
        "courses_completed": len(completed),
        "avg_progress":      avg_prog,
        "xp":                u.xp,
        "streak":            u.streak,
        "achievements":      [],          # kept so frontend doesn't break
        "today_hours":       float(today_log.hours) if today_log else 0.0,
        "target_hours":      u.daily_goal,
    }), 200


# ══════════════════════════════════════════════════════════════════════════════
# COURSE ROUTES  /api/courses
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/courses/my")
@token_required
def my_courses():
    courses = Course.query.filter_by(user_id=g.user.id).all()
    return jsonify([c.to_dict() for c in courses]), 200


@app.post("/api/courses/")
@token_required
def add_course():
    data  = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    level = data.get("level", "Beginner")

    if not title:
        return jsonify({"error": "title is required"}), 400
    if level not in ("Beginner", "Intermediate", "Advanced"):
        return jsonify({"error": "level must be Beginner, Intermediate, or Advanced"}), 400

    course = Course(user_id=g.user.id, title=title, level=level)
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201


@app.get("/api/courses/<int:course_id>")
@token_required
def get_course(course_id):
    course = Course.query.filter_by(id=course_id, user_id=g.user.id).first_or_404()
    return jsonify(course.to_dict()), 200


# The frontend calls /enrol after creating a course — just return success
# since courses are now directly owned by the user (no separate enrolment table)
@app.post("/api/courses/<int:course_id>/enrol")
@token_required
def enrol(course_id):
    course = Course.query.filter_by(id=course_id, user_id=g.user.id).first_or_404()
    return jsonify(course.to_dict()), 201


@app.patch("/api/courses/<int:course_id>/progress")
@token_required
def update_progress(course_id):
    data     = request.get_json(silent=True) or {}
    progress = int(data.get("progress", 0))

    if not (0 <= progress <= 100):
        return jsonify({"error": "progress must be 0-100"}), 400

    course = Course.query.filter_by(id=course_id, user_id=g.user.id).first_or_404()
    course.progress = progress

    if progress == 100 and course.status != "completed":
        course.status = "completed"
        g.user.xp    += 100   # flat XP per completed course

    db.session.commit()
    return jsonify(course.to_dict()), 200


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ROUTES  /api/analytics
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/analytics/log")
@token_required
def log_activity():
    data  = request.get_json(silent=True) or {}
    hours = float(data.get("hours", 0))
    if hours < 0:
        return jsonify({"error": "hours must be >= 0"}), 400

    today = datetime.date.today()
    log   = ActivityLog.query.filter_by(user_id=g.user.id, log_date=today).first()

    if log:
        log.hours = hours
    else:
        log = ActivityLog(user_id=g.user.id, log_date=today, hours=hours)
        db.session.add(log)

    db.session.commit()
    return jsonify({"date": today.isoformat(), "hours": log.hours}), 200


@app.get("/api/analytics/weekly")
@token_required
def weekly():
    today = datetime.date.today()
    days  = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]

    logs = {
        l.log_date: l.hours
        for l in ActivityLog.query.filter(
            ActivityLog.user_id  == g.user.id,
            ActivityLog.log_date >= days[0],
            ActivityLog.log_date <= days[-1],
        ).all()
    }

    return jsonify([
        {"date": d.isoformat(), "day": d.strftime("%a"), "hours": logs.get(d, 0.0)}
        for d in days
    ]), 200


@app.get("/api/analytics/courses")
@token_required
def course_breakdown():
    courses = Course.query.filter_by(user_id=g.user.id).all()
    return jsonify([
        {"course": c.title, "level": c.level, "progress": c.progress, "status": c.status}
        for c in courses
    ]), 200


# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
