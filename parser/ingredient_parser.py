"""
OpticEats — Stage 2: Ingredient Parser (v5 — Final)
======================================================
Fixes in v5:
  1. (223. () OCR noise -> [223] handled directly in fix_ocr_errors
  2. RE_VERBOSE_FLAVOUR expanded to also strip leftover (VANILLA) FLAVOURING SUBSTANCES
  3. Extra name cleaner strips any trailing FLAVOURING SUBSTANCES suffix
"""

import re


OCR_CHAR_FIXES = [
    (r'\}',  ')'),
    (r'\{',  '('),
    (r';',   ','),
    (r'\|',  'I'),
]

ENUMBER_FIXES = {
    r'\[?[sS][oO0][oO0][lL1]\]?':              '[500(ii)]',
    r'\[?5[oO0][oO0]\s*\(?[iI1][iI1]\)?\]?':  '[500(ii)]',
    r'\[?5[oO0]3\s*\(?[iI1][iI1]\)?\]?':       '[503(ii)]',
    r'503\(\s*\)':                              '[503(ii)]',
    r'503\s*\]':                                '[503(ii)]',
    r'\[?322\s*[/\\|,\.]\s*[}\)iI1]*\]?':      '[322(i)]',
    r'\[?322\s*\(?[iI1]\)?\]?':                '[322(i)]',
    r'471\s*&\s*472[eE]':                       '471 & 472e',
    r'\b2231\b':                                '223',
    r'\b22[sS]\b':                              '223',
    r'[Hh][Oo][Dd][Ii][Ss][Ee][Dd]':           'IODISED',
    r'[Hh][Oo][Dd][Ii][Zz][Ee][Dd]':           'IODISED',
    r'CONDITLONER':                             'CONDITIONER',
    r'CONDITONER':                              'CONDITIONER',
}

STRIP_PHRASES = [
    # Numbering system footnotes
    r'numbers?\s+in\s+brackets?\s+as\s+per\s+international\s+numbering\s+system',
    r'#\s*made\s+with\s+wheat\s+flour\s*\(?atta\)?',
    # Allergen statements — these are warnings, NOT ingredients
    r'allergens?\s*:.*',
    r'contains\s+wheat.*?sulphite[s]?\.?',
    r'contains\s+wheat.*?\.',
    r'contains\s+milk.*?\.',
    r'contains\s+soy.*?\.',
    r'contains\s+nuts.*?\.',
    r'contains\s+gluten.*?\.',
    r'may\s+contain\s+traces?\s+of.*?\.',
    r'may\s+contain\s+.*?\.',
    r'manufactured\s+in\s+a\s+facility.*?\.',
    r'manufactured\s+in.*?\.',
    r'produced\s+in.*?\.',
    r'processed\s+in.*?\.',
    r'best\s+before.*?\.',
    r'store\s+in.*?\.',
    r'keep\s+(refrigerated|cool|dry).*?\.',
    # Cocoa percentage declarations
    r'min\.?\s*cocoa\s*:\s*\d+%',
    r'minimum\s+cocoa\s+content.*?\.',
    r'\bmin\.cocoa[:\s]+\d+\s*%',
    # Soy/nut warnings
    r'soy\s+and\s+its\s+products',
    r'tree\s+nuts\s+and\s+(their\s+)?derivatives',
    r'and\s+its\s+products',
]


def fix_ocr_errors(text):
    for pattern, replacement in ENUMBER_FIXES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    for pattern, replacement in OCR_CHAR_FIXES:
        text = re.sub(pattern, replacement, text)
    for phrase in STRIP_PHRASES:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)

    # Fix percentage misreads
    text = re.sub(r'\((\d{2})9\)', lambda m: f'({m.group(1)}%)', text)
    text = re.sub(
        r'\((\d+\.\d+)\)(?!\s*%)',
        lambda m: (f'({m.group(1)[:-1]}%)' if m.group(1).endswith('9')
                   else f'({m.group(1)}%)'),
        text
    )

    # FIX 1: Handle (223. () OCR noise pattern -> [223]
    # Matches (223) or (223.) or (223. () or (223. ())
    text = re.sub(r'\(223[\.\s]*\(?\s*\)', '[223]', text)
    # Catch any remaining (3-digit-number. ...) noise
    text = re.sub(r'\((\d{3})\.\s*\(\s*\)', r'[\1]', text)

    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[,\s]+$', '', text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — SPLIT
# ─────────────────────────────────────────────────────────────────────────────

def split_ingredients(text):
    parts   = []
    current = []
    depth   = 0
    for char in text:
        if char in '([':
            depth += 1
            current.append(char)
        elif char in ')]':
            depth = max(0, depth - 1)
            current.append(char)
        elif char in ',;' and depth == 0:
            part = ''.join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    last = ''.join(current).strip()
    if last:
        parts.append(last)
    return [p.strip().strip(',').strip() for p in parts if len(p.strip()) > 1]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — PARSE
# ─────────────────────────────────────────────────────────────────────────────

RE_PERCENTAGE     = re.compile(r'\(\s*(\d+(?:\.\d+)?)\s*%\s*\)')
RE_ENUMBER_SQUARE = re.compile(r'\[([^\]]*\d{3}[^\]]*)\]')
RE_ENUMBER_ROUND  = re.compile(r'(?<!\w)\((\d{3,4}[a-zA-Z]?(?:\([ivxIVX]+\))?)\.*\)(?!\w)')
RE_ENUMBER_CODE   = re.compile(r'\b(\d{3,4}[a-zA-Z]?(?:\([ivxIVX]+\))?)\b')
RE_TRAILING_AND   = re.compile(r'\s+AND\s*$', re.IGNORECASE)

# FIX 2: Expanded to also strip (VANILLA) FLAVOURING SUBSTANCES leftover
RE_VERBOSE_FLAVOUR = re.compile(
    r'\s*(NATURE IDENTICAL\s*&?\s*ARTIFICIAL\s*)?\(VANILLA\)\s*FLAVOURING SUBSTANCES',
    re.IGNORECASE
)


def extract_percentage(text):
    match = RE_PERCENTAGE.search(text)
    if match:
        try:
            pct = float(match.group(1))
            if 0 < pct <= 100:
                cleaned = (text[:match.start()] + ' ' + text[match.end():]).strip()
                return pct, cleaned
        except ValueError:
            pass
    return None, text


def extract_enumbers(text):
    enumbers = []
    spans_to_remove = []

    for match in RE_ENUMBER_SQUARE.finditer(text):
        content = match.group(1)
        if re.search(r'\d{3}', content):
            codes = re.split(r'[,&]|\band\b', content)
            for code in codes:
                code_match = RE_ENUMBER_CODE.search(code.strip())
                if code_match:
                    enumbers.append(code_match.group(1))
            spans_to_remove.append((match.start(), match.end()))

    for match in RE_ENUMBER_ROUND.finditer(text):
        content = match.group(1)
        if re.match(r'^\d{3,4}', content):
            enumbers.append(content)
            spans_to_remove.append((match.start(), match.end()))

    result_text = text
    for start, end in sorted(spans_to_remove, reverse=True):
        result_text = result_text[:start] + result_text[end:]

    result_text = re.sub(r'\(\s*[\.\s]*\)', '', result_text)
    result_text = re.sub(r'\.\s*\(', '', result_text)
    result_text = re.sub(r'\s*\.\s*$', '', result_text)
    return enumbers, result_text.strip()


def clean_ingredient_name(name):
    name = re.sub(r'^[\s,;:]+', '', name)
    name = re.sub(r'[\s,;:]+$', '', name)

    # FIX 2: Strip verbose flavouring descriptions
    name = RE_VERBOSE_FLAVOUR.sub('', name).strip()

    # FIX 3: Strip any remaining FLAVOURING SUBSTANCES suffix
    name = re.sub(r'\s*FLAVOURING SUBSTANCES\s*$', '', name, flags=re.IGNORECASE).strip()

    # Strip trailing AND
    name = RE_TRAILING_AND.sub('', name).strip()

    # Balance brackets
    open_count  = name.count('(')
    close_count = name.count(')')
    if open_count > close_count:
        name = name + ')' * (open_count - close_count)
    elif close_count > open_count:
        for _ in range(close_count - open_count):
            idx = name.rfind(')')
            name = name[:idx] + name[idx+1:]

    name = re.sub(r'\s*\.\s*$', '', name).strip()
    name = re.sub(r'^\d+$', '', name).strip()
    name = re.sub(r'\s+', ' ', name).strip().upper()
    return name


def parse_single_ingredient(raw):
    if not raw or not raw.strip():
        return None
    original         = raw.strip()
    text             = original
    percentage, text = extract_percentage(text)
    enumbers,   text = extract_enumbers(text)
    name             = clean_ingredient_name(text)
    if not name or len(name) < 2:
        return None
    if re.match(r'^[0-9\s,\.]+$', name):
        return None
    if re.match(r'^[A-Z]$', name):
        return None
    return {
        "name"      : name,
        "percentage": percentage,
        "e_numbers" : enumbers,
        "raw"       : original
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3B — SPLIT MERGED ITEMS
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_STANDALONE_INGREDIENTS = [
    "RAISING AGENTS",
    "IODISED SALT",
    "EMULSIFIERS",
    "LIQUID GLUCOSE",
    "MALT EXTRACT",
    "DOUGH CONDITIONER",
    "MALTODEXTRIN",
    "WHEAT BRAN",
    "REFINED PALM OIL",
    "MILK SOLIDS",
    "MILK POWDER",
    "WHEY POWDER",
]


def split_merged_ingredients(text):
    result    = []
    remaining = text.strip()
    found_any = False
    for known in sorted(KNOWN_STANDALONE_INGREDIENTS, key=len, reverse=True):
        idx = remaining.upper().find(known)
        if idx > 0:
            before = remaining[:idx].strip().rstrip(',').strip()
            after  = remaining[idx:].strip()
            if before and len(before) > 2:
                result.append(before)
                remaining = after
                found_any = True
                break
    if found_any:
        result.extend(split_merged_ingredients(remaining))
    else:
        result.append(remaining)
    return [r for r in result if r.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def parse_ingredients(clean_text):
    print("\n[OpticEats Parser] Starting Stage 2 - Ingredient Parsing...")
    fixed_text = fix_ocr_errors(clean_text)
    print(f"[OpticEats Parser] Fixed text:\n  {fixed_text[:250]}...\n")

    raw_parts = split_ingredients(fixed_text)
    print(f"[OpticEats Parser] Initial split -> {len(raw_parts)} parts")

    expanded_parts = []
    for part in raw_parts:
        sub = split_merged_ingredients(part)
        expanded_parts.extend(sub)

    if len(expanded_parts) > len(raw_parts):
        print(f"[OpticEats Parser] After merge-split -> {len(expanded_parts)} parts")

    ingredients = []
    for i, part in enumerate(expanded_parts):
        parsed = parse_single_ingredient(part)
        if parsed:
            ingredients.append(parsed)
            pct_str = f"  ({parsed['percentage']}%)" if parsed['percentage'] else ""
            enu_str = f"  e:{parsed['e_numbers']}"   if parsed['e_numbers']  else ""
            print(f"  [{i+1:2}] OK  {parsed['name']}{pct_str}{enu_str}")
        else:
            print(f"  [{i+1:2}] --  Skipped: '{part[:60]}'")

    print(f"\n[OpticEats Parser] Parsed {len(ingredients)} ingredients\n")
    return ingredients


def summarise_ingredients(ingredients):
    lines = [
        f"\n{'─'*60}",
        f"  OpticEats - Parsed Ingredients ({len(ingredients)} total)",
        f"{'─'*60}",
    ]
    for i, ing in enumerate(ingredients, 1):
        pct = f"  {ing['percentage']}%" if ing['percentage'] else ""
        enu = f"  e-nums: {', '.join(ing['e_numbers'])}" if ing['e_numbers'] else ""
        lines.append(f"  {i:2}. {ing['name']}{pct}{enu}")
    lines.append(f"{'─'*60}\n")
    return '\n'.join(lines)
