import re
import unicodedata

SECTIONS = {
    "4.1": "Indicazioni terapeutiche",
    "4.2": "Posologia e modo di somministrazione",
    "4.3": "Controindicazioni",
    "4.4": "Avvertenze speciali e precauzioni d’impiego",
    "4.5": "Interazioni con altri medicinali",
    "4.6": "Fertilità, gravidanza e allattamento",
    "4.7": "Effetti sulla capacità di guidare veicoli",
    "4.8": "Effetti indesiderati",
    "4.9": "Sovradosaggio",
    "6.2": "Incompatibilità",
}

ENGLISH_TITLES = {
    "4.1": "Therapeutic indications",
    "4.2": "Posology and method of administration",
    "4.3": "Contraindications",
    "4.4": "Special warnings and precautions for use",
    "4.5": "Interactions with other medicinal products",
    "4.6": "Fertility, pregnancy and lactation",
    "4.7": "Effects on ability to drive and use machines",
    "4.8": "Undesirable effects (side effects)",
    "4.9": "Overdose",
    "6.2": "Incompatibilities",
}

TITLE_PREFIXES = {
    "4.1": ("indicazioni terapeutiche", "therapeutic indications"),
    "4.2": ("posologia", "posology"),
    "4.3": ("controindicazioni", "contraindications"),
    "4.4": ("avvertenze speciali", "special warnings"),
    "4.5": ("interazioni", "interazione", "interaction"),
    "4.6": ("fertilita", "gravidanza", "fertility", "pregnancy"),
    "4.7": ("effetti sulla capacita", "effetti sulle capacita", "effects on ability"),
    "4.8": ("effetti indesiderati", "undesirable effects"),
    "4.9": ("sovradosaggio", "overdose"),
    "6.2": ("incompatibilita", "incompatibilities"),
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value.replace("’", "").replace("'", "")).strip()


def missing_text(value: str) -> bool:
    return re.sub(r"[^a-z]", "", normalize(value)) in {
        "", "notfound", "nontrovato", "non", "nan", "none",
    }
