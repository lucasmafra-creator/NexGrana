-- REFERENCE ONLY: additive operational tables for SIM Labs 0003.

-- Do not execute alongside Alembic. Do not apply to the financial NexGrana DB.

-- Assumes existing foundation tables. No Auth/RLS/roles/storage deployment is included.

BEGIN;


CREATE TABLE leases (
	key VARCHAR(80) NOT NULL, 
	owner VARCHAR(80) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
)

;


CREATE TABLE daily_reports (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	day VARCHAR(10) NOT NULL, 
	body TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_report_day UNIQUE (product_id, day), 
	FOREIGN KEY(product_id) REFERENCES products (id)
)

;

CREATE INDEX ix_daily_reports_product_id ON daily_reports (product_id);


CREATE TABLE project_configs (
	product_id VARCHAR(36) NOT NULL, 
	description TEXT NOT NULL, 
	platforms TEXT NOT NULL, 
	repository TEXT NOT NULL, 
	rules_json TEXT NOT NULL, 
	PRIMARY KEY (product_id), 
	FOREIGN KEY(product_id) REFERENCES products (id)
)

;


CREATE TABLE releases (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	version VARCHAR(80) NOT NULL, 
	notes TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_release_version UNIQUE (product_id, version), 
	FOREIGN KEY(product_id) REFERENCES products (id)
)

;

CREATE INDEX ix_releases_product_id ON releases (product_id);


CREATE TABLE artifacts (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	release_id VARCHAR(36) NOT NULL, 
	filename VARCHAR(200) NOT NULL, 
	platform VARCHAR(40) NOT NULL, 
	path TEXT NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	report_json TEXT NOT NULL, 
	manifest_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_artifact_release_hash UNIQUE (release_id, sha256), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(release_id) REFERENCES releases (id)
)

;

CREATE INDEX ix_artifacts_product_id ON artifacts (product_id);

CREATE INDEX ix_artifacts_release_id ON artifacts (release_id);


CREATE TABLE decisions (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	release_id VARCHAR(36), 
	title VARCHAR(180) NOT NULL, 
	problem TEXT NOT NULL, 
	impact TEXT NOT NULL, 
	recommendation TEXT NOT NULL, 
	options_json TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	reason TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	UNIQUE (release_id), 
	FOREIGN KEY(release_id) REFERENCES releases (id)
)

;

CREATE INDEX ix_decisions_product_id ON decisions (product_id);


CREATE TABLE evidence (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	release_id VARCHAR(36), 
	feedback_id VARCHAR(36), 
	filename VARCHAR(200) NOT NULL, 
	path TEXT NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_evidence_feedback_hash UNIQUE (feedback_id, sha256), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(release_id) REFERENCES releases (id), 
	FOREIGN KEY(feedback_id) REFERENCES feedbacks (id)
)

;

CREATE INDEX ix_evidence_product_id ON evidence (product_id);


CREATE TABLE integration_receipts (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	source VARCHAR(40) NOT NULL, 
	external_id VARCHAR(150) NOT NULL, 
	feedback_id VARCHAR(36) NOT NULL, 
	release_version VARCHAR(80) NOT NULL, 
	platform VARCHAR(40) NOT NULL, 
	screen VARCHAR(160) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	metadata_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_receipt_origin UNIQUE (product_id, source, external_id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(feedback_id) REFERENCES feedbacks (id)
)

;

CREATE INDEX ix_integration_receipts_feedback_id ON integration_receipts (feedback_id);

CREATE INDEX ix_integration_receipts_product_id ON integration_receipts (product_id);


CREATE TABLE jobs (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	artifact_id VARCHAR(36) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	attempts INTEGER NOT NULL, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	error TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	UNIQUE (artifact_id), 
	FOREIGN KEY(artifact_id) REFERENCES artifacts (id)
)

;

CREATE INDEX ix_jobs_product_id ON jobs (product_id);

CREATE INDEX ix_jobs_status ON jobs (status);


CREATE TABLE messages (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	sender VARCHAR(80) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	body TEXT NOT NULL, 
	task_id VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id)
)

;

CREATE INDEX ix_messages_product_id ON messages (product_id);


CREATE TABLE regression_cases (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	task_id VARCHAR(36) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	steps TEXT NOT NULL, 
	expected TEXT NOT NULL, 
	evidence_id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	UNIQUE (task_id), 
	FOREIGN KEY(task_id) REFERENCES tasks (id), 
	FOREIGN KEY(evidence_id) REFERENCES evidence (id)
)

;

CREATE INDEX ix_regression_cases_product_id ON regression_cases (product_id);


CREATE TABLE test_runs (
	id VARCHAR(36) NOT NULL, 
	product_id VARCHAR(36) NOT NULL, 
	release_id VARCHAR(36) NOT NULL, 
	artifact_id VARCHAR(36), 
	kind VARCHAR(40) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	result_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(release_id) REFERENCES releases (id), 
	FOREIGN KEY(artifact_id) REFERENCES artifacts (id)
)

;

CREATE INDEX ix_test_runs_release_id ON test_runs (release_id);

CREATE INDEX ix_test_runs_product_id ON test_runs (product_id);

COMMIT;