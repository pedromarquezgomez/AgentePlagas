import re
from app.customers.contracts import CustomerType


class CustomerTypeClassifier:
    def classify(self, text: str) -> CustomerType:
        if not text:
            return CustomerType.UNKNOWN

        text_lower = text.casefold()

        # Reglas basadas en palabras clave
        rules = [
            (CustomerType.HOSPITALITY, ["bar", "restaurante", "cafetería", "cafeteria", "hotel"]),
            (CustomerType.FOOD_BUSINESS, ["panadería", "panaderia", "carnicería", "carniceria", "supermercado", "almacén", "almacen"]),
            (CustomerType.COMMUNITY, ["comunidad", "vecindario", "bloque", "urbanización", "urbanizacion", "edificio"]),
            (CustomerType.PRIVATE_HOME, ["casa", "vivienda", "piso", "apartamento"]),
        ]

        for customer_type, keywords in rules:
            for kw in keywords:
                if len(kw) <= 4:
                    pattern = rf"\b{re.escape(kw)}\b"
                    if re.search(pattern, text_lower):
                        return customer_type
                else:
                    if kw in text_lower:
                        return customer_type

        return CustomerType.UNKNOWN
