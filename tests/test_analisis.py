"""Tests para los servicios de analisis de parametros acusticos (Milestone 3)."""

import numpy as np
import pytest

from app.services.acoustic_parameters import (
    calcular_parametros_acusticos,
    integral_schroeder,
    regresion_lineal,
    suavizar_signal,
)
from app.services.signal_utils import sintetizar_ri


class TestSuavizarSignal:
    """Tests para la funcion suavizar_signal."""

    def test_hilbert_no_negativo(self):
        """La envolvente de Hilbert debe ser no negativa."""
        signal = np.random.randn(1000)
        env = suavizar_signal(signal, "hilbert")
        assert np.all(env >= 0)

    def test_hilbert_misma_longitud(self):
        """La envolvente de Hilbert debe tener la misma longitud que la entrada."""
        signal = np.random.randn(500)
        assert len(suavizar_signal(signal, "hilbert")) == len(signal)

    def test_media_movil_misma_longitud(self):
        """La media movil debe tener la misma longitud que la entrada."""
        signal = np.random.randn(1000)
        assert len(suavizar_signal(signal, 50)) == len(signal)


class TestRegresionLineal:
    """Tests para la funcion regresion_lineal."""

    def test_regresion_lineal_conocida(self):
        """Verifica con una recta conocida y = 2x + 1."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        y = 2.0 * x + 1.0
        pendiente, ordenada, r2 = regresion_lineal(x, y)
        assert abs(pendiente - 2.0) < 1e-10
        assert abs(ordenada - 1.0) < 1e-10

    def test_regresion_lineal_r2_exacta(self):
        """Para datos perfectamente lineales, R^2 debe ser 1.0."""
        x = np.linspace(0, 10, 100)
        y = -5.0 * x + 3.0
        _, _, r2 = regresion_lineal(x, y)
        assert abs(r2 - 1.0) < 1e-10

    def test_regresion_lineal_pendiente(self):
        """Verifica pendiente con datos ruidosos conocidos."""
        np.random.seed(42)
        x = np.linspace(0, 10, 100)
        y = 3.0 * x + 5.0 + np.random.normal(0, 0.1, 100)
        pendiente, ordenada, _ = regresion_lineal(x, y)
        assert abs(pendiente - 3.0) < 0.5
        assert abs(ordenada - 5.0) < 1.0


class TestIntegralSchroeder:
    """Tests para la funcion integral_schroeder."""

    def test_integral_schroeder_forma(self):
        """Verifica que la EDC tiene la misma longitud que la entrada."""
        ri = np.random.randn(1000)
        edc = integral_schroeder(ri)
        assert len(edc) == len(ri)

    def test_schroeder_maximo_cero_db(self):
        """El primer valor de la integral de Schroeder debe ser 0 dB."""
        ri = np.random.randn(1000)
        edc = integral_schroeder(ri)
        assert abs(edc[0]) < 0.01

    def test_integral_schroeder_decreciente(self):
        """Verifica que la EDC es monotonamente decreciente."""
        ri = np.random.randn(1000)
        edc = integral_schroeder(ri)
        assert np.all(np.diff(edc) <= 0)

    def test_schroeder_ri_sintetizada(self):
        """Para una RI sintetizada con T60 conocido, la pendiente debe ser -60/T60 dB/s."""
        np.random.seed(0)
        fs = 44100
        t60 = 1.0
        ri = sintetizar_ri({1000.0: t60}, fs, duracion=3.0)
        edc = integral_schroeder(ri)
        t = np.arange(len(ri)) / fs
        # Rango T30 para ajuste
        mask = (edc >= -35) & (edc <= -5)
        pendiente, _, _ = regresion_lineal(t[mask], edc[mask])
        t60_estimado = -60.0 / pendiente
        assert abs(t60_estimado - t60) < t60 * 0.30


class TestCalcularParametros:
    """Tests para la funcion calcular_parametros_acusticos."""

    @pytest.fixture
    def ri_con_t60_conocido(self):
        """RI sintetizada con T60 = 2.0 s en todas las bandas."""
        np.random.seed(42)
        fs = 44100
        t60 = 2.0
        ri = sintetizar_ri(
            {fc: t60 for fc in [125, 250, 500, 1000, 2000, 4000]},
            fs,
            duracion=5.0,
        )
        return ri, fs, t60

    def test_parametros_ri_sintetizada(self, ri_con_t60_conocido):
        """T30 a 1000 Hz debe estar dentro del +-20% del T60 conocido."""
        ri, fs, t60 = ri_con_t60_conocido
        params = calcular_parametros_acusticos(ri, fs)
        t30_1000 = params["T30"][1000.0]
        assert t30_1000 is not None
        assert abs(t30_1000 - t60) < t60 * 0.20

    def test_d50_rango(self, ri_con_t60_conocido):
        """D50 debe estar entre 0% y 100% en todas las bandas."""
        ri, fs, _ = ri_con_t60_conocido
        params = calcular_parametros_acusticos(ri, fs)
        for val in params["D50"].values():
            if val is not None:
                assert 0.0 <= val <= 100.0

    def test_c80_consistencia(self):
        """RI con energia concentrada en primeros 10 ms debe tener C80 > 0."""
        np.random.seed(1)
        fs = 44100
        n = int(1.0 * fs)
        # Fondo de ruido muy bajo + energia temprana grande
        ri = np.random.randn(n) * 0.001
        n_early = int(0.01 * fs)
        ri[:n_early] += np.random.randn(n_early) * 10.0
        params = calcular_parametros_acusticos(ri, fs)
        c80_1000 = params["C80"][1000.0]
        if c80_1000 is not None:
            assert c80_1000 > 0

    def test_estructura_respuesta(self, ri_con_t60_conocido):
        """El resultado debe contener todos los parametros ISO 3382 y todas las bandas."""
        ri, fs, _ = ri_con_t60_conocido
        params = calcular_parametros_acusticos(ri, fs)
        for param in ["EDT", "T10", "T20", "T30", "D50", "C80"]:
            assert param in params
        for fc in [125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0]:
            assert fc in params["T30"]
