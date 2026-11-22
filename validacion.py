"""MÓDULO 7. Pruebas de balance, costos y decisión Newsvendor."""
from aleatoriedad import generar_escenario
from parametros import ParametrosCaso
from politicas import Politica, cantidad_optima, construir_politicas
from simulador import simular


def correr_validacion():
    # Caso determinista: 100 panes solicitados CADA día.
    p = ParametrosCaso().con_cambios(
        demanda_media=100, demanda_desviacion=0,
        factores_semana=(1,) * 7, dias_simulacion=7, replicas=2,
        costo_fijo_diario=10000, costo_desecho=100,
    )
    e = generar_escenario(p, 0)
    assert (e.demanda == 100).all()

    # Sobraproducción: se hornean 130 y se venden solo 100.
    pol130 = Politica('Exceso', 'Prueba', (130,) * 7)
    r = simular(p, e, pol130, True)
    assert r.panes_horneados == 910
    assert r.panes_vendidos == 700 and r.sobrantes == 210
    assert r.ventas_perdidas == 0
    esperado = 7 * (100 * p.precio_venta - 130 * p.costo_produccion
                    - 30 * p.costo_desecho - p.costo_fijo_diario)
    assert abs(r.ganancia - esperado) < 1e-9

    # Subproducción: se hacen 50, la otra mitad es venta perdida.
    pol50 = Politica('Defecto', 'Prueba', (50,) * 7)
    r2 = simular(p, e, pol50, True)
    assert r2.panes_vendidos == 350 and r2.ventas_perdidas == 350
    assert r2.sobrantes == 0
    for resultado in (r, r2):
        assert resultado.panes_horneados == resultado.panes_vendidos + resultado.sobrantes
        assert resultado.demanda_total == resultado.panes_vendidos + resultado.ventas_perdidas
        assert (resultado.detalles['Inventario final'] == 0).all()
        assert (resultado.detalles['Horneados'] == resultado.detalles['Vendidos']
                + resultado.detalles['Sobrantes (desechados)']).all()

    # Sin incertidumbre la cantidad óptima tiene que ser exactamente 100.
    assert cantidad_optima(p) == 100
    assert all(cantidad_optima(p, d) == 100 for d in range(7))

    # En condiciones inciertas un Q óptimo satisface la condición de CDF.
    from politicas import _cdf_redondeada
    p3 = ParametrosCaso()
    q = cantidad_optima(p3, 5)
    f = p3.factores_semana[5]
    mu, sigma = p3.demanda_media * f, p3.demanda_desviacion * f
    assert _cdf_redondeada(q, mu, sigma) >= p3.fractil_critico
    assert q == 0 or _cdf_redondeada(q - 1, mu, sigma) < p3.fractil_critico
    assert len(construir_politicas(p3)) == 4
    print('VERIFICACIÓN EXITOSA: balances, ganancia, demanda, inventario cero y Newsvendor.')
    return True


if __name__ == '__main__':
    correr_validacion()
