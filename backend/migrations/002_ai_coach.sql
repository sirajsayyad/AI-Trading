-- Additive private AI Coach conversations; existing users/curriculum must exist.

BEGIN;

CREATE TABLE IF NOT EXISTS ai_conversations (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	course_id VARCHAR(36),
	lesson_id VARCHAR(36),
	title VARCHAR(100) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(course_id) REFERENCES courses (id),
	FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE INDEX IF NOT EXISTS ix_ai_conversations_user_id ON ai_conversations (user_id);

CREATE INDEX IF NOT EXISTS ix_ai_conversations_updated_at ON ai_conversations (updated_at);

CREATE TABLE IF NOT EXISTS ai_messages (
	id SERIAL NOT NULL,
	conversation_id VARCHAR(36) NOT NULL,
	role VARCHAR(10) NOT NULL,
	content TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(conversation_id) REFERENCES ai_conversations (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_ai_messages_conversation_id ON ai_messages (conversation_id);

COMMIT;
