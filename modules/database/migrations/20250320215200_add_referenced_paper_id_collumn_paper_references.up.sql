-- Add additional collum field to the papers table
ALTER TABLE paper_references

ADD COLUMN  reference_paper_id  uuid    REFERENCES papers (id);
