"""
Big Data – 1. Praktikum (HSBI, WS 2026/27): Redis + Yelp-Business-Daten
Autor: Zhaoze Yu · Matrikelnr. 50293014

Gemeinsame Funktionen für Aufgabe 2 (genutzt von load_data.py, autocomplete.py, answers.py
und den Tests).

Datenmodell in Redis
--------------------
Schlüssel                 Typ     Inhalt                                          Aufgabe
business:<business_id>    STRING  unveränderter JSON-String des Betriebs          2 a
<name in Kleinbuchstaben> SET     alle business_ids mit genau diesem Namen        2 b
autocomplete:names        ZSET    alle Namen (klein), Score 0 -> lexikografisch   2 c
                                  sortiert; Präfixsuche per ZRANGEBYLEX

Warum ein zusätzliches Sorted Set? Redis kann Schlüssel nur über KEYS/SCAN nach einem
Muster durchsuchen; das geht linear über alle ~340 000 Schlüssel, und KEYS blockiert
dabei den Server. Im Sorted Set ist eine Präfixsuche dagegen eine Bereichsabfrage in
O(log N + M) (N = Anzahl Namen, M = Anzahl Treffer).
"""
import json

import redis

BUSINESS_PREFIX = "business:"
AUTOCOMPLETE_KEY = "autocomplete:names"


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------
def connect(host="localhost", port=6379, db=0):
    """Verbindung zum Redis-Server im Docker-Container (Port 6379 wird nach außen gemappt).

    - decode_responses=True: Antworten kommen als str statt bytes zurück.
    - protocol=2 (RESP2): redis-py >= 8 nutzt sonst RESP3 und schickt beim Verbinden
      'HELLO 3'. Redis-Server < 6 kennen diesen Befehl nicht; RESP2 funktioniert mit
      allen Versionen (CI testet gegen Redis 5 und 8).
    - ping() wirft sofort eine Exception, wenn der Container nicht läuft.
    """
    r = redis.Redis(host=host, port=port, db=db, decode_responses=True, protocol=2)
    r.ping()
    return r


# ---------------------------------------------------------------------------
# Reine Hilfsfunktionen (ohne Redis, siehe tests/test_1_unit.py)
# ---------------------------------------------------------------------------
def iter_businesses(path):
    """Datei Zeile für Zeile lesen. Das Format ist JSON Lines: ein JSON-Objekt pro Zeile,
    die Datei ist KEIN JSON-Array, json.load(ganze Datei) würde scheitern.

    Liefert (rohe Zeile, geparstes dict). Die rohe Zeile wird später unverändert
    gespeichert (2 a). Leere Zeilen werden übersprungen. encoding="utf-8" ist unter
    Windows Pflicht (Standard dort: cp1252); viele Namen enthalten Sonderzeichen.
    Speicherbedarf konstant, weil nie die ganze 135-MB-Datei im Speicher liegt.
    """
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield line, json.loads(line)


def name_key(name):
    """Schlüssel für 2 b: der Name in Kleinbuchstaben ('' für fehlende Namen).

    So landen 'Starbucks' und 'STARBUCKS' im selben Set. str.lower() ist Unicode-fähig
    ('CAFÉ' -> 'café').
    """
    return (name or "").lower()


def prefix_range(prefix):
    """Grenzen für ZRANGEBYLEX: alle Elemente, die mit prefix beginnen (2 c).

    Alle Elemente im Sorted Set haben denselben Score 0, deshalb sortiert Redis sie
    byteweise. '[abc' heißt "ab einschließlich 'abc'". Als obere Grenze wird das Byte
    0xFF angehängt: 0xFF kommt in gültigem UTF-8 nie vor, also liegt 'abc' + 0xFF hinter
    jedem String, der mit 'abc' beginnt, auch mit Umlauten, CJK oder Emojis danach.
    (Das Zeichen '\\xff' als str würde dagegen als UTF-8 C3 BF kodiert und Namen wie
    'abcé…' verpassen.)
    Rückgabe None bei leerem Präfix (sonst würde die ganze Liste geliefert).
    """
    p = name_key(prefix)
    if not p:
        return None
    lo = ("[" + p).encode("utf-8")
    return lo, lo + b"\xff"


def summarize(business_id, raw_json):
    """2 d: aus dem gespeicherten JSON die angezeigten Felder herausziehen."""
    b = json.loads(raw_json)
    return {
        "business_id": business_id,
        "name": b.get("name"),
        "address": b.get("address"),
        "city": b.get("city"),
        "state": b.get("state"),
        "postal_code": b.get("postal_code"),
        "stars": b.get("stars"),
        "review_count": b.get("review_count"),
        "is_open": b.get("is_open"),
        "categories": b.get("categories"),
    }


def format_details(rows):
    """Textausgabe für die input()-Schleife und answers.py: eine Zeile pro Betrieb."""
    lines = []
    for i, d in enumerate(rows, 1):
        addr = ", ".join(x for x in [d["address"], d["postal_code"], d["city"], d["state"]] if x)
        status = "geöffnet" if d["is_open"] == 1 else "geschlossen"
        lines.append(f"  {i:>3}. {d['name']} | {addr or '(keine Adresse)'} | "
                     f"{d['stars']} Sterne ({d['review_count']} Reviews, {status}) | id={d['business_id']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Import (Aufgabe 2 a + b, dazu der Index für 2 c)
# ---------------------------------------------------------------------------
def load(r, path, batch_size=5000, flush=False, verbose=True):
    """Alle Einträge der Datei in Redis schreiben und die Anzahl zurückgeben.

    Pro Betrieb drei Befehle: SET (2 a), SADD (2 b), ZADD (Index 2 c).
    Eine Pipeline (transaction=False) schickt jeweils batch_size Betriebe in einem
    Netzwerk-Roundtrip. Ohne Pipeline wären es ~580 000 einzelne Roundtrips; so sind es
    ~40, und der Import dauert Sekunden statt Minuten.
    Mehrfaches Importieren ist harmlos: SET überschreibt, SADD/ZADD ignorieren Duplikate.
    """
    if flush:
        r.flushdb()
    pipe = r.pipeline(transaction=False)
    count = 0
    for raw, obj in iter_businesses(path):
        bid = obj["business_id"]
        name = name_key(obj.get("name"))
        pipe.set(BUSINESS_PREFIX + bid, raw)          # 2 a: JSON-String unter business:<id>
        if name:
            pipe.sadd(name, bid)                       # 2 b: Name -> Menge von business_ids
            pipe.zadd(AUTOCOMPLETE_KEY, {name: 0})     # 2 c: Name in den sortierten Index
        count += 1
        if count % batch_size == 0:
            pipe.execute()                             # Stapel abschicken
            if verbose:
                print(f"  {count:>7} Datensätze importiert ...", flush=True)
    pipe.execute()                                     # Rest abschicken
    if verbose:
        print(f"Fertig: {count} Datensätze importiert.")
    return count


# ---------------------------------------------------------------------------
# Abfragen (Aufgabe 2 c + d)
# ---------------------------------------------------------------------------
def autocomplete(r, prefix, limit=None):
    """2 c: alle Namen, die mit prefix beginnen (Groß-/Kleinschreibung egal), sortiert.

    Genau EIN Redis-Befehl (ZRANGEBYLEX), kein KEYS/SCAN über die Datenbank
    (nachgewiesen in tests/test_3_locality.py).
    """
    rng = prefix_range(prefix)
    if rng is None:
        return []
    args = {"start": 0, "num": limit} if limit else {}
    return r.zrangebylex(AUTOCOMPLETE_KEY, rng[0], rng[1], **args)


def ids_for_name(r, name):
    """2 b: Menge der business_ids zu einem Namen (ein SMEMBERS)."""
    return r.smembers(name_key(name))


def details(r, name):
    """2 d: Adressen und Sterne aller Betriebe mit diesem Namen.

    Zwei Schritte, zwei Befehle: SMEMBERS liefert die business_ids, ein einziges MGET holt
    alle zugehörigen JSON-Strings auf einmal (statt eines GET pro Betrieb).
    """
    ids = sorted(ids_for_name(r, name))
    raws = r.mget([BUSINESS_PREFIX + i for i in ids]) if ids else []
    return [summarize(bid, raw) for bid, raw in zip(ids, raws) if raw is not None]
