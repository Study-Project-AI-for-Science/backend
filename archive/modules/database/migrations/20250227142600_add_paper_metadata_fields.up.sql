-- Add additional metadata fields to the papers table
ALTER TABLE papers
ADD COLUMN abstract TEXT,
ADD COLUMN online_url TEXT,
ADD COLUMN published_date TIMESTAMPTZ,
ADD COLUMN updated_date TIMESTAMPTZ;