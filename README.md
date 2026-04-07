# CNC

**1. Preparación del Entorno (Visual Studio Code)**
Para trabajar este proyecto en Visual Studio Code (VS Code) tanto en Windows 11 como en Linux, no necesitas herramientas externas pesadas.

Extensiones obligatorias en VS Code:

Python (desarrollada por Microsoft): Es la extensión base que incluye IntelliSense, linting y soporte para depuración.

Pylance: Viene incluida con la extensión de Python, mejora la velocidad de autocompletado y revisión de errores (similar al compilador estricto de C++).

**Librerías a instalar:**
Abre la terminal de VS Code y ejecuta el siguiente comando. Solo necesitamos pyserial para la comunicación por puertos COM (Windows) o /dev/ttyACM0 (Linux) con tu Arduino. La librería de interfaz gráfica (tkinter) ya viene instalada por defecto en Python.

Bash
pip install pyserial

**2. Código del Software de Control (Python)**
Este código está diseñado para ser directo, sin módulos innecesarios. Transforma coordenadas básicas de un archivo Gerber a G-Code en memoria, dibuja la trayectoria en una interfaz gráfica y se comunica con GRBL.

Nota didáctica: En Python, no declaramos el tipo de variable (como int o float en C++), el lenguaje lo infiere. Además, el self es el equivalente al puntero this en C++

**CODIGO**

**3. Preparación para Sustentación ante Jurados (Preguntas "Corchadoras")**
  
Dado que tu objetivo es aprobar la tecnología en electrónica industrial  y evitar que los jurados cuestionen la validez técnica de tu desarrollo, he preparado respuestas a las preguntas críticas más probables:

- **Pregunta del Jurado**: "Python no es un lenguaje de tiempo real. Su interfaz gráfica y procesamiento están sometidos al Global Interpreter Lock (GIL). ¿Cómo garantiza que la máquina no sufra retrasos o pierda pasos durante el ruteo de la PCB si el computador se queda pegado?
  
      "Tu respuesta: "El requerimiento de tiempo real crítico (hard real-time) para la generación de los pulsos hacia los motores paso a paso no es responsabilidad de Python. Esa tarea la ejecuta el microcontrolador (Arduino Uno) mediante su timer por interrupciones de hardware operando con el firmware GRBL. El software en Python trabaja como un despachador de 'alto nivel' (soft real-time) enviando comandos G-Code. El envío se maneja mediante handshaking (GRBL envía un "ok" cuando su buffer interno tiene espacio). Por lo tanto, incluso si Python presenta latencia, el Arduino tiene suficientes comandos en buffer para mantener el movimiento fluido y sin perder pasos."

- Pregunta del Jurado: "Usted afirma que no usó aplicaciones externas como FlatCAM o CopperCAM y que sube el archivo Gerber directamente. El formato RS-274X de los archivos Gerber es extremadamente complejo, involucra macros, flashes de aperturas y compensación de herramienta. ¿Cómo resolvió todo eso en su código Python?
      "Tu respuesta: "Para la validación del prototipo, implementé un algoritmo de análisis léxico iterativo que extrae directamente las primitivas geométricas del formato Gerber, específicamente las macros de interpolación lineal (D01 para dibujo y D02 para desplazamiento). Sin embargo, hay que acotar que este es un proyecto a nivel tecnológico de la Universidad ECCI. Desarrollar un compilador Gerber completo abarca años de desarrollo de software. Mi código demuestra la arquitectura de un sistema embebido que lee las coordenadas base X/Y de un archivo de texto y las transforma en desplazamientos vectoriales (G0 y G1) de manera directa en memoria."

- **Pregunta del Jurado:** "El proyecto dice enfocarse en solucionar problemas de costos frente a alternativas externas como JLCPCB. Pero las PCBs tienen agujeros para los componentes (Through-Hole) y archivos Excellon para los taladros. Su código actual solo lee archivos Gerber. ¿Cómo haría la perforación?"Tu respuesta: "El presente prototipo es la base funcional del ruteado. Los archivos Excellon (NC Drill) se basan en el mismo principio de coordenadas absolutas que el G-Code y los archivos Gerber. La escalabilidad de mi código, al estar orientado a objetos, me permite crear fácilmente un nuevo método (una nueva función en la clase Python) que lea los comandos 'T' (Tool) y coordenadas 'X Y' del archivo de perforación y los envíe de manera idéntica al microcontrolador usando los ejes motorizados ya implementados en la estructura."
