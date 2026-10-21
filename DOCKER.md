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
npm run persistent:prepare
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

Initialize the internal PostgreSQL database:

```bash
docker compose --env-file docker.env up -d postgres
docker compose --env-file docker.env run --rm grademax npm run postgres:migrate
docker compose --env-file docker.env run --rm grademax npm run postgres:seed
```

## Notes

- Large/local working folders are intentionally excluded from the Docker build context by `.dockerignore`.
- The application stores admin paper uploads in Cloudflare R2 and worksheet page downloads in temporary container storage. Local ingestion and processing scripts use the mounted `/app/data`, `/app/output`, and `/app/logs` folders.
- Place private runtime files such as `google-service-account.json` in the mounted `config` folder, not in the image.

## Production (www.grademax.me behind Cloudflare)

Cloudflare shows "Bad gateway 502, Host: Error" whenever the server behind it fails to answer. Each item below closes one way that happened or can happen.

| Cause | Symptom | Fix |
| --- | --- | --- |
| nginx header buffer (4k default) smaller than the sign-in response (~5 KB session cookie + ~3 KB headers) | 502 on sign-in, and for signed-in users roughly hourly when the token refreshes | `deploy/nginx/grademax.conf`: `proxy_buffer_size 16k` etc. |
| Signed-in browser's cookies exceed nginx's 8k request-header line | 400 "Request Header Or Cookie Too Large" | `large_client_header_buffers 4 32k` (same file) |
| `docker compose down` before a multi-minute build | 502 for everyone during every deploy | `scripts/deploy/deploy.sh`: build first, swap, health-check, roll back |
| Node hung or "unhealthy" (Docker does not restart those) | 502/504 until someone notices | `scripts/deploy/watchdog.sh` from cron, every minute |
| Image built without `--env-file docker.env` | Sign-in button goes to `http://localhost` | Dockerfile now refuses to build with placeholder `NEXT_PUBLIC_*` values |
| Long PDF generation | 504 from nginx at 60 s, or 524 from Cloudflare at 100 s | `proxy_read_timeout 100s`; the app caps normal users at 30 questions |

One-time server setup:

```bash
sudo cp deploy/nginx/grademax.conf /etc/nginx/sites-available/grademax   # merge with the existing site file
sudo nginx -t && sudo systemctl reload nginx
chmod +x scripts/deploy/*.sh
( crontab -l 2>/dev/null; echo "* * * * * $PWD/scripts/deploy/watchdog.sh >> $HOME/grademax-watchdog.log 2>&1" ) | crontab -
```

Every deploy:

```bash
bash scripts/deploy/deploy.sh
```

Diagnose a 502:

```bash
sudo grep -E "too big header|connect\(\) failed|upstream timed out" /var/log/nginx/error.log | tail
docker ps --filter name=grademax-app --format '{{.Status}}'   # "Up 2 minutes" = it just restarted
docker compose --env-file docker.env logs --since 30m grademax | tail -80
tail -20 ~/grademax-watchdog.log
```
