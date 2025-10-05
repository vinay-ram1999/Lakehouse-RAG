create extension if not exists vector;

create table if not exists documents (
  id uuid primary key,
  file_name text not null,
  file_path text not null,
  file_metadata json,
  created_at timestamptz default now()
);

create table if not exists document_chunks (
  id uuid primary key,
  document_id uuid not null references documents(id) on delete cascade,
  content text not null,
  embedding vector(768) not null,
  chunk_order int not null,
  created_at timestamptz default now()
);

create index if not exists document_chunk_embedding_index
on document_chunks using hnsw (embedding vector_cosine_ops);
