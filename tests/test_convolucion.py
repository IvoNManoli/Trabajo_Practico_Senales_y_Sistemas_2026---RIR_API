"""Tests para el servicio de convolucion de audio con RI."""

import numpy as np
import pytest

from app.services.convolution import convolucionar


class TestConvolucionar:
    """Tests para la funcion convolucionar."""

    def test_longitud_salida(self):
        """La salida debe tener longitud len(audio) + len(ri) - 1 (modo full)."""
        audio = np.random.randn(44100).astype(np.float32)
        ri = np.random.randn(4410).astype(np.float32)
        resultado = convolucionar(audio, ri, fs_audio=44100, fs_ri=44100)
        assert len(resultado) == len(audio) + len(ri) - 1

    def test_normalizacion(self):
        """El maximo absoluto de la salida debe ser aproximadamente 0.9."""
        np.random.seed(0)
        audio = np.random.randn(44100).astype(np.float32)
        ri = np.random.randn(4410).astype(np.float32)
        resultado = convolucionar(audio, ri, fs_audio=44100, fs_ri=44100)
        assert abs(np.max(np.abs(resultado)) - 0.9) < 1e-5

    def test_dtype_float32(self):
        """La salida debe ser float32."""
        audio = np.random.randn(1000).astype(np.float64)
        ri = np.random.randn(100).astype(np.float64)
        resultado = convolucionar(audio, ri, fs_audio=44100, fs_ri=44100)
        assert resultado.dtype == np.float32

    def test_audio_silencioso(self):
        """Si el audio es silencio, la salida tambien debe ser silencio."""
        audio = np.zeros(1000, dtype=np.float32)
        ri = np.random.randn(100).astype(np.float32)
        resultado = convolucionar(audio, ri, fs_audio=44100, fs_ri=44100)
        assert np.all(resultado == 0.0)

    def test_resampleo_fs_distinto(self):
        """Con fs distintos la salida debe tener el fs del audio (longitud coherente)."""
        fs_audio = 44100
        fs_ri = 48000
        audio = np.random.randn(fs_audio).astype(np.float32)
        ri = np.random.randn(fs_ri // 10).astype(np.float32)
        resultado = convolucionar(audio, ri, fs_audio=fs_audio, fs_ri=fs_ri)
        ri_resampleada_esperada = round(len(ri) * fs_audio / fs_ri)
        assert len(resultado) == pytest.approx(len(audio) + ri_resampleada_esperada - 1, abs=2)

    def test_mismo_fs_no_resamplea(self):
        """Con el mismo fs, la longitud de salida es exactamente len(audio) + len(ri) - 1."""
        audio = np.ones(1000, dtype=np.float32)
        ri = np.ones(100, dtype=np.float32)
        resultado = convolucionar(audio, ri, fs_audio=44100, fs_ri=44100)
        assert len(resultado) == 1099
