"""MÓDULO 6. Figuras PNG para presentación y panel Streamlit."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from parametros import DIAS_SEMANA

COLORES_POLITICA = {
    'A': '#C96B45',
    'B': '#DF9D50',
    'C': '#7F9E84',
    'D': '#536F86',
}
COLOR_DEMANDA = '#5C6773'


def _color_politica(nombre):
    return COLORES_POLITICA.get(nombre.split('.', 1)[0], '#757575')


def _configurar():
    plt.rcParams.update({
        'figure.figsize': (11.5, 6), 'figure.dpi': 125,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.alpha': 0.16, 'font.size': 10,
    })


def _guardar(fig, carpeta, nombre):
    ruta = Path(carpeta) / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=2)
    fig.savefig(ruta, dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return ruta


def grafica_demanda(ejemplos, carpeta):
    _configurar()
    df = next(iter(ejemplos.values()))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(df['Día'].iloc[:45], df['Demanda'].iloc[:45], color=COLOR_DEMANDA, linewidth=2)
    axes[0].set(title='Demanda aleatoria: primeros 45 días', xlabel='Día', ylabel='Panes solicitados')
    axes[1].hist(df['Demanda'], bins=24, color=COLOR_DEMANDA, edgecolor='white')
    axes[1].set(title='Distribución de la demanda del año', xlabel='Demanda (panes/día)', ylabel='Frecuencia')
    return _guardar(fig, carpeta, '01_demanda_aleatoria.png')


def grafica_horneado(politicas, carpeta):
    _configurar()
    fig, ax = plt.subplots()
    x = np.arange(7)
    ancho = .2
    for i, pol in enumerate(politicas):
        ax.bar(x + (i - 1.5) * ancho, pol.horneado_semana, width=ancho,
               label=pol.nombre, color=_color_politica(pol.nombre))
    ax.set(xticks=x, xticklabels=DIAS_SEMANA, ylabel='Panes horneados',
           title='Cantidad de horneado según la política y el día')
    ax.legend(fontsize=8)
    return _guardar(fig, carpeta, '02_horneado_por_dia.png')


def grafica_ganancias(resumen: pd.DataFrame, carpeta):
    _configurar()
    nombres = list(resumen.index)
    fig, ax = plt.subplots()
    medias = resumen['Ganancia media (M COP)'].to_numpy()
    inferior = (resumen['Ganancia media (M COP)'] - resumen['IC 95% inferior (M COP)']).to_numpy()
    superior = (resumen['IC 95% superior (M COP)'] - resumen['Ganancia media (M COP)']).to_numpy()
    ax.barh(nombres[::-1], medias[::-1], xerr=np.array([inferior[::-1], superior[::-1]]),
            color=[_color_politica(nombre) for nombre in reversed(nombres)], capsize=4)
    ax.set(xlabel='Ganancia anual esperada (millones COP)',
           title='Comparación de ganancias (barras de error: IC 95%)')
    for i, val in enumerate(medias[::-1]):
        ax.annotate(f'{val:.1f} M', (val, i), xytext=(4 if val >= 0 else -4, 0),
                    textcoords='offset points', va='center',
                    ha='left' if val >= 0 else 'right')
    return _guardar(fig, carpeta, '03_ganancias_comparadas.png')


def grafica_riesgo(resultados, carpeta):
    _configurar()
    fig, ax = plt.subplots()
    for nombre, df in resultados.items():
        ax.hist(df['ganancia'] / 1e6, bins=25, alpha=0.43, label=nombre,
                color=_color_politica(nombre), density=True)
    ax.set(title='Riesgo: distribución de ganancias anuales',
           xlabel='Ganancia (millones COP)', ylabel='Densidad')
    ax.legend(fontsize=8)
    return _guardar(fig, carpeta, '04_distribucion_ganancias.png')


def grafica_desperdicio_faltantes(resumen, carpeta):
    _configurar()
    fig, ax = plt.subplots()
    for nombre, f in resumen.iterrows():
        ax.scatter(f['Panes desechados'], f['Ventas perdidas'], s=220,
                   color=_color_politica(nombre), label=nombre, alpha=.9)
        ax.annotate(nombre[:2], (f['Panes desechados'], f['Ventas perdidas']),
                    xytext=(8, 5), textcoords='offset points')
    ax.set(title='El dilema: desperdiciar pan o perder ventas',
           xlabel='Panes desechados al año', ylabel='Ventas perdidas al año')
    ax.legend(fontsize=8)
    return _guardar(fig, carpeta, '05_desperdicio_vs_faltantes.png')


def grafica_pico(pico, ajustado, carpeta):
    _configurar()
    nombres = list(pico.index)
    sin_replanificar = pico.loc[nombres, 'Ganancia media (M COP)'].to_numpy()
    replanificado = ajustado.loc[nombres, 'Ganancia media (M COP)'].to_numpy()
    colores = [_color_politica(nombre) for nombre in nombres]
    x = np.arange(len(nombres))
    fig, ax = plt.subplots()
    ax.bar(x - .19, sin_replanificar, .38, color='white', edgecolor=colores, hatch='///')
    ax.bar(x + .19, replanificado, .38, color=colores)
    for posicion, sin_ajuste, con_ajuste in zip(x, sin_replanificar, replanificado):
        ax.annotate(f'{con_ajuste - sin_ajuste:+.2f} M', (posicion, max(sin_ajuste, con_ajuste)),
                    xytext=(0, 6), textcoords='offset points', ha='center', va='bottom')
    ax.set(xticks=x, xticklabels=[n.split('.')[0] for n in nombres],
           xlabel='Política', ylabel='Ganancia anual (millones COP)',
           title='Pico de demanda (+30%)\nCosto de oportunidad de no replanificar por política')
    ax.margins(y=.12)
    ax.legend(handles=[
        Patch(facecolor='white', edgecolor='#555555', hatch='///', label='Sin replanificar (exp. 4)'),
        Patch(facecolor='#555555', label='Replanificado (exp. 5)'),
    ], loc='upper center', bbox_to_anchor=(.5, -.13), ncols=2)
    return _guardar(fig, carpeta, '06_pico_demanda.png')


def grafica_ejemplo(ejemplos, mejor, carpeta):
    _configurar()
    df = ejemplos[mejor].iloc[:28]
    fig, ax = plt.subplots()
    ax.plot(df['Día'], df['Demanda'], '-o', label='Demanda real', color=COLOR_DEMANDA, ms=4)
    ax.step(df['Día'], df['Horneados'], where='mid', label='Horneado', color=_color_politica(mejor), lw=2)
    ax.fill_between(df['Día'].to_numpy(), df['Demanda'].to_numpy(), df['Horneados'].to_numpy(),
                    where=df['Demanda'].to_numpy() > df['Horneados'].to_numpy(),
                    color='#C0525B', alpha=.15, label='Ventas perdidas')
    ax.set(xlabel='Día', ylabel='Unidades',
           title=f'Primeros 28 días: {mejor}')
    ax.legend()
    return _guardar(fig, carpeta, '07_ejemplo_28_dias.png')
