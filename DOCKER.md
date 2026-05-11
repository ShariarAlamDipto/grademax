# Docker Setup

This project runs as a production Next.js standalone container. Runtime working files are bind-mounted outside the image so rebuilds and container replacement do not remove uploaded/source PDFs, generated PDFs, logs, or private config.

## Persistent Host Folders

By default, Docker Compose mounts these folders from `../grademax-persistent`:

- `data` -> `/app/data`
- `logs` -> `/app/logs`
- `output` -> `/app/output`
- `config` -> `/app/config`
- `../postgres_data` -> PostgreSQL data directory

PostgreSQL is internal to Docker Compose only. It is reachable by the app at `postgres:5432`; it is not published on a host port.

Change the host location with `GRADEMAX_PERSIST_DIR` in `docker.env`.

## First Run

```bash
cp docker.env.example docker.env
mkdir -p ../grademax-persistent/{data,logs,output,config}
mkdir -p ../postgres_data
cp -R config/. ../grademax-persistent/config/
```

Fill `docker.env` with the real Supabase and R2 values. The `NEXT_PUBLIC_*` values are needed at build time as well as runtime, so rebuild after changing them:

```bash
docker compose --env-file docker.env up --build -d
```

Open:

```text
http://127.0.0.1:3004
```

## Useful Commands

```bash
docker compose logs -f grademax
docker compose restart grademax
docker compose down
```

Run one-off project scripts inside the same image:

```bash
docker compose --env-file docker.env run --rm grademax npm run ingest:papers -- --data-dir=/app/data/raw
docker compose --env-file docker.env run --rm grademax python scripts/preflight_check.py
```

## Notes

- Large/local working folders are intentionally excluded from the Docker build context by `.dockerignore`.
- The application stores admin paper uploads in Cloudflare R2 and worksheet page downloads in temporary container storage. Local ingestion and processing scripts use the mounted `/app/data`, `/app/output`, and `/app/logs` folders.
- Place private runtime files such as `google-service-account.json` in the mounted `config` folder, not in the image.
