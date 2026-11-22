# Simulación de inventario — Panadería El Buen Horno

**Caso:** una panadería ficticia debe decidir **cuántos panes hornear cada día**. El pan es perecedero y al finalizar la jornada cualquier sobrante se descarta. Si la demanda supera lo horneado, los clientes no atendidos representan **ventas perdidas**. Se quiere **maximizar la ganancia esperada**, no minimizar el costo de inventario de una bodega.

> Los valores del proyecto son supuestos didácticos en pesos colombianos (COP), no datos reales de una panadería.

## 1. Ejecutar el proyecto

Instala Python 3.10 o superior, abre una terminal dentro de esta carpeta y ejecuta:

```bash
pip install -r requirements.txt
python main.py
```

Alternativas:

```bash
python main.py --replicas 100   # prueba rápida
python validacion.py           # comprueba los balances y las fórmulas
streamlit run app.py           # interfaz para presentar el trabajo
```

`main.py` guarda tablas CSV y siete gráficas PNG en `resultados/`. `app.py` permite cambiar los parámetros de la simulación en vivo.

## 2. Planteamiento del problema

Al empezar cada mañana, el dueño decide **Q = número de panes a hornear**. La demanda del día **D** no se conoce todavía. Cuando llega el cliente:

- Se venden `min(Q, D)` panes.
- Sobran y se desechan `max(Q - D, 0)` panes.
- Se pierden `max(D - Q, 0)` ventas.
- El inventario del día siguiente vuelve a **cero**. No se conservan panes del día anterior.

**Pregunta:** ¿cuál política de horneado produce mayor ganancia con un riesgo aceptable de desperdicio y faltantes?

## 3. Estructura (equivalente a la del simulador de importadora)

| Archivo | Propósito |
|---|---|
| `parametros.py` | Entradas, costos, variabilidad, demanda semanal y réplicas |
| `aleatoriedad.py` | Genera demanda diaria Normal truncada/redondeada, con números aleatorios comunes |
| `politicas.py` | Decide Q para cada día y calcula el óptimo Newsvendor |
| `simulador.py` | Motor diario: hornear → vender → botar sobrantes → contar pérdidas → ganancia |
| `montecarlo.py` | Réplicas, IC 95%, comparación pareada, sensibilidad y estrés |
| `graficas.py` | Siete gráficas de resultados |
| `validacion.py` | Pruebas de que el modelo funciona |
| `main.py` | Corre los experimentos y exporta datos |
| `app.py` | Panel interactivo en Streamlit |

## 4. Datos del caso (supuestos)

| Parámetro | Valor base |
|---|---:|
| Producto | Pan artesanal individual |
| Demanda base | 110 panes/día (antes del factor semanal) |
| Desviación de demanda | 24 panes/día |
| Factores lunes a domingo | 0,85; 0,90; 0,95; 1,00; 1,10; 1,35; 1,20 |
| Precio por unidad (P) | $3.500 COP |
| Costo variable de producción (C) | $1.500 COP |
| Costo extra por descartar (G) | $150 COP |
| Valor recuperado de sobrante (S) | $0 COP |
| Penalización reputacional extra por faltante | $0 COP |
| Costo fijo diario (F) | $65.000 COP |
| Producción fija de la política A | 110 panes/día |
| Horizonte | 365 días |
| Réplicas Monte Carlo | 500 años independientes |
| Semilla | 2026 |

**Importante:** los costos fijos afectan el resultado financiero, pero no cambian la cantidad óptima, siempre que no dependan de Q. Los costos de producción se pagan por **todo lo horneado**, no solo por lo vendido.

## 5. Fórmulas del modelo

**Ventas:** `V = min(Q, D)`

**Desechados:** `E = max(Q - D, 0)`

**Ventas perdidas:** `L = max(D - Q, 0)`

**Ganancia del día:**

```text
Ganancia = P·V − C·Q − G·E + S·E − F − penalizacion·L
```

La pérdida de margen por ventas no realizadas **ya está incluida en los menores ingresos**; por eso la penalización por faltante se deja en cero inicialmente. Si se usa un valor positivo, representa un costo **adicional**, como pérdida estimada de clientes futuros, no el margen que ya se dejó de ganar.

### Newsvendor: cantidad óptima

Para un pan adicional, hay dos riesgos marginales:

```text
Costo de excedente (Co) = costo de producción + costo de desecho − valor recuperado
Costo de faltante  (Cu) = precio − costo de producción + penalización adicional
Fractil crítico (α) = Cu / (Cu + Co)
```

Con los números base:

```text
Cu = 3500 − 1500 + 0 = 2000 COP
Co = 1500 + 150 − 0 = 1650 COP
α  = 2000 / (2000 + 1650) ≈ 54,79%
```

Se busca la **menor cantidad entera Q** tal que `P(D <= Q) >= α`. Eso implica que hacer un pan adicional solo compensa si la probabilidad de venderlo justifica su costo de desperdicio. El programa usa la distribución redondeada y truncada en cero, e integra correctamente la mezcla de los días de la semana; no emplea la demanda futura realizada para optimizar.

## 6. Políticas comparadas

| Política | Decisión antes de abrir |
|---|---|
| **A. Producción fija** | Hornear siempre 110 panes, sin importar el día |
| **B. Demanda promedio** | Hornear la media prevista de cada día de la semana |
| **C. Newsvendor global** | Elegir un Q óptimo único para toda la semana, con su distribución combinada |
| **D. Newsvendor semanal** | Calcular un Q óptimo para cada día de la semana |

La política D puede aprovechar más información que C porque considera el patrón semanal. En general una Q por día puede superar o empatar a una Q única en **ganancia esperada**, siempre que el modelo supuesto de demanda sea correcto.

## 7. Secuencia del simulador

```text
Para cada réplica r:
  generar las 365 demandas de ese año
  para cada política (se usa la MISMA secuencia de demanda):
    para cada día t:
      determinar el Q planeado según el día
      D = demanda que se presenta ese día
      ventas = min(Q, D)
      desperdicio = max(Q - D, 0)
      perdidas = max(D - Q, 0)
      calcular ingresos, costos y ganancia
      poner inventario restante = 0
  acumular métricas anuales

Al finalizar todas las réplicas:
  promediar ganancias y cantidades
  obtener intervalos de confianza y comparaciones pareadas
  calcular sensibilidad y prueba de estrés
  exportar PNG y CSV
```

### Indicadores clave

- **Ganancia anual promedio:** total esperado de COP ganados tras cubrir costos variables, fijos y de desperdicio.
- **Fill rate:** `panes vendidos / panes demandados`.
- **Tasa de desperdicio:** `panes desechados / panes horneados`.
- **Ventas perdidas:** clientes que pidieron panes y no pudieron comprarlos.
- **Riesgo de pérdida:** porcentaje de años simulados en los que la ganancia fue negativa.
- **IC al 95%:** aproximación normal de la incertidumbre del estimador de ganancia media, calculada a partir de réplicas independientes.

## 8. Experimentos

1. **Comparación base:** se simulan los mismos 365 días de demanda para cada política, repetidos durante 500 réplicas independientes.
2. **Comparación pareada:** se compara la diferencia de ganancia entre la mejor y cada otra política, usando la misma réplica de demanda.
3. **Sensibilidad:** se modifica el costo extra de desechar un pan de $0 a $1.000, recalculando las políticas para cada costo.
4. **Pico no previsto:** la demanda aumenta 30% sin modificar las decisiones calculadas inicialmente.
5. **Replanificación:** después de conocer el incremento, se actualiza el pronóstico y se calculan nuevos Q.

**Nota sobre el experimento 5:** el generador utiliza la misma distribución de demanda elevada en ambos experimentos y conserva las semillas. Por diferencias de redondeo de coma flotante, los valores diarios pueden no coincidir exactamente; la diferencia importante es el pronóstico utilizado para tomar la decisión.

## 9. Validación y limitaciones

`validacion.py` comprueba: balances de pan (horneado = vendido + descartado), demanda (demandado = vendido + perdido), inventario final cero, ganancia en un caso determinista, y condición del fractil óptimo.

**Supuestos:** un único tipo de pan, producción terminada antes de la demanda, precio y costos constantes, sin límite de capacidad de horno, sin inventario entre días, demanda independiente entre días y mayor movimiento en fin de semana. No se modela clima, festivos, devoluciones, cierre del establecimiento ni demanda inducida por promociones. Para aplicarlo a una panadería real se debe reemplazar la distribución supuesta con ventas **y una estimación de ventas perdidas**, ya que las ventas observadas pueden estar limitadas por el stock.

## 10. Recomendación para presentar

Explica primero el dilema de hornear demasiado o demasiado poco; muestra las políticas; describe que a cada una le toca **el mismo año**; compara ganancia, desperdicio y faltantes; termina mostrando cómo cambia la decisión cuando se ajustan los costos o aumenta inesperadamente la demanda. Las conclusiones numéricas se calculan con `main.py` y se guardan en `resultados/`.
