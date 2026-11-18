-- Aufgabe 3 c): Import mit COPY (cqlsh-Befehl, liest die CSV-Dateien im Container)
USE movielens;

COPY movies (movie_id, title, genres)
  FROM '/home/cassandra/ml-latest-small/movies.csv'
  WITH HEADER = true AND ESCAPE = '"';

COPY ratings (user_id, movie_id, rating, rated_at)
  FROM '/home/cassandra/ml-latest-small/ratings.csv'
  WITH HEADER = true;
