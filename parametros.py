"""MÓDULO 1. Parámetros del modelo Newsvendor para una panadería.

Valores monetarios en pesos colombianos (COP). Datos hipotéticos,
NO son registros de una panadería real.
"""
from dataclasses import dataclass, replace


DIAS_SEMANA = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


@dataclass(frozen=True)
class ParametrosCaso:
    # Demanda: Normal por día, redondeada y truncada a cero.
    demanda_media: float = 110.0
    demanda_desviacion: float = 24.0
    # Multiplicadores de lunes a domingo; se conoce su patrón antes de decidir.
    factores_semana: tuple[float, ...] = (0.85, 0.90, 0.95, 1.00, 1.10, 1.35, 1.20)

    # Costos, precio y valor residual (salvamento) del pan del día.
    precio_venta: float = 3500.0
    costo_produccion: float = 1500.0
    costo_desecho: float = 150.0  # gasto adicional por pan desechado
    valor_rescate: float = 0.0    # lo que se recupera del pan sobrante (aquí, cero)
    penalizacion_faltante: float = 0.0  # costo reputacional extra, opcional
    costo_fijo_diario: float = 65000.0

    # Políticas y Monte Carlo.
    horneado_fijo: int = 110
    dias_simulacion: int = 365
    replicas: int = 500
    semilla: int = 2026

    @property
    def costo_exceso(self) -> float:
        """Co: costo marginal de hacer un pan que no se vende."""
        return self.costo_produccion + self.costo_desecho - self.valor_rescate

    @property
    def costo_defecto(self) -> float:
        """Cu: costo marginal de no hacer un pan que se habría vendido."""
        return self.precio_venta - self.costo_produccion + self.penalizacion_faltante

    @property
    def fractil_critico(self) -> float:
        """Cu/(Cu+Co) para el problema Newsvendor clásico."""
        den = self.costo_defecto + self.costo_exceso
        return self.costo_defecto / den if den > 0 else 0.5

    def validar(self):
        if self.demanda_media < 0 or self.demanda_desviacion < 0:
            raise ValueError('La media y desviación de demanda deben ser >= 0.')
        if len(self.factores_semana) != 7 or any(f < 0 for f in self.factores_semana):
            raise ValueError('Se necesitan siete factores semanales no negativos.')
        if self.precio_venta <= self.costo_produccion:
            raise ValueError('El precio debe ser mayor que el costo de producción para el caso de ejemplo.')
        if self.costo_exceso <= 0:
            raise ValueError('El costo de exceso debe ser positivo.')
        if self.penalizacion_faltante < 0 or self.costo_fijo_diario < 0:
            raise ValueError('Las penalizaciones y gastos fijos no pueden ser negativos.')
        if self.horneado_fijo < 0 or self.dias_simulacion < 1 or self.replicas < 1:
            raise ValueError('Horneado >= 0; días y réplicas >= 1.')
        if not (0 < self.fractil_critico < 1):
            raise ValueError('El fractil crítico debe estar entre 0 y 1.')
        return self

    def con_cambios(self, **cambios):
        return replace(self, **cambios).validar()


# Experimento de estrés: demanda sube sin que las políticas se reajusten.
# La subida se aplica a toda la semana, no a los precios ni costos.
CAMBIOS_PICO_DEMANDA = dict(multiplicador_demanda=1.30)
