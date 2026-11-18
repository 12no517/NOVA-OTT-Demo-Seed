#!/usr/bin/env python3
"""Idempotently add up to 1,000 TMDB movies and 500 synthetic NOVA demo users."""
import hashlib
import os
import secrets
import sys
import time
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# When cloned as <project>/tools_demo_data, find_dotenv walks up to <project>/.env.
load_dotenv()

DB = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "Netflix_OTT"),
}
TOKEN = os.getenv("TMDB_API_READ_TOKEN", "").strip()
MOVIE_TARGET = 1000
USER_TARGET = 500
DEMO_PASSWORD = os.getenv("NOVA_DEMO_USER_PASSWORD", "NovaDemo@2026")

FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Ishaan", "Kabir", "Reyansh", "Ayaan", "Rohan", "Krishna", "Ananya", "Diya", "Aadhya", "Ira", "Kiara", "Meera", "Saanvi", "Myra", "Priya", "Sara", "Neha", "Riya", "Tara", "Zoya", "Nisha"]
LAST = ["Sharma", "Verma", "Singh", "Gupta", "Mehta", "Agarwal", "Patel", "Reddy", "Nair", "Kapoor", "Malhotra", "Iyer", "Joshi", "Khan", "Das", "Rao", "Chopra", "Bose", "Mishra", "Jain"]


def make_password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"pbkdf2_sha256$100000${salt}${digest}"


def tmdb_get(path, params=None):
    url = "https://api.themoviedb.org/3" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "User-Agent": "NOVA-OTT-Demo-Seeder/1.0",
    })
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                time.sleep(min(2 ** attempt, 20))
                continue
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"TMDB HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError("TMDB request failed after retries")


def ensure_genres(cur):
    result = tmdb_get("/genre/movie/list", {"language": "en"})
    genre_map = {}
    for genre in result.get("genres", []):
        cur.execute("INSERT IGNORE INTO Genres (Genre_name) VALUES (%s)", (genre["name"],))
        cur.execute("SELECT Genre_ID FROM Genres WHERE Genre_name=%s", (genre["name"],))
        row = cur.fetchone()
        if row:
            genre_map[int(genre["id"])] = int(row[0])
    return genre_map


def seed_users(cur):
    new_users = 0
    new_profiles = 0
    for number in range(1, USER_TARGET + 1):
        email = f"nova.demo.user{number:03d}@example.com"
        cur.execute("SELECT User_ID FROM Users WHERE Email=%s", (email,))
        row = cur.fetchone()
        first = FIRST[(number - 1) % len(FIRST)]
        last = LAST[((number - 1) // len(FIRST) + number * 3) % len(LAST)]
        name = f"{first} {last} {number:03d}"
        if row:
            user_id = int(row[0])
        else:
            cur.execute(
                "INSERT INTO Users (Name, Email, Password, Phone) VALUES (%s,%s,%s,%s)",
                (name, email, make_password_hash(DEMO_PASSWORD), f"DEMO{number:06d}"),
            )
            user_id = int(cur.lastrowid)
            new_users += 1
        cur.execute("SELECT Profile_ID FROM Profiles WHERE User_ID=%s LIMIT 1", (user_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO Profiles (User_ID, Profile_Name, Is_Kids, Age) VALUES (%s,%s,FALSE,%s)",
                (user_id, first, 18 + (number % 43)),
            )
            new_profiles += 1
    return new_users, new_profiles


def seed_movies(cur, genre_map, db):
    inserted = 0
    scanned = 0
    for page in range(1, 501):
        payload = tmdb_get("/discover/movie", {
            "include_adult": "false",
            "include_video": "false",
            "language": "en-US",
            "page": page,
            "sort_by": "popularity.desc",
            "vote_count.gte": 5,
        })
        movies = payload.get("results", [])
        if not movies:
            break
        for movie in movies:
            if inserted >= MOVIE_TARGET:
                break
            scanned += 1
            title = (movie.get("title") or movie.get("original_title") or "").strip()[:150]
            if not title:
                continue
            raw_year = (movie.get("release_date") or "")[:4]
            year = int(raw_year) if raw_year.isdigit() and 1901 <= int(raw_year) <= 2155 else None
            description = (movie.get("overview") or "No synopsis available.").strip()
            language = (movie.get("original_language") or "en").upper()[:50]
            cur.execute(
                "SELECT Content_ID FROM Content WHERE Title=%s AND Type='Movie' "
                "AND ((Release_YEAR=%s) OR (Release_YEAR IS NULL AND %s IS NULL)) LIMIT 1",
                (title, year, year),
            )
            existing = cur.fetchone()
            if existing:
                content_id = int(existing[0])
            else:
                cur.execute(
                    "INSERT INTO Content "
                    "(Title, Description, Release_YEAR, Duration, Type, Maturity_rating, Language) "
                    "VALUES (%s,%s,%s,NULL,'Movie','NR',%s)",
                    (title, description, year, language),
                )
                content_id = int(cur.lastrowid)
                inserted += 1

            poster_path = movie.get("poster_path")
            if poster_path:
                poster_url = "https://image.tmdb.org/t/p/w500" + poster_path
                cur.execute(
                    "INSERT INTO Content_Posters "
                    "(Content_ID, Poster_URL, Poster_Source, TMDB_ID) "
                    "VALUES (%s,%s,'tmdb',%s) "
                    "ON DUPLICATE KEY UPDATE Poster_URL=VALUES(Poster_URL), "
                    "Poster_Source='tmdb', TMDB_ID=VALUES(TMDB_ID)",
                    (content_id, poster_url, movie.get("id")),
                )

            for tmdb_genre_id in movie.get("genre_ids", []):
                genre_id = genre_map.get(int(tmdb_genre_id))
                if genre_id:
                    cur.execute(
                        "INSERT IGNORE INTO Content_Genres (Content_ID, Genre_ID) VALUES (%s,%s)",
                        (content_id, genre_id),
                    )

        db.commit()
        print(f"TMDB page {page} processed | new movies: {inserted}/{MOVIE_TARGET}")
        if inserted >= MOVIE_TARGET or page >= int(payload.get("total_pages", 500)):
            break
    return inserted, scanned


def main():
    if not TOKEN:
        sys.exit("ERROR: TMDB_API_READ_TOKEN is missing from the NOVA project .env file.")
    if not DB["password"]:
        sys.exit("ERROR: DB_PASSWORD is missing from the NOVA project .env file.")
    print("Connecting to NOVA OTT database...")
    db = mysql.connector.connect(**DB)
    cur = db.cursor()
    try:
        # Fail early with a clear message if the main project schema is not installed.
        for table in ("Users", "Profiles", "Content", "Genres", "Content_Genres"):
            cur.execute(f"SELECT 1 FROM {table} LIMIT 1")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS Content_Posters ("
            "Content_ID INT PRIMARY KEY, Poster_URL VARCHAR(1000) NOT NULL, "
            "Poster_Source VARCHAR(30) NOT NULL DEFAULT 'manual_url', TMDB_ID BIGINT NULL, "
            "Updated_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
            "FOREIGN KEY (Content_ID) REFERENCES Content(Content_ID) ON DELETE CASCADE)"
        )
        db.commit()

        print("Creating or completing the 500 synthetic demo users...")
        users_added, profiles_added = seed_users(cur)
        db.commit()

        print("Fetching TMDB genres and movie catalogue...")
        genre_map = ensure_genres(cur)
        db.commit()
        movies_added, scanned = seed_movies(cur, genre_map, db)

        cur.execute("SELECT COUNT(*) FROM Users WHERE Email LIKE 'nova.demo.user%@example.com'")
        total_demo_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Content WHERE Type='Movie'")
        total_movies = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM Content c JOIN Content_Posters p ON p.Content_ID=c.Content_ID "
            "WHERE c.Type='Movie'"
        )
        total_posters = cur.fetchone()[0]
        print("\nSEED COMPLETE")
        print(f"New demo users: {users_added}; total demo users: {total_demo_users}")
        print(f"New profiles: {profiles_added}")
        print(f"New movies: {movies_added}; total movies in database: {total_movies}")
        print(f"Movies with posters: {total_posters}; TMDB rows scanned: {scanned}")
        print("Demo email range: nova.demo.user001@example.com to nova.demo.user500@example.com")
        print(f"Demo password: {DEMO_PASSWORD}")
        print("Set NOVA_DEMO_USER_PASSWORD in .env before running to use a different password.")
    finally:
        cur.close()
        db.close()


if __name__ == "__main__":
    main()
