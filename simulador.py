"""MÓDULO 4. Simula las operaciones de panadería día a día.

Producción -> demanda -> venta -> excedente desechado -> contabilidad.
El inventario al final del día SIEMPRE es cero: el pan es perecedero.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from parametros import DIAS_SEMANA, ParametrosCaso
from aleatoriedad import Escenario
from politicas import Politica


@dataclass
class Resultado:
    politica: str
    ganancia: float
    ingresos: float
    costo_produccion: float
    costo_desecho: float
    costo_fijo: float
    penalizacion_faltante: float
    panes_horneados: int
    panes_vendidos: int
    sobrantes: int
    ventas_perdidas: int
    demanda_total: int
    dias_con_faltante: int
    dias_con_desperdicio: int
    detalles: pd.DataFrame | None = None

    @property
    def nivel_servicio(self) -> float:
        """Fill rate = ventas / demanda (100% si demanda total es cero)."""
        return self.panes_vendidos / self.demanda_total if self.demanda_total else 1.0

    @property
    def tasa_desperdicio(self) -> float:
        return self.sobrantes / self.panes_horneados if self.panes_horneados else 0.0

    def como_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != 'detalles'} | {
            'nivel_servicio': self.nivel_servicio,
            'tasa_desperdicio': self.tasa_desperdicio,
        }


def simular(p: ParametrosCaso, escenario: Escenario, politica: Politica,
            guardar_detalles: bool = False) -> Resultado:
    d = escenario.demanda
    q = politica.cantidades(escenario.dia_semana)
    vendidos = np.minimum(q, d)
    sobrantes = np.maximum(q - d, 0)
    faltantes = np.maximum(d - q, 0)
    ingresos = vendidos * p.precio_venta
    produccion = q * p.costo_produccion
    desecho = sobrantes * p.costo_desecho
    rescate = sobrantes * p.valor_rescate
    penalizacion = faltantes * p.penalizacion_faltante
    fijo = np.full(d.size, p.costo_fijo_diario)
    # El margen perdido de los faltantes YA se refleja en menores ingresos;
    # penalización agrega solo un costo reputacional externo (si se configura).
    ganancia = ingresos + rescate - produccion - desecho - penalizacion - fijo

    detalles = None
    if guardar_detalles:
        detalles = pd.DataFrame({
            'Día': np.arange(1, len(d) + 1),
            'Día de semana': [DIAS_SEMANA[x] for x in escenario.dia_semana],
            'Demanda': d, 'Horneados': q, 'Vendidos': vendidos,
            'Sobrantes (desechados)': sobrantes, 'Ventas perdidas': faltantes,
            'Ingresos (COP)': ingresos, 'Costos de producción (COP)': produccion,
            'Costos de desecho (COP)': desecho,
            'Valor rescatado (COP)': rescate,
            'Costo fijo (COP)': fijo,
            'Penalización (COP)': penalizacion,
            'Ganancia (COP)': ganancia,
            'Inventario final': np.zeros(d.size, dtype=int),
        })

    return Resultado(
        politica=politica.nombre,
        ganancia=float(ganancia.sum()),
        ingresos=float((ingresos + rescate).sum()),
        costo_produccion=float(produccion.sum()),
        costo_desecho=float(desecho.sum()),
        costo_fijo=float(fijo.sum()),
        penalizacion_faltante=float(penalizacion.sum()),
        panes_horneados=int(q.sum()),
        panes_vendidos=int(vendidos.sum()),
        sobrantes=int(sobrantes.sum()),
        ventas_perdidas=int(faltantes.sum()),
        demanda_total=int(d.sum()),
        dias_con_faltante=int(np.count_nonzero(faltantes)),
        dias_con_desperdicio=int(np.count_nonzero(sobrantes)),
        detalles=detalles,
    )
