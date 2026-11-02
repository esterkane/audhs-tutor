"""Conservative closed-language frame for saved retry facts, never general tutoring."""

import re

from app.orchestrator.saved_evidence_selection import NUMBERS

# Unknown words retain the ordinary tutor path. This vocabulary grants no tool permissions.
WORDS = frozenset(
    """
a an the our ours my we i me your us this that these those it its their in on at of for from with
and or to as by between against versus vs then each both all any
compare compares comparison comparisons contrast contrasts difference differences show shows give
report reports summarize check correct using use please pls
full fully retry retries retrying update only strategy strategies decision decisions decide decided
count counts active minimum first second third fourth last latest earliest earlier later local
experiment experiments trial trials case cases worker workers row rows recorded saved stored
observation observations read reads new fresh freshly initial initially original reused reuse reuses
reusing did does do was were is are has had have what which many followed follow see saw outcome
outcomes result results afterwards after before now end final condition conditions test tests commit
commits committed succeeded successful success failure failed same different unchanged changed above
below equal greater less than not no own deactivation deactivate deactivated affected performed
explanation explanations claimed claim claims true false originally again
supabase postgresql postgres
unser unsere unserem unseren unserer unseres
vergleiche vergleichen vergleich vergleicht unterschied unterschiede zeige zeigen gib bericht
berichte nutze nutzen benutze bitte
vollständige vollständigen vollständiger vollständig vollständiges retry retries update only
entscheidung entscheidungen anzahl anzahlwerte aktive aktiven aktiver aktiv minimum erste ersten
erster erstes zweite zweiten zweiter dritter dritte dritten vierte vierten letzter letzte letzten
früheren frühere späteren spätere lokalen lokale lokaler lokal versuch versuche versuchen versuchs
fall fälle falls kräfte kräften zeilen gespeicherte gespeicherten gespeichert beobachtung
beobachtungen gelesene gelesenen gelesen lesen las neu neue neuen neuer frische frisch ursprüngliche
ursprünglichen ursprünglicher übernommen übernommene übernahm wiederverwendet wiederverwenden
jeweils folgte folgen was welche welcher welchen welches wurde wurden war waren ist sind hat haben
bei dem den der die das im in mit und oder von zu zum zur aus nach vor am ende ergebnis ergebnisse
bedingung bedingungen erfolgreich erfolgreiches erfolgte erfolgreichern commit commits deaktivieren
deaktiviert betroffene betroffen gezählt gezählte zählte eigene eigenen nicht kein keine nur
gleichen gleich anders ursprünglichen nochmals aufgezeichnet aufgezeichnete aufgezeichneten
""".split()
) | frozenset(NUMBERS)
FORMAT_WORDS = frozenset(
    """
no not without do don t please sql commands code query queries quiz quizzes or and nor claims claim
of inspecting inspect inspection a the live current project about new run rerun experiment
statements execute neues ausführen
keine kein keinen ohne bitte sql befehle code abfragen abfrage quiz und oder keine behauptung
behauptungen einer eines aktuellen aktuellen projektprüfung projektdatenbank neuen versuch
""".split()
)


REASON_WORDS = frozenset(
    "why because even though despite reason reasons explain explains explained distinction "
    "deactivating complete its warum wieso obwohl entschied entscheiden erklärt erkläre "
    "erläutere deshalb trotzdem erfolgreichen vollständigen unterscheidung unterschied "
    "verpflichtet bedeutet bedeutete zeile sein seine seinen entschieden selben".split()
)


def supported_fact_frame(question: str, *, reasoning: bool = False) -> bool:
    if len(question) > 4000:
        return False
    if reasoning and not (
        re.search(r"\b(?:why|warum|wieso)\b", question, re.I)
        and re.search(r"\b(?:full|complete|vollständige[rns]?)\s+retry\b", question, re.I)
        and re.search(r"\b(?:update[- ]only|nur\s+update)\b", question, re.I)
        and re.search(r"\bcommit(?:s|ted)?\b", question, re.I)
        and re.search(r"decid|decision|entschied|entscheidung|deactivat|deaktivier", question, re.I)
    ):
        return False
    if re.search(
        r"\b(?:do not|don't|nicht)\s+(?:compare|show|vergleiche|zeige)|\bwhat\s+if\b|\bhow\s+(?!many\b)",
        question,
        re.I,
    ):
        return False
    if re.search(r"\b(?:only|just)\s+show\b|\bnur\s+(?:die|den|das)\b", question, re.I):
        return False
    if re.search(r"\b(?:which|what)\s+(?:commit|transaction|actor)\b", question, re.I):
        return False
    if re.search(
        r"\b(?:no|keine[nr]?)\s+(?:retry[-\s]+)?(?:comparison|vergleich)\b", question, re.I
    ):
        return False
    if re.search(
        r"\band\s+(?:commit|update|retry|deactivate)\s+(?:the|this|that|it|them|my|our)\b",
        question,
        re.I,
    ):
        return False
    if not (reasoning and re.search(r"\b(?:why|warum|wieso)\b", question, re.I)) and not re.search(
        r"\b(?:compare|contrast|show|give|report|summarize|check|correct|what|which|vergleiche|vergleich|zeige|gib|was|welche[rns]?)\b",
        question,
        re.I,
    ):
        return False
    question = re.sub(r"\bexperiment[0-9]+-[0-9a-f]{12}\b", "experiment", question)
    tokens: list[str] = []
    for clause in re.split(r"[.!?]+", question):
        words = re.findall(r"[^\W\d_]+|[0-9]+", clause.casefold())
        if not words:
            continue
        negated = re.match(
            r"\s*(?:please\s+)?(?:no\b|without\b|do not\b|don't\b|keine?\b|ohne\b)", clause, re.I
        )
        if negated:
            constraint = re.sub(r"\binvented\s+observations\b", "", clause, flags=re.I)
            constraint_words = re.findall(r"[^\W\d_]+|[0-9]+", constraint.casefold())
            if set(constraint_words) <= FORMAT_WORDS:
                continue
            return False
        tokens.extend(word for word in words if not word.isdigit())
    if not tokens or any(
        word not in (WORDS | REASON_WORDS if reasoning else WORDS) for word in tokens
    ):
        return False
    return bool(
        set(tokens)
        & {
            "count",
            "counts",
            "read",
            "decision",
            "decisions",
            "result",
            "results",
            "observations",
            "retry",
            "retries",
            "anzahl",
            "entscheidung",
            "entscheidungen",
            "ergebnisse",
            "beobachtungen",
        }
    )
