"""MÓDULO 2. Generación de la demanda aleatoria diaria.

Números aleatorios comunes: cada política enfrenta la MISMA demanda
para cada réplica; así la comparación no depende de quién tuvo suerte.
"""
from dataclasses import dataclass
import numpy as np
from parametros import ParametrosCaso


@dataclass
class Escenario:
    demanda: np.ndarray
    dia_semana: np.ndarray  # lunes=0, ... domingo=6


def generar_escenario(p: ParametrosCaso, replica: int,
                      multiplicador_demanda: float = 1.0) -> Escenario:
    if multiplicador_demanda <= 0:
        raise ValueError('El multiplicador de demanda debe ser positivo.')
    rng = np.random.default_rng([int(p.semilla), int(replica)])
    dias = np.arange(p.dias_simulacion, dtype=int)
    semana = dias % 7
    factores = np.asarray(p.factores_semana)[semana]
    media = p.demanda_media * factores * multiplicador_demanda
    desv = p.demanda_desviacion * factores * multiplicador_demanda
    demanda = np.maximum(0, np.rint(rng.normal(loc=media, scale=desv))).astype(int)
    return Escenario(demanda=demanda, dia_semana=semana)
