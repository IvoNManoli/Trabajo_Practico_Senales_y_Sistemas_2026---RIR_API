# Código utilizado para generar la plantilla Markdown profesional
Este documento sirve como registro formal de las interacciones con modelos de Inteligencia Artificial para el diseño, desarrollo y refactorización del código correspondiente al 
proyecto.

---

## 🛠️ Información del Proyecto y Entorno proporcionada a la IA

| Parámetro | Detalle |
| :--- | :--- |
| **Materia** | Señales y Sistemas / Procesamiento de Señales |
| **Milestone / Entrega** | M1: Generación de Señales de Audio Básicas |
| **Fecha de Registro** | Mayo 2026 |
| **Modelos de IA Usados** | Gemini 1.5 Pro / GPT-4o |
| **Entorno de Ejecución** | Python 3.12+ (Gestionado con `uv`) |

---

## 🚀 1. M1: Generación de Ruido Blanco y Ruido Rosa

### 📌 Test densidad espectral ruido rosa
* **Objetivo:** Crear un test que verifique que la densidad espectral del ruido rosa generado sea correcta

| Prompt Enviado a la IA | 
| :--- | 
| *Generar un test de pytest que indique que la pendiente de caída de amplitud por tercio de octava es de -3 dB* | 

| Respuesta: | 
| :--- | 
```python
def test_ruido_rosa_pendiente_espectral(self):
    """Verifica la pendiente de caida de la PSD usando FFT directa."""
    fs = 44100
    duracion = 4.0
    ruido = generar_ruido_rosa(duracion, fs)
    
    # 1. FFT real directa para obtener el espectro de potencia
    n = len(ruido)
    frecuencias = np.fft.rfftfreq(n, d=1/fs)
    psd = (np.abs(np.fft.rfft(ruido)) ** 2) / (fs * n)
    
    # 2. Definimos nuestra propia banda de interes en audio (de 20 Hz a 15000 Hz)
    f_min, f_max = 20, 15000
    mascara = (frecuencias >= f_min) & (frecuencias <= f_max)
    
    # 3. Cambio de escala a log-log
    log_f = np.log10(frecuencias[mascara])
    log_psd = np.log10(psd[mascara])
    
    # 4. Ajuste lineal por mínimos cuadrados (Regresión lineal)
    pendiente, _ = np.polyfit(log_f, log_psd, 1)
    
    # 5. Evaluacion de la ley 1/f (pendiente ideal = -1.0)
    # Se establece una tolerancia de 0.15 debido a la naturaleza estocástica de la señal
    assert np.isclose(pendiente, -1.0, atol=0.15), \
        f"Pendiente espectral incorrecta: {pendiente:.2f}. Se esperaba ~ -1.0"
