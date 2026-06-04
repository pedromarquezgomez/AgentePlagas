import math
from datetime import datetime, date, time, timedelta, timezone
from app.services.visit_service import VisitService
from app.services.incident_service import IncidentService
from app.services.customer_service import CustomerService

# Coordenadas por defecto de ciudades de la Costa del Sol para geocodificación fallback
CITY_COORDS = {
    "malaga": (36.7212, -4.4214),
    "málaga": (36.7212, -4.4214),
    "torremolinos": (36.6226, -4.4996),
    "benalmadena": (36.5956, -4.5249),
    "benalmádena": (36.5956, -4.5249),
    "fuengirola": (36.5398, -4.6247),
    "marbella": (36.5101, -4.8824),
    "estepona": (36.4256, -5.1472),
}

OFFICE_COORDS = (36.7212, -4.4214)  # Málaga Oficina Central


def haversine_distance(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
    # Calcula la distancia del círculo máximo en kilómetros entre dos puntos
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0  # Radio de la Tierra en km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


class RouteOptimizer:
    def __init__(self) -> None:
        self.visit_service = VisitService()
        self.incident_service = IncidentService()
        self.customer_service = CustomerService()

    async def get_visit_coordinates(self, visit: dict) -> tuple[float, float]:
        # Intentar obtener coordenadas del site
        incident_id = visit.get("incident_id")
        if incident_id:
            try:
                incident = await self.incident_service.get_incident(incident_id)
                site_id = incident.get("site_id")
                if site_id:
                    site = await self.customer_service.get_site(site_id)
                    lat = site.get("latitude")
                    lon = site.get("longitude")
                    if lat is not None and lon is not None:
                        return float(lat), float(lon)
            except Exception:
                pass

        # Fallback basado en parsear la dirección o texto
        addr = (visit.get("address") or "").lower()
        for city, coords in CITY_COORDS.items():
            if city in addr:
                return coords

        # Fallback final a la oficina central
        return OFFICE_COORDS

    async def optimize_route(self, technician_id: str, visit_date: date, apply: bool = False) -> dict:
        # 1. Obtener visitas programadas para el técnico en ese día
        visits = await self.visit_service.list_calendar_visits(
            start_date=visit_date,
            end_date=visit_date,
            technician_id=technician_id,
        )

        if len(visits) <= 1:
            return {
                "technician_id": technician_id,
                "date": visit_date.isoformat(),
                "original_distance_km": 0.0,
                "optimized_distance_km": 0.0,
                "savings_percent": 0.0,
                "visits": visits,
                "applied": False,
            }

        # 2. Obtener coordenadas de cada visita
        visit_coords = []
        for v in visits:
            coords = await self.get_visit_coordinates(v)
            visit_coords.append((v, coords))

        # 3. Calcular distancia original (siguiendo el orden actual de hora de inicio)
        # Ordenar visitas por la fecha y hora de inicio actual
        def parse_start(item_tuple):
            val = item_tuple[0].get("scheduled_start")
            dt = parse_datetime(val)
            if dt:
                return dt
            return datetime.min.replace(tzinfo=timezone.utc)

        ordered_visit_coords = sorted(visit_coords, key=parse_start)

        original_distance = 0.0
        current_loc = OFFICE_COORDS
        for v, coords in ordered_visit_coords:
            original_distance += haversine_distance(current_loc, coords)
            current_loc = coords
        original_distance += haversine_distance(current_loc, OFFICE_COORDS)  # regreso a la oficina

        # 4. Resolver TSP Greedy (Nearest Neighbor) empezando en la oficina
        optimized_visit_coords = []
        unvisited = list(visit_coords)
        current_loc = OFFICE_COORDS

        while unvisited:
            # Buscar el más cercano
            closest_idx = 0
            min_dist = float("inf")
            for i, (v, coords) in enumerate(unvisited):
                dist = haversine_distance(current_loc, coords)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            
            selected = unvisited.pop(closest_idx)
            optimized_visit_coords.append(selected)
            current_loc = selected[1]

        # Distancia optimizada
        optimized_distance = 0.0
        current_loc = OFFICE_COORDS
        for v, coords in optimized_visit_coords:
            optimized_distance += haversine_distance(current_loc, coords)
            current_loc = coords
        optimized_distance += haversine_distance(current_loc, OFFICE_COORDS)

        savings = original_distance - optimized_distance
        savings_percent = (savings / original_distance * 100.0) if original_distance > 0 else 0.0

        # 5. Generar nuevos horarios secuenciales en base al recorrido optimizado
        # Iniciamos a las 8:00 AM
        base_datetime = datetime.combine(visit_date, time(8, 0, 0)).replace(tzinfo=timezone.utc)
        
        updated_visits = []
        for index, (v, coords) in enumerate(optimized_visit_coords):
            start = base_datetime + timedelta(hours=index * 2)
            end = start + timedelta(hours=1, minutes=30)
            
            v_updated = dict(v)
            v_updated["scheduled_start"] = start.isoformat()
            v_updated["scheduled_end"] = end.isoformat()
            
            if apply:
                # Guardar en base de datos
                await self.visit_service.update_visit(v["id"], {
                    "scheduled_start": start.isoformat(),
                    "scheduled_end": end.isoformat(),
                })
            
            updated_visits.append(v_updated)

        return {
            "technician_id": technician_id,
            "date": visit_date.isoformat(),
            "original_distance_km": round(original_distance, 1),
            "optimized_distance_km": round(optimized_distance, 1),
            "savings_percent": round(savings_percent, 1),
            "visits": updated_visits,
            "applied": apply,
        }
