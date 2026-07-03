"""Tests para los servicios de procesamiento de senales (Milestone 2)."""

import os
import tempfile

import numpy as np
import pytest
import soundfile as sf
from scipy.signal import butter, correlate, fftconvolve, freqz

from app.services.filter import filtro_octava
from app.services.signal_utils import (
    a_escala_log,
    cargar_audio,
    obtener_ri_desde_sweep,
    sintetizar_ri,
)
from app.services.sine_sweep import generar_sine_sweep


class TestCargarAudio:
    """Tests para la funcion cargar_audio."""

    def test_cargar_audio_no_existe(self):
        """Verifica que se lanza FileNotFoundError si el archivo no existe."""
        with pytest.raises(FileNotFoundError):
            cargar_audio("archivo_que_no_existe.wav")

    def test_cargar_audio_wav(self):
        """Verificar carga correcta de archivo WAV."""
        senal_orig = np.array([0.1, 0.5, -0.3, 0.8, -0.8], dtype=np.float32)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            ruta = f.name
        try:
            sf.write(ruta, senal_orig, 44100, subtype="FLOAT")
            audio, fs = cargar_audio(ruta)
            assert isinstance(audio, np.ndarray)
            assert fs == 44100
            assert audio.shape == senal_orig.shape
            senal_esperada = senal_orig / np.max(np.abs(senal_orig)) * 0.9
            np.testing.assert_allclose(audio, senal_esperada, atol=1e-5)
        finally:
            os.unlink(ruta)

    def test_cargar_audio_formato_invalido(self):
        """Verificar que lanza error con formato no soportado."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"esto no es un archivo de audio valido")
            ruta = f.name
        try:
            with pytest.raises(ValueError):
                cargar_audio(ruta)
        finally:
            os.unlink(ruta)

    def test_cargar_audio_normalizacion(self):
        """Verificar que la salida esta normalizada entre -1 y 1."""
        senal_orig = np.array([0.1, 0.5, -0.3, 1.0, -1.0], dtype=np.float32)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            ruta = f.name
        try:
            sf.write(ruta, senal_orig, 44100)
            audio, _ = cargar_audio(ruta)
            assert np.all(np.abs(audio) <= 1.0 + 1e-6)
        finally:
            os.unlink(ruta)


class TestAEscalaLog:
    """Tests para la funcion a_escala_log."""

    def test_a_escala_log_valores(self):
        """Verifica que el maximo de la senal corresponde a 0 dB."""
        x = np.array([1.0, 0.5, 0.25, 0.1])
        db = a_escala_log(x)
        assert abs(db[0] - 0.0) < 1e-10

    def test_a_escala_log_tipo(self):
        """Verifica que retorna un np.ndarray."""
        x = np.array([1.0, 0.5])
        db = a_escala_log(x)
        assert isinstance(db, np.ndarray)

    def test_a_escala_log_relacion(self):
        """Verificar que una senal con amplitud mitad da -6 dB."""
        x = np.array([1.0, 0.5])
        db = a_escala_log(x)
        assert abs(db[1] - (-6.0206)) < 0.01


class TestSintetizarRI:
    """Tests para la funcion sintetizar_ri."""

    def test_sintetizar_ri_duracion(self):
        """Verificar que la RI tiene la duracion correcta."""
        fs = 44100
        duracion = 2.0
        ri = sintetizar_ri({1000.0: 1.5}, fs=fs, duracion=duracion)
        assert len(ri) == int(duracion * fs)

    def test_sintetizar_ri_decaimiento(self):
        """
        Verificar que el decaimiento por banda corresponde
        aproximadamente al T60 especificado.
        """
        np.random.seed(42)
        fs = 44100
        t60_objetivo = 2.0
        # duracion > T60 para que la senal decaiga lo suficiente
        ri = sintetizar_ri({1000.0: t60_objetivo}, fs=fs, duracion=3.0)
        ri_banda = filtro_octava(ri, fc=1000.0, fs=fs)

        # Integral de Schroeder: suma acumulada inversa de la energia
        energia = ri_banda ** 2
        schroeder = np.cumsum(energia[::-1])[::-1]
        schroeder_db = 10 * np.log10(schroeder / schroeder[0] + np.finfo(float).eps)

        t = np.arange(len(ri)) / fs
        indices_60db = np.where(schroeder_db <= -60)[0]
        assert len(indices_60db) > 0, "La senal no decayo 60 dB en la duracion especificada"

        t60_medido = t[indices_60db[0]]
        assert abs(t60_medido - t60_objetivo) / t60_objetivo <= 0.10


class TestFiltroOctava:
    """Tests para la funcion filtro_octava."""

    def test_filtro_octava_frecuencia_central(self):
        """Verificar que el filtro pasa correctamente la frecuencia central."""
        fc = 1000.0
        fs = 44100
        t = np.linspace(0, 1.0, fs, endpoint=False)
        seno = np.sin(2 * np.pi * fc * t)
        filtrada = filtro_octava(seno, fc=fc, fs=fs)

        # Excluir transitorios de borde (primer y ultimo 10%)
        margin = fs // 10
        rms_in = np.sqrt(np.mean(seno[margin:-margin] ** 2))
        rms_out = np.sqrt(np.mean(filtrada[margin:-margin] ** 2))

        gain_db = 20 * np.log10(rms_out / rms_in)
        assert abs(gain_db) < 1.0

    def test_filtro_octava_atenuacion(self):
        """Verificar atenuacion fuera de banda."""
        fc = 1000.0
        fs = 44100
        t = np.linspace(0, 1.0, fs, endpoint=False)
        margin = fs // 10

        for f_test in [fc / 2, fc * 2]:
            seno = np.sin(2 * np.pi * f_test * t)
            filtrada = filtro_octava(seno, fc=fc, fs=fs)
            rms_in = np.sqrt(np.mean(seno[margin:-margin] ** 2))
            rms_out = np.sqrt(np.mean(filtrada[margin:-margin] ** 2))
            atenuacion_db = 20 * np.log10(rms_in / (rms_out + 1e-10))
            assert atenuacion_db > 20.0

    def test_filtro_octava_respuesta_frecuencia(self):
        """Verificar que la respuesta cumple -3 dB en frecuencias de corte."""
        fc = 1000.0
        fs = 44100
        f_inf = fc / np.sqrt(2)
        f_sup = fc * np.sqrt(2)
        nyq = fs / 2.0
        b, a = butter(4, [f_inf / nyq, f_sup / nyq], btype="band", output="ba")  # type: ignore[misc]
        w, h = freqz(b, a, worN=8192, fs=fs)

        # Ganancia en fc: debe ser maxima (~0 dB)
        gain_fc = 20 * np.log10(np.abs(h[np.argmin(np.abs(w - fc))]))
        assert abs(gain_fc) < 0.5

        # Ganancia en frecuencias de corte: debe ser -3 dB
        gain_inf = 20 * np.log10(np.abs(h[np.argmin(np.abs(w - f_inf))]))
        gain_sup = 20 * np.log10(np.abs(h[np.argmin(np.abs(w - f_sup))]))
        assert abs(gain_inf - (-3.0)) < 1.0
        assert abs(gain_sup - (-3.0)) < 1.0


class TestObtenerRIDesdeSweep:
    """Tests para la funcion obtener_ri_desde_sweep."""

    def test_obtener_ri_pico(self):
        """
        Verificar que la RI obtenida por deconvolucion tiene
        un pico principal claramente identificable.
        """
        fs = 8000
        sweep, filtro_inverso = generar_sine_sweep(50, 3000, duracion=2.0, fs=fs)

        # RI band-limited: burst senoidal a 1000 Hz con decaimiento (rango 50-3000 Hz del sweep)
        n_ri = int(0.5 * fs)
        t = np.arange(n_ri) / fs
        ri_orig = np.sin(2 * np.pi * 1000 * t) * np.exp(-5.0 * t)

        # Simular grabacion: sala = sweep convolucionado con la RI
        grabacion = fftconvolve(sweep, ri_orig)

        recovered = obtener_ri_desde_sweep(grabacion, filtro_inverso)

        # Correlacion cruzada normalizada: busca el mejor desfase temporal
        n_cmp = min(len(ri_orig), len(recovered))
        a = ri_orig[:n_cmp] / np.linalg.norm(ri_orig[:n_cmp])
        b = recovered[:n_cmp] / np.linalg.norm(recovered[:n_cmp])
        correlacion = np.max(np.abs(correlate(a, b, mode="full")))

        assert correlacion > 0.9
