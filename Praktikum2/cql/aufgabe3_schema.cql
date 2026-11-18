-- Aufgabe 3 a) + c): Keyspace movielens und Basistabellen movies / ratings
-- Aufruf im Container:  cqlsh -f /home/cassandra/cql/aufgabe3_schema.cql

-- a) Keyspace anlegen und aktivieren (ein Knoten -> RF 1)
CREATE KEYSPACE IF NOT EXISTS movielens
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
USE movielens;

-- c) movies.csv: movieId,title,genres
--    Genres laut Hinweis als einfacher Text (z. B. 'Adventure|Animation|Children')
CREATE TABLE IF NOT EXISTS movies (
  movie_id int PRIMARY KEY,
  title    text,
  genres   text
);

-- c) ratings.csv: userId,movieId,rating,timestamp
--    Die CSV ist nach userId, dann movieId sortiert und (userId, movieId) ist eindeutig
--    -> natürlicher Primärschlüssel; alle Bewertungen eines Nutzys liegen in einer Partition.
--    timestamp = Sekunden seit 1970 (UTC) -> bigint (der CQL-Typ timestamp erwartet Millisekunden)
CREATE TABLE IF NOT EXISTS ratings (
  user_id  int,
  movie_id int,
  rating   float,
  rated_at bigint,
  PRIMARY KEY ((user_id), movie_id)
);
