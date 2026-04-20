# Control CNC PCB - Generador CAM y Monitor en Tiempo Real

Este proyecto es una interfaz gráfica de usuario (GUI) desarrollada en Python con Tkinter para el control de máquinas CNC, enfocada específicamente en el ruteo y grabado de placas de circuito impreso (PCB). 

El software permite conectarse a una máquina con firmware GRBL, controlar sus ejes manualmente, cargar archivos Gerber y de perforación, generar el G-Code de aislamiento (CAM) automáticamente, y monitorear el proceso de corte con visualizadores en pantalla.

## 🚀 Características Principales

* **Comunicación Serial:** Conexión directa con GRBL seleccionando el puerto COM y los baudios.
* **Control Manual (Jog):** Botones para mover los ejes X, Y, Z y establecer ceros de trabajo.
* **Procesamiento de Archivos Gerber y Excellon:** Lectura e interpretación de archivos `.GBR` para pistas y carga de coordenadas de perforación para los agujeros de los componentes.
* **Motor CAM Integrado:** Generación de rutas de aislamiento (isolation routing) utilizando matemáticas geométricas para rodear las pistas de cobre.
* **Manejo de Herramientas (Tool Change):** Generación de pausas automáticas (`M0`) entre el ruteo y la perforación para permitir el cambio de broca en V a broca cilíndrica.
* **Corte de Borde:** Generación automática de trayectorias para recortar el perímetro final de la placa PCB.
* **Seguridad y Control:** Botón de parada de emergencia (STOP) que detiene la máquina y eleva el eje Z, junto con un sistema de reanudación segura.
* **Monitores de Visualización:** * **Monitor de Referencia:** Muestra el diseño original en azul cyan, las perforaciones y la simulación del corte en verde.
    * **Monitor en Tiempo Real:** Muestra el progreso de la fresa sobre la placa de cobre durante el trabajo físico.
* **Cálculo de Dimensiones:** Detección automática del tamaño real del diseño en milímetros para evitar salir de los límites de la placa.

---

## 🛠️ Requisitos Previos e Instalación del Software

Para ejecutar este software, necesitas tener **Python 3.x** instalado en tu computadora. Además, el programa depende de algunas librerías externas que realizan el cálculo geométrico y la comunicación con la máquina.

### Librerías requeridas:
Abre tu terminal (Símbolo del sistema, PowerShell o la terminal de VS Code) y ejecuta el siguiente comando para instalar las dependencias necesarias:

`pip install pyserial shapely Pillow opencv-python numpy`

* **`pyserial`**: Permite la comunicación por puerto USB/COM entre tu computadora y la placa controladora de la CNC.
* **`shapely`**: Es el "cerebro" matemático del motor CAM. Se usa para crear polígonos, fusionar geometrías y calcular el contorno de aislamiento alrededor de las pistas del Gerber.
* **`Pillow`**, **`opencv-python` (`cv2`)** y **`numpy`**: Librerías de procesamiento visual, necesarias para la función de cargar y convertir imágenes JPG/PNG a trayectorias G-Code.

---

## 💻 Instalación de Firmware (GRBL) y Hardware

Para que este software funcione, tu máquina debe estar controlada por un **Arduino UNO** (o compatible) con una **CNC Shield V3** ejecutando el firmware **GRBL v1.1**. 

### Pasos para preparar el Hardware y Firmware:

1. **Descargar GRBL:**
   * Ve al repositorio oficial de GRBL en GitHub: [grbl/grbl](https://github.com/gnea/grbl)
   * Descarga el proyecto como un archivo `.zip` (Code -> Download ZIP).

2. **Instalar GRBL en Arduino IDE:**
   * Abre el Arduino IDE en tu computadora.
   * Ve a `Programa` -> `Incluir Librería` -> `Añadir biblioteca .ZIP...` y selecciona el archivo que descargaste.
   * Ve a `Archivo` -> `Ejemplos` -> `grbl` -> `grblUpload`.
   * Conecta tu Arduino UNO por USB, selecciona la placa y el puerto correctos en el IDE, y presiona **Subir**. ¡Tu Arduino ahora es el cerebro de una CNC!

3. **Ensamblaje Electrónico:**
   * Desconecta el Arduino del USB.
   * Monta la **CNC Shield V3** sobre el Arduino UNO, encajando cuidadosamente los pines.
   * Inserta los **Drivers de los motores paso a paso** (ej. A4988 o DRV8825) en los zócalos correspondientes a los ejes X, Y y Z. *Asegúrate de instalarlos en la orientación correcta para no quemarlos.*
   * Conecta los motores paso a paso a la Shield.
   * Conecta una fuente de alimentación adecuada (ej. 12V o 24V) a los bornes de potencia de la CNC Shield.

4. **Calibración inicial:**
   * Puedes usar el botón de "⚙️ Configuración GRBL" de este software para ajustar los pasos por milímetro de tus motores (parámetros `$100`, `$101`, `$102` en GRBL) según la transmisión mecánica (correas o husillos) de tu máquina.

---

## 📚 Arquitectura del Código y Funciones Principales

El código está estructurado mediante Programación Orientada a Objetos (POO) bajo la clase `CNCControlApp`. A continuación, se detallan las funciones más importantes y lo que hacen:

### 1. Interfaz y Configuración
* `__init__(self, root)`: Inicializa la aplicación, configura la ventana principal y llama a la creación de la interfaz.
* `crear_interfaz(self)`: Construye todos los elementos visuales (botones, etiquetas, canvas) usando Tkinter y los empaqueta en la pantalla.

### 2. Comunicación y Control CNC
* `conectar_serial(self)`: Abre el puerto COM seleccionado e inicia la comunicación con GRBL.
* `mover_jog(self, eje, direccion)`: Envía comandos G-code de movimiento manual (`G91 G0`) a la máquina basados en los botones de la interfaz.
* `fijar_cero(self, ejes)`: Envía el comando (ej. `G92 X0 Y0`) para decirle a la máquina que su posición actual es el nuevo cero de trabajo.

### 3. Procesamiento de Archivos y CAM
* `cargar_gerber(self)`: Abre un cuadro de diálogo para seleccionar un archivo `.GBR`. Lee las coordenadas de las líneas, las escala y las dibuja (en color cyan) en el Monitor de Referencia.
* `cargar_perforaciones(self)`: Extrae las coordenadas de un archivo de taladros para generar agujeros, uniéndolos al mismo origen del Gerber.
* `fijar_origen_clic(self, event)`: Detecta el clic izquierdo del mouse en el monitor derecho. Convierte los píxeles de la pantalla a coordenadas reales de la PCB, guarda ese punto como el nuevo origen `(0,0)` y dibuja una cruz roja.
* `generar_gcode_aislamiento(self, diametro_broca, z_corte, z_seguro, feedrate)`:
    * Toma las coordenadas puras del Gerber y las ajusta restando el origen seleccionado por el usuario.
    * Usa `shapely` (`LineString` y `unary_union`) para fusionar las líneas.
    * Aplica un `.buffer()` para "engordar" la línea según el ancho de la pista y el radio de la broca.
    * Extrae el contorno exterior (`exterior.coords`) y lo traduce a instrucciones de coordenadas de corte (`G1`).
* `dibujar_rutas_gcode_en_canvas(self)`: Lee la lista de G-code generada, extrae las posiciones X e Y usando expresiones regulares (`re`), le suma el origen para cuadrar la vista, y dibuja las rutas generadas en color verde sobre el Monitor de Referencia.
* `calcular_dimensiones_gcode(self)`: Escanea el G-code generado buscando el valor máximo y mínimo de X e Y. Con esto, calcula y muestra en pantalla el ancho y alto total en milímetros del trabajo final.

### 4. Ejecución y Seguridad
* `iniciar_grabado(self)`: Lee línea por línea el G-Code final y lo envía a la CNC por el puerto serial. A medida que la máquina responde "ok", actualiza el Monitor en Tiempo Real pintando el rastro azul del recorrido de la broca.
* `detener_ruteo(self)`: Detiene el proceso inmediatamente enviando un comando de interrupción (`\x18`), cancela las alarmas y eleva el husillo a una posición segura.
* `reanudar_maquina(self)`: Envía el comando de ciclo de inicio (`~`) para despertar a la máquina de una pausa `M0` programada tras haber realizado un cambio físico de broca.

---

## ⚙️ Cómo usar el programa

1. **Conexión:** Selecciona tu puerto COM, elige los baudios (normalmente 115200 para GRBL) y haz clic en *Conectar e Inicializar*.
2. **Carga de Archivos:** Carga tu archivo de pistas `.GBR` desde el botón *1. Cargar Gerber*. Tu diseño aparecerá a la derecha en color cyan. Si tienes huecos pasantes, carga tu archivo de taladros con *Cargar Perforaciones*.
3. **Selección de Origen:** Haz clic en el monitor derecho sobre la esquina de tu diseño donde quieras que comience el corte físico. Aparecerá una cruz roja de "Origen (0,0)".
4. **Generación de G-Code:** Ve a *2. Configuración CAM* e introduce los parámetros de tu fresa (diámetro, profundidad de corte). Se dibujarán líneas verdes confirmando la ruta de aislamiento y verás las dimensiones reales en la etiqueta de la barra superior.
5. **Preparación Física:** Usa los botones de control Jog para llevar la punta de tu máquina a la esquina de tu placa de cobre y presiona *Cero XY* y *Cero Z*.
6. **A Cortar:** Presiona *▶ Iniciar Grabado PCB*. Observa cómo el monitor izquierdo traza el movimiento real de la máquina.
7. **Cambio de Herramienta:** Si añadiste perforaciones, la máquina se detendrá al terminar de grabar pistas. Cambia la broca en V por una broca de perforación, reestablece el *Cero Z* y presiona *⏯ Continuar (Cambio Broca)* para terminar el trabajo.
