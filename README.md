# Control CNC PCB - Generador CAM y Monitor en Tiempo Real con Registro de Pruebas

Este proyecto es una interfaz gráfica de usuario (GUI) avanzada desarrollada en Python con Tkinter para el control y automatización de máquinas CNC, optimizada para el aislamiento y ruteo de placas de circuito impreso (PCB) a partir de archivos estándar de manufactura (Gerber y Excellon).

El software permite conectarse a una máquina con firmware GRBL, controlar sus ejes mediante movimiento manual (Jog), encender/apagar el husillo, realizar alineación visual del origen, procesar matemáticamente pistas complejas (aislamiento por vaciado), programar perforaciones y contornos de corte de borde con control automático de cambio de herramientas, y generar un registro métrico de rendimiento de pruebas empíricas.

---

## 🚀 Características Principales

* **Comunicación Serial Activa:** Conexión interactiva con GRBL seleccionando puertos autodetectados de manera inteligente (COM/USB/ACM) y control de baudios.
* **Consola de Configuración Directa:** Acceso para modificar los parámetros internos del firmware GRBL (valores `$$`) directamente desde la GUI sin software externo.
* **Control de Husillo (Spindle Control):** Botones integrados para encender (`M3`) y apagar (`M5`) el motor de corte de forma remota.
* **Procesamiento de Archivos de Manufactura:**
  * **Capa Gerber (.GBR):** Lectura, escala automática y mapeo del circuito de cobre. Detecta automáticamente unidades en pulgadas (`%MOIN*%`) y las convierte a milímetros.
  * **Capa Excellon/Taladro (.DRL/.TXT):** Carga dinámica de coordenadas de perforación mapeadas con respecto al mismo origen de la placa.
* **Alineación por un Clic (Origen Relativo):** Permite al operario definir el punto `(0,0)` de trabajo haciendo clic en cualquier parte del diseño del monitor de referencia.
* **Motor CAM Avanzado con V-Bit Math:**
  * Generación de trayectorias con múltiples pasadas para vaciado de cobre a voluntad del usuario.
  * Compensación trigonométrica automática para herramientas cónicas (V-Bits).
  * Optimización geométrica mediante la librería `shapely` para evitar colisiones, estirar pistas de conexión y saltar trazos redundantes internos en los pads.
* **Manejo de Herramientas y Pausas Sincronizadas (`M0`):** Implementación de paradas automáticas organizadas para cambios seguros de brocas físicas (broca en V -> broca helicoidal -> fresa de corte) con instrucciones en pantalla.
* **Corte de Borde por Pasadas Dinámicas:** Generación automática de un marco exterior perimetral (Bounding Box) con una holgura segura de 2 mm y cálculo de desgaste con cortes progresivos hacia el eje Z.
* **Monitores Visuales Interactivos:**
  * **Monitor de Referencia (Derecho):** Muestra el diseño original en color cyan, el área perimetral de corte en magenta, las perforaciones en naranja y las trayectorias finales procesadas en verde.
  * **Monitor en Tiempo Real (Izquierdo):** Renderiza el trayecto que realiza físicamente la fresa sobre la placa de cobre durante la ejecución real.
* **Seguridad por Hilos y Estados:**
  * Ejecución del código G-code en un hilo independiente (`threading`) para prevenir el bloqueo de la interfaz gráfica de usuario.
  * Botón de Parada de Emergencia (STOP) que interrumpe la transmisión instantáneamente (`\x18`), limpia la cola del buffer, levanta el eje Z a zona segura y apaga los motores.
* **Módulo de Métricas e Historial de Pruebas (Data Logging):** Guarda automáticamente la duración exacta y el archivo procesado en un archivo físico de texto (`Resultados_Tesis_Log.txt`) para alimentar las gráficas y análisis de la tesis.

---

## 🛠️ Requisitos Previos e Instalación del Software

Para ejecutar este software, necesitas tener **Python 3.x** instalado en tu computadora.

### Librerías requeridas:
Abre tu terminal (Símbolo del sistema, PowerShell o la terminal de VS Code) y ejecuta el siguiente comando para instalar las dependencias necesarias:

`pip install pyserial shapely Pillow opencv-python numpy`

* **`pyserial`**: Permite la comunicación por puerto USB/COM entre tu computadora y la placa controladora de la CNC.
* **`shapely`**: El cerebro matemático detrás del CAM. Realiza operaciones espaciales de polígonos, contornos y fusiones.
* **`Pillow`**, **`opencv-python` (`cv2`)** y **`numpy`**: Requeridos para funciones experimentales de conversión de imágenes (matrices de píxeles) a código numérico.

---

## 💻 Instalación de Firmware (GRBL) y Hardware

Para que este software funcione, tu máquina debe estar controlada por un **Arduino UNO** (o compatible) con una **CNC Shield V3** ejecutando el firmware **GRBL v1.1**. 

### Pasos para preparar el Hardware y Firmware:

1. **Descargar GRBL:**
   * Ve al repositorio oficial de GRBL en GitHub: [grbl/grbl](https://github.com/gnea/grbl)
   * Descarga el proyecto como un archivo `.zip`.

2. **Instalar GRBL en Arduino IDE:**
   * Abre el Arduino IDE.
   * Ve a `Programa` -> `Incluir Librería` -> `Añadir biblioteca .ZIP...` y selecciona el archivo descargado.
   * Ve a `Archivo` -> `Ejemplos` -> `grbl` -> `grblUpload`.
   * Conecta tu Arduino UNO por USB, selecciona la placa y puerto correctos en el IDE, y presiona **Subir**.

3. **Ensamblaje Electrónico:**
   * Monta la **CNC Shield V3** sobre el Arduino UNO.
   * Inserta los **Drivers de los motores paso a paso** (A4988 o DRV8825) en los zócalos de los ejes X, Y y Z. *Asegúrate de instalarlos con la orientación correcta para evitar daños eléctricos.*
   * Conecta los motores paso a paso y la fuente de alimentación externa (12V - 24V) a la bornera de la CNC Shield.

---

## 📚 Arquitectura del Código y Funciones Principales

El software implementa Programación Orientada a Objetos (POO) estructurada dentro de la clase principal `CNCControlApp`:

### 1. Interfaz y Estado de Seguridad
* `crear_interfaz(self)`: Construye los controles empleando Tkinter, con lógica de inhabilitación dinámica de botones durante el ruteo para evitar que el operario mande comandos manuales en medio de un trabajo en curso.

### 2. Comunicación y Control CNC
* `conectar_grbl(self)`: Inicializa la conexión por puerto serial físico, desbloquea GRBL enviando el comando `$X` y sincroniza las posiciones lógicas.
* `mover_manual(self, eje, distancia)`: Envía comandos instantáneos en modo incremental (`G91 G0`) para el control de los ejes de la máquina.
* `enviar_comando_grbl(self, comando)`: Interfaz central de envío de strings hacia la CNC con control síncrono de respuesta de confirmación (`ok`/`error`).

### 3. Motor CAM y Geometría Computacional (El Núcleo Científico)
* `generar_gcode_aislamiento(...)`: 
  * Calcula el diámetro efectivo si la broca es cónica (V-Bit) mediante trigonometría.
  * Realiza limpieza espacial: filtra "cruces" de relleno internas de pads cargados en el Gerber para evitar pasadas de corte innecesarias que debiliten mecánicamente el cobre de la placa.
  * Estira ligeramente las pistas (`dist_ext = 0.4`) para asegurar una interconexión física robusta entre las líneas y los pads circulares/rectangulares.
  * Genera trayectorias de aislamiento en bucle (`num_pasadas`) mediante offsets sucesivos usando `.buffer()` geométrico de `shapely`.
* `generar_corte_borde(self)`: Escanea las dimensiones extremas del circuito, añade una holgura segura de 2 mm de margen a la redonda y genera un contorno G-Code progresivo de corte con descenso controlado por pasadas en el eje Z (`paso_z = 0.5`).

### 4. Ejecución en Paralelo y Registro Científico
* `iniciar_ruteo(self)` y `hilo_enviar_gcode(self)`: Ejecuta la transmisión de instrucciones G-Code en un hilo separado de la interfaz gráfica. Esto garantiza que la GUI no se congele y responda de inmediato al botón de **Parada de Emergencia**.
* **Módulo Métrico:** Al terminar con éxito un ruteo, calcula la diferencia temporal exacta (`time.time() - self.tiempo_inicio_ruteo`), muestra los resultados en la interfaz y escribe el historial detallado en `Resultados_Tesis_Log.txt`.

---

## ⚙️ Guía de Operación Paso a Paso

1. **Conexión:** Selecciona el puerto serial y baudios (predeterminado 115200) y haz clic en *Conectar e Inicializar*.
2. **Carga de Gerber:** Carga el archivo `.GBR` de pistas. Haz clic en el visualizador derecho para marcar tu "Origen (0,0)" con la cruz roja.
3. **Parámetros CAM:** Abre *2. Configuración CAM*, define el tipo de broca (V-Bit o Cilíndrica), su diámetro físico y las pasadas de aislamiento deseadas. Genera las trayectorias verdes.
4. **Perforación y Borde:** Si es necesario, carga los taladros con *Cargar Perforaciones* (puntos naranjas) y presiona *Generar Corte de Borde* (borde cyan).
5. **Calibración Física:** Mueve manualmente tu CNC hasta la esquina física de la placa de cobre y haz clic en *Cero XY* y *Cero Z*.
6. **Ejecución:** Haz clic en *▶ Iniciar Grabado PCB*. Sigue el rastro del mecanizado en tiempo real en la pantalla izquierda.
7. **Cambio de Herramienta:** Durante las pausas automatizadas (`M0`), la máquina detendrá sus movimientos. Cambia la broca física, reajusta la altura con *Cero Z* y presiona *⏯ Continuar* para reanudar el trabajo.
