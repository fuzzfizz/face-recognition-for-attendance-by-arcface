CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS students (
  student_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(256),
  email VARCHAR(256),
  auth_uid VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_students_auth_uid ON students(auth_uid);

CREATE TABLE IF NOT EXISTS registration_sessions (
  id BIGSERIAL PRIMARY KEY,
  student_id VARCHAR(64) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
  session_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  image_count INT NOT NULL DEFAULT 0,
  uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL,
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_registration_sessions_student_id ON registration_sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_status ON registration_sessions(session_status);

CREATE TABLE IF NOT EXISTS face_images (
  id BIGSERIAL PRIMARY KEY,
  registration_session_id BIGINT NOT NULL REFERENCES registration_sessions(id) ON DELETE CASCADE,
  student_id VARCHAR(64) NOT NULL REFERENCES students(student_id),
  storage_path TEXT NOT NULL,
  storage_url TEXT,
  file_name TEXT NOT NULL,
  file_size INT,
  mime_type VARCHAR(64),
  capture_timestamp TIMESTAMP,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  quality_score REAL,
  face_confidence REAL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_face_images_session_id ON face_images(registration_session_id);
CREATE INDEX IF NOT EXISTS idx_face_images_student_id ON face_images(student_id);
CREATE INDEX IF NOT EXISTS idx_face_images_status ON face_images(status);

CREATE TABLE IF NOT EXISTS training_jobs (
  id BIGSERIAL PRIMARY KEY,
  student_id VARCHAR(64) REFERENCES students(student_id) ON DELETE SET NULL,
  session_id BIGINT REFERENCES registration_sessions(id) ON DELETE SET NULL,
  job_type VARCHAR(32) NOT NULL,
  job_status VARCHAR(32) NOT NULL DEFAULT 'queued',
  started_at TIMESTAMP NULL,
  finished_at TIMESTAMP NULL,
  error_message TEXT,
  model_version VARCHAR(128),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_training_jobs_student_id ON training_jobs(student_id);
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(job_status);

CREATE TABLE IF NOT EXISTS face_embeddings (
  id BIGSERIAL PRIMARY KEY,
  student_id VARCHAR(64) NOT NULL REFERENCES students(student_id),
  image_id BIGINT NOT NULL REFERENCES face_images(id) ON DELETE CASCADE,
  embedding BYTEA NOT NULL,
  embedding_type VARCHAR(64) NOT NULL DEFAULT 'arcface-512',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_student_id ON face_embeddings(student_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_image_id ON face_embeddings(image_id);

COMMENT ON TABLE students IS 'Stores basic information about users/students';
COMMENT ON TABLE registration_sessions IS 'Tracks each photo upload session by a student';
COMMENT ON TABLE face_images IS 'Stores metadata for each uploaded face image';
COMMENT ON TABLE training_jobs IS 'Tracks model training jobs (incremental or full)';
COMMENT ON TABLE face_embeddings IS 'Stores face embeddings (vectors) generated from the model';
