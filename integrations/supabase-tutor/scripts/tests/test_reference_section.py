"""Section-local evidence, independently identified by route, family and visible heading."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_section import SectionReference, section_markdown

BASE = "https://supabase.com/docs/reference/cli/"
CLI = """<nav><section id="supabase-status"><h2>False navigation</h2></section></nav>
<section id="introduction"><h1>Supabase CLI</h1><p>Intro.</p></section>
<section id="supabase-status"><h2>supabase status</h2><p>Show local services.</p>
<section><h3>Example</h3>
<pre><code><div><div aria-hidden="true">1</div><div class="code-line-content">first &lt; 2</div></div>
<div><div aria-hidden="true">2</div><div class="code-line-content"></div></div>
<div><div aria-hidden="true">3</div><div class="code-line-content">    last</div></div></code></pre>
</section><section id="nested-command"><h2>Nested command</h2>Separate example.</section>
</section><section id="next-command"><h2>Next command</h2>Adjacent example.</section>"""


def test_only_the_requested_command_and_exact_multiline_code():
    page = SectionReference(CLI)
    doc = page.markdown(BASE + "supabase-status")
    assert doc.startswith("# supabase status\n")
    assert "### Example" in doc and "first < 2\n\n    last\n" in doc
    assert all(word not in doc for word in ["Adjacent", "Separate", "False navigation", "Intro."])
    assert "Separate example." in page.markdown(BASE + "nested-command")


@pytest.mark.parametrize(
    "html,url",
    [
        (CLI.replace("<h2>supabase status", "<h2>other"), BASE + "supabase-status"),
        (CLI.replace("Supabase CLI", "Self-Hosting Auth"), BASE + "introduction"),
        (CLI + '<section id="supabase-status"><h2>supabase status</h2></section>', BASE + "supabase-status"),
        (CLI.split("</pre>")[0], BASE + "supabase-status"),
        (CLI, BASE + "absent"),
        (CLI, BASE + "supabase-status#next-command"),
    ],
)
def test_refuses_ambiguous_or_missing_evidence(html, url):
    with pytest.raises(ValueError):
        section_markdown(html, url)
