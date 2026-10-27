"""Reviewed diagnostic plans for reported PostgreSQL errors, without invented SQL."""

import re
from dataclasses import dataclass
from typing import Any

from app.integrations.supabase_reviewed import DIAGNOSTICS

IDENTITY = "SELECT current_database(), current_user, current_schema(), current_schemas(true);"
RELATIONS = """SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;"""
COLUMNS = """SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position;"""
POLICIES = """SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname = 'public';"""


@dataclass(frozen=True)
class Diagnostic:
    key: str
    patterns: tuple[str, ...]
    english: str
    german: str
    question_en: str
    question_de: str
    sql: str
    source: str


PLANS = (
    Diagnostic(
        "table_privilege",
        (r"permission denied for table\b", r"keine berechtigung f[üu]r tabelle\b"),
        "The reported table permission error concerns effective access to the table. A row policy "
        "does not grant table privileges. With the required privileges, an ordinary SELECT filtered "
        "to no matching rows normally returns an empty result, rather than that table permission error. "
        "This does not establish which grant is missing: check the failing operation and actual role. "
        "Column privileges and functions invoked by a query can require separate investigation.",
        "Der gemeldete Tabellenberechtigungsfehler betrifft den effektiven Zugriff auf die Tabelle. "
        "Eine Zeilenrichtlinie erteilt keine Tabellenberechtigungen. Sind die nötigen Berechtigungen "
        "vorhanden, liefert ein normales SELECT ohne passende Zeilen gewöhnlich ein leeres Ergebnis. "
        "Damit ist noch nicht festgestellt, welche Berechtigung fehlt: Prüfe die konkrete Operation "
        "und die tatsächliche Rolle. Spaltenberechtigungen und aufgerufene Funktionen sind gesondert zu prüfen.",
        "Which database role executes the failing operation?",
        "Welche Datenbankrolle führt die fehlgeschlagene Operation aus?",
        DIAGNOSTICS,
        "https://www.postgresql.org/docs/17/ddl-rowsecurity.html",
    ),
    Diagnostic(
        "schema_privilege",
        (r"permission denied for schema\b", r"keine berechtigung f[üu]r schema\b"),
        "The reported schema permission error points to schema access, a separate boundary from "
        "table privileges and row policies. Schema USAGE permits looking up objects; it does not "
        "itself grant SELECT on a table. Check the effective role and schema access before changing RLS.",
        "Der gemeldete Schemaberechtigungsfehler betrifft den Zugriff auf das Schema. Diese Grenze "
        "ist von Tabellenrechten und Zeilenrichtlinien getrennt. USAGE erlaubt die Objektsuche, "
        "erteilt aber selbst kein SELECT auf einer Tabelle. Prüfe Rolle und Schemazugriff vor einer RLS-Änderung.",
        "Under which role and schema does the failing request run?",
        "Mit welcher Rolle und welchem Schema läuft die fehlgeschlagene Anfrage?",
        "SELECT current_user, nspname, has_schema_privilege(current_user, oid, 'USAGE') AS schema_usage "
        "FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema';",
        "https://www.postgresql.org/docs/17/ddl-schemas.html",
    ),
    Diagnostic(
        "missing_relation",
        (r"relation\s+[^\n]{1,160}\s+does not exist", r"relation\s+[^\n]{1,160}\s+existiert nicht"),
        "The reported relation name could not be resolved in that query context. This is not proof "
        "that a migration failed. Check the database, schema/search path and exact identifier spelling, "
        "including quoted case. Catalog visibility is permission-dependent; an absent entry in an "
        "information-schema view alone does not prove the object does not exist.",
        "Der gemeldete Relationsname konnte im Abfragekontext nicht aufgelöst werden. Das beweist "
        "keine fehlgeschlagene Migration. Prüfe Datenbank, Schema/Suchpfad und die genaue Schreibweise "
        "einschließlich zitierter Groß-/Kleinschreibung. Die Sichtbarkeit im Informationsschema hängt "
        "von Berechtigungen ab; ein fehlender Eintrag beweist allein nicht, dass das Objekt fehlt.",
        "What is the exact schema-qualified name intended by the failing query?",
        "Wie lautet der beabsichtigte vollständig qualifizierte Relationsname?",
        IDENTITY + "\n" + RELATIONS,
        "https://www.postgresql.org/docs/17/ddl-schemas.html",
    ),
    Diagnostic(
        "missing_column",
        (r"column\s+[^\n]{1,160}\s+does not exist", r"spalte\s+[^\n]{1,160}\s+existiert nicht"),
        "The reported column reference could not be resolved in that query context. Check exact "
        "column spelling, quoted case, table aliases and the relation being queried. This does not "
        "prove the stored schema is wrong; the reference or alias scope may be wrong. The column "
        "inventory below only shows objects visible to the current user.",
        "Die gemeldete Spaltenreferenz konnte im Abfragekontext nicht aufgelöst werden. Prüfe "
        "Schreibweise, zitierte Groß-/Kleinschreibung, Tabellenaliase und die abgefragte Relation. "
        "Das beweist kein falsches Datenbankschema; auch Referenz oder Alias-Gültigkeit können falsch "
        "sein. Die Spaltenübersicht zeigt nur Objekte, die für die aktuelle Rolle sichtbar sind.",
        "What exact query and column reference produced the error?",
        "Welche genaue Abfrage und Spaltenreferenz haben den Fehler ausgelöst?",
        IDENTITY + "\n" + COLUMNS,
        "https://www.postgresql.org/docs/17/infoschema-columns.html",
    ),
    Diagnostic(
        "row_check",
        (r"new row violates row.level security policy", r"neue zeile verletzt.*zeilensicherheit"),
        "The reported new-row RLS error concerns a proposed row that fails an applicable row-security "
        "check. It differs from a SELECT returning no rows. Inspect the operation, effective role, "
        "JWT identity and applicable WITH CHECK expressions; where WITH CHECK is omitted, a USING "
        "expression can also supply that check. The policy text alone does not establish the request's "
        "identity or which expression failed. Do not disable RLS to make the error disappear.",
        "Der gemeldete RLS-Fehler für eine neue Zeile betrifft eine vorgeschlagene Zeile, die eine "
        "anwendbare Zeilensicherheitsprüfung nicht erfüllt. Das ist etwas anderes als ein SELECT ohne "
        "Ergebniszeilen. Prüfe Operation, effektive Rolle, JWT-Identität und WITH CHECK-Ausdrücke; "
        "ohne eigenes WITH CHECK kann auch USING diese Prüfung liefern. Der Richtlinientext beweist "
        "weder die Anfrageidentität noch den konkret gescheiterten Ausdruck. Deaktiviere RLS nicht als Abkürzung.",
        "Which operation and authenticated identity produced the rejected row?",
        "Welche Operation und authentifizierte Identität führten zur abgelehnten Zeile?",
        IDENTITY + "\n" + POLICIES,
        "https://www.postgresql.org/docs/17/ddl-rowsecurity.html",
    ),
)


INSUFFICIENT_PRIVILEGE = Diagnostic(
    "insufficient_privilege",
    (),
    "SQLSTATE 42501 names an insufficient-privilege condition; the code alone does not distinguish "
    "a missing table or schema privilege from a row-security write rejection or another protected "
    "operation. Use the complete error message and failing statement to locate the boundary. "
    "A policy existing does not prove that object privileges exist or that the request satisfies it.",
    "SQLSTATE 42501 bezeichnet eine unzureichende Berechtigung. Der Code allein unterscheidet nicht "
    "zwischen fehlenden Tabellen- oder Schemarechten, einer abgelehnten RLS-Schreibprüfung und "
    "anderen geschützten Operationen. Ordne die Grenze anhand der vollständigen Fehlermeldung "
    "und Anweisung ein. Eine vorhandene Richtlinie beweist weder Objektrechte noch ihre Erfüllung.",
    "What complete error message and statement accompanied SQLSTATE 42501?",
    "Welche vollständige Fehlermeldung und Anweisung gehören zu SQLSTATE 42501?",
    DIAGNOSTICS,
    "https://www.postgresql.org/docs/17/errcodes-appendix.html",
)


def mixed_plan(plans: list[Diagnostic]) -> Diagnostic:
    """Keep distinct reported boundaries separate; never synthesize one root cause."""
    english = "Several error boundaries were reported. Investigate them separately:\n\n"
    german = "Es wurden mehrere Fehlergrenzen gemeldet. Untersuche sie getrennt:\n\n"
    english += "\n\n".join(plan.english for plan in plans)
    german += "\n\n".join(plan.german for plan in plans)
    english += (
        "\n\nAssociate each message with its exact statement, database, role and time. "
        "Different messages do not establish a shared cause or prove an earlier fix succeeded."
    )
    german += (
        "\n\nOrdne jede Meldung ihrer genauen Anweisung, Datenbank, Rolle und Zeit zu. "
        "Verschiedene Meldungen beweisen weder eine gemeinsame Ursache noch eine erfolgreiche frühere Reparatur."
    )
    queries = list(
        dict.fromkeys(
            query.strip() for plan in plans for query in plan.sql.split(";") if query.strip()
        )
    )
    return Diagnostic(
        "mixed_" + "_".join(plan.key for plan in plans),
        (),
        english,
        german,
        "Which exact statement and role produced each error, and in what order?",
        "Welche genaue Anweisung und Rolle verursachten die einzelnen Meldungen, und in welcher Reihenfolge?",
        ";\n".join(queries) + ";",
        "\n".join(
            dict.fromkeys(
                ["https://www.postgresql.org/docs/17/errcodes-appendix.html"]
                + [plan.source for plan in plans]
            )
        ),
    )


def select_plan(text: str, state: Any) -> Diagnostic | None:
    if state.mode != "incident" or state.active_lab is not None or len(text) > 8000:
        return None
    # A resolved/negated report is not a new failure. Preserve distinct mixed error boundaries.
    if re.search(r"no longer|not getting|not seeing|kein.*mehr|nicht mehr", text, re.I):
        return None
    found = [plan for plan in PLANS if any(re.search(p, text, re.I) for p in plan.patterns)]
    codes = {code.upper() for code in re.findall(r"\b(?:42P01|42703|42501)\b", text, re.I)}
    if "42P01" in codes and PLANS[2] not in found:
        found.append(PLANS[2])
    if "42703" in codes and PLANS[3] not in found:
        found.append(PLANS[3])
    if "42501" in codes and not any(
        plan.key in {"table_privilege", "schema_privilege", "row_check"} for plan in found
    ):
        found.append(INSUFFICIENT_PRIVILEGE)
    if len(found) > 1:
        return mixed_plan(found)
    return found[0] if found else None


def incident_turn(text: str, state: Any, plan: Diagnostic) -> Any:
    from app.integrations.supabase_project import project_module

    project = project_module()
    from backend.tutor.schemas import Incident

    german = state.language == "de"
    explanation = plan.german if german else plan.english
    question = plan.question_de if german else plan.question_en
    role_reported = re.search(
        r"\b(?:as|role|rolle|als)\s*[:=]?\s*[\"']?(?:authenticated|anon|postgres|service_role)\b",
        text,
        re.I,
    )
    if role_reported and plan.key in {"table_privilege", "schema_privilege"}:
        question = (
            "Welche genaue Abfrage und vollständige Fehlermeldung gehören zu dieser Rolle?"
            if german
            else "What exact query and complete error were observed under that role?"
        )
    note = (
        "Diese unveränderten Diagnosebeispiele wurden nicht gegen deine Datenbank ausgeführt. "
        "Öffentliche Schemas werden als public geführt; passe den Schemakontext bei Bedarf an. "
        "Ein Administratortest ersetzt nicht den Test mit der tatsächlichen Anwendungsidentität."
        if german
        else "These fixed diagnostic examples have not been run against your database. Queries naming "
        "public inspect that schema; adapt the schema context when needed. An administrator test "
        "does not substitute for the actual application identity."
    )
    body = explanation + "\n\n" + note + "\n\n```sql\n" + plan.sql + "\n```\n\n" + question
    body += "\n\n" + plan.source
    # No guessed root cause, evidence, remediation, ledger score or replacement of learner fields.
    turn = project.TutorTurn(
        incident=Incident(),
        mode="incident",
        language=state.language,
        persona_on=state.persona_on,
        speech=(
            "Mehrere Fehlergrenzen wurden gemeldet. Ordne jede Meldung ihrer Anweisung und Rolle zu."
            if german
            else "Several error boundaries were reported. Match each message to its statement and role."
        )
        if plan.key.startswith("mixed_")
        else explanation.split(". ")[0] + ".",
        text=body,
        next_question=question,
    )
    return turn
