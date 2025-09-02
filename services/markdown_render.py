import re
import bleach
from bleach.css_sanitizer import CSSSanitizer
import markdown2

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
    "p","span","div","pre","code","hr","br","em","strong",
    "blockquote","ul","ol","li","h1","h2","h3","h4","h5","h6",
    "table","thead","tbody","tr","th","td"
})
ALLOWED_ATTRS = {"*": ["class", "id", "style"]}
CSS_SAN = CSSSanitizer()
_ws = re.compile(r"\s+")

def render(md_text: str) -> tuple[str, str]:
    html = markdown2.markdown(md_text or "", extras=[
        "fenced-code-blocks","tables","strike","footnotes","wiki-tables"
    ])
    safe = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, css_sanitizer=CSS_SAN)
    plain = _ws.sub(" ", bleach.clean(safe, tags=[], strip=True)).strip()
    return safe, plain
