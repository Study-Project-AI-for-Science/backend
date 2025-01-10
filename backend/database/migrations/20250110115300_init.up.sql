CREATE TABLE papers (
    id uuid PRIMARY KEY,
    title text NOT NULL,
    authors text NOT NULL,
    file_url text NOT NULL,
    file_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);