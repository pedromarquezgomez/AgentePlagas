PEST_TYPE_COCKROACH = "COCKROACH"
PEST_TYPE_RODENT = "RODENT"
PEST_TYPE_ANT = "ANT"
PEST_TYPE_FLYING_INSECT = "FLYING_INSECT"
PEST_TYPE_STORED_PRODUCT_INSECT = "STORED_PRODUCT_INSECT"
PEST_TYPE_UNKNOWN = "UNKNOWN"

# Mapeo de términos individuales casefold al tipo de plaga normalizado
PEST_TERM_TO_TYPE = {
    # Cucarachas
    "cucaracha": PEST_TYPE_COCKROACH,
    "cucarachas": PEST_TYPE_COCKROACH,
    "cockroach": PEST_TYPE_COCKROACH,
    "cockroaches": PEST_TYPE_COCKROACH,

    # Roedores
    "roedor": PEST_TYPE_RODENT,
    "roedores": PEST_TYPE_RODENT,
    "rodent": PEST_TYPE_RODENT,
    "rodents": PEST_TYPE_RODENT,
    "rata": PEST_TYPE_RODENT,
    "ratas": PEST_TYPE_RODENT,
    "ratón": PEST_TYPE_RODENT,
    "raton": PEST_TYPE_RODENT,
    "ratones": PEST_TYPE_RODENT,

    # Hormigas
    "hormiga": PEST_TYPE_ANT,
    "hormigas": PEST_TYPE_ANT,
    "ant": PEST_TYPE_ANT,
    "ants": PEST_TYPE_ANT,

    # Insectos voladores (mosquitos/avispas/moscas)
    "mosquito": PEST_TYPE_FLYING_INSECT,
    "mosquitos": PEST_TYPE_FLYING_INSECT,
    "avispa": PEST_TYPE_FLYING_INSECT,
    "avispas": PEST_TYPE_FLYING_INSECT,
    "mosca": PEST_TYPE_FLYING_INSECT,
    "moscas": PEST_TYPE_FLYING_INSECT,

    # Plagas de productos almacenados (gorgojo/polilla)
    "gorgojo": PEST_TYPE_STORED_PRODUCT_INSECT,
    "gorgojos": PEST_TYPE_STORED_PRODUCT_INSECT,
    "polilla": PEST_TYPE_STORED_PRODUCT_INSECT,
    "polillas": PEST_TYPE_STORED_PRODUCT_INSECT,

    # Bichos raros / Desconocido
    "bichos raros": PEST_TYPE_UNKNOWN,
    "bicho raro": PEST_TYPE_UNKNOWN,
    "plaga rara": PEST_TYPE_UNKNOWN,
    "plagas raras": PEST_TYPE_UNKNOWN,
    "unknown": PEST_TYPE_UNKNOWN,
}

# Configuración de metadatos de negocio asociada a cada tipo de plaga
PEST_TYPE_METADATA = {
    PEST_TYPE_COCKROACH: {
        "spanish": "cucarachas",
        "priority": "high",
        "requires_human_review": False,
    },
    PEST_TYPE_RODENT: {
        "spanish": "roedores",
        "priority": "high",
        "requires_human_review": False,
    },
    PEST_TYPE_ANT: {
        "spanish": "hormigas",
        "priority": "medium",
        "requires_human_review": False,
    },
    PEST_TYPE_FLYING_INSECT: {
        "spanish": "mosquitos/avispas",
        "priority": "medium",
        "requires_human_review": False,
    },
    PEST_TYPE_STORED_PRODUCT_INSECT: {
        "spanish": "gorgojo/polilla",
        "priority": "medium",
        "requires_human_review": False,
    },
    PEST_TYPE_UNKNOWN: {
        "spanish": None,
        "priority": "medium",
        "requires_human_review": True,
    },
}

# Para mantener compatibilidad con imports anteriores
PEST_TAXONOMY_TERMS = {term: meta["spanish"] or "unknown" for term, type_key in PEST_TERM_TO_TYPE.items() for meta in [PEST_TYPE_METADATA[type_key]]}

