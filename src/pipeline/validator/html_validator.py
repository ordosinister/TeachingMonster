"""Quick HTML validator for generated slide HTML."""
from html.parser import HTMLParser
from typing import Dict


class _SlideHTMLValidator(HTMLParser):
    """Parse slide_html and collect structural evidence."""
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.root_tags: list[str] = []
        self.has_aspect_ratio = False
        self.has_text_zone = False
        self.has_image_zone = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        style = attrs_dict.get("style", "")
        if self.depth == 0:
            self.root_tags.append(tag)
        if "aspect-ratio" in style or "aspect-ratio:16" in style.replace(" ", ""):
            self.has_aspect_ratio = True
        if tag in ("ul", "ol"):
            self.has_text_zone = True
        if "border" in style and ("dashed" in style or "dotted" in style):
            self.has_image_zone = True
        self.depth += 1

    def handle_endtag(self, tag):
        self.depth = max(0, self.depth - 1)


def validate_slide_html(html: str) -> Dict[str, any]:
    """Validate a single slide_html string."""
    validator = _SlideHTMLValidator()
    validator.feed(html)
    passed = (
        len(validator.root_tags) == 1
        and validator.root_tags[0] == "div"
        and validator.has_aspect_ratio
    )
    return {
        "single_root": len(validator.root_tags) == 1 and validator.root_tags[0] == "div",
        "has_aspect_ratio": validator.has_aspect_ratio,
        "has_text_zone": validator.has_text_zone,
        "has_image_zone": validator.has_image_zone,
        "passed": passed,
    }


def validate_all(layouts: list) -> Dict[str, any]:
    """Validate all SlideLayout objects and return summary."""
    results = {}
    all_passed = True
    for idx, layout in enumerate(layouts, start=1):
        result = validate_slide_html(layout.slide_html)
        results[f"slide_{idx}"] = result
        if not result["passed"]:
            all_passed = False
    return {
        "all_passed": all_passed,
        "details": results,
    }