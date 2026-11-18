USE Netflix_OTT;

-- Synthetic demo users
SELECT COUNT(*) AS demo_users
FROM Users
WHERE Email LIKE 'nova.demo.user%@example.com';

-- Total movie catalogue records
SELECT COUNT(*) AS total_movies
FROM Content
WHERE Type = 'Movie';

-- Movies with a mapped poster
SELECT COUNT(*) AS movies_with_posters
FROM Content c
JOIN Content_Posters p ON p.Content_ID = c.Content_ID
WHERE c.Type = 'Movie';

-- Movies grouped by genre
SELECT g.Genre_name, COUNT(*) AS movie_count
FROM Genres g
JOIN Content_Genres cg ON cg.Genre_ID = g.Genre_ID
JOIN Content c ON c.Content_ID = cg.Content_ID
WHERE c.Type = 'Movie'
GROUP BY g.Genre_ID, g.Genre_name
ORDER BY movie_count DESC;
