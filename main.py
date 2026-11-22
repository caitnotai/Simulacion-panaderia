"""Punto de entrada: comparación, validación, sensibilidad y siete figuras.

    python main.py
    python main.py --replicas 200
    python main.py --sin-validacion
    streamlit run app.py
"""
import argparse
from pathlib import Path
import pandas as pd
import graficas
from montecarlo import (analizar_sensibilidad, comparacion_pareada,
                        correr_montecarlo, tabla_resumen)
from parametros import DIAS_SEMANA, ParametrosCaso, CAMBIOS_PICO_DEMANDA
from politicas import construir_politicas
from validacion import correr_validacion

RESULTADOS = Path(__file__).parent / 'resultados'


def titulo(s):
    print('\n' + '=' * 85 + '\n' + s + '\n' + '=' * 85)


def main():
    parser = argparse.ArgumentParser(description='Panadería — problema Newsvendor')
    parser.add_argument('--replicas', type=int, default=500)
    parser.add_argument('--sin-validacion', action='store_true')
    args = parser.parse_args()

    p = ParametrosCaso().con_cambios(replicas=args.replicas)
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    politicas = construir_politicas(p)

    titulo('PANADERÍA EL BUEN HORNO | ¿CUÁNTOS PANES HORNEAR CADA DÍA?')
    print('Modelo de un producto perecedero. Datos ficticios, valores en COP.')
    print(f'Demanda base: media {p.demanda_media:.0f}, desviación {p.demanda_desviacion:.0f} panes/día.')
    print(f'Precio ${p.precio_venta:,.0f} | Costo producción ${p.costo_produccion:,.0f} | '
          f'Desecho ${p.costo_desecho:,.0f} | Costo fijo diario ${p.costo_fijo_diario:,.0f}')
    print(f'Costo por exceso Co = ${p.costo_exceso:,.0f} | '
          f'Costo por defecto Cu = ${p.costo_defecto:,.0f}')
    print(f'Fractil crítico Cu/(Cu+Co) = {p.fractil_critico:.2%}')
    print('\nHORNEADO PLANIFICADO (Lunes a Domingo)')
    print('Días:', ', '.join(DIAS_SEMANA))
    for pol in politicas:
        print(f' {pol.nombre:28} -> {list(pol.horneado_semana)}')

    if not args.sin_validacion:
        titulo('VALIDACIÓN DEL MODELO')
        correr_validacion()

    titulo(f'EXPERIMENTO 1 | {p.replicas} RÉPLICAS DE {p.dias_simulacion} DÍAS')
    resultados, ejemplos = correr_montecarlo(p, politicas)
    resumen = tabla_resumen(resultados)
    print(resumen.round(2).to_string())
    mejor = resumen.index[0]
    print(f'\nMejor según ganancia media: {mejor}')

    titulo('EXPERIMENTO 2 | COMPARACIÓN PAREADA')
    pareada = comparacion_pareada(resultados, mejor)
    print(pareada.round(3).to_string())

    titulo('EXPERIMENTO 3 | IMPACTO DEL COSTO DE DESECHO')
    sensibilidad = analizar_sensibilidad(p)
    print(sensibilidad.round(3).to_string(index=False))

    titulo('EXPERIMENTO 4 | DEMANDA 30% SUPERIOR A LA PREVISTA')
    # Las cuatro políticas se dejan iguales: nadie sabía que llegaba el pico.
    resultados_pico, _ = correr_montecarlo(
        p, politicas, guardar_ejemplo=False, **CAMBIOS_PICO_DEMANDA)
    resumen_pico = tabla_resumen(resultados_pico)
    print(resumen_pico.round(2).to_string())

    titulo('EXPERIMENTO 5 | REPLANIFICAR AL CONOCER EL PICO')
    # Se recalcula la política con un pronóstico actualizado de demanda.
    p_ajustado = p.con_cambios(demanda_media=p.demanda_media * 1.30,
                              demanda_desviacion=p.demanda_desviacion * 1.30)
    politicas_ajustadas = construir_politicas(p_ajustado)
    resultados_ajustados, _ = correr_montecarlo(p_ajustado, politicas_ajustadas,
                                               guardar_ejemplo=False)
    resumen_ajustado = tabla_resumen(resultados_ajustados)
    print(resumen_ajustado.round(2).to_string())
    print('Nota: mismas semillas y distribución de demanda de pico; la política A sigue fija.')

    # CSV para análisis y demostración. Tienen codificación Excel compatible.
    resumen.round(4).to_csv(RESULTADOS / 'resumen_politicas.csv', encoding='utf-8-sig')
    pareada.round(4).to_csv(RESULTADOS / 'comparacion_pareada.csv', encoding='utf-8-sig')
    sensibilidad.round(4).to_csv(RESULTADOS / 'sensibilidad_desecho.csv', index=False, encoding='utf-8-sig')
    resumen_pico.round(4).to_csv(RESULTADOS / 'resumen_pico_demanda.csv', encoding='utf-8-sig')
    resumen_ajustado.round(4).to_csv(RESULTADOS / 'resumen_pico_replanificado.csv', encoding='utf-8-sig')
    pd.concat(resultados, names=['politica', 'replica']).to_csv(RESULTADOS / 'detalle_replicas.csv', encoding='utf-8-sig')
    for nombre, df in ejemplos.items():
        etiqueta = nombre.split('.')[0]
        df.to_csv(RESULTADOS / f'ejemplo_365_dias_{etiqueta}.csv', index=False, encoding='utf-8-sig')

    rutas = [
        graficas.grafica_demanda(ejemplos, RESULTADOS),
        graficas.grafica_horneado(politicas, RESULTADOS),
        graficas.grafica_ganancias(resumen, RESULTADOS),
        graficas.grafica_riesgo(resultados, RESULTADOS),
        graficas.grafica_desperdicio_faltantes(resumen, RESULTADOS),
        graficas.grafica_pico(resumen, resumen_pico, RESULTADOS),
        graficas.grafica_ejemplo(ejemplos, mejor, RESULTADOS),
    ]
    titulo('CONCLUSIONES DEL EXPERIMENTO')
    fila = resumen.loc[mejor]
    print(f'1. Mayor ganancia esperada: {mejor}: ${fila["Ganancia media (M COP)"]:.2f} millones.')
    print(f'2. Nivel de servicio de la ganadora: {fila["Fill rate (%)"]:.1f}%.')
    print(f'3. Desperdicio: {fila["Panes desechados"]:,.0f} panes por año en promedio.')
    print(f'4. Ventas perdidas: {fila["Ventas perdidas"]:,.0f} panes por año en promedio.')
    print(f'5. Ante un pico inesperado, la mejor política es: {resumen_pico.index[0]}.')
    print(f'6. Si se actualiza el pronóstico, la mejor política es: {resumen_ajustado.index[0]}.')
    print('\nLos resultados se calcularon con DEMANDA SIMULADA, no ventas reales.')
    print(f'Archivos generados en: {RESULTADOS}')
    for ruta in rutas:
        print(f' - {ruta.name}')


if __name__ == '__main__':
    main()
