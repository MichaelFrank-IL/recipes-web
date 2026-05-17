#!/usr/bin/env python3
"""Import simple Markdown recipe files into recipes.js.

Expected Markdown shape:

Link: https://example.com/recipe

For the sauce:
* ingredient

Preparation (in 30 minutes)

- Step one
- Step two
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse


ACCENTS = ["green", "tomato", "yellow", "blue", "purple", "red"]
DEFAULT_OUTPUT = Path("recipes.js")

STEP_HEADINGS = (
    "preparation",
    "instructions",
    "method",
    "directions",
    "steps",
    "пригот",
    "готов",
)

TAG_KEYWORDS = [
    "air fryer",
    "beef",
    "bean",
    "bowl",
    "cabbage",
    "caesar",
    "cauliflower",
    "chicken",
    "dressing",
    "fish",
    "goulash",
    "kebab",
    "kofta",
    "meatball",
    "pasta",
    "pesto",
    "pork",
    "potato",
    "rice",
    "salad",
    "salmon",
    "sauce",
    "shawarma",
    "soup",
    "turkey",
    "vegetable",
    "zucchini",
]


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def strip_frontmatter(text: str) -> tuple[str, dict[str, object]]:
    if not text.startswith("---"):
        return text, {}

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not match:
        return text, {}

    frontmatter: dict[str, object] = {}
    current_key: str | None = None
    for raw_line in match.group(1).splitlines():
        line = raw_line.rstrip()
        key_value = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        list_value = re.match(r"^\s*-\s*(.+)$", line)

        if key_value:
            current_key = key_value.group(1).strip().lower()
            value = key_value.group(2).strip()
            if value:
                frontmatter[current_key] = clean_inline(value)
            else:
                frontmatter[current_key] = []
            continue

        if list_value and current_key:
            frontmatter.setdefault(current_key, [])
            if isinstance(frontmatter[current_key], list):
                frontmatter[current_key].append(clean_inline(list_value.group(1)))

    return text[match.end() :], frontmatter


def clean_inline(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^#+\s*", "", value)
    value = re.sub(r"^>\s*", "", value)
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"__(.*?)__", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", value)
    value = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_bullet(value: str) -> str:
    value = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", value)
    return clean_inline(value)


def title_from_path(path: Path, text: str, frontmatter: dict[str, object]) -> str:
    for key in ("title", "name"):
        value = frontmatter.get(key)
        if isinstance(value, str) and value:
            return value

    for line in text.splitlines():
        match = re.match(r"^\s*#\s+(.+)$", line)
        if match:
            return clean_inline(match.group(1))

    return path.stem.strip()


def slugify(title: str, used: set[str]) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    if not slug:
        slug = "recipe-" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]

    base = slug
    counter = 2
    while slug in used:
        slug = f"{base}-{counter}"
        counter += 1

    used.add(slug)
    return slug


def source_from_url(url: str | None, fallback: str) -> tuple[str, str | None]:
    if not url:
        return fallback, None

    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    return host or url, url


def parse_time_minutes(value: str | None) -> int | None:
    if not value:
        return None

    text = value.lower()
    total = 0

    hour_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:hours?|hrs?|hr|h|час(?:а|ов)?)", text)
    minute_match = re.search(r"(\d+)\s*(?:minutes?|mins?|min|m|мин(?:ут(?:а|ы)?)?)", text)

    if hour_match:
        total += round(float(hour_match.group(1).replace(",", ".")) * 60)
    if minute_match:
        total += int(minute_match.group(1))

    if total:
        return total

    return None


def parse_servings(value: str | None) -> str | None:
    if not value:
        return None

    patterns = [
        r"(?:serves|servings|yield|portions?)\s*:?\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)",
        r"([0-9]+(?:\s*[-–]\s*[0-9]+)?)\s*(?:servings|portions|people)",
        r"(?:порци[ийя]|порций)\s*:?\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(1).replace("–", "-").replace(" ", "")

    return None


def is_step_heading(line: str) -> bool:
    cleaned = clean_inline(line).lower()
    return any(heading in cleaned for heading in STEP_HEADINGS)


def extract_link(line: str) -> str | None:
    match = re.match(r"^\s*(?:link|source|url)\s*:\s*(\S+)", line, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def detect_category(title: str, ingredients: list[str], tags: list[str]) -> str:
    text = " ".join([title, *ingredients, *tags]).lower()

    if any(word in text for word in ("breakfast", "pancake")):
        return "Breakfast"
    if any(word in text for word in ("dessert", "cake", "crumble", "muffin", "pie")):
        return "Baking"
    if "soup" in text:
        return "Soup"
    if any(word in text for word in ("salad", "dressing")):
        return "Salad"
    if any(word in text for word in ("cauliflower", "zucchini", "bean", "pea")) and not any(
        word in text for word in ("chicken", "beef", "pork", "fish", "salmon", "turkey")
    ):
        return "Vegetarian"
    if any(word in text for word in ("sauce", "pesto", "harissa")):
        return "Sauce"

    return "Dinner"


def extract_tags(title: str, body: str, frontmatter: dict[str, object]) -> list[str]:
    found: list[str] = []

    raw_tags = frontmatter.get("tags")
    if isinstance(raw_tags, str):
        found.extend(re.split(r"[, ]+", raw_tags))
    elif isinstance(raw_tags, list):
        found.extend(str(tag) for tag in raw_tags)

    found.extend(tag.strip("#") for tag in re.findall(r"#([\w/-]+)", body, flags=re.UNICODE))

    haystack = f"{title}\n{body}".lower()
    for keyword in TAG_KEYWORDS:
        if keyword in haystack:
            found.append(keyword)

    cleaned: list[str] = []
    seen: set[str] = set()
    for tag in found:
        tag = clean_inline(tag).strip("# ").lower()
        if not tag or tag in {"recipe", "recipes"} or tag in seen:
            continue
        cleaned.append(tag)
        seen.add(tag)

    return cleaned[:5] or ["recipe"]


def parse_markdown_recipe(path: Path, accent: str, used_ids: set[str]) -> dict[str, object]:
    raw_text = read_text(path).replace("\r\n", "\n").replace("\r", "\n")
    text, frontmatter = strip_frontmatter(raw_text)
    title = title_from_path(path, text, frontmatter)

    source_url: str | None = None
    intro_lines: list[str] = []
    ingredients: list[str] = []
    steps: list[str] = []
    notes: list[str] = []
    time_minutes: int | None = parse_time_minutes(str(frontmatter.get("time", "")))
    servings = parse_servings(str(frontmatter.get("servings", "")))
    section = "intro"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        link = extract_link(line)
        if link:
            source_url = link
            continue

        if re.match(r"^\s*#\s+", line):
            continue

        heading_line = re.sub(r"^\s*#{1,6}\s*", "", line).strip()
        if is_step_heading(heading_line):
            section = "steps"
            time_minutes = time_minutes or parse_time_minutes(heading_line)
            servings = servings or parse_servings(heading_line)
            continue

        time_minutes = time_minutes or parse_time_minutes(heading_line)
        servings = servings or parse_servings(heading_line)

        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line):
            item = clean_bullet(line)
            if not item:
                continue
            if section == "steps":
                steps.append(item)
            else:
                ingredients.append(item)
                section = "ingredients"
            continue

        cleaned = clean_inline(heading_line)
        if not cleaned:
            continue

        if section != "steps" and cleaned.endswith(":"):
            ingredients.append(cleaned)
            section = "ingredients"
            continue

        if section == "steps":
            notes.append(cleaned)
        elif section == "intro":
            intro_lines.append(cleaned)

    source, source_url = source_from_url(source_url, path.stem)
    tags = extract_tags(title, text, frontmatter)
    category = str(frontmatter.get("category") or detect_category(title, ingredients, tags))

    if not ingredients:
        ingredients = ["Ingredients were not found in the Markdown file."]
    if not steps:
        steps = ["Preparation steps were not found in the Markdown file."]

    intro = " ".join(intro_lines).strip()
    if not intro:
        intro = f"Imported from {source}."

    recipe: dict[str, object] = {
        "id": slugify(title, used_ids),
        "title": title,
        "category": category,
        "timeMinutes": time_minutes or 0,
        "servings": servings or "Not listed",
        "source": source,
        "tags": tags,
        "accent": accent,
        "intro": intro,
        "ingredients": ingredients,
        "steps": steps,
        "notes": notes or ["Imported from Markdown."],
    }

    if source_url:
        recipe["sourceUrl"] = source_url

    return recipe


def recipe_sort_key(path: Path) -> str:
    return path.name.casefold()


def write_recipes_js(recipes: list[dict[str, object]], output_path: Path) -> None:
    payload = json.dumps(recipes, ensure_ascii=False, indent=2)
    output_path.write_text(f"window.familyRecipes = {payload};\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Markdown recipe files into recipes.js.")
    parser.add_argument("folder", help="Folder containing *.md recipe files.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JavaScript file. Defaults to recipes.js in the current folder.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include Markdown files in subfolders too.",
    )
    args = parser.parse_args()

    source_folder = Path(args.folder).expanduser().resolve()
    output_path = Path(args.output).resolve()

    if not source_folder.is_dir():
        raise SystemExit(f"Recipe folder does not exist: {source_folder}")

    pattern = "**/*.md" if args.recursive else "*.md"
    markdown_files = sorted(source_folder.glob(pattern), key=recipe_sort_key)
    if not markdown_files:
        raise SystemExit(f"No Markdown files found in: {source_folder}")

    used_ids: set[str] = set()
    recipes = [
        parse_markdown_recipe(path, ACCENTS[index % len(ACCENTS)], used_ids)
        for index, path in enumerate(markdown_files)
    ]

    write_recipes_js(recipes, output_path)
    print(f"Imported {len(recipes)} recipes into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
