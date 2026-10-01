"""p3 vocab card identity with meaning and direction

Vocabulary cards used to be identified by `lang:word` (`review_item.prompt_json.ref`), so two
meanings of one word collapsed into one card. The identity is now
`lang:direction:normalised word:normalised meaning` (`kernel/practice.vocab_ref`). This data step
rewrites the refs of existing cards from their stored question/answer; item ids and FSRS state are
untouched, so review history is preserved. No schema change.

Revision ID: 'ffb15bdebad6'
down_revision: Union[str, Sequence[str], None] = '5798bbccbea6'
Create Date: 2026-09-20 13:30:38.604878

"""

import json
import unicodedata
from collections.abc import Sequence
from urllib.parse import quote

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ffb15bdebad6"
down_revision: str | Sequence[str] | None = "5798bbccbea6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _norm(
    text: str,
) -> str:  # same rule as kernel/practice.norm_text (copied: migrations import nothing)
    return unicodedata.normalize("NFC", " ".join(str(text).split())).lower()


def upgrade() -> None:
    """Data step: legacy `lang:word` refs → `lang:forward:<word>:<meaning>`."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, prompt_json FROM review_item WHERE item_type = 'vocab'")
    ).all()
    for item_id, raw in rows:
        prompt = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        if prompt.get("direction") is not None:
            continue  # already in the new format
        ref = str(prompt.get("ref") or "")
        lang = str(prompt.get("lang") or ref.split(":", 1)[0]).lower()
        direction = str(prompt.get("direction") or "forward")
        word, meaning = str(prompt.get("q") or ""), str(prompt.get("a") or "")
        if direction == "reverse":
            word, meaning = meaning, word
        prompt.update(
            {
                "ref": f"{lang}:{direction}:{quote(_norm(word), safe='')}:{quote(_norm(meaning), safe='')}",
                "direction": direction,
                "lang": lang,
            }
        )
        conn.execute(
            sa.text("UPDATE review_item SET prompt_json = :p WHERE id = :id"),
            {"p": json.dumps(prompt, ensure_ascii=False), "id": item_id},
        )


def downgrade() -> None:
    """Back to `lang:word` (meanings collapse again; ids and schedules stay)."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, prompt_json FROM review_item WHERE item_type = 'vocab'")
    ).all()
    for item_id, raw in rows:
        prompt = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        lang = str(prompt.get("lang") or "").lower()
        word = str(prompt.get("q") or "")
        prompt["ref"] = f"{lang}:{_norm(word)}"
        conn.execute(
            sa.text("UPDATE review_item SET prompt_json = :p WHERE id = :id"),
            {"p": json.dumps(prompt, ensure_ascii=False), "id": item_id},
        )
