from datetime import datetime, timedelta, timezone
from typing import Any

class AvailabilityService:
    @classmethod
    def calculate_free_slots(
        cls,
        busy_slots: list[tuple[datetime, datetime]],
        start_date: datetime | None = None,
        duration_minutes: int = 60,
        max_slots: int = 3,
    ) -> list[str]:
        """
        Calcula hasta `max_slots` de duración `duration_minutes` que no se solapen
        con los `busy_slots` provistos. Respetando el horario de Lunes a Viernes de 09:00 a 17:00.
        """
        if start_date is None:
            # Empezar desde mañana
            now = datetime.now(timezone.utc)
            start_date = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        
        # Asegurarse de que start_date tiene zona horaria
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        free_slots: list[str] = []
        current_day = start_date

        # Iterar hasta un máximo de 30 días para evitar bucles infinitos
        for _ in range(30):
            if len(free_slots) >= max_slots:
                break

            # 1. Omitir fines de semana (5 = Sábado, 6 = Domingo)
            if current_day.weekday() >= 5:
                current_day += timedelta(days=1)
                continue

            # 2. Definir horario laboral de 09:00 a 17:00 en el día actual
            work_start = current_day.replace(hour=9, minute=0, second=0, microsecond=0)
            work_end = current_day.replace(hour=17, minute=0, second=0, microsecond=0)

            # 3. Iterar en intervalos de la duración especificada
            block_start = work_start
            while block_start + timedelta(minutes=duration_minutes) <= work_end:
                if len(free_slots) >= max_slots:
                    break

                block_end = block_start + timedelta(minutes=duration_minutes)

                # Comprobar solapamiento con slots ocupados
                has_overlap = False
                for busy_start, busy_end in busy_slots:
                    # Asegurar zonas horarias
                    if busy_start.tzinfo is None:
                        busy_start = busy_start.replace(tzinfo=timezone.utc)
                    if busy_end.tzinfo is None:
                        busy_end = busy_end.replace(tzinfo=timezone.utc)

                    # Solapamiento si: block_start < busy_end y block_end > busy_start
                    if block_start < busy_end and block_end > busy_start:
                        has_overlap = True
                        break

                if not has_overlap:
                    free_slots.append(block_start.isoformat())

                # Avanzar al siguiente intervalo (no solapado necesariamente, pero avanzamos el bloque)
                block_start += timedelta(minutes=duration_minutes)

            # Avanzar al día siguiente
            current_day += timedelta(days=1)

        return free_slots
