"""
Beantwortet Aufgabe 3 d), e), f) über den Python-Treiber (nach Import ausführen).

Aufruf:  python answers.py [user_id] [Filmtitel]
         Standard: Nutzy 42 und "Toy Story (1995)"
"""
import sys

import movielens_cassandra as mc


def section(title):
    print("\n" + "=" * 72 + f"\n{title}\n" + "=" * 72)


def main(user_id=42, title="Toy Story (1995)"):
    user_id = int(user_id)
    s = mc.connect()

    section("Zeilenzahlen (Kontrolle des Imports)")
    for t in ("movies", "ratings", "movies_by_user", "users_by_movie", "movies_by_title"):
        print(f"  {t:<16} {mc.count(s, f'SELECT COUNT(*) FROM {t}'):>7}")

    section("d) Die ersten 10 Zeilen von movies und ratings")
    for t in ("movies", "ratings"):
        print(f"-- {t}")
        for r in mc.first_rows(s, t, 10):
            print("  ", dict(r._asdict()))

    section(f"e) Die ersten 5 Filme (alphabetisch), die Nutzy {user_id} bewertet hat")
    total = mc.count(s, "SELECT COUNT(*) FROM movies_by_user WHERE user_id = %s", (user_id,))
    for i, r in enumerate(mc.movies_rated_by(s, user_id, limit=5), 1):
        print(f"  {i}. {r.title}  (movie_id {r.movie_id}, Bewertung {r.rating})")
    print(f"  Nutzy {user_id} hat insgesamt {total} Filme bewertet.")

    section(f'f) Welche Nutzys haben "{title}" bewertet?')
    ids = mc.movie_ids_for_title(s, title)
    print(f"  movie_id(s) zu diesem Titel: {ids}")
    for mid in ids:
        users = mc.users_who_rated(s, mid)
        print(f"  movie_id {mid}: {len(users)} Nutzys; die ersten 10: {[u.user_id for u in users[:10]]}")
        avg = sum(u.rating for u in users) / len(users) if users else 0
        print(f"  Durchschnittsbewertung: {avg:.2f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
