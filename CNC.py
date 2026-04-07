import tkinter as tk
from tkinter import filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import re

class CNCControlApp:
    def __init__(self, root):
        """
        Constructor de la clase (Equivalente en C++: CNCControlApp()).
        Aquí inicializamos las variables y la interfaz gráfica.
        """
        self.root = root
        self.root.title("Software de Control CNC - Proyecto de Grado")
        self.root.geometry("900x600")

        # Variables de estado (Equivalente a variables privadas en C++)
        self.puerto_serial = None
        self.gcode_lista = []
        self.conectado = False

        self.crear_interfaz()

    def crear_interfaz(self):
        """Crea los botones y el área visual de la aplicación."""
        # --- Panel de Controles (Izquierda) ---
        panel_control = tk.Frame(self.root, width=250, bg="#f0f0f0")
        panel_control.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(panel_control, text="Puerto Serial (Arduino):").pack(pady=5)
        
        # Buscar puertos disponibles
        puertos = [puerto.device for puerto in serial.tools.list_ports.comports()]
        self.puerto_seleccionado = tk.StringVar()
        if puertos:
            self.puerto_seleccionado.set(puertos[0])
        
        self.menu_puertos = tk.OptionMenu(panel_control, self.puerto_seleccionado, *puertos if puertos else ["Ninguno"])
        self.menu_puertos.pack(pady=5)

        self.btn_conectar = tk.Button(panel_control, text="Conectar GRBL", command=self.conectar_grbl, bg="lightblue")
        self.btn_conectar.pack(pady=10, fill=tk.X)

        self.btn_cargar = tk.Button(panel_control, text="Cargar Archivo Gerber", command=self.cargar_gerber)
        self.btn_cargar.pack(pady=10, fill=tk.X)

        self.btn_iniciar = tk.Button(panel_control, text="Iniciar Ruteo", command=self.iniciar_ruteo, bg="lightgreen", state=tk.DISABLED)
        self.btn_iniciar.pack(pady=10, fill=tk.X)
        
        self.btn_detener = tk.Button(panel_control, text="Detener (Parada de Emergencia)", command=self.detener_ruteo, bg="salmon")
        self.btn_detener.pack(pady=10, fill=tk.X)

        self.lbl_estado = tk.Label(panel_control, text="Estado: Desconectado", fg="red")
        self.lbl_estado.pack(side=tk.BOTTOM, pady=20)

        # --- Panel de Visualización (Derecha) ---
        panel_visual = tk.Frame(self.root)
        panel_visual.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(panel_visual, text="Visualización en Tiempo Real de Trayectoria").pack()
        # Canvas es un lienzo donde dibujaremos las líneas como si fuera la herramienta de la CNC
        self.canvas = tk.Canvas(panel_visual, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def conectar_grbl(self):
        """Establece comunicación serial con el Arduino que contiene GRBL."""
        puerto = self.puerto_seleccionado.get()
        if puerto == "Ninguno":
            messagebox.showerror("Error", "No se encontraron puertos COM.")
            return

        try:
            # GRBL trabaja por defecto a 115200 baudios
            self.puerto_serial = serial.Serial(puerto, 115200, timeout=1)
            # Despertar a GRBL enviando enter
            self.puerto_serial.write(b"\r\n\r\n")
            time.sleep(2)  # Esperar a que inicialice
            self.puerto_serial.flushInput()
            
            self.conectado = True
            self.lbl_estado.config(text=f"Estado: Conectado a {puerto}", fg="green")
            self.btn_conectar.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar: {e}")

    def cargar_gerber(self):
        """Abre un archivo Gerber, extrae las coordenadas y genera G-code en memoria."""
        ruta_archivo = filedialog.askopenfilename(title="Seleccionar archivo Gerber", filetypes=(("Gerber Files", "*.gbr *.gtl *.gbl"), ("All Files", "*.*")))
        if not ruta_archivo:
            return

            self.gcode_lista.clear()
            self.canvas.delete("all") # Limpiar visualizador
        
        # PROCESAMIENTO GERBER A G-CODE DIRECTO (Cumpliendo el requerimiento de no usar apps externas)
        # Nota: El estándar Gerber RS-274X es muy complejo. Este es un parseador simplificado
        # que extrae comandos de movimiento lineal (X... Y... D01/D02).
        
        with open(ruta_archivo, 'r') as f:
            lineas_gerber = f.readlines()

        self.gcode_lista.append("G21") # Configurar en milímetros
        self.gcode_lista.append("G90") # Coordenadas absolutas
        self.gcode_lista.append("M3 S1000") # Encender husillo (spindle)

        coord_x = 0
        coord_y = 0
        
        for linea in lineas_gerber:
            # Expresiones regulares para encontrar X e Y en el Gerber
            match_x = re.search(r'X([\+\-]?\d+)', linea)
            match_y = re.search(r'Y([\+\-]?\d+)', linea)
            
            if match_x or match_y:
                # El formato Gerber suele multiplicar por 10000 o 100000, dividimos para obtener mm
                # (Se debe ajustar este divisor según la resolución generada por tu software de diseño PCB)
                divisor = 10000.0 
                if match_x: coord_x = float(match_x.group(1)) / divisor
                if match_y: coord_y = float(match_y.group(1)) / divisor

                # D01 es corte/movimiento de trabajo (G1), D02 es movimiento rápido sin corte (G0)
                if 'D01' in linea:
                    self.gcode_lista.append(f"G1 X{coord_x:.3f} Y{coord_y:.3f} F200") # F200 es la velocidad
                    # Dibujar en el canvas (Multiplicamos por 5 para escalar visualmente en la pantalla)
                    self.canvas.create_oval(coord_x*5, coord_y*5, (coord_x*5)+2, (coord_y*5)+2, fill="white", outline="white")
                elif 'D02' in linea:
                    self.gcode_lista.append(f"G0 X{coord_x:.3f} Y{coord_y:.3f}")
        
        self.gcode_lista.append("M5") # Apagar husillo
        self.gcode_lista.append("G0 X0 Y0") # Volver al origen

        messagebox.showinfo("Éxito", f"Archivo Gerber cargado y traducido. {len(self.gcode_lista)} comandos generados.")
        if self.conectado:
            self.btn_iniciar.config(state=tk.NORMAL)

    def iniciar_ruteo(self):
        """Inicia un hilo (thread) separado para no congelar la interfaz mientras se envía a GRBL."""
        self.btn_iniciar.config(state=tk.DISABLED)
        # Usamos threading igual que en C++ (std::thread) para tareas asíncronas
        hilo_envio = threading.Thread(target=self.hilo_enviar_gcode)
        hilo_envio.start()

    def hilo_enviar_gcode(self):
        """Función que envía línea por línea a GRBL esperando el 'ok'."""
        for comando in self.gcode_lista:
            # Para visualizar el avance, imprimimos en consola
            print(f"Enviando: {comando}") 
            
            comando_bytes = (comando + '\n').encode('utf-8')
            self.puerto_serial.write(comando_bytes)
            
            # Esperar respuesta de GRBL (Handshake)
            respuesta = self.puerto_serial.readline().decode('utf-8').strip()
            while "ok" not in respuesta and "error" not in respuesta:
                respuesta = self.puerto_serial.readline().decode('utf-8').strip()

            if "error" in respuesta:
                print(f"GRBL reportó un error con el comando: {comando}")
        
        self.btn_iniciar.config(state=tk.NORMAL)
        messagebox.showinfo("Proceso Terminado", "El ruteo de la PCB ha finalizado con éxito.")

    def detener_ruteo(self):
        """Parada de emergencia (Soft Reset en GRBL)."""
        if self.conectado:
            # Comando especial de GRBL para parada inmediata (Ctrl+X)
            self.puerto_serial.write(b'\x18') 
            messagebox.showwarning("Emergencia", "Proceso detenido por el usuario.")

# Ejecución principal de la aplicación (Equivalente al int main() de C++)
if __name__ == "__main__":
    ventana_principal = tk.Tk()
    app = CNCControlApp(ventana_principal)
    ventana_principal.mainloop() # Bucle infinito que mantiene la interfaz abierta