---
status: complete
slug: library-demo
---

# Library — Book Tracking API Tech Design

## Tech stack
- C# / .NET 9
- PostgreSQL
- Dapper

## Architecture overview

Single module, `Library`, exposing minimal REST endpoints for tracking
books and authors. A user creates an author, then creates books linked
to the author, then updates reading status as they read.

<module name="Library">

<entities>

### Author

A person who wrote one or more books. Authors exist independently of books.

```sql
CREATE TABLE authors (
  id           UUID        PRIMARY KEY,
  name         TEXT        NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_authors_name ON authors(name);
```

**Invariants:** name is non-empty.

### Book

A title the user wants to track. Each book has exactly one author and a
reading-status that transitions through the lifecycle.

```sql
CREATE TABLE books (
  id           UUID        PRIMARY KEY,
  author_id    UUID        NOT NULL REFERENCES authors(id),
  title        TEXT        NOT NULL,
  status       TEXT        NOT NULL CHECK (status IN ('unread','reading','completed','abandoned')),
  page_count   INT         NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_books_author ON books(author_id);
CREATE INDEX idx_books_status ON books(status);
```

**Invariants:** title is non-empty; page_count > 0; status transitions
unread → reading → completed | abandoned.

</entities>

<enums>

### ReadingStatus

- unread
- reading
- completed
- abandoned

</enums>

<contracts>

### CreateAuthorRequest

- name: string — required, non-empty

### AuthorResponse

- id: Guid
- name: string

### CreateBookRequest

- authorId: Guid — required
- title: string — required, non-empty
- pageCount: int — required, > 0

### BookResponse

- id: Guid
- authorId: Guid
- title: string
- status: ReadingStatus
- pageCount: int

### UpdateStatusRequest

- status: ReadingStatus — required

</contracts>

<routes>

### POST /authors

Request: `CreateAuthorRequest`
Response: `AuthorResponse`

### GET /authors/{id}

Response: `AuthorResponse`

### POST /books

Request: `CreateBookRequest`
Response: `BookResponse`

### GET /books/{id}

Response: `BookResponse`

### PUT /books/{id}/status

Request: `UpdateStatusRequest`
Response: `BookResponse`

</routes>

</module>
