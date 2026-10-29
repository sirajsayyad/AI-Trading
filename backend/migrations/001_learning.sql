-- Additive PostgreSQL LMS migration. Back up the database before applying.

-- Existing courses, modules, lessons and users must already exist.

BEGIN;


CREATE TABLE IF NOT EXISTS course_info (
	course_id VARCHAR(36) NOT NULL,
	metadata_json JSON NOT NULL,
	PRIMARY KEY (course_id),
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS lesson_info (
	lesson_id VARCHAR(36) NOT NULL,
	metadata_json JSON NOT NULL,
	PRIMARY KEY (lesson_id),
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS enrollments (
	user_id VARCHAR(36) NOT NULL,
	course_id VARCHAR(36) NOT NULL,
	enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (user_id, course_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_enrollments_course_id ON enrollments (course_id);


CREATE TABLE IF NOT EXISTS lecture_progress (
	user_id VARCHAR(36) NOT NULL,
	lesson_id VARCHAR(36) NOT NULL,
	position FLOAT NOT NULL,
	completed BOOLEAN NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (user_id, lesson_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_lecture_progress_lesson_id ON lecture_progress (lesson_id);


CREATE TABLE IF NOT EXISTS bookmarks (
	user_id VARCHAR(36) NOT NULL,
	lesson_id VARCHAR(36) NOT NULL,
	position FLOAT NOT NULL,
	notes TEXT NOT NULL,
	PRIMARY KEY (user_id, lesson_id, position),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_bookmarks_lesson_id ON bookmarks (lesson_id);


CREATE TABLE IF NOT EXISTS quiz_results (
	id SERIAL NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	lesson_id VARCHAR(36) NOT NULL,
	score INTEGER NOT NULL,
	answers JSON NOT NULL,
	attempted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_quiz_results_lesson_id ON quiz_results (lesson_id);

CREATE INDEX IF NOT EXISTS ix_quiz_results_user_id ON quiz_results (user_id);

COMMIT;
