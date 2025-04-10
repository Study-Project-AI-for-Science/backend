CREATE TABLE paper_references
(
    id         uuid PRIMARY KEY,
    title      text        NOT NULL,
    authors    text        NOT NULL,
    fields     jsonb       NOT NULL,
    paper_id   uuid        NOT NULL REFERENCES papers (id),
    created_at timestamptz NOT NULL DEFAULT now()
);