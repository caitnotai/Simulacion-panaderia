"""MÓDULO 3. Cuatro decisiones de horneado a comparar.

El óptimo Newsvendor usa F(Q*) >= Cu/(Cu+Co) para la distribución de demanda.
Al ser la demanda una normal REDONDEADA y TRUNCADA a cero, se usa su CDF
exacta para cantidades enteras, no se mira la demanda del futuro.
"""
from dataclasses import dataclass
from statistics import NormalDist
import numpy as np
from parametros import ParametrosCaso

NORMAL = NormalDist()


def _cdf_redondeada(q: int, media: float, desv: float) -> float:
    """P(D<=q), D=max(0, round(N(media,desv))), para q>=0."""
    if q < 0:
        return 0.0
    if desv == 0:
        return 1.0 if max(0, int(np.rint(media))) <= q else 0.0
    return NORMAL.cdf((q + 0.5 - media) / desv)


def _cuantil_discreto(cdf, alpha: float, cota: int) -> int:
    """Menor número entero Q con CDF(Q)>=alpha, búsqueda binaria."""
    if cdf(0) >= alpha:
        return 0
    bajo, alto = 0, max(1, cota)
    while cdf(alto) < alpha:
        alto *= 2
    while bajo + 1 < alto:
        medio = (bajo + alto) // 2
        if cdf(medio) >= alpha:
            alto = medio
        else:
            bajo = medio
    return alto


def cantidad_optima(p: ParametrosCaso, dia_semana: int | None = None) -> int:
    """Optimiza una sola cantidad global (None) o específica para un día.

    La CDF global es una mezcla equiponderada de los siete días.
    Para horizontes no múltiplos de 7, usa pesos según la frecuencia
    real de cada día dentro del horizonte.
    """
    p.validar()
    pesos = np.bincount(np.arange(p.dias_simulacion) % 7, minlength=7).astype(float)
    pesos /= pesos.sum()
    alpha = p.fractil_critico
    cota = int(max(20, (p.demanda_media + 8 * p.demanda_desviacion) * max(p.factores_semana)))
    if dia_semana is not None:
        if not 0 <= dia_semana <= 6:
            raise ValueError('El día de semana debe estar entre 0 y 6.')
        factor = p.factores_semana[dia_semana]
        return _cuantil_discreto(
            lambda q: _cdf_redondeada(q, p.demanda_media * factor,
                                      p.demanda_desviacion * factor), alpha, cota)

    def cdf_mezcla(q):
        return sum(pesos[i] * _cdf_redondeada(q, p.demanda_media * f,
                   p.demanda_desviacion * f)
                   for i, f in enumerate(p.factores_semana))

    return _cuantil_discreto(cdf_mezcla, alpha, cota)


@dataclass(frozen=True)
class Politica:
    nombre: str
    descripcion: str
    horneado_semana: tuple[int, ...]

    def cantidades(self, dias_semana: np.ndarray) -> np.ndarray:
        return np.asarray(self.horneado_semana, dtype=int)[dias_semana]


def construir_politicas(p: ParametrosCaso) -> list[Politica]:
    p.validar()
    q_global = cantidad_optima(p)
    q_dias = tuple(cantidad_optima(p, d) for d in range(7))
    media_dias = tuple(int(np.rint(p.demanda_media * f)) for f in p.factores_semana)
    return [
        Politica('A. Producción fija',
                 f'Hornear {p.horneado_fijo} panes todos los días, sin ajustar la demanda.',
                 (p.horneado_fijo,) * 7),
        Politica('B. Demanda promedio',
                 'Hornear el promedio esperado según el día de la semana.',
                 media_dias),
        Politica('C. Newsvendor global',
                 f'Hornear {q_global} panes cada día usando el fractil crítico.',
                 (q_global,) * 7),
        Politica('D. Newsvendor semanal',
                 'Hornear una cantidad óptima distinta para cada día de la semana.',
                 q_dias),
    ]
