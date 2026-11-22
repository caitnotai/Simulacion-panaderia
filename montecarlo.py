"""MÓDULO 5. Réplicas Monte Carlo, IC 95%, comparación pareada, estrés.

Cada política recibe las mismas demandas en la misma réplica.
NO reentrenamos las políticas usando demandas futuras de evaluación.
"""
from collections.abc import Sequence
import numpy as np
import pandas as pd
from parametros import ParametrosCaso
from aleatoriedad import generar_escenario
from politicas import Politica, construir_politicas
from simulador import simular


METRICAS = [
    'ganancia', 'ingresos', 'costo_produccion', 'costo_desecho',
    'costo_fijo', 'penalizacion_faltante', 'panes_horneados',
    'panes_vendidos', 'sobrantes', 'ventas_perdidas', 'demanda_total',
    'nivel_servicio', 'tasa_desperdicio', 'dias_con_faltante',
    'dias_con_desperdicio',
]


def correr_montecarlo(p: ParametrosCaso, politicas: Sequence[Politica] | None = None,
                      multiplicador_demanda: float = 1.0,
                      guardar_ejemplo: bool = True):
    p.validar()
    politicas = list(politicas or construir_politicas(p))
    filas = {pol.nombre: [] for pol in politicas}
    ejemplos = {}
    for replica in range(p.replicas):
        escenario = generar_escenario(p, replica, multiplicador_demanda)
        for pol in politicas:
            resultado = simular(p, escenario, pol,
                                guardar_detalles=(guardar_ejemplo and replica == 0))
            filas[pol.nombre].append({'replica': replica, **resultado.como_dict()})
            if replica == 0 and guardar_ejemplo:
                ejemplos[pol.nombre] = resultado.detalles
    return {nom: pd.DataFrame(registros).set_index('replica') for nom, registros in filas.items()}, ejemplos


def tabla_resumen(resultados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    lista = []
    for nombre, df in resultados.items():
        n = len(df)
        desvest = df['ganancia'].std(ddof=1) if n > 1 else 0.0
        semiancho = 1.96 * desvest / np.sqrt(n)  # IC normal aproximado
        lista.append({
            'Política': nombre,
            'Ganancia media (M COP)': df['ganancia'].mean() / 1e6,
            'IC 95% inferior (M COP)': (df['ganancia'].mean() - semiancho) / 1e6,
            'IC 95% superior (M COP)': (df['ganancia'].mean() + semiancho) / 1e6,
            'Ingresos (M COP)': df['ingresos'].mean() / 1e6,
            'Costo producción (M COP)': df['costo_produccion'].mean() / 1e6,
            'Costo desecho (M COP)': df['costo_desecho'].mean() / 1e6,
            'Panes horneados': df['panes_horneados'].mean(),
            'Panes vendidos': df['panes_vendidos'].mean(),
            'Panes desechados': df['sobrantes'].mean(),
            'Ventas perdidas': df['ventas_perdidas'].mean(),
            'Fill rate (%)': 100 * df['panes_vendidos'].sum() / max(1, df['demanda_total'].sum()),
            'Desperdicio (%)': 100 * df['sobrantes'].sum() / max(1, df['panes_horneados'].sum()),
            'Prob. año con pérdida (%)': 100 * (df['ganancia'] < 0).mean(),
            'Días con faltante': df['dias_con_faltante'].mean(),
        })
    return pd.DataFrame(lista).set_index('Política').sort_values('Ganancia media (M COP)', ascending=False)


def comparacion_pareada(resultados: dict[str, pd.DataFrame], mejor: str) -> pd.DataFrame:
    """Diferencia mejor - rival usando la MISMA réplica de demanda."""
    filas = []
    base = resultados[mejor]['ganancia']
    for nombre, df in resultados.items():
        if nombre == mejor:
            continue
        diferencias = (base - df['ganancia']).dropna()
        promedio = diferencias.mean()
        semiancho = (1.96 * diferencias.std(ddof=1) / np.sqrt(len(diferencias))
                     if len(diferencias) > 1 else 0.0)
        filas.append({
            'Comparada con': nombre,
            'Ventaja media de la mejor (M COP)': promedio / 1e6,
            'IC 95% inferior (M COP)': (promedio - semiancho) / 1e6,
            'IC 95% superior (M COP)': (promedio + semiancho) / 1e6,
            'P(mejor gana en una réplica) (%)': 100 * (diferencias > 0).mean(),
        })
    return pd.DataFrame(filas).set_index('Comparada con')


def analizar_sensibilidad(p: ParametrosCaso, replicas: int = 150) -> pd.DataFrame:
    """Comprueba cuánto conviene hornear si aumenta el costo de desechar pan.
    En cada caso las políticas se recalculan con los costos conocidos.
    """
    filas = []
    for costo in (0, 150, 300, 600, 1000):
        ps = p.con_cambios(costo_desecho=float(costo), replicas=min(replicas, p.replicas))
        pols = construir_politicas(ps)
        res, _ = correr_montecarlo(ps, pols, guardar_ejemplo=False)
        resumen = tabla_resumen(res)
        mejor = resumen.index[0]
        filas.append({
            'Costo desecho por pan (COP)': costo,
            'Fractil crítico': ps.fractil_critico,
            'Q Newsvendor global': pols[2].horneado_semana[0],
            'Q Newsvendor sábado': pols[3].horneado_semana[5],
            'Mejor política': mejor,
            'Ganancia mejor (M COP)': resumen.iloc[0]['Ganancia media (M COP)'],
            'Desperdicio mejor (%)': resumen.iloc[0]['Desperdicio (%)'],
        })
    return pd.DataFrame(filas)
