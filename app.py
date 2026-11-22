"""Interfaz interactiva: streamlit run app.py.

La aplicación reutiliza los mismos módulos que el programa de consola.
"""
import streamlit as st
import pandas as pd
from parametros import ParametrosCaso, DIAS_SEMANA
from politicas import construir_politicas
from montecarlo import correr_montecarlo, tabla_resumen, comparacion_pareada

st.set_page_config(page_title='El Buen Horno | Newsvendor', page_icon='🥖', layout='wide')
st.title('🥖 Panadería El Buen Horno')
st.caption('Simulación Monte Carlo · Newsvendor para un producto perecedero · Datos ficticios en COP')
st.info('Cada mañana se hornea una cantidad Q. Los panes que no se venden se desechan y los clientes sin pan representan ventas perdidas.')

with st.sidebar:
    st.header('Parámetros de la panadería')
    st.caption('Cambia las suposiciones y compara las estrategias.')
    with st.expander('Demanda', expanded=True):
        media = st.slider('Demanda promedio base (panes/día)', 20, 300, 110, 5)
        desviacion = st.slider('Variabilidad de demanda (σ)', 0, 100, 24, 2)
        fin_semana = st.checkbox('Mayor demanda el fin de semana', value=True)
        pico = st.checkbox('Simular un pico inesperado (+30%)', value=False)
    with st.expander('Costos (COP)', expanded=True):
        precio = st.number_input('Precio por pan', 1000, 20000, 3500, 100, key='precio')
        # Un nuevo máximo cambia la identidad del widget aunque conserve su clave.
        costo_maximo = int(precio) - 1
        st.session_state.costo = min(st.session_state.get('costo', 1500), costo_maximo)
        costo = st.number_input('Costo de hacer un pan', min_value=100, max_value=costo_maximo,
                                step=100, key='costo')
        desecho = st.number_input('Costo extra de botar un pan', 0, 5000, 150, 50)
        fijo = st.number_input('Gastos fijos por día', 0, 500000, 65000, 5000)
        rescate_maximo = int(costo) - 1
        st.session_state.rescate = min(st.session_state.get('rescate', 0), rescate_maximo)
        rescate = st.number_input('Valor recuperado por pan sobrante', min_value=0,
                                  max_value=rescate_maximo, step=50, key='rescate')
        penalizacion = st.number_input('Penalización adicional por venta perdida', 0, 5000, 0, 100)
    with st.expander('Experimento', expanded=False):
        fijo_q = st.slider('Panes diarios: política fija A', 0, 400, 110, 5)
        dias = st.slider('Días de simulación', 28, 365, 365, 7)
        replicas = st.select_slider('Réplicas Monte Carlo', [50, 100, 200, 500, 1000], value=200)
        semilla = st.number_input('Semilla aleatoria', 0, 999999, 2026)

factores = (0.85, 0.90, 0.95, 1.0, 1.10, 1.35, 1.20) if fin_semana else (1,) * 7
try:
    p = ParametrosCaso().con_cambios(
        demanda_media=float(media), demanda_desviacion=float(desviacion),
        factores_semana=tuple(factores), precio_venta=float(precio),
        costo_produccion=float(costo), costo_desecho=float(desecho),
        costo_fijo_diario=float(fijo), valor_rescate=float(rescate),
        penalizacion_faltante=float(penalizacion), horneado_fijo=int(fijo_q),
        dias_simulacion=int(dias), replicas=int(replicas), semilla=int(semilla),
    )
except ValueError as e:
    st.error(f'Parámetros inválidos: {e}')
    st.stop()
politicas = construir_politicas(p)

@st.cache_data(show_spinner=False)
def calcular(p, politicas, pico):
    resultados, ejemplos = correr_montecarlo(p, politicas,
                                               multiplicador_demanda=1.3 if pico else 1.0)
    resumen = tabla_resumen(resultados)
    return resultados, ejemplos, resumen

with st.spinner('Calculando escenarios...'):
    resultados, ejemplos, resumen = calcular(p, politicas, pico)
mejor = resumen.index[0]
fila = resumen.iloc[0]
if pico:
    st.warning('Pico de demanda activo: las políticas se planificaron SIN conocer el incremento del 30%.')

m1, m2, m3, m4 = st.columns(4)
m1.metric('Fractil crítico', f'{p.fractil_critico:.1%}', help='Cu / (Cu + Co)')
m2.metric('Mayor ganancia esperada', f'${fila["Ganancia media (M COP)"]:.2f} M')
m3.metric('Mejor política', mejor.split('.')[0])
m4.metric('Ventas atendidas', f'{fila["Fill rate (%)"]:.1f}%')
st.subheader('¿Cuánto hornear según el día?')
tabla_q = pd.DataFrame({'Día': DIAS_SEMANA})
for pol in politicas:
    tabla_q[pol.nombre] = pol.horneado_semana
st.dataframe(tabla_q, width='stretch', hide_index=True)
st.caption('El horneado se decide antes de observar las ventas del día, nunca después.')

tab1, tab2, tab3, tab4 = st.tabs(['Ganancias', 'Un mes de ejemplo', 'Desperdicio y riesgo', 'Resultados completos'])
with tab1:
    st.subheader('Ganancia esperada por política')
    st.bar_chart(resumen['Ganancia media (M COP)'])
    st.write('Intervalos de confianza aproximados al 95%:')
    st.dataframe(resumen[['Ganancia media (M COP)', 'IC 95% inferior (M COP)',
                          'IC 95% superior (M COP)']].round(2), width='stretch')
    st.write('Comparación pareada (mismos días y mismas demandas para cada política):')
    st.dataframe(comparacion_pareada(resultados, mejor).round(3), width='stretch')
with tab2:
    opcion = st.selectbox('Política para observar', list(ejemplos), index=list(ejemplos).index(mejor))
    df = ejemplos[opcion]
    st.line_chart(df.iloc[:28].set_index('Día')[['Demanda', 'Horneados', 'Vendidos']])
    st.dataframe(df.iloc[:28], width='stretch', hide_index=True)
with tab3:
    st.dataframe(resumen[['Panes desechados', 'Ventas perdidas', 'Desperdicio (%)',
                          'Fill rate (%)', 'Prob. año con pérdida (%)']].round(2), width='stretch')
    st.scatter_chart(resumen.reset_index(), x='Panes desechados', y='Ventas perdidas', color='Política')
    st.caption('Desperdicio = sobrantes / horneados. Fill rate = vendidos / demandados.')
with tab4:
    st.dataframe(resumen.round(2), width='stretch')
    st.download_button('Descargar resumen CSV', resumen.to_csv().encode('utf-8-sig'),
                       'resumen_panaderia.csv', 'text/csv')
    st.download_button('Descargar ejemplo diario CSV', ejemplos[mejor].to_csv(index=False).encode('utf-8-sig'),
                       'ejemplo_panaderia.csv', 'text/csv')
st.caption('El modelo considera un único tipo de pan, producción diaria y valor de rescate cero por defecto.')
