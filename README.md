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

From the NOVA OTT project root, clone this repository into the expected folder, install the dependencies, and run the importer:

```bash
git clone https://github.com/12no517/NOVA-OTT-Demo-Seed.git tools_demo_data && python3 -m pip install -r tools_demo_data/requirements.txt && python3 tools_demo_data/seed.py
```

If the folder already exists, update it first or remove only that cloned `tools_demo_data` folder before running the clone command again. Do not remove your project folder or database.

With a virtual environment, activate it first:

```bash
source .venv/bin/activate
git clone https://github.com/12no517/NOVA-OTT-Demo-Seed.git tools_demo_data && python3 -m pip install -r tools_demo_data/requirements.txt && python3 tools_demo_data/seed.py
```

The script reads the NOVA project's `.env` file from the parent folder.

## What it inserts

- Up to 1,000 movies from TMDB Discover, including titles, descriptions, release years, language, genre links and poster URLs.
- 500 synthetic users with one profile each.
- Poster metadata in the local `instance/poster_map.json` file and downloaded artwork in `static/uploads/posters/`; no new MySQL table or column is created.

Existing demo emails and matching title/year/movie records are reused or skipped. The script does not drop the database or delete existing records. It is safe to rerun to fill missing records.

## Demo accounts

- Email range: `nova.demo.user001@example.com` through `nova.demo.user500@example.com`.
- Password: `NOVA_DEMO_USER_PASSWORD` (defaults to `NovaDemo@2026`).

These are shared test credentials. Do not use them on a public production deployment.

## Verify

Run the queries in [verify.sql](verify.sql) in MySQL Workbench or the MySQL client.

## TMDB

Requires internet access to `api.themoviedb.org` and `image.tmdb.org`. TMDB data and images are subject to its terms and attribution requirements: https://www.themoviedb.org/terms-of-use

## Reliable poster display

The seeder downloads TMDB artwork into the NOVA project's `static/uploads/posters/` folder and stores same-origin `/static/uploads/posters/...` paths in `instance/poster_map.json`, outside MySQL. If a previous version created the optional `Content_Posters` table, the seeder only reads its records to migrate mappings to JSON; it does not create, update, alter, or drop that table. The movie refresh pass processes the first 1,000 catalogue results even if those titles already exist, so it refreshes poster mappings rather than inserting duplicates only.
