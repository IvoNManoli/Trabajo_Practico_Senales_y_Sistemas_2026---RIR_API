"""Tests para los servicios de procesamiento de senales (Milestone 2)."""

import os
import tempfile

import numpy as np
import pytest
import soundfile as sf

from app.services.filter import filtro_octava
from app.services.signal_utils import a_escala_log, cargar_audio, sintetizar_ri


class TestCargarAudio:
    """Tests para la funcion cargar_audio."""

    def test_cargar_audio_no_existe(self):
        """Verifica que se lanza FileNotFoundError si el archivo no existe."""
        with pytest.raises(FileNotFoundError):
            cargar_audio("archivo_que_no_existe.wav")

    def test_cargar_audio_retorna_tupla(self):
        """Verifica que retorna una tupla (signal, fs) — requiere archivo de prueba."""
        pytest.skip("Requiere archivo de audio de prueba")

    def test_cargar_audio_wav(self):
        """Verificar carga correcta de archivo WAV."""
        senal_orig = np.array([0.1, 0.5, -0.3, 0.8, -0.8], dtype=np.float32)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            ruta = f.name
        try:
            sf.write(ruta, senal_orig, 44100)
            audio, fs = cargar_audio(ruta)
            assert isinstance(audio, np.ndarray)
            assert fs == 44100
            assert audio.shape == senal_orig.shape
            np.testing.assert_allclose(audio, senal_orig, atol=1e-5)
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
