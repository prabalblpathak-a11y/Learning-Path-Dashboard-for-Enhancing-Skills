-- ============================================================
-- SkillForge Learning Path Dashboard - MySQL Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS skillforge;
USE skillforge;

-- -------------------------------------------------------
-- USERS
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)        NOT NULL,
    email       VARCHAR(150)        NOT NULL UNIQUE,
    password    VARCHAR(255)        NOT NULL,          -- bcrypt hash
    avatar_url  VARCHAR(500)        DEFAULT NULL,
    bio         VARCHAR(300)        DEFAULT NULL,
    xp          INT                 DEFAULT 0,
    streak      INT                 DEFAULT 0,
    last_login  DATETIME            DEFAULT NULL,
    created_at  DATETIME            DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME            DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- -------------------------------------------------------
-- COURSES
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200)        NOT NULL,
    description TEXT                DEFAULT NULL,
    level       ENUM('Beginner','Intermediate','Advanced') NOT NULL DEFAULT 'Beginner',
    category    VARCHAR(100)        DEFAULT NULL,
    thumbnail   VARCHAR(500)        DEFAULT NULL,
    total_xp    INT                 DEFAULT 100,
    created_by  INT                 DEFAULT NULL,      -- NULL = system course
    created_at  DATETIME            DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- -------------------------------------------------------
-- USER ↔ COURSE ENROLMENTS
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrolments (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL,
    course_id       INT             NOT NULL,
    progress        TINYINT UNSIGNED DEFAULT 0,       -- 0-100 %
    status          ENUM('active','completed','paused') DEFAULT 'active',
    enrolled_at     DATETIME        DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME        DEFAULT NULL,
    UNIQUE KEY uq_user_course (user_id, course_id),
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- ACHIEVEMENTS (badge catalogue)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)        NOT NULL UNIQUE,
    description VARCHAR(300)        DEFAULT NULL,
    icon        VARCHAR(10)         DEFAULT '🏆',     -- emoji icon
    xp_reward   INT                 DEFAULT 0
);

-- Seed default achievements
INSERT IGNORE INTO achievements (name, description, icon, xp_reward) VALUES
('First Course',   'Enrolled in your first course',        '🎯', 50),
('7-Day Streak',   'Logged in 7 days in a row',            '🔥', 100),
('Course Master',  'Completed a course',                   '🥇', 200),
('Speed Learner',  'Completed 3 courses',                  '🚀', 300),
('Coder',          'Completed a programming course',       '💻', 150);

-- -------------------------------------------------------
-- USER ACHIEVEMENTS (earned badges)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_achievements (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL,
    achievement_id  INT             NOT NULL,
    earned_at       DATETIME        DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_ach (user_id, achievement_id),
    FOREIGN KEY (user_id)        REFERENCES users(id)        ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- DAILY ACTIVITY LOG  (used for Weekly Activity chart)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT             NOT NULL,
    log_date    DATE            NOT NULL,
    hours       DECIMAL(4,2)    DEFAULT 0.00,
    UNIQUE KEY uq_user_date (user_id, log_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- DAILY GOALS
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_goals (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL UNIQUE,
    target_hours    DECIMAL(4,2)    DEFAULT 2.00,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- SEED: Sample courses
-- -------------------------------------------------------
INSERT IGNORE INTO courses (id, title, description, level, category, total_xp) VALUES
(1, 'HTML & CSS',    'Web page structure and styling',                 'Beginner',     'Web',    100),
(2, 'JavaScript',    'Core JS concepts and DOM manipulation',          'Intermediate', 'Web',    200),
(3, 'React',         'Component-based UI development with React',      'Advanced',     'Web',    300),
(4, 'Python Basics', 'Introduction to Python programming language',   'Beginner',     'Backend',100),
(5, 'SQL & MySQL',   'Relational databases and query writing',        'Intermediate', 'Backend',150);
