import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time
import re
import os

class CNCControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Software de Control CNC - Proyecto de Grado")
        self.root.geometry("1300x700") # Ventana más ancha para acomodar los dos lienzos

        # Variables de estado
        self.puerto_serial = None
        self.gcode_lista = []
        self.conectado = False
        self.archivo_cargado = False

        # Variables de visualización
        self.escala_visual = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.cursor_herramienta = None 

        self.crear_interfaz()

    def crear_interfaz(self):
        # --- PANEL DE CONTROLES (Izquierda) ---
        panel_control = tk.Frame(self.root, width=300, bg="#f0f0f0")
        panel_control.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # 1. Conexión
        tk.Label(panel_control, text="1. CONEXIÓN", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=(5,0))
        puertos = [puerto.device for puerto in serial.tools.list_ports.comports()]
        self.puerto_seleccionado = tk.StringVar(value=puertos[0] if puertos else "Ninguno")
        tk.OptionMenu(panel_control, self.puerto_seleccionado, *puertos if puertos else ["Ninguno"]).pack(pady=5)
        
        self.btn_conectar = tk.Button(panel_control, text="Conectar e Inicializar GRBL", command=self.conectar_grbl, bg="lightblue")
        self.btn_conectar.pack(pady=5, fill=tk.X)

        self.btn_config = tk.Button(panel_control, text="⚙️ Configuración GRBL", command=self.abrir_configuracion, state=tk.DISABLED)
        self.btn_config.pack(pady=5, fill=tk.X)

        # 2. Control Manual
        self.frame_manual = tk.LabelFrame(panel_control, text="2. CONTROL MANUAL (Jog)", bg="#f0f0f0")
        self.frame_manual.pack(pady=10, fill=tk.X)
        
        tk.Button(self.frame_manual, text="Y+", width=5, command=lambda: self.mover_manual("Y", 10)).grid(row=0, column=1, pady=2)
        tk.Button(self.frame_manual, text="X-", width=5, command=lambda: self.mover_manual("X", -10)).grid(row=1, column=0, padx=2)
        tk.Button(self.frame_manual, text="X+", width=5, command=lambda: self.mover_manual("X", 10)).grid(row=1, column=2, padx=2)
        tk.Button(self.frame_manual, text="Y-", width=5, command=lambda: self.mover_manual("Y", -10)).grid(row=2, column=1, pady=2)
        tk.Button(self.frame_manual, text="Set Cero (X0 Y0)", bg="yellow", command=self.set_cero_manual).grid(row=3, column=0, columnspan=3, pady=5)

        # 3. Archivos y Ruteo
        tk.Label(panel_control, text="3. ARCHIVO Y RUTEO", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=(15,0))
        self.btn_cargar = tk.Button(panel_control, text="Cargar Archivo Gerber", command=self.cargar_gerber)
        self.btn_cargar.pack(pady=5, fill=tk.X)

        self.lbl_archivo = tk.Label(panel_control, text="Ningún archivo cargado", fg="blue", wraplength=280, bg="#f0f0f0")
        self.lbl_archivo.pack(pady=5)

        self.btn_iniciar = tk.Button(panel_control, text="Iniciar Ruteo", command=self.iniciar_ruteo, bg="lightgreen", state=tk.DISABLED)
        self.btn_iniciar.pack(pady=5, fill=tk.X)
        
        self.btn_detener = tk.Button(panel_control, text="Parada de Emergencia", command=self.detener_ruteo, bg="salmon")
        self.btn_detener.pack(pady=5, fill=tk.X)

        self.lbl_estado = tk.Label(panel_control, text="Estado: Desconectado", fg="red", font=("Arial", 10, "bold"), bg="#f0f0f0")
        self.lbl_estado.pack(side=tk.BOTTOM, pady=20)

        # --- PANEL DE VISUALIZACIÓN (Derecha - Dividido en dos) ---
        panel_visual = tk.Frame(self.root)
        panel_visual.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Lienzo 1: Vista Previa
        marco_ref = tk.LabelFrame(panel_visual, text="Vista Previa (Diseño Original)", font=("Arial", 10, "bold"))
        marco_ref.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.canvas_ref = tk.Canvas(marco_ref, bg="black")
        self.canvas_ref.pack(fill=tk.BOTH, expand=True)

        # Lienzo 2: Trazado en Vivo
        marco_rt = tk.LabelFrame(panel_visual, text="Trazado en Vivo (Tiempo Real CNC)", font=("Arial", 10, "bold"))
        marco_rt.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.canvas_rt = tk.Canvas(marco_rt, bg="black")
        self.canvas_rt.pack(fill=tk.BOTH, expand=True)

    def enviar_comando_grbl(self, comando, esperar_respuesta=True):
        if self.puerto_serial and self.conectado:
            self.puerto_serial.write((comando + '\n').encode('utf-8'))
            if esperar_respuesta:
                time.sleep(0.1) 
                return self.puerto_serial.read_all().decode('utf-8')
        return ""

    def conectar_grbl(self):
        puerto = self.puerto_seleccionado.get()
        if puerto == "Ninguno":
            messagebox.showerror("Error", "Seleccione un puerto válido.")
            return
        try:
            self.puerto_serial = serial.Serial(puerto, 115200, timeout=1)
            self.puerto_serial.write(b"\r\n\r\n")
            time.sleep(2)
            self.puerto_serial.flushInput()
            self.conectado = True
            
            self.enviar_comando_grbl("$X") 
            self.enviar_comando_grbl("$130=190") 
            self.enviar_comando_grbl("$131=190") 
            self.enviar_comando_grbl("$20=1")    
            self.enviar_comando_grbl("G92 X0 Y0 Z0")

            self.lbl_estado.config(text=f"Conectado: {puerto} | 19x19cm", fg="green")
            self.btn_conectar.config(state=tk.DISABLED)
            self.btn_config.config(state=tk.NORMAL)
            self.actualizar_estado_manual()
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"Error: {e}")

    def abrir_configuracion(self):
        if not self.conectado: return
        vent_conf = tk.Toplevel(self.root)
        vent_conf.title("Configuración Interna de GRBL")
        vent_conf.geometry("400x400")

        tk.Label(vent_conf, text="Consola GRBL (Ej. ingresa $$ para ver config):").pack(pady=5)
        txt_consola = scrolledtext.ScrolledText(vent_conf, width=45, height=15)
        txt_consola.pack(pady=5)

        self.puerto_serial.flushInput()
        respuesta = self.enviar_comando_grbl("$$")
        txt_consola.insert(tk.END, respuesta)

        frame_envio = tk.Frame(vent_conf)
        frame_envio.pack(pady=5)
        
        entrada_cmd = tk.Entry(frame_envio, width=25)
        entrada_cmd.pack(side=tk.LEFT, padx=5)

        def enviar_cmd():
            cmd = entrada_cmd.get()
            resp = self.enviar_comando_grbl(cmd)
            txt_consola.insert(tk.END, f"\n> {cmd}\n{resp}")
            entrada_cmd.delete(0, tk.END)

        tk.Button(frame_envio, text="Enviar", command=enviar_cmd).pack(side=tk.LEFT)

    def mover_manual(self, eje, distancia):
        if self.conectado and not self.archivo_cargado:
            comando = f"G91 G0 {eje}{distancia} \n G90"
            self.enviar_comando_grbl(comando, esperar_respuesta=False)

    def set_cero_manual(self):
        if self.conectado:
            self.enviar_comando_grbl("G92 X0 Y0", esperar_respuesta=False)
            messagebox.showinfo("Set Cero", "Posición actual establecida como Origen (X0 Y0).")

    def actualizar_estado_manual(self):
        estado = tk.DISABLED if self.archivo_cargado else tk.NORMAL
        for widget in self.frame_manual.winfo_children():
            widget.configure(state=estado)

    def cargar_gerber(self):
        ruta_archivo = filedialog.askopenfilename(title="Seleccionar archivo Gerber", filetypes=(("Gerber", "*.gbr *.gtl *.gbl"), ("Todos", "*.*")))
        if not ruta_archivo:
            return

        nombre_archivo = os.path.basename(ruta_archivo)
        self.lbl_archivo.config(text=f"Archivo: {nombre_archivo}")
        
        self.archivo_cargado = True
        self.actualizar_estado_manual()

        self.gcode_lista.clear()
        # Limpiar ambos lienzos y resetear el cursor
        self.canvas_ref.delete("all")
        self.canvas_rt.delete("all")
        self.cursor_herramienta = None
        
        with open(ruta_archivo, 'r') as f:
            lineas_gerber = f.readlines()

        divisor = 10000.0 
        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')

        for linea in lineas_gerber:
            match_x = re.search(r'X([\+\-]?\d+)', linea)
            match_y = re.search(r'Y([\+\-]?\d+)', linea)
            if match_x: 
                val_x = float(match_x.group(1)) / divisor
                min_x, max_x = min(min_x, val_x), max(max_x, val_x)
            if match_y:
                val_y = float(match_y.group(1)) / divisor
                min_y, max_y = min(min_y, val_y), max(max_y, val_y)

        self.root.update_idletasks()
        # Usamos el ancho y alto del lienzo de referencia para escalar
        ancho_canvas = self.canvas_ref.winfo_width()
        alto_canvas = self.canvas_ref.winfo_height()

        rango_x = (max_x - min_x) if (max_x - min_x) > 0 else 1
        rango_y = (max_y - min_y) if (max_y - min_y) > 0 else 1

        escala_x = (ancho_canvas - 80) / rango_x
        escala_y = (alto_canvas - 80) / rango_y

        self.escala_visual = min(escala_x, escala_y)

        self.offset_x = 40 - (min_x * self.escala_visual)
        self.offset_y = alto_canvas - 40 + (min_y * self.escala_visual) 

        self.gcode_lista.append("G21\nG90\nM3 S1000") 

        prev_x, prev_y = 0.0, 0.0
        for linea in lineas_gerber:
            match_x = re.search(r'X([\+\-]?\d+)', linea)
            match_y = re.search(r'Y([\+\-]?\d+)', linea)
            
            coord_x = float(match_x.group(1)) / divisor if match_x else prev_x
            coord_y = float(match_y.group(1)) / divisor if match_y else prev_y

            if 'D01' in linea or 'D1*' in linea:
                self.gcode_lista.append(f"G1 X{coord_x:.3f} Y{coord_y:.3f} F200")
                px1 = (prev_x * self.escala_visual) + self.offset_x
                py1 = self.offset_y - (prev_y * self.escala_visual)
                px2 = (coord_x * self.escala_visual) + self.offset_x
                py2 = self.offset_y - (coord_y * self.escala_visual)
                
                # Dibujamos SOLO en la pantalla de Vista Previa
                self.canvas_ref.create_line(px1, py1, px2, py2, fill="#00FF00", width=1)
                
            elif 'D02' in linea or 'D2*' in linea:
                self.gcode_lista.append(f"G0 X{coord_x:.3f} Y{coord_y:.3f}")
            
            prev_x, prev_y = coord_x, coord_y

        self.gcode_lista.append("M5\nG0 X0 Y0")

        if self.conectado:
            self.btn_iniciar.config(state=tk.NORMAL)

    def iniciar_ruteo(self):
        self.btn_iniciar.config(state=tk.DISABLED)
        self.pos_previa_x = None
        self.pos_previa_y = None
        threading.Thread(target=self.hilo_enviar_gcode, daemon=True).start()

    def actualizar_cursor_tiempo_real(self, comando):
        match_x = re.search(r'X([\+\-]?\d+\.?\d*)', comando)
        match_y = re.search(r'Y([\+\-]?\d+\.?\d*)', comando)
        
        if match_x and match_y:
            coord_x = float(match_x.group(1))
            coord_y = float(match_y.group(1))
            
            px = (coord_x * self.escala_visual) + self.offset_x
            py = self.offset_y - (coord_y * self.escala_visual)
            
            if self.pos_previa_x is not None and self.pos_previa_y is not None:
                if 'G1' in comando:
                    # Dibujamos el trazado SOLO en la pantalla en Vivo
                    self.canvas_rt.create_line(self.pos_previa_x, self.pos_previa_y, px, py, fill="cyan", width=3)
            
            self.pos_previa_x, self.pos_previa_y = px, py

            # El cursor de la herramienta se dibuja SOLO en la pantalla en Vivo
            if self.cursor_herramienta is None:
                self.cursor_herramienta = self.canvas_rt.create_oval(px-6, py-6, px+6, py+6, fill="red")
            else:
                self.canvas_rt.coords(self.cursor_herramienta, px-6, py-6, px+6, py+6)
                self.canvas_rt.tag_raise(self.cursor_herramienta)

    def hilo_enviar_gcode(self):
        for comando in self.gcode_lista:
            comando_bytes = (comando + '\n').encode('utf-8')
            self.puerto_serial.write(comando_bytes)
            self.root.after(0, self.actualizar_cursor_tiempo_real, comando)
            
            respuesta = self.puerto_serial.readline().decode('utf-8').strip()
            while "ok" not in respuesta and "error" not in respuesta:
                respuesta = self.puerto_serial.readline().decode('utf-8').strip()

        self.btn_iniciar.config(state=tk.NORMAL)
        self.archivo_cargado = False
        self.root.after(0, self.actualizar_estado_manual)
        messagebox.showinfo("Terminado", "El ruteo ha finalizado con éxito.")

    def detener_ruteo(self):
        if self.conectado:
            self.puerto_serial.write(b'\x18') 
            messagebox.showwarning("Emergencia", "Proceso detenido. Máquina reiniciada (Soft Reset).")

if __name__ == "__main__":
    ventana_principal = tk.Tk()
    app = CNCControlApp(ventana_principal)
    ventana_principal.mainloop()