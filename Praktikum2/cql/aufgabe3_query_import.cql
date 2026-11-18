-- Aufgabe 3 e) + f): Import der denormalisierten CSV-Dateien (erzeugt von denormalize.py)
USE movielens;

COPY movies_by_user (user_id, title, movie_id, rating, rated_at)
  FROM '/home/cassandra/denormalized/movies_by_user.csv'
  WITH HEADER = true AND ESCAPE = '"';

COPY users_by_movie (movie_id, user_id, title, rating, rated_at)
  FROM '/home/cassandra/denormalized/users_by_movie.csv'
  WITH HEADER = true AND ESCAPE = '"';

COPY movies_by_title (title, movie_id, genres)
  FROM '/home/cassandra/denormalized/movies_by_title.csv'
  WITH HEADER = true AND ESCAPE = '"';
