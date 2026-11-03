-- task-flow 스키마 (PostgreSQL / Supabase). SQLite 스키마(alembic 두 개)와 같은 테이블·열이다.
-- 날짜와 시각은 SQLite와 같이 글자(text)로 둔다. 여러 번 실행해도 안전하다.

create table if not exists users (
    id bigint generated always as identity primary key,
    username text not null unique,
    password_hash text not null
);

create table if not exists sessions (
    id text primary key,
    user_id bigint not null references users (id),
    created_at text not null
);

create table if not exists tasks (
    id bigint generated always as identity primary key,
    title text not null,
    description text not null default '',
    status text not null check (status in ('TODO', 'IN_PROGRESS', 'DONE')),
    created_at text not null,
    updated_at text not null,
    owner_id bigint references users (id),
    priority text not null default 'NORMAL' check (priority in ('LOW', 'NORMAL', 'HIGH')),
    due_date text
);

-- Supabase의 공개 API(anon, authenticated)로는 읽고 쓸 수 없게 막는다. 정책은 만들지 않는다.
-- 백엔드는 테이블 주인 계정으로 연결하므로 영향이 없다.
alter table users enable row level security;
alter table sessions enable row level security;
alter table tasks enable row level security;
