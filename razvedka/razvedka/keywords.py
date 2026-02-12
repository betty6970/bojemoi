# Multilingual keyword dictionaries for CTI extraction
# Categories: ddos (weight 3), target (weight 2), time (weight 1)

INTENTION_KEYWORDS: dict[str, dict[str, list[tuple[str, int]]]] = {
    "russian": {
        "ddos": [
            ("ддос", 3), ("ddos", 3), ("атака", 3), ("атаковать", 3),
            ("обстрел", 3), ("удар", 3), ("бомбить", 3), ("положить", 3),
            ("ддосить", 3), ("флуд", 3), ("ботнет", 3), ("стресс", 3),
        ],
        "target": [
            ("цель", 2), ("мишень", 2), ("объект", 2), ("сайт", 2),
            ("сервер", 2), ("инфраструктура", 2), ("портал", 2),
            ("домен", 2), ("ресурс", 2),
        ],
        "time": [
            ("завтра", 1), ("сегодня", 1), ("сейчас", 1), ("скоро", 1),
            ("вечером", 1), ("ночью", 1), ("утром", 1), ("следующий", 1),
            ("начинаем", 1), ("готовьтесь", 1), ("в атаку", 1),
        ],
    },
    "english": {
        "ddos": [
            ("ddos", 3), ("attack", 3), ("strike", 3), ("hit", 3),
            ("flood", 3), ("botnet", 3), ("takedown", 3), ("take down", 3),
            ("stress", 3), ("knock offline", 3), ("overload", 3),
        ],
        "target": [
            ("target", 2), ("objective", 2), ("site", 2), ("server", 2),
            ("infrastructure", 2), ("portal", 2), ("domain", 2),
            ("website", 2), ("resource", 2),
        ],
        "time": [
            ("tomorrow", 1), ("tonight", 1), ("now", 1), ("soon", 1),
            ("next", 1), ("ready", 1), ("prepare", 1), ("incoming", 1),
            ("launch", 1),
        ],
    },
    "arabic": {
        "ddos": [
            ("هجوم", 3), ("ddos", 3), ("ضرب", 3), ("اسقاط", 3),
            ("تدمير", 3), ("هجمة", 3), ("فيضان", 3),
        ],
        "target": [
            ("هدف", 2), ("موقع", 2), ("سيرفر", 2), ("خادم", 2),
            ("بنية تحتية", 2), ("بوابة", 2),
        ],
        "time": [
            ("غدا", 1), ("الليلة", 1), ("قريبا", 1), ("الآن", 1),
            ("استعدوا", 1), ("جاهزون", 1),
        ],
    },
    "french": {
        "ddos": [
            ("ddos", 3), ("attaque", 3), ("frapper", 3), ("bombarder", 3),
            ("inonder", 3), ("botnet", 3), ("saturer", 3),
        ],
        "target": [
            ("cible", 2), ("objectif", 2), ("site", 2), ("serveur", 2),
            ("infrastructure", 2), ("portail", 2), ("domaine", 2),
        ],
        "time": [
            ("demain", 1), ("ce soir", 1), ("maintenant", 1), ("bientôt", 1),
            ("prochaine", 1), ("préparez", 1), ("lancement", 1),
        ],
    },
}

# France-related keywords (all lowercase for matching)
FRANCE_KEYWORDS: list[str] = [
    "france", "français", "francais", "french", "francia", "frankreich",
    "франция", "французский", "французская", "французские",
    "فرنسا", "الفرنسية",
    ".fr", ".gouv.fr",
    "paris", "lyon", "marseille", "toulouse",
    "macron", "élysée", "elysee",
]

# Temporal patterns (regex fragments)
TEMPORAL_PATTERNS: list[str] = [
    r"\d{1,2}[./]\d{1,2}[./]\d{2,4}",      # dates: 12/03/2025, 12.03.25
    r"\d{1,2}:\d{2}",                        # times: 14:00, 9:30
    r"\d{1,2}\s*(?:am|pm|AM|PM)",            # 9am, 3 PM
    r"(?:UTC|GMT|MSK|CET)[+-]?\d*",          # timezones
]
