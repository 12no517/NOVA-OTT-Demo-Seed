# NOVA OTT Demo Data Seeder

Populate an existing NOVA OTT MySQL database with up to **1,000 real movie records from TMDB** and **500 synthetic demo users**.

Movie metadata and poster paths are fetched from TMDB at runtime. User records are synthetic test accounts, not real people.

## Requirements

- Run the NOVA OTT schema first (`database/schema.sql`).
- MySQL running.
- Python 3.10+.
- TMDB API Read Access Token.

## Configure

Place these variables in the NOVA OTT project's `.env` file:

```env
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=YOUR_MYSQL_PASSWORD
DB_NAME=Netflix_OTT
TMDB_API_READ_TOKEN=YOUR_TMDB_READ_ACCESS_TOKEN
NOVA_DEMO_USER_PASSWORD=NovaDemo@2026
```

Never commit `.env` or share real credentials.

## One-command import

Place this repository inside your NOVA OTT project folder as `tools_demo_data`, or copy its `seed.py`, `requirements.txt`, and README into that folder.

From the NOVA OTT project root, run:

```bash
python3 -m pip install -r tools_demo_data/requirements.txt && python3 tools_demo_data/seed.py
```

If using a virtual environment, activate it first:

```bash
source .venv/bin/activate
python3 -m pip install -r tools_demo_data/requirements.txt && python3 tools_demo_data/seed.py
```

The script reads `.env` from the project root (one directory above `tools_demo_data`).

## What it inserts

- Up to 1,000 movies from TMDB Discover, including titles, descriptions, release years, language, genre links and poster URLs.
- 500 synthetic users with one profile each.
- A `Content_Posters` table if it does not already exist.

Existing demo emails and matching title/year/movie records are skipped. The script does not drop the database or delete existing records. It is safe to rerun to fill missing records.

## Demo accounts

- Email range: `nova.demo.user001@example.com` through `nova.demo.user500@example.com`.
- Password: `NOVA_DEMO_USER_PASSWORD` (defaults to `NovaDemo@2026`).

These are shared test credentials. Do not use them on a public production deployment.

## Verify

```sql
USE Netflix_OTT;
SELECT COUNT(*) AS demo_users
FROM Users
WHERE Email LIKE 'nova.demo.user%@example.com';

SELECT COUNT(*) AS movies
FROM Content
WHERE Type='Movie';

SELECT COUNT(*) AS movies_with_posters
FROM Content c
JOIN Content_Posters p ON p.Content_ID=c.Content_ID
WHERE c.Type='Movie';
```

## TMDB

Requires internet access to `api.themoviedb.org` and `image.tmdb.org`. TMDB data and images are subject to its terms and attribution requirements: https://www.themoviedb.org/terms-of-use
