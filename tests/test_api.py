"""Tests para los endpoints de la API (Milestone 3)."""

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _generar_wav_bytes(duracion: float = 1.0, fs: int = 44100) -> bytes:
    """Genera un archivo WAV en memoria con decaimiento exponencial para los tests."""
    n = int(duracion * fs)
    t = np.arange(n) / fs
    np.random.seed(7)
    signal = np.exp(-3.0 * t) * np.random.randn(n)
    signal = signal / np.max(np.abs(signal)) * 0.9
    buf = io.BytesIO()
    sf.write(buf, signal, fs, format="WAV")
    buf.seek(0)
    return buf.read()


class TestHealthEndpoint:
    """Tests para el endpoint /health."""

    def test_health_returns_200(self):
        """Verifica que /health responde con status 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy(self):
        """Verifica que el status es 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_version(self):
        """Verifica que la respuesta incluye la version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data


class TestRootEndpoint:
    """Tests para el endpoint raiz /."""

    def test_root_returns_200(self):
        """Verifica que / responde con status 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_api_info(self):
        """Verifica que la raiz devuelve informacion de la API."""
        response = client.get("/")
        data = response.json()
        assert data["name"] == "RIR-API"
        assert "docs" in data


class TestSignalsEndpoints:
    """Tests para los endpoints de generacion de senales."""

    def test_pink_noise_returns_wav(self):
        """Verifica que /pink-noise genera y devuelve un WAV valido."""
        response = client.post(
            "/api/v1/signals/pink-noise", json={"duracion": 1.0, "fs": 44100}
        )
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    def test_sine_sweep_returns_wav(self):
        """Verifica que /sine-sweep genera y devuelve un WAV valido."""
        response = client.post(
            "/api/v1/signals/sine-sweep",
            json={"f1": 100.0, "f2": 8000.0, "duracion": 1.0, "fs": 44100},
        )
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    def test_synthetic_ir_returns_wav(self):
        """Verifica que /synthetic-ir genera y devuelve un WAV valido."""
        response = client.post(
            "/api/v1/signals/synthetic-ir",
            data={"t60_1000": "1.5", "fs": "44100", "duracion": "3.0"},
        )
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    def test_sine_sweep_pair_returns_zip(self):
        """Verifica que /sine-sweep-pair devuelve un ZIP con sweep y filtro inverso."""
        response = client.post(
            "/api/v1/signals/sine-sweep-pair",
            json={"f1": 100.0, "f2": 8000.0, "duracion": 1.0, "fs": 44100},
        )
        assert response.status_code == 200
        assert "application/zip" in response.headers["content-type"]

    def test_sine_sweep_pair_contiene_dos_wavs(self):
        """Verifica que el ZIP contiene sine_sweep.wav y filtro_inverso.wav."""
        import io
        import zipfile
        response = client.post(
            "/api/v1/signals/sine-sweep-pair",
            json={"f1": 100.0, "f2": 8000.0, "duracion": 1.0, "fs": 44100},
        )
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        nombres = zf.namelist()
        assert "sine_sweep.wav" in nombres
        assert "filtro_inverso.wav" in nombres

    def test_sine_sweep_f1_mayor_f2_retorna_400(self):
        """Verifica que f1 >= f2 retorna HTTP 400."""
        response = client.post(
            "/api/v1/signals/sine-sweep",
            json={"f1": 5000.0, "f2": 100.0, "duracion": 1.0, "fs": 44100},
        )
        assert response.status_code == 400


class TestFiltersEndpoints:
    """Tests para los endpoints de filtrado."""

    def test_frequencies_returns_list(self):
        """Verifica que /frequencies devuelve una lista de frecuencias."""
        response = client.get("/api/v1/filters/frequencies")
        assert response.status_code == 200
        data = response.json()
        assert "frecuencias" in data
        assert len(data["frecuencias"]) > 0

    def test_band_filter_returns_wav(self):
        """Verifica que /band filtra el audio y devuelve un WAV."""
        wav_bytes = _generar_wav_bytes(duracion=0.5)
        response = client.post(
            "/api/v1/filters/band",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            data={"fc": "1000.0"},
        )
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    def test_band_filter_frecuencia_invalida_retorna_400(self):
        """Verifica que una frecuencia no disponible retorna HTTP 400."""
        wav_bytes = _generar_wav_bytes(duracion=0.5)
        response = client.post(
            "/api/v1/filters/band",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            data={"fc": "999.0"},
        )
        assert response.status_code == 400


class TestAnalysisEndpoints:
    """Tests para los endpoints de analisis completo de RI."""

    def test_analysis_endpoint(self):
        """Verifica que /impulse-response devuelve parametros acusticos y curvas de Schroeder."""
        wav_bytes = _generar_wav_bytes(duracion=2.0)
        response = client.post(
            "/api/v1/analysis/impulse-response",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "parametros" in data
        assert "T30" in data["parametros"]
        assert "EDT" in data["parametros"]

    def test_invalid_file_returns_422(self):
        """Verifica que un archivo no valido retorna HTTP 422."""
        response = client.post(
            "/api/v1/analysis/impulse-response",
            files={"file": ("test.txt", b"esto no es audio", "text/plain")},
        )
        assert response.status_code == 422


class TestAcousticsEndpoints:
    """Tests para los endpoints de parametros acusticos."""

    def test_parameters_endpoint(self):
        """Verifica que /parameters devuelve un valor global (no por banda) por parametro."""
        wav_bytes = _generar_wav_bytes(duracion=2.0)
        response = client.post(
            "/api/v1/acoustics/parameters",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        for param in ["EDT", "T10", "T20", "T30", "D50", "C80"]:
            assert param in data
            assert isinstance(data[param], (float, int)) or data[param] is None

    def test_parameters_global_es_promedio_500_1000(self):
        """Verifica que el valor global de /parameters sea el promedio de 500 y 1000 Hz."""
        wav_bytes = _generar_wav_bytes(duracion=2.0)
        global_response = client.post(
            "/api/v1/acoustics/parameters",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        by_bands_response = client.post(
            "/api/v1/acoustics/parameters/by-bands",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        globales = global_response.json()
        bandas = by_bands_response.json()["bandas_hz"]
        for param in ["EDT", "T10", "T20", "T30", "D50", "C80"]:
            val_500 = bandas["500"][param]
            val_1000 = bandas["1000"][param]
            if val_500 is not None and val_1000 is not None:
                assert globales[param] == pytest.approx((val_500 + val_1000) / 2)

    def test_parameters_by_bands_endpoint(self):
        """Verifica que /parameters/by-bands reorganiza los resultados por banda."""
        wav_bytes = _generar_wav_bytes(duracion=2.0)
        response = client.post(
            "/api/v1/acoustics/parameters/by-bands",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "bandas_hz" in data


class TestConvolucionEndpoints:
    """Tests para los endpoints de convolucion de audio."""

    def test_convolucion_con_ri_returns_wav(self):
        """Verifica que /with-ir devuelve un WAV convolucionado."""
        audio_bytes = _generar_wav_bytes(duracion=1.0)
        ri_bytes = _generar_wav_bytes(duracion=0.5)
        response = client.post(
            "/api/v1/convolution/with-ir",
            files={
                "audio": ("audio.wav", audio_bytes, "audio/wav"),
                "ri": ("ri.wav", ri_bytes, "audio/wav"),
            },
        )
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    def test_convolucion_con_ri_sintetica_returns_wav(self):
        """Verifica que /with-synthetic-ir devuelve un WAV con reverb sintetica."""
        audio_bytes = _generar_wav_bytes(duracion=1.0)
        response = client.post(
            "/api/v1/convolution/with-synthetic-ir",
            files={"audio": ("audio.wav", audio_bytes, "audio/wav")},
            data={"t60_1000": "1.5", "duracion": "2.0"},
        )
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    def test_convolucion_archivo_invalido_returns_422(self):
        """Verifica que un archivo no valido retorna HTTP 422."""
        response = client.post(
            "/api/v1/convolution/with-ir",
            files={
                "audio": ("audio.txt", b"no es audio", "text/plain"),
                "ri": ("ri.txt", b"no es audio", "text/plain"),
            },
        )
        assert response.status_code == 422


class TestUtilsEndpoints:
    """Tests para los endpoints de utilidades."""

    def test_schroeder_endpoint(self):
        """Verifica que /schroeder devuelve la curva de Schroeder."""
        wav_bytes = _generar_wav_bytes(duracion=0.5)
        response = client.post(
            "/api/v1/utils/schroeder",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "nivel_db" in data
        assert "tiempo" in data
        assert data["nivel_db"][0] == pytest.approx(0.0, abs=0.01)

    def test_log_scale_endpoint(self):
        """Verifica que /log-scale devuelve la senal en dB."""
        wav_bytes = _generar_wav_bytes(duracion=0.5)
        response = client.post(
            "/api/v1/utils/log-scale",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "nivel_db" in data

    def test_smoothing_hilbert_endpoint(self):
        """Verifica que /smoothing con Hilbert devuelve la envolvente."""
        wav_bytes = _generar_wav_bytes(duracion=0.5)
        response = client.post(
            "/api/v1/utils/smoothing",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            data={"metodo": "hilbert"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "envolvente" in data
        assert all(v >= 0 for v in data["envolvente"])


