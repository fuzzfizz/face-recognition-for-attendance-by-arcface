-- 20260630000000_init_schema.sql
-- Supabase Database Initialization Migration

-- 1. Create 'users' table
create table if not exists public.users (
    id bigint generated always as identity primary key,
    student_id varchar(20) not null unique,
    name varchar(100) null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Index for fast user lookups by student ID
create index if not exists idx_users_student_id on public.users(student_id);

-- 2. Create 'user_images' table
create table if not exists public.user_images (
    id bigint generated always as identity primary key,
    user_id bigint not null references public.users(id) on delete cascade,
    image_path varchar(255) null,
    image_base64 text null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Index for looking up images belonging to a user
create index if not exists idx_user_images_user_id on public.user_images(user_id);

-- 3. Create 'registration_queue' table
create table if not exists public.registration_queue (
    id bigint generated always as identity primary key,
    student_id varchar(20) not null,
    image_path varchar(255) not null,
    status varchar(20) not null default 'pending',
    error_message text null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    processed_at timestamp with time zone null
);

-- Indexes for status checks and training queues
create index if not exists idx_registration_queue_student_id on public.registration_queue(student_id);
create index if not exists idx_registration_queue_status on public.registration_queue(status);

-- 4. Create 'check_in_logs' table
create table if not exists public.check_in_logs (
    id bigint generated always as identity primary key,
    user_id bigint references public.users(id) on delete set null null,
    student_id varchar(20) null,
    similarity_score double precision null,
    device_id varchar(50) null,
    timestamp timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Index for ordering check-in logs by time
create index if not exists idx_check_in_logs_timestamp on public.check_in_logs(timestamp desc);

-- 5. Row Level Security (RLS) Configuration
-- We disable RLS on these tables so that the FastAPI backend can communicate with them.
-- Note: If you want to use public Anon Key with RLS enabled, you will need to define 
-- explicit SELECT/INSERT policies. If using the Service Role Key, RLS is bypassed automatically.
alter table public.users disable row level security;
alter table public.user_images disable row level security;
alter table public.registration_queue disable row level security;
alter table public.check_in_logs disable row level security;


-- ─────────────────────────────────────────────────────────────
-- SUPABASE STORAGE BUCKET CONFIGURATION
-- ─────────────────────────────────────────────────────────────

-- 1. Insert 'face-images' bucket into storage buckets if it doesn't exist
insert into storage.buckets (id, name, public)
values ('face-images', 'face-images', true)
on conflict (id) do nothing;

-- 2. Drop existing storage policies if they exist to prevent errors
drop policy if exists "Allow Public Select" on storage.objects;
drop policy if exists "Allow Public Insert" on storage.objects;
drop policy if exists "Allow Public Update" on storage.objects;
drop policy if exists "Allow Public Delete" on storage.objects;

-- 3. Create policies to allow public reads and uploads for the face-images bucket
create policy "Allow Public Select"
on storage.objects for select
using ( bucket_id = 'face-images' );

create policy "Allow Public Insert"
on storage.objects for insert
with check ( bucket_id = 'face-images' );

create policy "Allow Public Update"
on storage.objects for update
using ( bucket_id = 'face-images' );

create policy "Allow Public Delete"
on storage.objects for delete
using ( bucket_id = 'face-images' );
