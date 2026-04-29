-- Create both databases needed by the application
CREATE DATABASE hti_pipeline;
GRANT ALL PRIVILEGES ON DATABASE hti_pipeline TO supplier;
GRANT ALL PRIVILEGES ON DATABASE supplier_hub TO supplier;
