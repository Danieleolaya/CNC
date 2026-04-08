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
        self.root.title("Control CNC PCB - Sistema de Bloqueo de Seguridad")
        self.root.geometry("1400x750")

        # Variables de estado
        self.puerto_serial = None
        self.gcode_lista = []
        self.conectado = False
        self.archivo_cargado = False
        self.ruteo_activo = False

        # Parámetros de Grabado PCB (Eje Z)
        self.Z_SEGURIDAD = 5.0  # Altura para moverse sin tocar la placa
        self.Z_GRABADO = -0.1   # Profundidad de penetración en el cobre
        self.F_CORTE = 150      # Velocidad de avance al grabar

        # Variables de visualización
        self.escala_rt, self.offset_x_rt, self.offset_y_rt = 1.0, 0, 0
        self.escala_ref, self.offset_x_ref, self.offset_y_ref = 1.0, 0, 0
        self.cursor_herramienta = None 

        self.crear_interfaz()

    def crear_interfaz(self):
        # --- PANEL DE CONTROLES (Izquierda) ---
        panel_control = tk.Frame(self.root, width=320, bg="#f0f0f0")
        panel_control.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # 1. Conexión y Baudios
        tk.Label(panel_control, text="1. CONEXIÓN Y SERIAL", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=(5,0))
        
        frame_serial = tk.Frame(panel_control, bg="#f0f0f0")
        frame_serial.pack(pady=5)
        
        puertos = [puerto.device for puerto in serial.tools.list_ports.comports()]
        self.puerto_seleccionado = tk.StringVar(value=puertos[0] if puertos else "Ninguno")
        tk.OptionMenu(frame_serial, self.puerto_seleccionado, *puertos if puertos else ["Ninguno"]).pack(side=tk.LEFT, padx=2)
        
        baudios = ["9600", "19200", "38400", "57600", "115200"]
        self.baudios_seleccionados = tk.StringVar(value="115200")
        tk.OptionMenu(frame_serial, self.baudios_seleccionados, *baudios).pack(side=tk.LEFT, padx=2)
        
        self.btn_conectar = tk.Button(panel_control, text="Conectar e Inicializar", command=self.conectar_grbl, bg="lightblue")
        self.btn_conectar.pack(pady=5, fill=tk.X)

        self.btn_config = tk.Button(panel_control, text="⚙️ Configuración GRBL", command=self.abrir_configuracion, state=tk.DISABLED)
        self.btn_config.pack(pady=5, fill=tk.X)

        # 2. Control Manual (X, Y, Z)
        self.frame_manual = tk.LabelFrame(panel_control, text="2. CONTROL MANUAL (Jog)", bg="#f0f0f0")
        self.frame_manual.pack(pady=10, fill=tk.X, padx=5)
        
        frame_xy = tk.Frame(self.frame_manual, bg="#f0f0f0")
        frame_xy.grid(row=0, column=0, padx=5)
        tk.Button(frame_xy, text="Y+", width=5, command=lambda: self.mover_manual("Y", 10)).grid(row=0, column=1)
        tk.Button(frame_xy, text="X-", width=5, command=lambda: self.mover_manual("X", -10)).grid(row=1, column=0)
        tk.Button(frame_xy, text="X+", width=5, command=lambda: self.mover_manual("X", 10)).grid(row=1, column=2)
        tk.Button(frame_xy, text="Y-", width=5, command=lambda: self.mover_manual("Y", -10)).grid(row=2, column=1)

        frame_z = tk.Frame(self.frame_manual, bg="#f0f0f0")
        frame_z.grid(row=0, column=1, padx=15)
        tk.Button(frame_z, text="Z+ (Subir)", width=8, bg="#e0e0e0", command=lambda: self.mover_manual("Z", 2)).pack(pady=2)
        tk.Button(frame_z, text="Z- (Bajar)", width=8, bg="#e0e0e0", command=lambda: self.mover_manual("Z", -2)).pack(pady=2)

        tk.Button(self.frame_manual, text="Cero XY", bg="yellow", width=8, command=self.set_cero_xy).grid(row=1, column=0, pady=5)
        tk.Button(self.frame_manual, text="Cero Z", bg="#ffcc00", width=8, command=self.set_cero_z).grid(row=1, column=1, pady=5)

        # 3. Archivos y Ruteo
        tk.Label(panel_control, text="3. ARCHIVO Y RUTEO", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=(15,0))
        self.btn_cargar = tk.Button(panel_control, text="Cargar Gerber", command=self.cargar_gerber)
        self.btn_cargar.pack(pady=5, fill=tk.X)

        # Nuevo botón para desbloquear (limpiar archivo)
        self.btn_limpiar = tk.Button(panel_control, text="Descartar Archivo (Desbloquear Manual)", command=self.limpiar_archivo, state=tk.DISABLED, bg="#ffe6e6")
        self.btn_limpiar.pack(pady=2, fill=tk.X)

        self.lbl_archivo = tk.Label(panel_control, text="Sin archivo", fg="blue", bg="#f0f0f0")
        self.lbl_archivo.pack()

        self.btn_iniciar = tk.Button(panel_control, text="Iniciar Grabado PCB", command=self.iniciar_ruteo, bg="lightgreen", state=tk.DISABLED)
        self.btn_iniciar.pack(pady=5, fill=tk.X)
        
        self.btn_detener = tk.Button(panel_control, text="STOP", command=self.detener_ruteo, bg="salmon")
        self.btn_detener.pack(pady=5, fill=tk.X)

        self.lbl_estado = tk.Label(panel_control, text="Desconectado", fg="red", font=("Arial", 10, "bold"), bg="#f0f0f0")
        self.lbl_estado.pack(side=tk.BOTTOM, pady=10)

        # --- PANEL DE VISUALIZACIÓN ---
        panel_visual = tk.Frame(self.root)
        panel_visual.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        panel_visual.columnconfigure(0, weight=6, uniform="grupo1")
        panel_visual.columnconfigure(1, weight=4, uniform="grupo1")
        panel_visual.rowconfigure(0, weight=1)

        marco_rt = tk.LabelFrame(panel_visual, text="Monitor CNC en Tiempo Real", font=("Arial", 11, "bold"), fg="#0044cc")
        marco_rt.grid(row=0, column=0, sticky="nsew", padx=5)
        self.canvas_rt = tk.Canvas(marco_rt, bg="black")
        self.canvas_rt.pack(fill=tk.BOTH, expand=True)

        marco_ref = tk.LabelFrame(panel_visual, text="Referencia y Coordenadas", font=("Arial", 10, "bold"))
        marco_ref.grid(row=0, column=1, sticky="nsew", padx=5)
        
        self.canvas_ref = tk.Canvas(marco_ref, bg="#1a1a1a", height=250)
        self.canvas_ref.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        marco_coords = tk.Frame(marco_ref)
        marco_coords.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        tk.Label(marco_coords, text="Monitor de Ejes (X, Y, Z):", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.txt_coordenadas = scrolledtext.ScrolledText(marco_coords, height=12, bg="#2b2b2b", fg="#00FF00", font=("Consolas", 10))
        self.txt_coordenadas.pack(fill=tk.BOTH, expand=True)

    def enviar_comando_grbl(self, comando, esperar_respuesta=True):
        if self.puerto_serial and self.conectado:
            try:
                self.puerto_serial.write((comando + '\n').encode('utf-8'))
                if esperar_respuesta:
                    time.sleep(0.05) 
                    return self.puerto_serial.read_all().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"Error enviando comando: {e}")
        return ""

    def conectar_grbl(self):
        puerto = self.puerto_seleccionado.get()
        if puerto == "Ninguno":
            messagebox.showerror("Error", "Seleccione un puerto válido.")
            return
        baudios = int(self.baudios_seleccionados.get())
        try:
            self.puerto_serial = serial.Serial(puerto, baudios, timeout=1)
            self.puerto_serial.write(b"\r\n\r\n")
            time.sleep(2)
            self.puerto_serial.flushInput()
            self.conectado = True
            
            self.enviar_comando_grbl("$X")
            self.enviar_comando_grbl("$132=100")
            self.enviar_comando_grbl("$21=0")
            self.enviar_comando_grbl("G92 X0 Y0 Z0")

            self.lbl_estado.config(text=f"Conectado: {puerto} @ {baudios}", fg="green")
            self.btn_conectar.config(state=tk.DISABLED)
            self.btn_config.config(state=tk.NORMAL)
            self.actualizar_estado_manual()
            
            if self.archivo_cargado:
                self.btn_iniciar.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar: {e}")

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
        if self.conectado:
            comando = f"G91 G0 {eje}{distancia}\nG90"
            self.enviar_comando_grbl(comando, esperar_respuesta=False)

    def set_cero_xy(self):
        if self.conectado:
            self.enviar_comando_grbl("G92 X0 Y0")
            messagebox.showinfo("Reset", "Origen XY fijado.")

    def set_cero_z(self):
        if self.conectado:
            self.enviar_comando_grbl("G92 Z0")
            messagebox.showinfo("Reset Z", "Punta de herramienta fijada como Z0 (superficie).")

    def actualizar_estado_manual(self):
        # Deshabilita el control si se está grabando O si ya se cargó un archivo
        estado = tk.DISABLED if (self.ruteo_activo or self.archivo_cargado) else tk.NORMAL
        
        # Búsqueda recursiva para apagar también los botones dentro de los frames de XY y Z
        def set_estado_widgets(parent):
            for child in parent.winfo_children():
                try: child.configure(state=estado)
                except: pass
                set_estado_widgets(child) # Llamada recursiva

        # Aplicar el estado a todo lo que esté dentro de frame_manual
        set_estado_widgets(self.frame_manual)

    def limpiar_archivo(self):
        """Descarga el archivo actual y desbloquea el control manual."""
        self.archivo_cargado = False
        self.gcode_lista.clear()
        self.lbl_archivo.config(text="Sin archivo")
        self.canvas_ref.delete("all")
        self.canvas_rt.delete("all")
        self.txt_coordenadas.delete("1.0", tk.END)
        self.cursor_herramienta = None
        if hasattr(self, 'pos_p_x'):
            del self.pos_p_x
            del self.pos_p_y
            
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_limpiar.config(state=tk.DISABLED)
        self.actualizar_estado_manual()

    def cargar_gerber(self):
        ruta = filedialog.askopenfilename(filetypes=[("Gerber", "*.gbr *.gtl *.gbl")])
        if not ruta: return

        self.lbl_archivo.config(text=os.path.basename(ruta))
        self.archivo_cargado = True
        self.gcode_lista.clear()
        
        # Limpiar pantallas
        self.canvas_ref.delete("all")
        self.canvas_rt.delete("all")
        self.txt_coordenadas.delete("1.0", tk.END)
        self.cursor_herramienta = None
        if hasattr(self, 'pos_p_x'):
            del self.pos_p_x
            del self.pos_p_y

        with open(ruta, 'r') as f:
            lineas = f.readlines()

        divisor = 10000.0
        coords = []
        for l in lineas:
            mx, my = re.search(r'X([\+\-]?\d+)', l), re.search(r'Y([\+\-]?\d+)', l)
            if mx or my:
                vx = float(mx.group(1))/divisor if mx else 0
                vy = float(my.group(1))/divisor if my else 0
                coords.append((vx, vy))

        if not coords:
            messagebox.showerror("Error", "El archivo Gerber no contiene coordenadas válidas de trazado.")
            self.archivo_cargado = False
            return

        self.root.update_idletasks()
        ancho_rt, alto_rt = self.canvas_rt.winfo_width(), self.canvas_rt.winfo_height()
        ancho_ref, alto_ref = self.canvas_ref.winfo_width(), self.canvas_ref.winfo_height()

        min_x = min(c[0] for c in coords); max_x = max(c[0] for c in coords)
        min_y = min(c[1] for c in coords); max_y = max(c[1] for c in coords)
        rx, ry = (max_x - min_x) or 1, (max_y - min_y) or 1

        self.escala_rt = min((ancho_rt-60)/rx, (alto_rt-60)/ry)
        self.offset_x_rt = 30 - (min_x * self.escala_rt)
        self.offset_y_rt = alto_rt - 30 + (min_y * self.escala_rt)

        self.escala_ref = min((ancho_ref-40)/rx, (alto_ref-40)/ry)
        self.offset_x_ref = 20 - (min_x * self.escala_ref)
        self.offset_y_ref = alto_ref - 20 + (min_y * self.escala_ref)

        self.gcode_lista.append(f"G21\nG90\nG0 Z{self.Z_SEGURIDAD}")
        
        px, py = 0.0, 0.0
        herramienta_abajo = False

        for l in lineas:
            mx, my = re.search(r'X([\+\-]?\d+)', l), re.search(r'Y([\+\-]?\d+)', l)
            if not mx and not my: continue
            
            cx = float(mx.group(1))/divisor if mx else px
            cy = float(my.group(1))/divisor if my else py

            if 'D01' in l or 'D1*' in l:
                if not herramienta_abajo:
                    self.gcode_lista.append(f"G1 Z{self.Z_GRABADO} F100")
                    herramienta_abajo = True
                self.gcode_lista.append(f"G1 X{cx:.3f} Y{cy:.3f} F{self.F_CORTE}")
                
                x1, y1 = (px*self.escala_ref)+self.offset_x_ref, self.offset_y_ref-(py*self.escala_ref)
                x2, y2 = (cx*self.escala_ref)+self.offset_x_ref, self.offset_y_ref-(cy*self.escala_ref)
                self.canvas_ref.create_line(x1, y1, x2, y2, fill="#00FF00")

            elif 'D02' in l or 'D2*' in l:
                if herramienta_abajo:
                    self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD}")
                    herramienta_abajo = False
                self.gcode_lista.append(f"G0 X{cx:.3f} Y{cy:.3f}")

            px, py = cx, cy

        self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD}\nG0 X0 Y0")
        
        # ACTIVA LOS CONTROLES SEGÚN EL ESTADO
        self.btn_limpiar.config(state=tk.NORMAL)
        self.actualizar_estado_manual() # Bloquea el manual automáticamente
        if self.conectado: self.btn_iniciar.config(state=tk.NORMAL)

    def actualizar_cursor_tiempo_real(self, comando):
        mx = re.search(r'X([\+\-]?\d+\.?\d*)', comando)
        my = re.search(r'Y([\+\-]?\d+\.?\d*)', comando)
        mz = re.search(r'Z([\+\-]?\d+\.?\d*)', comando)
        
        if mx or my or mz:
            info = f"Moviendo -> "
            if mx: info += f"X:{float(mx.group(1)):.2f} "
            if my: info += f"Y:{float(my.group(1)):.2f} "
            if mz: info += f"Z:{float(mz.group(1)):.2f} "
            self.txt_coordenadas.insert(tk.END, info + "\n")
            self.txt_coordenadas.see(tk.END)

        if mx and my:
            cx, cy = float(mx.group(1)), float(my.group(1))
            px, py = (cx*self.escala_rt)+self.offset_x_rt, self.offset_y_rt-(cy*self.escala_rt)
            
            if hasattr(self, 'pos_p_x') and 'G1' in comando:
                self.canvas_rt.create_line(self.pos_p_x, self.pos_p_y, px, py, fill="cyan", width=2)
            
            self.pos_p_x, self.pos_p_y = px, py
            if not self.cursor_herramienta:
                self.cursor_herramienta = self.canvas_rt.create_oval(px-5, py-5, px+5, py+5, fill="red")
            else:
                self.canvas_rt.coords(self.cursor_herramienta, px-5, py-5, px+5, py+5)

    def iniciar_ruteo(self):
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_limpiar.config(state=tk.DISABLED) # Evitar que lo borre mientras rutea
        self.ruteo_activo = True
        self.actualizar_estado_manual()
        self.txt_coordenadas.delete("1.0", tk.END)
        threading.Thread(target=self.hilo_enviar_gcode, daemon=True).start()

    def hilo_enviar_gcode(self):
        for cmd in self.gcode_lista:
            if not self.ruteo_activo: break 
                
            self.puerto_serial.write((cmd + '\n').encode('utf-8'))
            self.root.after(0, self.actualizar_cursor_tiempo_real, cmd)
            
            while self.ruteo_activo:
                res = self.puerto_serial.readline().decode('utf-8', errors='ignore').strip()
                if "ok" in res or "error" in res:
                    break
        
        self.ruteo_activo = False
        self.root.after(0, lambda: self.btn_iniciar.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.btn_limpiar.config(state=tk.NORMAL))
        self.root.after(0, self.actualizar_estado_manual)
        
        if self.ruteo_activo:
            self.root.after(0, lambda: messagebox.showinfo("Listo", "Grabado de PCB finalizado."))

    def detener_ruteo(self):
        if self.conectado:
            self.ruteo_activo = False
            self.puerto_serial.write(b'\x18')
            time.sleep(0.5) 
            
            self.enviar_comando_grbl("$X", esperar_respuesta=False) 
            self.enviar_comando_grbl("G0 Z10", esperar_respuesta=False) 
            
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_limpiar.config(state=tk.NORMAL)
            self.actualizar_estado_manual()
            messagebox.showwarning("Parada", "¡Emergencia activada! Se ha detenido la máquina.")

if __name__ == "__main__":
    tk_root = tk.Tk()
    app = CNCControlApp(tk_root)
    tk_root.mainloop()