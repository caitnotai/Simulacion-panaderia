"""Pruebas de la interfaz con Streamlit AppTest."""
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def por_etiqueta(controles, etiqueta):
    return next(control for control in controles if control.label == etiqueta)


class PruebasApp(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(Path(__file__).with_name('app.py'), default_timeout=15).run()
        self.verificar_panel()

    def verificar_panel(self):
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(list(self.app.error), [])
        self.assertEqual(len(self.app.metric), 4)

    def test_carga_inicial(self):
        self.assertEqual(self.app.number_input(key='precio').value, 3500)
        self.assertEqual(self.app.number_input(key='costo').value, 1500)
        self.assertEqual(self.app.number_input(key='rescate').value, 0)

    def test_pico_de_demanda(self):
        por_etiqueta(self.app.checkbox, 'Simular un pico inesperado (+30%)').check().run()
        self.verificar_panel()
        self.assertIn('Pico de demanda activo', self.app.warning[0].value)

    def test_desviacion_cero(self):
        por_etiqueta(self.app.slider, 'Variabilidad de demanda (σ)').set_value(0).run()
        self.verificar_panel()
        tabla = self.app.tabs[0].dataframe[0].value
        self.assertTrue((tabla['Ganancia media (M COP)'] == tabla['IC 95% inferior (M COP)']).all())
        self.assertTrue((tabla['Ganancia media (M COP)'] == tabla['IC 95% superior (M COP)']).all())

    def test_rescate_maximo_sin_costo_de_desecho(self):
        por_etiqueta(self.app.number_input, 'Costo extra de botar un pan').set_value(0)
        rescate = self.app.number_input(key='rescate')
        self.assertEqual(rescate.max, 1499)
        rescate.set_value(int(rescate.max)).run()
        self.verificar_panel()
        self.assertEqual(self.app.number_input(key='rescate').value, 1499)

    def test_persistencia_y_ajuste_de_costos(self):
        self.app.number_input(key='costo').set_value(1900).run()
        self.app.number_input(key='rescate').set_value(1200).run()

        self.app.number_input(key='precio').set_value(4200).run()
        self.verificar_panel()
        self.assertEqual(self.app.number_input(key='costo').value, 1900)

        self.app.number_input(key='costo').set_value(1600).run()
        self.verificar_panel()
        self.assertEqual(self.app.number_input(key='rescate').value, 1200)

        self.app.number_input(key='precio').set_value(1000).run()
        self.verificar_panel()
        self.assertEqual(self.app.number_input(key='costo').value, 999)
        self.assertEqual(self.app.number_input(key='rescate').value, 998)

    def test_parametros_invalidos(self):
        with patch('parametros.ParametrosCaso.con_cambios', side_effect=ValueError('caso de prueba')):
            self.app.run()
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(self.app.error[0].value, 'Parámetros inválidos: caso de prueba')
        self.assertEqual(len(self.app.metric), 0)
