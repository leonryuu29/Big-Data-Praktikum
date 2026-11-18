-- Aufgabe 3 e) + f): Abfragen (jeweils genau eine Partition)
USE movielens;

-- e) Die ersten 5 Filme (alphabetisch), die Nutzy 42 bewertet hat
SELECT title, rating FROM movies_by_user WHERE user_id = 42 LIMIT 5;

-- e) Wie viele Filme hat Nutzy 42 insgesamt bewertet?
SELECT COUNT(*) FROM movies_by_user WHERE user_id = 42;

-- f) Welche Nutzys haben "Toy Story (1995)" bewertet?
--    Schritt 1: Titel -> movie_id
SELECT movie_id, title FROM movies_by_title WHERE title = 'Toy Story (1995)';
--    Schritt 2: alle Nutzys dieses Films (hier die ersten 10) und ihre Anzahl
SELECT user_id, rating FROM users_by_movie WHERE movie_id = 1 LIMIT 10;
SELECT COUNT(*) FROM users_by_movie WHERE movie_id = 1;

-- Doppelte Titel: ein Titel, zwei Filme -> zwei Zeilen in derselben Partition
SELECT * FROM movies_by_title WHERE title = 'Emma (1996)';

-- Gegenprobe: dieselbe Frage auf der Basistabelle ratings ist nicht effizient möglich
-- (movie_id ist dort nur Clustering Column) und wird ohne ALLOW FILTERING abgelehnt:
SELECT user_id FROM ratings WHERE movie_id = 1;
