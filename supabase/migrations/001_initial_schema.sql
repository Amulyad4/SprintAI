-- AI Sprint Manager — Supabase schema with per-user data isolation (RLS)
-- Run this in Supabase Dashboard → SQL Editor (or via Supabase CLI)

-- ── projects ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id          BIGSERIAL PRIMARY KEY,
    owner_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "projects_select_own" ON projects
    FOR SELECT USING (auth.uid() = owner_id);
CREATE POLICY "projects_insert_own" ON projects
    FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "projects_update_own" ON projects
    FOR UPDATE USING (auth.uid() = owner_id);
CREATE POLICY "projects_delete_own" ON projects
    FOR DELETE USING (auth.uid() = owner_id);

-- ── team_members ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_members (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    role         TEXT,
    velocity_avg DOUBLE PRECISION DEFAULT 10.0,
    project_id   BIGINT REFERENCES projects(id) ON DELETE CASCADE,
    avatar_color TEXT DEFAULT '#3b82f6'
);

CREATE INDEX IF NOT EXISTS idx_team_members_project ON team_members(project_id);

ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "team_members_all_own_project" ON team_members
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = team_members.project_id AND p.owner_id = auth.uid()
        )
    );

-- ── sprints ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sprints (
    id               BIGSERIAL PRIMARY KEY,
    project_id       BIGINT REFERENCES projects(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    goal             TEXT,
    start_date       TEXT,
    end_date         TEXT,
    status           TEXT DEFAULT 'Planning',
    planned_points   INTEGER DEFAULT 0,
    completed_points INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sprints_project ON sprints(project_id);

ALTER TABLE sprints ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sprints_all_own_project" ON sprints
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = sprints.project_id AND p.owner_id = auth.uid()
        )
    );

-- ── tasks ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id              BIGSERIAL PRIMARY KEY,
    sprint_id       BIGINT REFERENCES sprints(id) ON DELETE SET NULL,
    project_id      BIGINT REFERENCES projects(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    assignee_id     BIGINT REFERENCES team_members(id) ON DELETE SET NULL,
    priority        TEXT DEFAULT 'Medium',
    status          TEXT DEFAULT 'Todo',
    issue_type      TEXT DEFAULT 'Task',
    story_points    INTEGER DEFAULT 1,
    estimated_hours DOUBLE PRECISION,
    actual_hours    DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    tags            TEXT,
    blocker_note    TEXT,
    due_date        TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_sprint ON tasks(sprint_id);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tasks_all_own_project" ON tasks
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = tasks.project_id AND p.owner_id = auth.uid()
        )
    );

-- ── sprint_metrics ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sprint_metrics (
    id               BIGSERIAL PRIMARY KEY,
    sprint_id        BIGINT UNIQUE REFERENCES sprints(id) ON DELETE CASCADE,
    velocity         DOUBLE PRECISION,
    completion_rate  DOUBLE PRECISION,
    avg_cycle_time   DOUBLE PRECISION,
    blockers_count   INTEGER DEFAULT 0,
    on_time_tasks    INTEGER DEFAULT 0,
    late_tasks       INTEGER DEFAULT 0
);

ALTER TABLE sprint_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sprint_metrics_all_own_project" ON sprint_metrics
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM sprints s
            JOIN projects p ON p.id = s.project_id
            WHERE s.id = sprint_metrics.sprint_id AND p.owner_id = auth.uid()
        )
    );

-- ── activity_log ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log (
    id            BIGSERIAL PRIMARY KEY,
    project_id    BIGINT REFERENCES projects(id) ON DELETE CASCADE,
    sprint_id     BIGINT,
    task_id       BIGINT,
    task_title    TEXT,
    actor         TEXT DEFAULT 'System',
    action        TEXT,
    field_changed TEXT,
    old_value     TEXT,
    new_value     TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_log(project_id);

ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "activity_log_all_own_project" ON activity_log
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = activity_log.project_id AND p.owner_id = auth.uid()
        )
    );
