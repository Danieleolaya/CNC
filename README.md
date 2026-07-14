# Control CNC PCB - Generador CAM y Monitor en Tiempo Real

Este proyecto es una interfaz gráfica de usuario (GUI) desarrollada en Python con Tkinter para el control y monitoreo de máquinas CNC, diseñada específicamente para el ruteo de aislamiento, perforación y corte de placas de circuito impreso (PCB).

El software permite realizar una conexión directa con tarjetas controladoras que utilicen firmware GRBL, controlar manualmente los ejes, cargar archivos Gerber (`.GBR`) y Excellon (`.drl`/`.txt`), procesar trayectorias mediante un motor CAM geométrico avanzado, gestionar cambios de herramienta guiados y visualizar el progreso de corte en tiempo real.

---

## 🚀 Características Principales

* **Comunicación Serial Multiplataforma:** Autodetecta y filtra puertos seriales útiles en Windows (puertos `COM`) y en Linux (puertos `/dev/ttyUSB` o `/dev/ttyACM`).
* **Control Manual Integrado (Jogging):** Control interactivo para mover los ejes X, Y y Z en milímetros, fijar ceros de trabajo virtuales (`G10 L20`), retornar al origen de forma rápida y controlar el motor (husillo/spindle) mediante comandos directos (`M3`/`M5`).
* **Motor CAM de Aislamiento Avanzado:**
  * **Trigonometría para Brocas Conónicas (V-Bit):** Ajuste del diámetro efectivo de corte en base a la profundidad y ángulo de la broca.
  * **Cálculo de Colisiones y Unión Geométrica:** Fusión de pistas y pads mediante operaciones poligonales para evitar pasadas redundantes.
  * **Aislamiento Multi-Pasada:** Configuración del número de pasadas para vaciado de cobre (estover) facilitando la soldadura.
  * **Compensación de Esquinas y Pistas:** Estiramiento inteligente de extremos de pista para evitar cortes incompletos.
* **Procesamiento de Perforaciones (Excellon):** Permite importar coordenadas de taladros para automatizar los agujeros de componentes, alineándose automáticamente con el origen gráfico seleccionado.
* **Corte de Borde Automático (Profiling):** Calcula el contenedor exterior (*Bounding Box*) del circuito y genera trayectorias en múltiples pasadas de profundidad (*Step-downs*) para recortar el contorno físico de la placa.
* **Manejo de Pausas y Cambio de Herramienta:** Inserta pausas físicas (`M0`) acompañadas de instrucciones y guías en pantalla para realizar la calibración de altura de manera segura durante el cambio de brocas.
* **Monitoreo Visual Dual:**
  * **Monitor de Referencia (Derecha):** Renderiza el diseño original en cyan, el corte de borde en magenta, las perforaciones en naranja y las trayectorias de aislamiento resultantes en verde. Permite asignar el origen de coordenadas `(0,0)` haciendo clic en pantalla.
  * **Monitor en Tiempo Real (Izquierda):** Grafica y sigue la posición actual del husillo, mostrando el rastro físico del mecanizado en tiempo real.
* **Registro de Tesis (Logging):** Almacena automáticamente los resultados de mecanizado (nombre del archivo y tiempo total de ejecución) en el archivo `Resultados_Tesis_Log.txt` para análisis de rendimiento académico.

---

## 🛠️ Requisitos Previos e Instalación

Este programa está escrito en Python 3 y utiliza librerías de cálculo geométrico y procesamiento de imágenes. A continuación se presentan las instrucciones detalladas para preparar el entorno tanto en Windows como en Linux.

### Dependencias Principales:
* **`pyserial`**: Gestión de la comunicación por bus serial USB.
* **`shapely`**: Motor geométrico para la construcción de buffers y la fusión de polígonos.
* **`Pillow`**: Procesamiento de imágenes para visualizadores de interfaz.
* **`opencv-python` y `numpy`**: Conversión y aproximación matemática de contornos en imágenes bitmap.

---

### 💻 Instalación en Windows

1. **Instalar Python:**
   * Descarga la última versión de [Python 3](https://www.python.org/downloads/) para Windows.
   * **IMPORTANTE:** Durante la instalación, marca la casilla **"Add Python to PATH"** (Añadir Python al PATH) antes de presionar instalar.
2. **Instalar las Dependencias:**
   * Abre la consola de comandos (**CMD** o **PowerShell**).
   * Ejecuta el siguiente comando:
     ```cmd
     pip install pyserial shapely Pillow opencv-python numpy
     ```
3. **Ejecutar el Software:**
   * Navega hasta la carpeta del proyecto y ejecuta:
     ```cmd
     python main.py
     ```

---

### 🐧 Instalación en Linux (Ubuntu/Debian)

En Linux, la interfaz gráfica de Python (Tkinter) no viene instalada por defecto en algunas distribuciones y debe configurarse de forma independiente junto con los permisos del puerto serial.

1. **Actualizar el Sistema e Instalar Python3 y Tkinter:**
   * Abre una terminal y ejecuta:
     ```bash
     sudo apt update
     sudo apt install python3 python3-pip python3-tk -y
     ```
2. **Configurar los Permisos del Puerto Serial (Crucial para Conectarse a la CNC):**
   * Por defecto, Linux restringe el acceso de usuarios comunes a los dispositivos USB seriales (`ttyUSB` o `ttyACM`). Para otorgar permisos permanentes a tu usuario, agrégalo al grupo `dialout`:
     ```bash
     sudo usermod -a -G dialout $USER
     ```
   * **NOTA:** Debes cerrar sesión o reiniciar el equipo para que este cambio de permisos surta efecto.
3. **Instalar las Dependencias de Python:**
   * Instala los paquetes requeridos por medio de `pip`:
     ```bash
     pip3 install pyserial shapely Pillow opencv-python numpy
     ```
4. **Ejecutar el Software:**
   * Corre el programa con:
     ```bash
     python3 main.py
     ```

---

## ⚙️ Conexión, Firmware (GRBL) y Hardware

Para que el software interactúe correctamente con tu máquina, la placa controladora (usualmente **Arduino UNO + CNC Shield V3**) debe tener cargado el firmware **GRBL v1.1**.

### Pasos de Preparación:
1. **Instalar GRBL:** Descarga la librería oficial desde [gnea/grbl](https://github.com/gnea/grbl) e instálala en tu Arduino IDE usando la opción *Incluir Librería .ZIP*. Sube el ejemplo `grblUpload` a tu Arduino.
2. **Configuración de la CNC Shield:** Acopla la Shield sobre el Arduino UNO. Asegúrate de instalar correctamente los drivers paso a paso (A4988/DRV8825) con sus respectivos disipadores de calor y jumpers de microstepping.
3. **Calibración de Parámetros:** Desde la consola del software (botón **⚙️ Configuración GRBL**), digita `$$` para visualizar los parámetros internos de GRBL. Calibra los pasos por milímetro de tus motores de avance en base al paso de tus varillas roscadas o correas:
   * `$100` (Eje X)
   * `$101` (Eje Y)
   * `$102` (Eje Z)

---

## 📚 Arquitectura del Código e Innovaciones de Software

Este software ha sido diseñado bajo arquitectura orientada a objetos en Python, incorporando prácticas robustas de programación industrial y control en tiempo real. A continuación se detallan las clases y bloques matemáticos clave:

```
  ┌────────────────────────────────────────────────────────┐
  │                   Tkinter Main Thread                  │
  │  (Captura eventos GUI, Clic de Origen, Visualizadores)  │
  └───────────┬─────────────────────────────────▲──────────┘
              │                                 │
              │ Inicia                          │ Envía Respuestas
              │ Hilo Secundario                 │ y Posicionamientos
              ▼                                 │
  ┌─────────────────────────────────────────────┴──────────┐
  │                 Background Thread (Worker)             │
  │     (Envío secuencial de G-Code por Puerto Serial)     │
  └────────────────────────────────────────────────────────┘
```

### 1. Desacoplamiento por Multithreading (Hilos)
* **El Problema:** Al enviar miles de líneas de G-Code por el puerto serial, el programa tiene que esperar el caracter `"ok"` de respuesta de GRBL. Si esto se hace en el mismo hilo de la interfaz, la ventana de Tkinter se congelará, se mostrará como *"No Responde"* y el usuario no podrá presionar el botón de **STOP** ni ver el progreso en tiempo real.
* **La Solución:** Implementamos un hilo independiente de ejecución mediante la librería `threading`. El método `iniciar_ruteo()` crea un hilo secundario:
  ```python
  threading.Thread(target=self.hilo_enviar_gcode, daemon=True).start()
  ```
  Esto permite que la interfaz gráfica (Hilo Principal) siga ejecutando su bucle de eventos (`mainloop`), manteniendo activos los botones de emergencia y la actualización continua del lienzo.

### 2. Algoritmo Geométrico del Motor CAM (Shapely)
El motor CAM integrado automatiza el engorroso proceso de aislar las pistas de cobre utilizando matemática de polígonos avanzados:
* **Generación de Buffers de Compensación:** El Gerber define las pistas como líneas simples (`LineString`). Para modelar el cobre real y las zonas de aislamiento, se aplica un buffer de dilatación de radio variable:
  ```python
  cobre_pistas = unary_union(lineas_pistas).buffer(ancho_pista_deseado / 2.0, cap_style=1, join_style=1)
  ```
* **Fusión de Cobre Real (`unary_union`):** Las pistas y las almohadillas de soldadura (pads) se unifican matemáticamente eliminando las intersecciones internas. Esto evita pasadas redundantes o que la fresa corte a través de pistas que pertenecen al mismo nodo de conexión.
* **Aislamiento Multi-Pasada:** Se calculan múltiples buffers concéntricos (`offset_base + pasada * paso_lateral`) de manera progresiva. La broca recorre los bordes externos de estas uniones para limpiar un canal ancho de cobre, reduciendo drásticamente la probabilidad de cortocircuitos por rebabas metálicas al soldar.

### 3. Trigonometría Aplicada a Brocas Cónicas (V-Bit)
A diferencia de una fresa cilíndrica de diámetro constante, las fresas de grabado de circuitos suelen ser de punta en "V" (conos). El ancho real del surco tallado varía en proporción directa a la profundidad del corte.
El programa aplica de forma transparente la siguiente fórmula trigonométrica para calcular el diámetro real que la herramienta tendrá en el cobre:

$$\text{Diámetro Efectivo} = \text{Diámetro de Punta} + 2 \cdot \left( |Z_{\text{corte}}| \cdot \tan\left(\frac{\text{Ángulo}}{2}\right) \right)$$

* **Explicación en código:**
  ```python
  profundidad_fisica = abs(z_corte)
  media_angulo_rad = math.radians(angulo / 2.0)
  ensanchamiento = 2.0 * (profundidad_fisica * math.tan(media_angulo_rad))
  diametro_efectivo = diametro + ensanchamiento
  ```
  Esto compensa automáticamente la desviación geométrica, garantizando un ancho de aislamiento preciso y protegiendo las pistas finas de ser destruidas por un ensanchamiento excesivo en V.

### 4. Sincronización y Cambio de Herramienta Semiautomático (M0 Tool Change)
Dado que fabricar un PCB requiere tres procesos secuenciales de diámetros y características mecánicas totalmente diferentes (Aislamiento de pistas, Perforación de componentes y Recorte del contorno), el software integra comandos de parada física e instrucciones interactivas:
* **Secuencia de Calibración de Broca:** Entre procesos, se insertan comandos `M0` (Program Stop) con retardos de sincronía `G4 P1.0` que detienen la máquina físicamente y apagan el husillo.
* **Procedimiento Paso a Paso en Código:**
  1. La CNC termina el ruteo, eleva Z, viaja al origen X0 Y0 y se detiene (`M0`). El usuario retira la broca de ruteo e introduce la de taladrado (dejándola libre).
  2. Al presionar **Continuar**, el software baja a `Z0.0` y vuelve a detenerse (`M0`). El usuario baja la broca suelta hasta que toque físicamente el cobre y la aprieta.
  3. Esto asegura una nivelación perfecta del eje Z en 0 sin necesidad de sensores externos costosos. Al presionar **Continuar** nuevamente, la máquina eleva Z a su altura de seguridad y procede a perforar con precisión absoluta.

### 5. Análisis Predictivo de Dimensiones
Para proteger el hardware ante colisiones mecánicas, el programa analiza la lista completa de G-Code antes de enviarlo:
```python
match_x = re.search(r'X[:\s=]*([-0-9.]+)', linea_limpia)
```
Escanea el G-Code en busca de las coordenadas extremas y determina de manera automática las dimensiones máximas y mínimas en milímetros del contorno útil. Si estas dimensiones exceden los límites físicos de tu máquina o de la placa física cargada, el operario es alertado en la barra de estado antes de pulsar el botón de encendido.

---



| Pregunta Típica del Jurado | Explicación Técnica Simplificada | ¿Dónde se ve en el Código? |
| :--- | :--- | :--- |
| **¿Por qué la interfaz no se congela cuando la máquina está trabajando?** | Usamos **Multithreading** (programación concurrente). El envío del G-Code y la lectura de respuestas seriales se ejecutan en un hilo secundario en segundo plano, mientras el hilo principal (main thread) se dedica exclusivamente a refrescar la pantalla y capturar clics de parada de emergencia. | `threading.Thread(...)` en el método `iniciar_ruteo`. |
| **¿Cómo alineas las pistas, los taladros y el corte de contorno si vienen de archivos diferentes?** | Implementamos un sistema de **traslación de vectores**. Al hacer clic en el lienzo, se calculan las coordenadas del origen físico `(pos_p_x, pos_p_y)`. Al generar el código final, a cada coordenada de los archivos importados se le resta este vector de origen. Esto traslada geométricamente todos los diseños a una matriz unificada con el mismo origen `(0,0)`. | Operaciones del tipo `x_relativo = x - origen_x` en `generar_gcode_perforaciones` y `generar_gcode_aislamiento`. |
| **¿Cómo evitas colisiones o que el motor corte en áreas no deseadas?** | Se emplean **estados y bloqueos lógicos** (*software locks*). Si no hay un puerto serial conectado, el botón de inicio se desactiva. Si el ruteo está activo, se deshabilitan las opciones de control manual para que el usuario no envíe movimientos accidentales por consola mientras la máquina trabaja. Además, el botón de parada inyecta un byte de interrupción inmediata (`\x18`) que interrumpe la cola de almacenamiento en el buffer del chip controlador. | Métodos `actualizar_estado_manual()`, `iniciar_ruteo()`, y comando de escape `\x18` en `detener_ruteo()`. |
| **¿Por qué usas la librería Shapely y no haces tú mismo los cálculos de distancia en las pistas?** | Calcular el contorno de compensación (*offsetting*) de líneas unidas en ángulos agudos requiere trigonometría analítica extremadamente compleja. Shapely es una librería estándar industrial que implementa el algoritmo **GEOS** (C++). Utiliza polígonos geométricos reales en lugar de píxeles, logrando una precisión matemática de centésimas de milímetro para evitar cortocircuitos entre las pistas más delgadas. | Importación de `Shapely` y las funciones `.buffer()`, `Polygon()`, and `unary_union()`. |
| **¿Por qué es necesario calibrar la altura de la fresa a mano entre procesos?** | En fresadoras caseras no siempre disponemos de un sensor automático de altura (Z-probe). Por ende, nuestro programa implementa un **procedimiento guiado por pausas de software (`M0`)**. Al bajar a `Z0`, la punta de la herramienta queda exactamente sobre el plano del circuito. Esto permite calibrar visualmente y fijar de forma física la altura del eje Z sin requerir hardware adicional, reduciendo costos del prototipo. | Secuencia con comandos `M0` y mensajes interactivos en `generar_gcode_aislamiento()`. |
| **¿Dónde registras la evidencia de las pruebas físicas del proyecto?** | El software cuenta con un **módulo de telemetría y logging automático**. Cada vez que una placa termina su ruteo al 100% con éxito, se calcula el tiempo transcurrido y se escribe un registro con la fecha, el nombre del archivo y la duración del proceso en `Resultados_Tesis_Log.txt`. Esto constituye la evidencia de fiabilidad experimental requerida para la sección de resultados de la tesis. | Uso de `time.time()` y guardado incremental `log.write(...)` en `hilo_enviar_gcode()`. |
