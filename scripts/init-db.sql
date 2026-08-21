-- Create rag_db database
CREATE DATABASE rag_db;

-- Connect to rag_db and create pgvector extension
\c rag_db

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
