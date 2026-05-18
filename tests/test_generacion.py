"""Tests para los servicios de generacion de senales (Milestone 1)."""

import numpy as np
import pytest

from app.services.pink_noise import generar_ruido_rosa
from app.services.sine_sweep import generar_sine_sweep


class TestGenerarRuidoRosa:
    """Tests para la funcion generar_ruido_rosa."""

    def test_ruido_rosa_duracion(self):
        """Verifica que la longitud de la senal corresponda a duracion * fs."""
        duracion = 2.0
        fs = 44100
        ruido = generar_ruido_rosa(duracion, fs)
        expected_length = int(duracion * fs)
        assert len(ruido) == expected_length

    def test_ruido_rosa_tipo(self):
        """Verifica que la funcion retorna un np.ndarray."""
        ruido = generar_ruido_rosa(1.0, 44100)
        assert isinstance(ruido, np.ndarray)

    def test_ruido_rosa_normalizado(self):
        """Verifica que la senal esta normalizada entre -1 y 1."""
        ruido = generar_ruido_rosa(1.0, 44100)
        assert np.max(np.abs(ruido)) <= 1.0
    def test_ruido_rosa_pendiente_espectral(self):
        """Verifica la pendiente de caida de la PSD usando FFT directa."""
        fs = 44100
        duracion = 4.0
        ruido = generar_ruido_rosa(duracion, fs)
        
        # 1. FFT real directa para obtener el espectro de potencia
        n = len(ruido)
        frecuencias = np.fft.rfftfreq(n, d=1/fs)
        psd = (np.abs(np.fft.rfft(ruido)) ** 2) / (fs * n)
        
        # 2. Definimos nuestra propia banda de interes en audio (ej: de 20 Hz a f_nyquist/2)
        f_min, f_max = 20, 15000
        mascara = (frecuencias >= f_min) & (frecuencias <= f_max)
        
        # 3. Cambio de escala a log-log
        log_f = np.log10(frecuencias[mascara])
        log_psd = np.log10(psd[mascara])
        
        # 4. Ajuste lineal por cuadrados minimos
        pendiente, _ = np.polyfit(log_f, log_psd, 1)
        
        # 5. Evaluacion de la ley 1/f (pendiente ideal = -1.0)
        # Seteamos una tolerancia de 0.15 por la naturaleza estocastica del ruido
        assert np.isclose(pendiente, -1.0, atol=0.15), \
            f"Pendiente espectral incorrecta: {pendiente:.2f}. Se esperaba ~ -1.0"

class TestGenerarSineSweep:
    """Tests para la funcion generar_sine_sweep."""

    def test_sine_sweep_retorna_tupla(self):
        """Verifica que retorna una tupla con dos arrays."""
        resultado = generar_sine_sweep(20, 20000, 1.0, 44100)
        assert isinstance(resultado, tuple)
        assert len(resultado) == 2
        assert isinstance(resultado[0], np.ndarray)
        assert isinstance(resultado[1], np.ndarray)

    def test_sine_sweep_duracion(self):
        """Verifica que ambas senales tienen la longitud correcta."""
        duracion = 3.0
        fs = 44100
        sweep, filtro_inv = generar_sine_sweep(20, 20000, duracion, fs)
        expected_length = int(duracion * fs)
        assert len(sweep) == expected_length
        assert len(filtro_inv) == expected_length
