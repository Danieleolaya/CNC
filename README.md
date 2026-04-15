# Control CNC PCB - Generador CAM y Monitor en Tiempo Real

Este proyecto es una interfaz gráfica de usuario (GUI) desarrollada en Python con Tkinter para el control de máquinas CNC, enfocada específicamente en el ruteo y grabado de placas de circuito impreso (PCB). 

El software permite conectarse a una máquina con firmware GRBL, controlar sus ejes manualmente, cargar archivos Gerber, generar el G-Code de aislamiento (CAM) automáticamente, y monitorear el proceso de corte con visualizadores en pantalla.

## 🚀 Características Principales

* **Comunicación Serial:** Conexión directa con GRBL seleccionando el puerto COM y los baudios.
* **Control Manual (Jog):** Botones para mover los ejes X, Y, Z y establecer ceros de trabajo.
* **Procesamiento de Archivos Gerber:** Lectura e interpretación de archivos `.GBR`.
* **Motor CAM Integrado:** Generación de rutas de aislamiento (isolation routing) utilizando matemáticas geométricas para rodear las pistas de cobre.
* **Monitores de Visualización:** * **Monitor de Referencia:** Muestra el diseño original en azul cyan y la simulación del corte en verde.
    * **Monitor en Tiempo Real:** Muestra el progreso de la fresa sobre la placa de cobre durante el trabajo físico.
* **Cálculo de Dimensiones:** Detección automática del tamaño real del diseño en milímetros para evitar salir de los límites de la placa.

---

## 🛠️ Requisitos Previos e Instalación

Para ejecutar este software, necesitas tener **Python 3.x** instalado en tu computadora. Además, el programa depende de algunas librerías externas que realizan el cálculo geométrico y la comunicación con la máquina.

### Librerías requeridas:
Abre tu terminal (Símbolo del sistema, PowerShell o la terminal de VS Code) y ejecuta el siguiente comando para instalar las dependencias necesarias:

```bash
pip install pyserial shapely Pillow
