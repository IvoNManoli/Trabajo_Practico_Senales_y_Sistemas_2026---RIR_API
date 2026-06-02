"""Tests para los servicios de generacion de senales (Milestone 1)."""

from unittest.mock import patch

import numpy as np
import pytest

from app.services.grabacion_utils import reproducir_y_grabar
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
    def test_convolucion_genera_impulso(self):
        """Verifica que sweep x filtro_inverso produce un impulso con pico > 40 dB sobre el piso."""
        from scipy.signal import fftconvolve

        sweep, filtro_inverso = generar_sine_sweep(20, 20000, 5.0, 44100)
        resultado = fftconvolve(sweep, filtro_inverso)

        indice_pico = np.argmax(np.abs(resultado))
        valor_pico = np.abs(resultado[indice_pico])

        mascara = np.ones(len(resultado), dtype=bool)
        mascara[max(0, indice_pico - 100):indice_pico + 100] = False
        piso = np.mean(np.abs(resultado[mascara]))

        relacion_db = 20 * np.log10(valor_pico / piso)
        assert relacion_db >= 40, f"Relacion pico/piso insuficiente: {relacion_db:.1f} dB"


class TestReproducirYGrabar:
    """Tests para la funcion reproducir_y_grabar."""

    def _make_grabacion(self, duracion: float, fs: int) -> np.ndarray:
        """Genera un array que simula la salida de sd.playrec."""
        n_muestras = int(duracion * fs)
        return np.zeros((n_muestras, 1), dtype=np.float32)

    def test_acepta_senal_mono(self):
        """Verifica que la funcion acepta una senal 1D (mono)."""
        fs = 44100
        duracion_grabacion = 2.0
        signal_mono = np.zeros(fs)  # 1 segundo de silencio, 1D

        with patch("app.services.grabacion_utils.sd.playrec") as mock_playrec, \
             patch("app.services.grabacion_utils.sd.wait"):
            mock_playrec.return_value = self._make_grabacion(duracion_grabacion, fs)
            resultado = reproducir_y_grabar(signal_mono, fs, duracion_grabacion)

        assert isinstance(resultado, np.ndarray)
        assert resultado.ndim == 1

    def test_acepta_senal_estereo(self):
        """Verifica que la funcion acepta una senal 2D (estereo)."""
        fs = 44100
        duracion_grabacion = 2.0
        signal_estereo = np.zeros((fs, 2))  # 1 segundo, 2 canales

        with patch("app.services.grabacion_utils.sd.playrec") as mock_playrec, \
             patch("app.services.grabacion_utils.sd.wait"):
            mock_playrec.return_value = self._make_grabacion(duracion_grabacion, fs)
            resultado = reproducir_y_grabar(signal_estereo, fs, duracion_grabacion)

        assert isinstance(resultado, np.ndarray)
        assert resultado.ndim == 1

    def test_duracion_correcta(self):
        """Verifica que la grabacion tiene la duracion esperada con tolerancia del 1%."""
        fs = 44100
        duracion_grabacion = 3.0
        signal = np.zeros(fs)
        n_esperado = int(duracion_grabacion * fs)

        with patch("app.services.grabacion_utils.sd.playrec") as mock_playrec, \
             patch("app.services.grabacion_utils.sd.wait"):
            mock_playrec.return_value = self._make_grabacion(duracion_grabacion, fs)
            resultado = reproducir_y_grabar(signal, fs, duracion_grabacion)

        tolerancia = int(n_esperado * 0.01)
        assert abs(len(resultado) - n_esperado) <= tolerancia, (
            f"Duracion incorrecta: {len(resultado)} muestras, se esperaban {n_esperado} ± {tolerancia}"
        )

    def test_error_sin_dispositivo(self):
        """Verifica que lanza RuntimeError si no hay dispositivo de audio disponible."""
        import sounddevice as sd

        signal = np.zeros(44100)
        with patch("app.services.grabacion_utils.sd.playrec", side_effect=sd.PortAudioError("sin device")):
            with pytest.raises(RuntimeError, match="No hay dispositivo de audio disponible"):
                reproducir_y_grabar(signal, 44100, 2.0)
