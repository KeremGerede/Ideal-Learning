from typing import Tuple

# ================================================================
# HARMFUL CONTENT SAFETY CHECKER
# ================================================================
# Deterministic keyword-based pre-check for harmful learning requests.
# This runs BEFORE Gemini is called so no plan is ever created for
# unsafe topics, regardless of whether Gemini itself refuses or not.


def _normalize(text: str) -> str:
    """Lowercase + replace Turkish diacritics for consistent matching."""
    text = str(text or "").lower()
    for old, new in [("ı","i"),("ş","s"),("ğ","g"),("ü","u"),("ö","o"),("ç","c")]:
        text = text.replace(old, new)
    return text


# ----------------------------------------------------------------
# HARD-BLOCKED PHRASES
# If any of these appear in the combined topic + goal text, the
# request is always rejected. No exception.
# ----------------------------------------------------------------
_HARD_BLOCKED = [
    # Physical harm toward people
    "insanlara zarar ver",
    "birine zarar ver",
    "birini incit",
    "insanlari incit",
    "adam oldur",
    "insan oldur",
    "cinayet isle",
    "katillik ogr",
    "birini oldurm",

    # Weapons manufacturing / construction
    "bomba yap",
    "bomba uret",
    "patlayici yap",
    "patlayici uret",
    "silah yapim",
    "silah uretim",
    "ev yapimi silah",
    "atesli silah uret",
    "kesici silah yap",
    "oksuruk gazi",
    "kimyasal silah",
    "biyolojik silah",

    # Self-harm / suicide
    "intihar et",
    "kendine zarar ver",
    "kendimi oldur",
    "yasami son ver",
    "kendini oldur",
    "canima kiy",

    # Unauthorized account / credential theft
    "baskasinin hesabini",
    "baskasinin sifresini",
    "baskasinin bilgilerini cal",
    "baskasinin kimligini",
    "hesap ele gecir",
    "hesap cal",
    "sifre calmak",
    "kimlik calmak",
    "yetkisiz erisim ogren",
    "izinsiz sisteme gir",
    "izinsiz erisim ogren",
    "izinsiz hesaba gir",
    "baskasinin sistemine",

    # Malicious software creation
    "zararli yazilim yaz",
    "virusu yaz",
    "trojan yaz",
    "ransomware yaz",
    "ransomware gelistir",
    "malware yaz",
    "malware gelistir",
    "casus yazilim yaz",
    "spyware yaz",
    "keylogger yaz",
    "botnet kur",

    # Drugs
    "uyusturucu uretim",
    "uyusturucu imal",
    "uyusturucu satisi",
    "uyusturucu kacakciligi",
    "eroin uret",
    "kokain uret",
    "metamfetamin uret",

    # Fraud / forgery
    "sahte para uret",
    "sahte para bas",
    "sahte belge uret",
    "sahte kimlik uret",
    "dolandiricilik yapmayi ogren",
    "banka soymak",
    "kasa kirmak",
    "kredi karti klon",
    "kredi karti cal",

    # Terrorism / extremism
    "teror eylemi",
    "bombalı saldiri",
    "bombalı saldiri planla",
    "silahli saldiri planla",
    "terorist egitim",
    "militan egitim",
    "sehit olmak icin egitim",
    "cihad egitim",
    "insan kacakciligi",

    # Hate speech / targeted harassment
    "nefret soylemi uret",
    "irk ayrimciligi yap",
    "hedefli taciz",
    "kisisel bilgileri ifsa",

    # English equivalents (in case user types in English)
    "how to harm people",
    "how to kill",
    "build a bomb",
    "make a bomb",
    "make explosives",
    "manufacture weapons",
    "hack into someone",
    "steal someone",
    "steal credentials",
    "steal passwords",
    "unauthorized access learn",
    "write malware",
    "create malware",
    "write a virus",
    "create a virus",
    "commit fraud",
    "terrorist attack",
    "drug production",
    "drug trafficking",
    "self harm",
    "how to suicide",
]

# ----------------------------------------------------------------
# CONTEXT-SENSITIVE HARMFUL PHRASES
# Rejected UNLESS safe educational context is detected.
# E.g. "şifre kırma" alone is suspicious, but
# "şifre kırma güvenlik açıklarını etik pentesting ile test etmek" is OK.
# ----------------------------------------------------------------
_CONTEXT_SENSITIVE = [
    "sifre kir",
    "ddos saldiri",
    "phishing saldiri",
    "sisteme izinsiz",
    "agina izinsiz",
]

# ----------------------------------------------------------------
# SAFE EDUCATIONAL CONTEXT SIGNALS
# If any of these are in the combined text, context-sensitive phrases
# are treated as educational / defensive and are allowed.
# ----------------------------------------------------------------
_SAFE_CONTEXT = [
    "guvenlik",
    "koruma",
    "etik",
    "pentest",
    "penetrasyon",
    "savunma",
    "kendi sistem",
    "kendi hesab",
    "kendi agim",
    "legal",
    "izinli",
    "bug bounty",
    "ctf",
    "white hat",
    "aciklari bul",
    "zafiyetleri tespit",
    "security research",
    "ethical hacking",
    "ethical hack",
    "korunma yontem",
    "onlem al",
    "siber guvenlik",
    "cyber security",
    "bilgi guvenlik",
]


def is_harmful_learning_request(
    topic: str,
    goal: str,
    learning_preference: str | None = None
) -> Tuple[bool, str]:
    """
    Check whether a learning request involves harmful or unsafe content.

    Returns:
        (True, reason_phrase)  — request is harmful, must be rejected
        (False, "")            — request is safe, proceed normally

    This runs deterministically before any Gemini call so that no plan
    is created and no database write happens for unsafe requests.
    """

    combined = _normalize(f"{topic} {goal} {learning_preference or ''}")

    # 1. Hard-blocked phrases — always reject.
    for phrase in _HARD_BLOCKED:
        if phrase in combined:
            return True, phrase

    # 2. Context-sensitive phrases — reject unless safe context found.
    has_safe_context = any(safe in combined for safe in _SAFE_CONTEXT)

    if not has_safe_context:
        for phrase in _CONTEXT_SENSITIVE:
            if phrase in combined:
                return True, phrase

    return False, ""


def detect_gemini_safety_refusal(response_text: str) -> bool:
    """
    Detect if Gemini refused to respond due to safety concerns.

    Gemini sometimes returns plain text instead of JSON when it refuses
    a request. This function checks for known refusal signals so we can
    raise a proper error instead of falling through to the fallback plan.
    """

    if not response_text:
        return False

    text_lower = response_text.lower()

    refusal_signals = [
        "i'm not able to",
        "i cannot",
        "i can't",
        "i'm unable to",
        "harmful",
        "dangerous",
        "illegal",
        "against my",
        "safety guidelines",
        "not appropriate",
        "can't assist",
        "cannot assist",
        "unable to assist",
        "bu talebi",
        "zararlı içerik",
        "bu konuda yardım edemem",
        "güvenlik politikaları",
        "uygunsuz içerik",
        "bu isteği yerine getiremem",
        "etik olmayan",
        "zarar verebilecek",
    ]

    has_refusal_signal = any(signal in text_lower for signal in refusal_signals)

    # A real plan response will always start with '{' (JSON).
    # If it does NOT look like JSON and has a refusal signal, it's a refusal.
    stripped = response_text.strip()
    looks_like_json = stripped.startswith("{") or stripped.startswith("[")

    return has_refusal_signal and not looks_like_json
