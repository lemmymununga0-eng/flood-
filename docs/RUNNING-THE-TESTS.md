# Running the Tests

All three suites, and how to get the backend one running — which until 2026-10-02 had
never been executed because no PostgreSQL was available on the development machine.

| Suite | Count | Command |
|---|---:|---|
| ML pipeline | 37 | `python -m pytest ml/tests -q` |
| Frontend | 11 | `cd frontend && npm test` |
| Backend | 57 | see below — needs PostgreSQL |

## Backend: 57 tests

`backend/tests/conftest.py` deliberately runs against **real PostgreSQL**, not SQLite —
the project's schema uses Postgres behaviour the tests assert on, and substituting SQLite
would make them prove less than they appear to. Each test runs inside a transaction that
is rolled back, so the database stays clean between runs.

It expects exactly this DSN:

```
postgresql://floodshield:changeme_dev_only@localhost:5432/floodshield_zambia_test
```

### Option A — portable PostgreSQL (no installer, no service, no admin)

This is what was used to run the suite. The EnterpriseDB **binaries zip** works where the
installer does not: at time of writing `winget install PostgreSQL.PostgreSQL.16` fails
with `0x80190193 : Forbidden (403)` because EnterpriseDB rejects that download.

```powershell
# 1. download + extract (~323 MB)
Invoke-WebRequest `
  -Uri "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64-binaries.zip" `
  -OutFile pg16.zip
Expand-Archive pg16.zip -DestinationPath .\pg

# 2. initialise a throwaway data directory
"postgres" | Out-File -Encoding ascii -NoNewline pw.txt
.\pg\pgsql\bin\initdb.exe -D .\pgdata -U postgres --pwfile=pw.txt -E UTF8 --no-locale

# 3. start it on loopback only
.\pg\pgsql\bin\pg_ctl.exe -D .\pgdata -l pg.log -o "-p 5432 -h 127.0.0.1" start

# 4. create the role and database conftest.py expects
$env:PGPASSWORD = "postgres"
.\pg\pgsql\bin\psql.exe -U postgres -h 127.0.0.1 -c `
  "CREATE ROLE floodshield LOGIN PASSWORD 'changeme_dev_only' SUPERUSER;"
.\pg\pgsql\bin\createdb.exe -U postgres -h 127.0.0.1 -O floodshield floodshield_zambia_test

# 5. run them
cd backend
$env:DATABASE_URL = "postgresql://floodshield:changeme_dev_only@localhost:5432/floodshield_zambia_test"
python -m pytest -q
```

Two notes on step 2 and 3:

- `initdb` prints `warning: enabling "trust" authentication for local connections` to
  **stderr**. PowerShell with `$ErrorActionPreference = "Stop"` treats that as a failure
  and aborts even though initdb succeeded. Set it to `Continue` around these calls.
- `pg_ctl ... -w start` blocks until the server is ready and holds the console. Drop `-w`
  or run it detached if you are scripting.

### Option B — a normal PostgreSQL install

Any PostgreSQL 14+ works. Create the role and database as in step 4 above.

### Option C — point at an existing server

Set `DATABASE_URL` to any PostgreSQL you control. **Do not point it at the application's
own database** — `conftest.py` creates and drops tables.

## Result as of 2026-10-02

```
backend   57 passed in 55.86s
ml        37 passed
frontend  11 passed
```

Nothing in this project claims a pass count it has not measured. Before this date the
backend figure was reported everywhere as "57 written, never executed" precisely because
it had not been.
