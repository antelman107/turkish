#!/usr/bin/env python3
"""
Generate featured images for Turkish grammar articles using DALL-E 3.

Usage:
    OPENAI_API_KEY=sk-... python3 scripts/generate_images.py

The script will:
  1. Generate each image via DALL-E 3
  2. Convert PNG → WebP using cwebp
  3. Add `featured_image = 'slug.webp'` to each article's frontmatter

Requirements:
    pip install openai
    brew install webp  (for cwebp)
"""

import os
import re
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Run: pip install openai")
    sys.exit(1)

STATIC_DIR = Path(__file__).parent.parent / "themes/my/static"
CONTENT_DIR = Path(__file__).parent.parent / "content"

# Style prefix used for every prompt
STYLE = (
    "Cute cartoon guinea pig character named Anatoly in a detailed illustrated scene. "
    "Kawaii style with thick outlines, vibrant colors, anime-inspired digital art. "
    "High quality, educational illustration. No text in the image."
)

# article_file → (image_slug, scene_description)
ARTICLES: dict[str, tuple[str, str]] = {
    # ── ВРЕМЕНА ─────────────────────────────────────────────────────────────
    "времена/прошедшее-субъективное.ru.md": (
        "past_mish",
        f"{STYLE} The guinea pig looks shocked and wide-eyed, holding a phone, "
        "overhearing surprising gossip from behind a wall. Rumor bubbles float around. "
        "Cozy Turkish café background.",
    ),
    "времена/сложные-времена.ru.md": (
        "complex_tenses",
        f"{STYLE} The guinea pig is juggling three glowing clocks labeled PAST, PRESENT, FUTURE "
        "simultaneously, looking focused. Colourful clockwork gears in the background.",
    ),
    "времена/широкое-в-прошлом.ru.md": (
        "aorist_past",
        f"{STYLE} The guinea pig sits in a cosy old armchair reading a sepia newspaper, "
        "surrounded by vintage Turkish decor. Warm amber lighting, nostalgic atmosphere.",
    ),
    # ── ДОПОЛНИТЕЛЬНАЯ ТЕОРИЯ ────────────────────────────────────────────────
    "дополнительная теория/ana-kadar-incaya-kadar.ru.md": (
        "ana_kadar",
        f"{STYLE} The guinea pig runs eagerly on a path toward a giant finish-line banner "
        "that reads 'ANA KADAR'. Bright outdoor Turkish landscape in the background.",
    ),
    "дополнительная теория/açağı-kadar.ru.md": (
        "acagi_kadar",
        f"{STYLE} The guinea pig stands on tiptoes next to a measuring ruler, estimating "
        "approximately. Question marks and approximate symbols float around. Playful math classroom.",
    ),
    "дополнительная теория/boyunca.ru.md": (
        "boyunca",
        f"{STYLE} The guinea pig walks along the full length of a very long Bosphorus bridge "
        "from start to finish, tiny figure against a beautiful Istanbul skyline.",
    ),
    "дополнительная теория/dik-gibi.ru.md": (
        "dik_gibi",
        f"{STYLE} The guinea pig looks into a mirror and sees a majestic lion reflection. "
        'Speech bubble says "gibi". Colourful cartoon style.',
    ),
    "дополнительная теория/dik-kadar.ru.md": (
        "dik_kadar",
        f"{STYLE} The guinea pig stands on a scale perfectly balanced against a stack of "
        "carrots of equal weight. Balance scales illustration, bright colours.",
    ),
    "дополнительная теория/dik-takdirde-me-durumunda.ru.md": (
        "dik_takdirde",
        f"{STYLE} The guinea pig stands at a crossroads holding a signpost. One sign reads "
        "'takdirde', the other 'durumunda'. Dramatic if-then decision scene.",
    ),
    "дополнительная теория/dik-zaman-inca-ir-maz.ru.md": (
        "dik_zaman",
        f"{STYLE} The guinea pig is frozen mid-jump on a timeline showing three glowing "
        "moments: -dığında, -ınca, -ır maz. Dynamic action scene with a clock theme.",
    ),
    "дополнительная теория/dikca.ru.md": (
        "dikca",
        f"{STYLE} The guinea pig grows taller and taller as a pile of carrots next to it "
        "grows larger. The more carrots, the bigger the smile. Gradient growth chart.",
    ),
    "дополнительная теория/kadarıyla-gore.ru.md": (
        "kadarıyla_gore",
        f"{STYLE} The guinea pig holds a magnifying glass looking at a document, then "
        "points to a verdict sign that says 'göre'. Detective-style illustration.",
    ),
    "дополнительная теория/ki.ru.md": (
        "ki",
        f"{STYLE} The guinea pig connects two floating speech bubbles with a glowing bridge "
        "labeled 'ki'. Colourful connector-style educational illustration.",
    ),
    "дополнительная теория/maktansa.ru.md": (
        "maktansa",
        f"{STYLE} The guinea pig stands between two doors — one labelled SLEEP with a moon, "
        "one labelled WALK with sun — and firmly chooses the walk door. Decision scene.",
    ),
    "дополнительная теория/masina.ru.md": (
        "masina",
        f"{STYLE} The guinea pig squeezes itself into a tiny toy car, driving happily. "
        "The car is comically small. Bright cartoon road scene.",
    ),
    "дополнительная теория/meksizin.ru.md": (
        "meksizin",
        f"{STYLE} The guinea pig runs through a door confidently WITHOUT an umbrella, "
        "even though rain falls outside. 'meksizin' floats as a banner.",
    ),
    "дополнительная теория/mi-для-усиления-смысла.ru.md": (
        "mi_emphasis",
        f"{STYLE} The guinea pig stands on a stage with a spotlight, raising both paws "
        "dramatically with a giant exclamation mark. Emphatic pose, vivid colours.",
    ),
    "дополнительная теория/misligim-var-yok.ru.md": (
        "misligim",
        f"{STYLE} The guinea pig sneezes and covers its mouth with a paw, looking embarrassed. "
        "Speech bubble: 'Miş!'. Cute sick-day illustration.",
    ),
    "дополнительная теория/mış-gibi-yapmak.ru.md": (
        "mish_gibi",
        f"{STYLE} The guinea pig wears a fake mustache and glasses as a disguise, pretending "
        "to be asleep while peeking one eye open. Comedy acting scene.",
    ),
    "дополнительная теория/sürece.ru.md": (
        "surece",
        f"{STYLE} The guinea pig stands guard protectively in front of a glowing hourglass. "
        "Scene: 'as long as time flows, I stay'. Warm golden lighting.",
    ),
    "дополнительная теория/voprositelnye-mi.ru.md": (
        "mi_question",
        f"{STYLE} The guinea pig tilts its head with a giant question mark hovering above "
        "and 'mı / mi / mu / mü' written on floating bubbles. Curious expression.",
    ),
    "дополнительная теория/üzere.ru.md": (
        "uzere",
        f"{STYLE} The guinea pig is perched on the very edge of a diving board over a pool, "
        "about to jump but not yet jumping. Suspense, almost-action pose.",
    ),
    "дополнительная теория/временные-отрезки.ru.md": (
        "time_intervals",
        f"{STYLE} The guinea pig stands on a giant daily schedule wheel showing sabah, "
        "öğlen, akşam, gece sections with sun/moon icons. Cosy clock illustration.",
    ),
    "дополнительная теория/деепричастие-a-e.ru.md": (
        "dep_ae",
        f"{STYLE} The guinea pig runs in a loop — koşa koşa — leaving repeated footprint "
        "stamps. Dynamic motion trail, energetic cartoon.",
    ),
    "дополнительная теория/деепричастие-arak-erek.ru.md": (
        "dep_arak",
        f"{STYLE} The guinea pig reads a book while eating a carrot simultaneously, multitasking. "
        "Two actions at once. Colorful split-panel illustration.",
    ),
    "дополнительная теория/деепричастие-inca.ru.md": (
        "dep_inca",
        f"{STYLE} The guinea pig opens a door and immediately a confetti explosion happens. "
        'Moment of "as soon as" — instant reaction. Festive bright scene.',
    ),
    "дополнительная теория/деепричастие-ip-madan-meden.ru.md": (
        "dep_ip",
        f"{STYLE} The guinea pig chops a carrot and then immediately eats it in a chain of "
        "two linked action bubbles. Cooking cartoon, cute kitchen scene.",
    ),
    "дополнительная теория/деепричастия-kadar.ru.md": (
        "dep_kadar",
        f"{STYLE} The guinea pig stretches its arms as wide as possible showing 'as much as "
        "I can'. Measuring tape around it. Exaggerated cute expression.",
    ),
    "дополнительная теория/желательное-наклонение.ru.md": (
        "optative",
        f"{STYLE} The guinea pig blows out a birthday candle making a wish, eyes closed "
        "with a hopeful smile. Colourful birthday party scene.",
    ),
    "дополнительная теория/косвенная-речь.ru.md": (
        "reported_speech",
        f"{STYLE} The guinea pig whispers into another animal's ear which then tells a third "
        "animal. Chain of speech bubbles, rumour-passing scene. Turkish bazaar background.",
    ),
    "дополнительная теория/несмотря-на.ru.md": (
        "despite",
        f"{STYLE} The guinea pig walks cheerfully through a storm with no umbrella, "
        "completely unaffected. 'Despite the rain' energy. Determined cute expression.",
    ),
    "дополнительная теория/повелительное-наклонение.ru.md": (
        "imperative",
        f"{STYLE} The guinea pig stands on a podium like a general, pointing a tiny paw "
        "giving orders. Other small animals salute. Command and leadership scene.",
    ),
    "дополнительная теория/удвоение.ru.md": (
        "doubling",
        f"{STYLE} The guinea pig stands next to its mirror clone, both doing the same action. "
        "Yavaş yavaş energy — slow motion repeated action. Identical twins scene.",
    ),
    "дополнительная теория/форма-быстроты-iver.ru.md": (
        "iver",
        f"{STYLE} The guinea pig zooms at lightning speed with a speed blur, completing an "
        "action instantly. Superhero speed lines, quick action cartoon.",
    ),
    "дополнительная теория/числительные.ru.md": (
        "numbers",
        f"{STYLE} The guinea pig is a cheerful math teacher pointing to a colourful blackboard "
        "showing bir, iki, üç, dört in Turkish. Cute classroom scene.",
    ),
    # ── НЕОБХОДИМАЯ ТЕОРИЯ ───────────────────────────────────────────────────
    "необходимая теория/bilir-форма-возможности.ru.md": (
        "bilir",
        f"{STYLE} The guinea pig flexes confidently, cape flowing. 'Yapabilirim!' (I can do it!) "
        "in a speech bubble. Superhero ability scene, vibrant colours.",
    ),
    "необходимая теория/dan-beri.ru.md": (
        "dan_beri",
        f"{STYLE} The guinea pig stands at a timeline arrow pointing from a baby guinea pig "
        "photo in the past to the present-day self. 'Since birth' nostalgic illustration.",
    ),
    "необходимая теория/değil-с-глаголами.ru.md": (
        "degil",
        f"{STYLE} The guinea pig holds a big red NO sign, shaking its head firmly. "
        "Negation scene with X marks. Clear, decisive expression.",
    ),
    "необходимая теория/digindan-beri-ali-eli.ru.md": (
        "digindan_beri",
        f"{STYLE} The guinea pig looks back at a dotted line trail stretching behind it "
        "into the past horizon. 'Ever since...' reflective nostalgic scene.",
    ),
    "необходимая теория/dir.ru.md": (
        "dir",
        f"{STYLE} The guinea pig stands under a bright spotlight on a stage making a formal "
        "announcement. Official proclamation pose. Turkish official decor.",
    ),
    "необходимая теория/gerek-lazim.ru.md": (
        "gerek_lazim",
        f"{STYLE} The guinea pig holds a checklist of necessities — carrot, water, wheel — "
        "pointing at each item seriously. 'Must have' shopping list scene.",
    ),
    "необходимая теория/ken-когда.ru.md": (
        "ken",
        f"{STYLE} The guinea pig reads a book and sips tea simultaneously. Two actions in "
        "parallel. Split-screen cosy illustration, warm tea-time colours.",
    ),
    "необходимая теория/mak-icin.ru.md": (
        "mak_icin",
        f"{STYLE} The guinea pig runs with determination toward a goal star labelled 'İÇİN'. "
        "Purpose and motivation scene. Bright energetic illustration.",
    ),
    "необходимая теория/mali-meli.ru.md": (
        "mali_meli",
        f"{STYLE} The guinea pig stands at a dentist chair looking reluctant, knowing it "
        "must go in. 'I must (but I don't want to)' expression. Humorous obligation scene.",
    ),
    "необходимая теория/возвратное-местоимение-kendi.ru.md": (
        "kendi",
        f"{STYLE} The guinea pig looks into a mirror and points at its reflection saying 'BEN KENDİM'. "
        "Self-reflection, identity scene. Philosophical cute moment.",
    ),
    "необходимая теория/гармония-гласных.ru.md": (
        "vowel_harmony",
        f"{STYLE} The guinea pig conducts an orchestra of eight colourful floating vowels "
        "(a, e, ı, i, o, ö, u, ü) that harmonise together. Music and language fusion.",
    ),
    "необходимая теория/деепричастие-dik.ru.md": (
        "dep_dik",
        f"{STYLE} The guinea pig holds up a completed stamp or certificate of a finished action. "
        "Official past-action document. Achievement unlock scene.",
    ),
    "необходимая теория/если-желательный-тип.ru.md": (
        "if_optative",
        f"{STYLE} The guinea pig gazes at stars with a telescope, wishing 'if only...'. "
        "Night sky, dreamy optative wish scene. Soft glowing illustration.",
    ),
    "необходимая теория/если-нереальный-тип.ru.md": (
        "if_unreal",
        f"{STYLE} The guinea pig daydreams in a thought bubble of an imaginary alternate life "
        "— flying with wings — that never happened. Counterfactual fantasy.",
    ),
    "необходимая теория/если-реальный-тип.ru.md": (
        "if_real",
        f"{STYLE} The guinea pig stands under rain clouds holding a bright umbrella, "
        "looking confident. 'If it rains, I use an umbrella.' Real conditional scene.",
    ),
    "необходимая теория/личные-окончания.ru.md": (
        "personal_endings",
        f"{STYLE} The guinea pig stands with six small animal friends, each wearing a name "
        "badge: -im, -sin, -, -iz, -siniz, -ler. Grammar class group photo.",
    ),
    "необходимая теория/местоимения.ru.md": (
        "pronouns",
        f"{STYLE} The guinea pig stands in the centre surrounded by floating pronoun badges: "
        "ben, sen, o, biz, siz, onlar. Portrait gallery of pronouns.",
    ),
    "необходимая теория/отглагольные.ru.md": (
        "verbal_nouns",
        f"{STYLE} The guinea pig transforms a running action into a trophy labelled 'koşmak'. "
        "Verb-to-noun transformation magic. Colourful metamorphosis scene.",
    ),
    "необходимая теория/падежи-существительных.ru.md": (
        "cases",
        f"{STYLE} The guinea pig stands at the centre of arrows pointing in six directions: "
        "in, to, from, at, with, without. Cases compass-rose illustration.",
    ),
    "необходимая теория/побудительный-залог.ru.md": (
        "causative",
        f"{STYLE} The guinea pig boss sits in a big chair pointing at a smaller animal that "
        "does the work. 'Making someone do something' management scene.",
    ),
    "необходимая теория/причастие-an-en.ru.md": (
        "participle_an",
        f"{STYLE} The guinea pig wears a 'RUNNING' badge as a noun/adjective. Active particle "
        "floating around. Grammar superhero costume scene.",
    ),
    "необходимая теория/причастие-dik.ru.md": (
        "participle_dik",
        f"{STYLE} The guinea pig holds a framed photo of a past moment labelled '-dık'. "
        "Relative clause scrapbook. Nostalgic warm scene.",
    ),
    "необходимая теория/причина.ru.md": (
        "reason",
        f"{STYLE} The guinea pig points dramatically at a sign showing 'BECAUSE' with an "
        "arrow connecting cause to effect. Detective cause-and-effect scene.",
    ),
    "необходимая теория/развернутое-дополнение.ru.md": (
        "extended_object",
        f"{STYLE} The guinea pig unfolds a very long scroll with a complex nested sentence "
        "written on it. Extended complement length, humorous expression.",
    ),
    "необходимая теория/страдательный-залог.ru.md": (
        "passive",
        f"{STYLE} The guinea pig sits relaxed while a robot arm feeds it a carrot automatically. "
        "Passive — action is done TO the guinea pig. Lazy satisfied expression.",
    ),
    "необходимая теория/условные-наклонения.ru.md": (
        "conditionals_overview",
        f"{STYLE} The guinea pig stands at a dramatic crossroads with signposts showing "
        "REAL, UNREAL, WISH paths. Conditional fork-in-the-road scene.",
    ),
}


def download_image(url: str, dest: Path) -> None:
    urllib.request.urlretrieve(url, dest)


def to_webp(png_path: Path, webp_path: Path) -> None:
    result = subprocess.run(
        ["cwebp", "-q", "85", str(png_path), "-o", str(webp_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cwebp failed: {result.stderr.decode()}")


def add_featured_image(md_path: Path, image_slug: str) -> None:
    text = md_path.read_text(encoding="utf-8")
    if "featured_image" in text:
        return  # already set
    # Insert before closing +++
    text = re.sub(
        r"(\+\+\+\s*\n)",
        lambda m: f"featured_image = '{image_slug}.webp'\n{m.group(1)}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    md_path.write_text(text, encoding="utf-8")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    already_done = {p.stem for p in STATIC_DIR.glob("*.webp")}
    todo = [
        (rel, slug, prompt)
        for rel, (slug, prompt) in ARTICLES.items()
        if slug not in already_done
    ]

    print(f"{len(todo)} images to generate (skipping {len(ARTICLES) - len(todo)} already done)")

    for i, (rel_path, slug, prompt) in enumerate(todo, 1):
        md_path = CONTENT_DIR / rel_path
        if not md_path.exists():
            print(f"  SKIP (file not found): {rel_path}")
            continue

        png_path = STATIC_DIR / f"{slug}.png"
        webp_path = STATIC_DIR / f"{slug}.webp"

        print(f"[{i}/{len(todo)}] {slug} ...", end=" ", flush=True)
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            url = response.data[0].url
            download_image(url, png_path)
            to_webp(png_path, webp_path)
            png_path.unlink()  # remove PNG, keep only WebP
            add_featured_image(md_path, slug)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        # Rate limit: 5 images/min on DALL-E 3 standard tier
        if i < len(todo):
            time.sleep(13)

    print("\nDone! Run `hugo` and deploy.")


if __name__ == "__main__":
    main()
