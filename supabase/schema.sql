-- Schema for the Supabase storage backend.
-- Run in the Supabase SQL editor, or via `supabase db push`.

create table if not exists public.users (
    telegram_id   bigint primary key,
    username      text,
    full_name     text,
    language_code text,
    created_at    timestamptz not null default now()
);

create table if not exists public.messages (
    id          uuid primary key default gen_random_uuid(),
    telegram_id bigint not null references public.users (telegram_id) on delete cascade,
    role        text   not null check (role in ('user', 'assistant')),
    kind        text   not null default 'text' check (kind in ('text', 'voice', 'photo')),
    content     text   not null,
    created_at  timestamptz not null default now()
);

-- History is always read as "last N for this user", so index that access path.
create index if not exists messages_user_recent_idx
    on public.messages (telegram_id, created_at desc);

create table if not exists public.notes (
    id          uuid primary key default gen_random_uuid(),
    telegram_id bigint not null references public.users (telegram_id) on delete cascade,
    text        text   not null,
    tags        text[] not null default '{}',
    created_at  timestamptz not null default now()
);

create index if not exists notes_user_recent_idx
    on public.notes (telegram_id, created_at desc);

-- The bot connects with the service_role key and is the only writer, so RLS is
-- enabled with no permissive policy: anon/authenticated clients get nothing.
alter table public.users    enable row level security;
alter table public.messages enable row level security;
alter table public.notes    enable row level security;
