import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import time
import re
import os
import cv2
import numpy as np
from tkinter import simpledialog
import math
import re
from shapely.geometry import LineString
from shapely.ops import unary_union
import tkinter.messagebox as messagebox

class CNCControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control CNC PCB - Sistema de Bloqueo de Seguridad")
        self.root.geometry("1280x675")

        # Variables de estado
        self.puerto_serial = None
        self.gcode_lista = []
        self.gcode_lista_original = [] # Para guardar copia intacta al mover el origen
        self.ruta_archivo_actual = None # Para el CAM
        self.conectado = False
        self.archivo_cargado = False
        self.ruteo_activo = False

        # Parámetros de Grabado PCB (Eje Z)
        self.Z_SEGURIDAD = 5.0  # Altura para moverse sin tocar la placa
        self.Z_GRABADO = 0   # Profundidad de penetración en el cobre
        self.F_CORTE = 150      # Velocidad de avance al grabar
        self.Z_PERFORACION = -1.5 # Profundidad para atravesar la placa
        self.coords_perforaciones = [] # Guardará las coordenadas de los huequitos

        # Variables de visualización
        self.escala_rt, self.offset_x_rt, self.offset_y_rt = 1.0, 0, 0
        self.escala_ref, self.offset_x_ref, self.offset_y_ref = 1.0, 0, 0
        self.cursor_herramienta = None 

        self.crear_interfaz()

        self.lbl_progreso = tk.Label(self.root, text="", font=("Arial", 10, "bold"), fg="blue")
        self.lbl_progreso.place(relx=0.5, rely=0.91, anchor=tk.CENTER)

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

        # 2. Control Manual (Jog)
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

        tk.Button(self.frame_manual, text="Ir a Inicio (X0 Y0)", bg="#99ccff", width=18, command=self.volver_a_inicio).grid(row=2, column=0, columnspan=2, pady=5)
        
        # 3. Archivos y Ruteo
        tk.Label(panel_control, text="3. ARCHIVO Y RUTEO", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(pady=(15,0))
        
        self.btn_cargar = tk.Button(panel_control, text="1. Cargar Gerber", command=self.cargar_gerber)
        self.btn_cargar.pack(pady=2, fill=tk.X)

        self.btn_taladros = tk.Button(panel_control, text="Cargar Perforaciones", command=self.cargar_perforaciones, bg="#ffe599")
        self.btn_taladros.pack(pady=2, fill=tk.X)

        self.btn_borde = tk.Button(panel_control, text="Generar Corte de Borde", command=self.generar_corte_borde, bg="#b4a7d6") # Color lila para diferenciar
        self.btn_borde.pack(pady=2, fill=tk.X)
        
        # BOTÓN DE CONFIGURACIÓN DE TALADRO
        self.btn_conf_perf = tk.Button(panel_control, text="⚙️ Configurar Profundidad Taladro", command=self.configurar_z_perforacion, bg="#e0e0e0")
        self.btn_conf_perf.pack(pady=2, fill=tk.X)


        self.btn_cam = tk.Button(panel_control, text="2. Configuración CAM", command=self.abrir_menu_cam, state=tk.DISABLED, bg="#d9ead3")
        self.btn_cam.pack(pady=2, fill=tk.X)

        self.btn_cargar_img = tk.Button(panel_control, text="Cargar Imagen (PNG/JPG)", command=self.cargar_imagen_a_gcode, bg="#e6e6fa")
        self.btn_cargar_img.pack(pady=2, fill=tk.X)

        self.btn_limpiar = tk.Button(panel_control, text="Descartar Archivo (Desbloquear)", command=self.limpiar_archivo, state=tk.DISABLED, bg="#ffe6e6")
        self.btn_limpiar.pack(pady=2, fill=tk.X)

        self.lbl_archivo = tk.Label(panel_control, text="Sin archivo", fg="blue", bg="#f0f0f0")
        self.lbl_archivo.pack(pady=(5, 0))

        
        # Estado de la conexión al fondo del panel
        self.lbl_estado = tk.Label(panel_control, text="Desconectado", fg="red", font=("Arial", 10, "bold"), bg="#f0f0f0")
        self.lbl_estado.pack(side=tk.BOTTOM, pady=10)

        # --- PANEL DE VISUALIZACIÓN ---
        panel_visual = tk.Frame(self.root)
        panel_visual.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Ajustamos el grid: Fila 0 para los botones, Fila 1 para los monitores
        panel_visual.columnconfigure(0, weight=6, uniform="grupo1")
        panel_visual.columnconfigure(1, weight=4, uniform="grupo1")
        panel_visual.rowconfigure(0, weight=0) # Fila de los botones (no se expande verticalmente)
        panel_visual.rowconfigure(1, weight=1) # Fila de los monitores (ocupa todo el resto)

# --- BARRA DE EJECUCIÓN (Encima de los monitores) ---
        marco_ejecucion = tk.Frame(panel_visual)
        marco_ejecucion.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # 1. Sub-marco solo para organizar los botones en la parte superior
        marco_botones = tk.Frame(marco_ejecucion)
        marco_botones.pack(side=tk.TOP, fill=tk.X)

        self.btn_iniciar = tk.Button(marco_botones, text="▶ Iniciar Grabado PCB", command=self.iniciar_ruteo, bg="lightgreen", state=tk.DISABLED, font=("Arial", 11, "bold"), height=2)
        self.btn_iniciar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.btn_detener = tk.Button(marco_botones, text="🛑 STOP (Emergencia)", command=self.detener_ruteo, bg="salmon", font=("Arial", 11, "bold"), height=2)
        self.btn_detener.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_reanudar = tk.Button(marco_botones, text="⏯ Continuar (Cambio Broca)", command=self.reanudar_maquina, bg="orange", font=("Arial", 11, "bold"), height=2)
        self.btn_reanudar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 2. Etiqueta de dimensiones empaquetada DEBAJO de los botones
        self.lbl_dimensiones = tk.Label(marco_ejecucion, text="Tamaño: Esperando...", fg="#0044cc", font=("Arial", 11, "bold"))
        self.lbl_dimensiones.pack(side=tk.TOP, pady=(5, 0))

        # --- MONITORES (Ahora en la fila 1) ---
        marco_rt = tk.LabelFrame(panel_visual, text="Monitor CNC en Tiempo Real", font=("Arial", 11, "bold"), fg="#0044cc")
        marco_rt.grid(row=1, column=0, sticky="nsew", padx=5)
        self.canvas_rt = tk.Canvas(marco_rt, bg="black")
        self.canvas_rt.pack(fill=tk.BOTH, expand=True)

        marco_ref = tk.LabelFrame(panel_visual, text="Referencia y Coordenadas", font=("Arial", 10, "bold"))
        marco_ref.grid(row=1, column=1, sticky="nsew", padx=5)      
        self.canvas_ref = tk.Canvas(marco_ref, bg="#1a1a1a", height=250)
        self.canvas_ref.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        marco_coords = tk.Frame(marco_ref)
        marco_coords.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        tk.Label(marco_coords, text="Monitor de Ejes (X, Y, Z):", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        self.txt_coordenadas = scrolledtext.ScrolledText(marco_coords, height=12, bg="#2b2b2b", fg="#00FF00", font=("Consolas", 10))
        self.txt_coordenadas.pack(fill=tk.BOTH, expand=True)

    # =========================================================================
    #                    COMUNICACIÓN Y CONTROL GRBL
    # =========================================================================

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
            self.enviar_comando_grbl("G10 P0 L20 X0 Y0 Z0")

            self.lbl_estado.config(text=f"Conectado: {puerto} @ {baudios}", fg="green")
            self.btn_conectar.config(state=tk.DISABLED)
            self.btn_config.config(state=tk.NORMAL)
            self.actualizar_estado_manual()
            
            if self.gcode_lista:
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
            self.enviar_comando_grbl("G10 P0 L20 X0 Y0")
            messagebox.showinfo("Reset", "Origen XY fijado permanentemente.")

    def set_cero_z(self):
        if self.conectado:
            self.enviar_comando_grbl("G10 P0 L20 Z0")
            messagebox.showinfo("Reset Z", "Punta de herramienta fijada como Z0 (superficie).")
            
    def volver_a_inicio(self):
        if self.conectado:
            self.enviar_comando_grbl("G90", esperar_respuesta=False)
            self.enviar_comando_grbl(f"G0 Z{self.Z_SEGURIDAD}", esperar_respuesta=False)
            self.enviar_comando_grbl("G0 X0 Y0", esperar_respuesta=False)
            self.enviar_comando_grbl("G0 Z0.5", esperar_respuesta=False)

    def actualizar_estado_manual(self):
        estado = tk.DISABLED if (self.ruteo_activo or self.archivo_cargado) else tk.NORMAL
        def set_estado_widgets(parent):
            for child in parent.winfo_children():
                try: child.configure(state=estado)
                except: pass
                set_estado_widgets(child)
        set_estado_widgets(self.frame_manual)

    # =========================================================================
    #                    MÓDULO CAM Y ARCHIVOS (GERBER / IMAGEN)
    # =========================================================================

    def cargar_gerber(self):
        import re
        import os
        from tkinter import filedialog, messagebox
        
        ruta = filedialog.askopenfilename(filetypes=[("Gerber", "*.gbr *.gtl *.gbl *.nc *.txt"), ("Todos los archivos", "*.*")])
        if not ruta: return

        self.ruta_archivo_actual = ruta
        self.lbl_archivo.config(text=os.path.basename(ruta))
        self.archivo_cargado = True
        self.gcode_lista.clear()
        
        self.coords_crudas = [] 

        self.canvas_ref.delete("all")
        self.canvas_rt.delete("all")
        self.txt_coordenadas.delete("1.0", tk.END)
        self.cursor_herramienta = None
        self.pos_p_x = None
        self.pos_p_y = None
        
        try:
            with open(ruta, 'r') as f:
                lineas = f.readlines()

            # --- 0. DETECTAR UNIDADES ---
            unidad_pulgadas = False
            for l in lineas:
                if '%MOIN*%' in l:
                    unidad_pulgadas = True
                    break

            # --- 1. DICCIONARIO INTELIGENTE DE FORMAS (Círculo o Rectángulo) ---
            diccionario_aperturas = {}
            # Atrapa: %ADD10C,0.8*% o %ADD11R,0.8X0.8*%
            regex_def_apertura = re.compile(r'%ADD(\d+)([a-zA-Z]+),([\d.X]+)')
            
            for l in lineas:
                match_def = regex_def_apertura.search(l)
                if match_def:
                    d_code = match_def.group(1) 
                    forma = match_def.group(2).upper() # 'C' o 'R'
                    medida_str = match_def.group(3)
                    
                    if 'X' in medida_str:
                        w, h = map(float, medida_str.split('X'))
                    else:
                        w = float(medida_str)
                        h = w
                        
                    if unidad_pulgadas:
                        w *= 25.4
                        h *= 25.4
                        
                    # Reducimos un 15% el tamaño real como "Margen de Seguridad" 
                    # para que el CAM no fusione los que están muy juntos.
                    diccionario_aperturas[d_code] = {"forma": forma, "w": w * 0.85, "h": h * 0.85}

            # --- 2. EXTRAER COORDENADAS ---
            divisor = 100000.0
            coords = []
            px_tmp, py_tmp = 0.0, 0.0
            for l in lineas:
                mx, my = re.search(r'X([\+\-]?\d+)', l), re.search(r'Y([\+\-]?\d+)', l)
                if mx or my:
                    if mx:
                        px_tmp = float(mx.group(1))/divisor
                        if unidad_pulgadas: px_tmp *= 25.4
                    if my:
                        py_tmp = float(my.group(1))/divisor
                        if unidad_pulgadas: py_tmp *= 25.4
                    coords.append((px_tmp, py_tmp))

            if coords:
                min_x = min(c[0] for c in coords); max_x = max(c[0] for c in coords)
                min_y = min(c[1] for c in coords); max_y = max(c[1] for c in coords)
                rx, ry = (max_x - min_x) or 1, (max_y - min_y) or 1

                self.root.update_idletasks()
                ancho_ref, alto_ref = self.canvas_ref.winfo_width(), self.canvas_ref.winfo_height()
                self.escala_ref = min((ancho_ref-40)/rx, (alto_ref-40)/ry)
                self.offset_x_ref = 20 - (min_x * self.escala_ref)
                self.offset_y_ref = alto_ref - 20 + (min_y * self.escala_ref)

                px, py = 0.0, 0.0
                trazo_actual = [] 
                
                regex_cambio_d = re.compile(r'D([1-9]\d+)\*') 
                apertura_actual = {"forma": "C", "w": 0.8, "h": 0.8}

                # --- 3. DIBUJAR PISTAS Y PADS ---
                for l in lineas:
                    match_d = regex_cambio_d.search(l)
                    if match_d:
                        num_d = match_d.group(1)
                        if int(num_d) >= 10: 
                            apertura_actual = diccionario_aperturas.get(num_d, apertura_actual)

                    mx, my = re.search(r'X([\+\-]?\d+)', l), re.search(r'Y([\+\-]?\d+)', l)
                    
                    if mx:
                        cx = float(mx.group(1))/divisor
                        if unidad_pulgadas: cx *= 25.4
                    else: cx = px
                        
                    if my:
                        cy = float(my.group(1))/divisor
                        if unidad_pulgadas: cy *= 25.4
                    else: cy = py

                    if 'D01' in l or 'D1*' in l:
                        x1, y1 = (px*self.escala_ref)+self.offset_x_ref, self.offset_y_ref-(py*self.escala_ref)
                        x2, y2 = (cx*self.escala_ref)+self.offset_x_ref, self.offset_y_ref-(cy*self.escala_ref)
                        self.canvas_ref.create_line(x1, y1, x2, y2, fill="cyan", tags="diseno_cyan")
                        
                        if not trazo_actual:
                            trazo_actual.append((px, py))
                        trazo_actual.append((cx, cy))
                    
                    elif 'D02' in l or 'D2*' in l or 'D03' in l or 'D3*' in l:
                        if trazo_actual:
                            self.coords_crudas.append(trazo_actual)
                            trazo_actual = []
                            
                        if 'D03' in l or 'D3*' in l:
                            forma = apertura_actual["forma"]
                            rw = apertura_actual["w"] / 2.0
                            rh = apertura_actual["h"] / 2.0
                            
                            x_c = (cx*self.escala_ref)+self.offset_x_ref
                            y_c = self.offset_y_ref-(cy*self.escala_ref)
                            
                            if forma == 'R' or forma == 'S': 
                                # ES UN PAD CUADRADO/RECTANGULAR
                                # 1. Dibujamos el contorno para Shapeley
                                borde = [(cx-rw, cy-rh), (cx+rw, cy-rh), (cx+rw, cy+rh), (cx-rw, cy+rh), (cx-rw, cy-rh)]
                                # 2. Dibujamos una cruz interna para que sea macizo
                                cruz_x = [(cx-rw, cy-rh), (cx+rw, cy+rh)]
                                cruz_y = [(cx+rw, cy-rh), (cx-rw, cy+rh)]
                                self.coords_crudas.extend([borde, cruz_x, cruz_y])
                                
                                # Visual
                                r_w_vis, r_h_vis = max(2, int(rw*self.escala_ref)), max(2, int(rh*self.escala_ref))
                                self.canvas_ref.create_rectangle(x_c-r_w_vis, y_c-r_h_vis, x_c+r_w_vis, y_c+r_h_vis, outline="cyan")
                            
                            else:
                                # PAD CIRCULAR PERFECTO (Anillos concéntricos macizos sin picos)
                                import math
                                r_actual = rw
                                formas_circulo = []
                                
                                # Hacemos anillos concéntricos hacia el centro para rellenar (como una diana)
                                while r_actual >= 0.02:
                                    anillo = []
                                    # Polígono de 20 lados (circular perfecto para la CNC)
                                    for i in range(21):
                                        angulo = i * (2 * math.pi / 20)
                                        anillo.append((cx + r_actual * math.cos(angulo), cy + r_actual * math.sin(angulo)))
                                    formas_circulo.append(anillo)
                                    r_actual -= 0.15 # Espaciado denso para que el motor matemático lo fusione todo
                                
                                self.coords_crudas.extend(formas_circulo)
                                
                                # Visual (En la pantalla solo dibujamos el contorno para no saturarla)
                                r_vis = max(2, int(rw*self.escala_ref))
                                self.canvas_ref.create_oval(x_c-r_vis, y_c-r_vis, x_c+r_vis, y_c+r_vis, outline="cyan")

                    px, py = cx, cy

                if trazo_actual:
                    self.coords_crudas.append(trazo_actual)

                # --- 4. SEPARADOR DE BORDE PERSONALIZADO (PROTEUS) ---
                todos_x = [pt[0] for trazo in self.coords_crudas for pt in trazo]
                todos_y = [pt[1] for trazo in self.coords_crudas for pt in trazo]
                
                self.coords_borde_proteus = [] 
                
                if todos_x and todos_y:
                    min_x_abs = min(todos_x)
                    max_x_abs = max(todos_x)
                    min_y_abs = min(todos_y)
                    max_y_abs = max(todos_y)
                    
                    trazos_limpios = []
                    tolerancia = 0.5 
                    
                    for trazo in self.coords_crudas:
                        es_borde_placa = True
                        for x, y in trazo:
                            toca_marco = (abs(x - min_x_abs) <= tolerancia or 
                                          abs(max_x_abs - x) <= tolerancia or 
                                          abs(max_y_abs - y) <= tolerancia or 
                                          abs(y - min_y_abs) <= tolerancia)
                            if not toca_marco:
                                es_borde_placa = False
                                break
                        
                        if es_borde_placa:
                            self.coords_borde_proteus.append(trazo)
                        else:
                            trazos_limpios.append(trazo)
                    
                    self.coords_crudas = trazos_limpios

                # --- 5. REDIBUJAR DISEÑO INTELIGENTE EN PANTALLA ---
                self.canvas_ref.delete("diseno_cyan")
                
                # Pistas normales (Cyan)
                for trazo in self.coords_crudas:
                    for i in range(len(trazo)-1):
                        x1 = (trazo[i][0] * self.escala_ref) + self.offset_x_ref
                        y1 = self.offset_y_ref - (trazo[i][1] * self.escala_ref)
                        x2 = (trazo[i+1][0] * self.escala_ref) + self.offset_x_ref
                        y2 = self.offset_y_ref - (trazo[i+1][1] * self.escala_ref)
                        self.canvas_ref.create_line(x1, y1, x2, y2, fill="cyan", tags="diseno_cyan")
                        
                # TU borde personalizado (Magenta)
                for trazo in self.coords_borde_proteus:
                    for i in range(len(trazo)-1):
                        x1 = (trazo[i][0] * self.escala_ref) + self.offset_x_ref
                        y1 = self.offset_y_ref - (trazo[i][1] * self.escala_ref)
                        x2 = (trazo[i+1][0] * self.escala_ref) + self.offset_x_ref
                        y2 = self.offset_y_ref - (trazo[i+1][1] * self.escala_ref)
                        self.canvas_ref.create_line(x1, y1, x2, y2, fill="magenta", width=2, tags="diseno_cyan")

        except Exception as e:
            print("Nota: Error procesando archivo:", e)

        self.btn_cam.config(state=tk.NORMAL)
        self.btn_limpiar.config(state=tk.NORMAL)
        
        self.canvas_ref.bind("<Button-1>", self.fijar_origen_clic)
        messagebox.showinfo("Gerber Cargado", "1. Archivo leído correctamente con formas experimentales.\\n\\nAHORA DEBES hacer clic en '2. Configuración CAM'.")
   
    def abrir_menu_cam(self):
        # Creamos una ventana emergente para la configuración
        ventana_cam = tk.Toplevel(self.root)
        ventana_cam.title("Configuración CAM - Herramienta de Corte")
        ventana_cam.geometry("350x580") # Aumentamos un poco la altura para el nuevo ajuste
        ventana_cam.grab_set() # Bloquea la ventana principal hasta que se cierre esta

        tk.Label(ventana_cam, text="Ajustes de Generación de G-Code", font=("Arial", 12, "bold")).pack(pady=10)

        # --- 1. TIPO DE HERRAMIENTA ---
        tk.Label(ventana_cam, text="Tipo de Broca / Fresa:", font=("Arial", 9, "bold")).pack(pady=(5,0))
        self.var_tipo_broca = tk.StringVar(value="cilindrica")
        combo_broca = ttk.Combobox(ventana_cam, textvariable=self.var_tipo_broca, state="readonly")
        combo_broca['values'] = ("cilindrica", "v-bit")
        combo_broca.pack()

        # --- 2. DIÁMETRO ---
        tk.Label(ventana_cam, text="Diámetro / Punta (mm):").pack(pady=(10,0))
        self.entry_diametro = tk.Entry(ventana_cam, justify="center")
        self.entry_diametro.insert(0, "0.5") # Valor por defecto
        self.entry_diametro.pack()

        # --- 3. ÁNGULO (Para V-Bit) ---
        tk.Label(ventana_cam, text="Ángulo (Solo para V-Bit en grados):").pack(pady=(10,0))
        self.entry_angulo = tk.Entry(ventana_cam, justify="center")
        self.entry_angulo.insert(0, "30") # Valor por defecto
        self.entry_angulo.pack()

        # --- 4. PARÁMETROS Z Y AVANCE ---
        tk.Label(ventana_cam, text="Profundidad de Corte Z (mm) [Ej. -0.1]:").pack(pady=(10,0))
        self.entry_z_corte = tk.Entry(ventana_cam, justify="center")
        self.entry_z_corte.insert(0, "-0.1")
        self.entry_z_corte.pack()

        tk.Label(ventana_cam, text="Altura Segura Z (mm):").pack(pady=(10,0))
        self.entry_z_seguro = tk.Entry(ventana_cam, justify="center")
        self.entry_z_seguro.insert(0, "5.0")
        self.entry_z_seguro.pack()

        tk.Label(ventana_cam, text="Velocidad de Avance XY (Feedrate):").pack(pady=(10,0))
        self.entry_feedrate = tk.Entry(ventana_cam, justify="center")
        self.entry_feedrate.insert(0, "150")
        self.entry_feedrate.pack()

        tk.Label(ventana_cam, text="Número de pasadas (Vaciado de cobre):").pack(pady=(10,0))
        self.entry_pasadas = tk.Entry(ventana_cam, justify="center")
        self.entry_pasadas.insert(0, "1") # 1 pasada por defecto
        self.entry_pasadas.pack()

        # --- BOTÓN PARA PROCESAR ---
        btn_generar = tk.Button(ventana_cam, text="Generar Trayectorias", bg="lightgreen", font=("Arial", 10, "bold"),
                                command=lambda: self.procesar_cam_desde_interfaz(ventana_cam))
        btn_generar.pack(pady=20)

    def procesar_cam_desde_interfaz(self, ventana):
        try:
            # Leer valores de la ventana
            tipo_broca = self.var_tipo_broca.get()
            diametro = float(self.entry_diametro.get())
            z_corte = float(self.entry_z_corte.get())
            z_seguro = float(self.entry_z_seguro.get())
            feedrate = float(self.entry_feedrate.get())
            num_pasadas = int(self.entry_pasadas.get()) 
            
            # Condicionar el ángulo
            if tipo_broca == "v-bit":
                angulo = float(self.entry_angulo.get())
            else:
                angulo = 0.0

            # Llamar a la función matemática (¡Ya SIN el buffer_pistas!)
            self.generar_gcode_aislamiento(tipo_broca, diametro, angulo, z_corte, z_seguro, feedrate, num_pasadas)
            
            # Cerrar la ventana tras generar con éxito
            ventana.destroy()
            messagebox.showinfo("Éxito", f"G-Code generado con {num_pasadas} pasadas de aislamiento.")

        except ValueError:
            messagebox.showerror("Error", "Por favor ingresa solo números válidos en las casillas.")

    def funcion_boton_generar_cam(self):
        try:
            # Leer valores que ya tenías
            diametro = float(self.entry_diametro.get())
            z_corte = float(self.entry_z_corte.get())
            z_seguro = float(self.entry_z_seguro.get())
            feedrate = float(self.entry_feedrate.get())
            
            # --- NUEVO: Leer tipo y ángulo ---
            tipo_broca = self.var_tipo_broca.get()
            
            # Validar el ángulo (si es cilíndrica, da igual, mandamos 0)
            if tipo_broca == "v-bit":
                angulo = float(self.entry_angulo.get())
            else:
                angulo = 0.0

            # Llamar a la función matemática actualizada
            self.generar_gcode_aislamiento(tipo_broca, diametro, angulo, z_corte, z_seguro, feedrate)
            
        except ValueError:
            print("Error: Por favor ingresa solo números en las casillas de configuración.")

    def procesar_aislamiento(self, ventana):
        try:
            diametro = float(self.entry_broca.get())
            z_corte = float(self.entry_z_corte.get())
            z_seguro = float(self.entry_z_seguro.get())
            avance = int(self.entry_avance.get())
        except ValueError:
            messagebox.showerror("Error", "Ingresa valores numéricos válidos.")
            return

        ventana.destroy()
        self.generar_gcode_aislamiento(diametro, z_corte, z_seguro, avance)

    def fijar_origen_clic(self, event):
        # 1. Verificamos que el Gerber ya esté cargado
        if not hasattr(self, 'escala_ref') or not hasattr(self, 'offset_x_ref'):
            return

        # 2. Matemática inversa: Convertir los píxeles del clic a coordenadas reales del circuito
        self.pos_p_x = (event.x - self.offset_x_ref) / self.escala_ref
        self.pos_p_y = (self.offset_y_ref - event.y) / self.escala_ref

        # 3. Dibujar la cruz roja en la pantalla
        self.canvas_ref.delete("cruz_origen") # Borramos la cruz anterior si el usuario hace clic varias veces
        
        r = 10 # Tamaño de la cruz
        # Línea horizontal de la cruz
        self.canvas_ref.create_line(event.x - r, event.y, event.x + r, event.y, fill="red", width=2, tags="cruz_origen")
        # Línea vertical de la cruz
        self.canvas_ref.create_line(event.x, event.y - r, event.x, event.y + r, fill="red", width=2, tags="cruz_origen")
        # Texto indicativo
        self.canvas_ref.create_text(event.x + 12, event.y + 12, text="Origen (0,0)", fill="red", anchor="nw", tags="cruz_origen")

        print(f"Nuevo origen fijado en X: {self.pos_p_x:.3f}, Y: {self.pos_p_y:.3f}")


    def generar_gcode_aislamiento(self, tipo_broca, diametro, angulo, z_corte, z_seguro, feedrate, num_pasadas=1):
        import math
        from shapely.geometry import LineString, Polygon
        from shapely.ops import unary_union

        # --- AVISO DE INICIO AL USUARIO ---
        if hasattr(self, 'lbl_progreso'):
            self.lbl_progreso.config(text="Generando rutas pesadas... Por favor espere.", fg="blue")
            self.root.update()

        # --- 1. CÁLCULO DEL DIÁMETRO EFECTIVO ---
        if tipo_broca == "v-bit":
            profundidad_fisica = abs(z_corte)
            media_angulo_rad = math.radians(angulo / 2.0)
            ensanchamiento = 2.0 * (profundidad_fisica * math.tan(media_angulo_rad))
            diametro_efectivo = diametro + ensanchamiento
        else:
            diametro_efectivo = diametro
            
        print(f"Diámetro efectivo de corte: {diametro_efectivo:.3f}mm. Pasadas: {num_pasadas}")

        # --- 2. PREPARACIÓN GEOMÉTRICA ---
        ancho_pista_deseado = 1.0 # Ancho final que queremos para las pistas después del aislamiento
        offset_base = diametro_efectivo / 2.0 
        paso_lateral = diametro_efectivo * 0.60

        todos_x = [pt[0] for trazo in self.coords_crudas for pt in trazo]
        todos_y = [pt[1] for trazo in self.coords_crudas for pt in trazo]
        
        if hasattr(self, 'coords_borde_proteus'):
            for trazo in self.coords_borde_proteus:
                todos_x.extend([pt[0] for pt in trazo])
                todos_y.extend([pt[1] for pt in trazo])
        
        if not todos_x or not todos_y: return
        
        min_x_tot = min(todos_x)
        max_x_tot = max(todos_x)
        min_y_tot = min(todos_y)
        max_y_tot = max(todos_y)

        if self.pos_p_x is None or self.pos_p_y is None:
            self.pos_p_x, self.pos_p_y = min_x_tot, min_y_tot 

        trazos_abiertos = []
        poligonos_pads_raw = []
        marcos_encontrados = []
        
        if hasattr(self, 'coords_borde_proteus'):
            for trazo in self.coords_borde_proteus:
                trazo_desplazado = [(x - self.pos_p_x, y - self.pos_p_y) for x, y in trazo]
                marcos_encontrados.append(trazo_desplazado)

        # 2.1 Separar Pads (Cerrados) de Líneas (Abiertas)
        for trazo in self.coords_crudas:
            if len(trazo) >= 2:
                trazo_desplazado = [(x - self.pos_p_x, y - self.pos_p_y) for x, y in trazo]
                
                es_pad = False
                if len(trazo_desplazado) >= 4:
                    p_ini = trazo_desplazado[0]
                    p_fin = trazo_desplazado[-1]
                    if math.hypot(p_ini[0] - p_fin[0], p_ini[1] - p_fin[1]) < 0.001:
                        es_pad = True
                
                if es_pad:
                    try:
                        poly = Polygon(trazo_desplazado).buffer(0.001).buffer(-0.001)
                        if not poly.is_empty:
                            poligonos_pads_raw.append(poly)
                    except:
                        trazos_abiertos.append(trazo_desplazado)
                else:
                    trazos_abiertos.append(trazo_desplazado)

        # 2.2 Unir todos los pads reales en una sola capa matemática
        if poligonos_pads_raw:
            cobre_pads_exacto = unary_union(poligonos_pads_raw)
            # Dilatamos mínimamente para detectar si una línea está "dentro" del pad
            area_pads_cobertura = cobre_pads_exacto.buffer(0.02)
        else:
            cobre_pads_exacto = Polygon()
            area_pads_cobertura = Polygon()

        lineas_pistas = []

        # 2.3 Filtrar y estirar SOLO las pistas reales (Ignorar cruces internas)
        for trazo_abierto in trazos_abiertos:
            linea_temp = LineString(trazo_abierto)
            
            # MAGIA AQUÍ: Si la línea es una cruz interna de relleno, la ignoramos.
            if area_pads_cobertura.covers(linea_temp):
                continue
                
            # Si no es una cruz, es una pista real. ¡La estiramos!
            trazo_estirado = list(trazo_abierto)
            dist_ext = 0.4
            
            x0, y0 = trazo_estirado[0]
            x1, y1 = trazo_estirado[1]
            L1 = math.hypot(x1-x0, y1-y0)
            if L1 > 0:
                trazo_estirado[0] = (x0 - (x1-x0)/L1 * dist_ext, y0 - (y1-y0)/L1 * dist_ext)
                
            x_end, y_end = trazo_estirado[-1]
            x_prev, y_prev = trazo_estirado[-2]
            L2 = math.hypot(x_end-x_prev, y_end-y_prev)
            if L2 > 0:
                trazo_estirado[-1] = (x_end + (x_end-x_prev)/L2 * dist_ext, y_end + (y_end-y_prev)/L2 * dist_ext)
                
            lineas_pistas.append(LineString(trazo_estirado))

        # --- 3. CONSTRUCCIÓN DEL COBRE EXACTO ---
        if lineas_pistas:
            cobre_pistas = unary_union(lineas_pistas).buffer(ancho_pista_deseado / 2.0, cap_style=1, join_style=1)
        else:
            cobre_pistas = Polygon()

        # Unimos el cobre
        cobre_total = unary_union([cobre_pistas, cobre_pads_exacto])
        cobre_fusionado = cobre_total.buffer(0.05, join_style=1).buffer(-0.05, join_style=1)
        cobre_suavizado = cobre_fusionado.simplify(0.005, preserve_topology=True)

        rutas_corte = []

        # Aislar forzando las esquinas rectas para los pads cuadrados
        for pasada in range(num_pasadas):
            offset_actual = offset_base + (pasada * paso_lateral)
            poligonos_engordados = cobre_suavizado.buffer(offset_actual, cap_style=2, join_style=2)
            poligonos_finales = poligonos_engordados.simplify(0.01, preserve_topology=True)

            if poligonos_finales.geom_type == 'Polygon':
                rutas_corte.append(list(poligonos_finales.exterior.coords))
                for interior in poligonos_finales.interiors: 
                    rutas_corte.append(list(interior.coords))
            elif poligonos_finales.geom_type == 'MultiPolygon':
                for poly in poligonos_finales.geoms:
                    rutas_corte.append(list(poly.exterior.coords))
                    for interior in poly.interiors: 
                        rutas_corte.append(list(interior.coords))

        self.gcode_lista = [
            "G21 ; Unidades milimetros",
            "G90 ; Posicionamiento Absoluto",
            f"G0 Z{z_seguro} ; Subir a Z seguro"
        ]
        
        # --- 4. ESCRITURA DE PISTAS ---
        for ruta in rutas_corte:
            x_ini, y_ini = ruta[0]
            self.gcode_lista.append(f"G0 X{x_ini:.3f} Y{y_ini:.3f}")
            self.gcode_lista.append(f"G1 Z{z_corte:.3f} F{feedrate/2}")
            for x, y in ruta[1:]:
                self.gcode_lista.append(f"G1 X{x:.3f} Y{y:.3f} F{feedrate}")
            self.gcode_lista.append(f"G0 Z{z_seguro}")

        # --- 5. PERFORACIONES ---
        if hasattr(self, 'coords_perforaciones') and len(self.coords_perforaciones) > 0:
            self.gcode_lista.append("; --- SECCION DE PERFORACIONES ---")
            self.gcode_lista.append("G0 Z5.0 ; Subir para cambio de broca")
            self.gcode_lista.append("G0 X0 Y0 ; Ir a origen para comodidad")
            
            self.gcode_lista.append("G4 P1.0 ; Sincronizar grabado") 
            self.gcode_lista.append("M0 ; !!! PAUSA 1: PONGA BROCA DE PERFORAR (SUELTA) !!!")
            
            self.gcode_lista.append("G0 Z0.0 ; Bajar al ras de la placa")
            self.gcode_lista.append("G4 P1.0 ; Sincronizar")
            self.gcode_lista.append("M0 ; !!! PAUSA 2: APRIETE LA BROCA AHORA (NIVELADA) !!!")
            
            self.gcode_lista.append("G0 Z5.0 ; Subir para empezar")
            
            for px, py in self.coords_perforaciones:
                px_ajustado = px - self.pos_p_x
                py_ajustado = py - self.pos_p_y
                self.gcode_lista.append(f"G0 X{px_ajustado:.3f} Y{py_ajustado:.3f}")
                self.gcode_lista.append(f"G1 Z{self.Z_PERFORACION:.3f} F50")
                self.gcode_lista.append("G0 Z5.0")

        # --- 6. CORTE DE BORDE (PERFILADO FINAL) ---
        if marcos_encontrados:
            self.gcode_lista.append("; --- INICIO CORTE DE BORDE ---")
            self.gcode_lista.append("G0 Z5.0 ; Subir para cambio de broca")
            self.gcode_lista.append("G0 X0 Y0 ; Regresar al origen")
            
            self.gcode_lista.append("G4 P1.0 ; Sincronizar perforaciones")
            self.gcode_lista.append("M0 ; !!! PAUSA 3: PONGA FRESA DE CORTE (DEJELA SUELTA) !!!")
            
            self.gcode_lista.append("G0 Z0.0 ; Bajar al ras de la placa")
            self.gcode_lista.append("G4 P1.0 ; Sincronizar")
            self.gcode_lista.append("M0 ; !!! PAUSA 4: APRIETE LA FRESA FIRMEMENTE !!!")
            
            self.gcode_lista.append("G0 Z5.0 ; Subir para empezar")
            
            num_pasadas_borde = 4
            paso_z = self.Z_PERFORACION / num_pasadas_borde 
            
            for marco in marcos_encontrados:
                x_ini, y_ini = marco[0]
                self.gcode_lista.append(f"G0 X{x_ini:.3f} Y{y_ini:.3f}")
                for p in range(1, num_pasadas_borde + 1):
                    z_actual = paso_z * p
                    self.gcode_lista.append(f"G1 Z{z_actual:.3f} F50")
                    for x, y in marco[1:]:
                        self.gcode_lista.append(f"G1 X{x:.3f} Y{y:.3f} F{feedrate}")
                self.gcode_lista.append("G0 Z5.0")

        # --- 7. FIN DEL PROGRAMA ---
        self.gcode_lista.append("G4 P1.0 ; Sincronizar final")
        self.gcode_lista.append("G0 Z5.0 ; Levantar para no rayar")
        self.gcode_lista.append("G0 X0 Y0 ; Regresar al origen final")
        self.gcode_lista.append("M30 ; Fin del programa")

        if hasattr(self, 'lbl_progreso'):
            self.lbl_progreso.config(text="G-Code generado. Listo para Iniciar.", fg="blue")
            self.root.update()

        self.dibujar_rutas_gcode_en_canvas()

    def dibujar_rutas_gcode_en_canvas(self):
        # Borrar el diseño cyan original
        self.canvas_ref.delete("diseno_cyan")
        self.canvas_ref.delete("rutas_verdes")
        self.canvas_rt.delete("all")
        if not hasattr(self, 'escala_ref'): return
        import re 

        # Recuperamos tu origen para re-alinear el dibujo
        origen_x = self.pos_p_x if self.pos_p_x is not None else 0.0
        origen_y = self.pos_p_y if self.pos_p_y is not None else 0.0

        px, py = 0.0, 0.0
        for linea in self.gcode_lista:
            mx = re.search(r'X([\+\-]?\d+\.?\d*)', linea)
            my = re.search(r'Y([\+\-]?\d+\.?\d*)', linea)

            cx = float(mx.group(1)) if mx else px
            cy = float(my.group(1)) if my else py

            if 'G1 ' in linea:
                # Le sumamos el origen de vuelta a las coordenadas X/Y para que calce perfecto en pantalla
                x1_real = px + origen_x
                y1_real = py + origen_y
                x2_real = cx + origen_x
                y2_real = cy + origen_y

                x1 = (x1_real * self.escala_ref) + self.offset_x_ref
                y1 = self.offset_y_ref - (y1_real * self.escala_ref)
                x2 = (x2_real * self.escala_ref) + self.offset_x_ref
                y2 = self.offset_y_ref - (y2_real * self.escala_ref)
                
                self.canvas_ref.create_line(x1, y1, x2, y2, fill="#00FF00", width=2, tags="rutas_verdes") 
            
            px, py = cx, cy
        self.calcular_dimensiones_gcode()

        try:
            self.btn_iniciar.config(state=tk.NORMAL)
        except AttributeError:
            pass

    def dibujar_gcode_puro(self):
        self.canvas_ref.delete("all")
        if not self.gcode_lista: return

        coords_x, coords_y = [], []
        for linea in self.gcode_lista:
            mx, my = re.search(r'X([\+\-]?\d+\.?\d*)', linea), re.search(r'Y([\+\-]?\d+\.?\d*)', linea)
            if mx: coords_x.append(float(mx.group(1)))
            if my: coords_y.append(float(my.group(1)))
            
        if not coords_x or not coords_y: return

        min_x, max_x = min(coords_x), max(coords_x)
        min_y, max_y = min(coords_y), max(coords_y)
        rx, ry = (max_x - min_x) or 1, (max_y - min_y) or 1

        self.root.update_idletasks()
        ancho_ref, alto_ref = self.canvas_ref.winfo_width(), self.canvas_ref.winfo_height()
        if ancho_ref <= 1: ancho_ref = 400
        if alto_ref <= 1: alto_ref = 250

        self.escala_ref = min((ancho_ref-40)/rx, (alto_ref-40)/ry)
        self.offset_x_ref = 20 - (min_x * self.escala_ref)
        self.offset_y_ref = alto_ref - 20 + (min_y * self.escala_ref)

        # SOLO dibujamos las líneas G1 (Corte). 
        px, py = 0.0, 0.0
        for linea in self.gcode_lista:
            mx, my = re.search(r'X([\+\-]?\d+\.?\d*)', linea), re.search(r'Y([\+\-]?\d+\.?\d*)', linea)
            nx = float(mx.group(1)) if mx else px
            ny = float(my.group(1)) if my else py

            if linea.startswith('G1') and (mx or my):
                x1 = (px * self.escala_ref) + self.offset_x_ref
                y1 = self.offset_y_ref - (py * self.escala_ref)
                x2 = (nx * self.escala_ref) + self.offset_x_ref
                y2 = self.offset_y_ref - (ny * self.escala_ref)
                self.canvas_ref.create_line(x1, y1, x2, y2, fill="#00FF00", width=1) 
            
            px, py = nx, ny

        ox, oy = self.offset_x_ref, self.offset_y_ref
        r = 6
        self.canvas_ref.create_line(ox - r, oy, ox + r, oy, fill="red", width=2, tags="cruz_origen")
        self.canvas_ref.create_line(ox, oy - r, ox, oy + r, fill="red", width=2, tags="cruz_origen")
        self.canvas_ref.create_text(ox + 10, oy + 10, text="Origen (0,0)", fill="red", font=("Arial", 10, "bold"), tags="cruz_origen", anchor="w")

    def activar_fijar_origen(self):
        if not self.gcode_lista_original:
            messagebox.showwarning("Advertencia", "Primero genera el CAM.")
            return
        
        self.canvas_ref.bind("<Button-1>", self.fijar_nuevo_origen_gcode)
        self.canvas_ref.config(cursor="crosshair")
        messagebox.showinfo("Fijar Origen", "Haz clic en el visualizador para colocar el nuevo Origen (0,0).")

    def fijar_nuevo_origen_gcode(self, event):
        origen_x_mm = (event.x - self.offset_x_ref) / self.escala_ref
        origen_y_mm = (self.offset_y_ref - event.y) / self.escala_ref
        
        self.gcode_lista.clear()
        
        for linea in self.gcode_lista_original:
            if linea.startswith("G0") or linea.startswith("G1"):
                nueva_linea = linea
                mx = re.search(r'X([\+\-]?\d+\.?\d*)', linea)
                my = re.search(r'Y([\+\-]?\d+\.?\d*)', linea)
                
                if mx:
                    nx = float(mx.group(1)) - origen_x_mm
                    nueva_linea = nueva_linea.replace(f"X{mx.group(1)}", f"X{nx:.3f}")
                if my:
                    ny = float(my.group(1)) - origen_y_mm
                    nueva_linea = nueva_linea.replace(f"Y{my.group(1)}", f"Y{ny:.3f}")
                    
                self.gcode_lista.append(nueva_linea)
            else:
                self.gcode_lista.append(linea)

        self.canvas_ref.config(cursor="")
        self.canvas_ref.unbind("<Button-1>")
        self.dibujar_gcode_puro()

    def limpiar_archivo(self):
        self.archivo_cargado = False
        self.ruta_archivo_actual = None
        self.gcode_lista.clear()
        self.coords_perforaciones.clear()
        if hasattr(self, 'coords_borde'):
            self.coords_borde = []
        self.gcode_lista_original.clear()
        self.lbl_archivo.config(text="Sin archivo")
        self.canvas_ref.delete("all")
        self.canvas_rt.delete("all")
        self.txt_coordenadas.delete("1.0", tk.END)
        self.cursor_herramienta = None
        if hasattr(self, 'pos_p_x'):
            del self.pos_p_x; del self.pos_p_y
            
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_limpiar.config(state=tk.DISABLED)
        self.btn_cam.config(state=tk.DISABLED)
        #self.btn_origen.config(state=tk.DISABLED)
        self.actualizar_estado_manual()

    def cargar_imagen_a_gcode(self):
        ruta = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
        if not ruta: return

        ancho_mm = simpledialog.askfloat("Tamaño Físico", "Ingrese el ANCHO deseado de la placa en mm:", minvalue=5.0, maxvalue=300.0)
        if not ancho_mm: return

        self.lbl_archivo.config(text=f"Imagen: {os.path.basename(ruta)}")
        self.archivo_cargado = True
        self.gcode_lista.clear()
        
        self.canvas_ref.delete("all")
        self.canvas_rt.delete("all")
        self.txt_coordenadas.delete("1.0", tk.END)
        self.cursor_herramienta = None
        if hasattr(self, 'pos_p_x'):
            del self.pos_p_x; del self.pos_p_y

        img = cv2.imread(ruta, cv2.IMREAD_GRAYSCALE)
        alto_pix, ancho_pix = img.shape
        _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
        contornos, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contornos:
            messagebox.showerror("Error", "No se detectaron pistas.")
            self.limpiar_archivo()
            return

        escala = ancho_mm / ancho_pix
        alto_mm = alto_pix * escala

        self.gcode_lista.append(f"G21\nG90\nG0 Z{self.Z_SEGURIDAD}")

        for contorno in contornos:
            if len(contorno) < 3: continue 
            x_ini = contorno[0][0][0] * escala
            y_ini = (alto_pix - contorno[0][0][1]) * escala 
            
            self.gcode_lista.append(f"G0 X{x_ini:.3f} Y{y_ini:.3f}")
            self.gcode_lista.append(f"G1 Z{self.Z_GRABADO} F100") 
            
            for punto in contorno[1:]:
                cx = punto[0][0] * escala
                cy = (alto_pix - punto[0][1]) * escala
                self.gcode_lista.append(f"G1 X{cx:.3f} Y{cy:.3f} F{self.F_CORTE}")
                
            self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD}")

        self.gcode_lista.append("G0 X0 Y0")

        # Reutilizamos nuestra función limpia para visualizar imágenes también
        self.gcode_lista_original = list(self.gcode_lista)
        self.dibujar_gcode_puro()

        self.btn_limpiar.config(state=tk.NORMAL)
        self.btn_origen.config(state=tk.NORMAL)
        self.actualizar_estado_manual() 
        if self.conectado: self.btn_iniciar.config(state=tk.NORMAL)
        messagebox.showinfo("Éxito", f"Imagen convertida a G-Code.\nTamaño: {ancho_mm:.1f}x{alto_mm:.1f} mm")

    def calcular_dimensiones_gcode(self):
        if not self.gcode_lista:
            self.lbl_dimensiones.config(text="Tamaño del diseño: Archivo vacío")
            return

        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')
        
        for linea in self.gcode_lista:
            # Limpiar comentarios estándar de G-code
            linea_limpia = linea.upper().split(';')[0].split('(')[0] 
            
            # Búsqueda mejorada: Acepta X10, X 10, X:10, X=10, etc.
            match_x = re.search(r'X[:\s=]*([-0-9.]+)', linea_limpia)
            match_y = re.search(r'Y[:\s=]*([-0-9.]+)', linea_limpia)

            if match_x:
                x_val = float(match_x.group(1))
                min_x = min(min_x, x_val)
                max_x = max(max_x, x_val)
            if match_y:
                y_val = float(match_y.group(1))
                min_y = min(min_y, y_val)
                max_y = max(max_y, y_val)

        # Si se encontraron coordenadas válidas
        if min_x != float('inf'):
            ancho = max_x - min_x
            alto = max_y - min_y
            self.lbl_dimensiones.config(text=f"Tamaño del diseño: Ancho X {ancho:.2f} mm | Alto Y {alto:.2f} mm")
        else:
            self.lbl_dimensiones.config(text="Tamaño del diseño: No se detectaron coordenadas XY")

    def cargar_perforaciones(self):
        # Asegurarnos de que el Gerber principal ya esté cargado para tener la escala y el origen
        if not self.archivo_cargado:
            messagebox.showwarning("Aviso", "Por favor, carga primero el Gerber principal y configura el CAM para alinear las perforaciones correctamente.")
            return

        ruta = filedialog.askopenfilename(title="Selecciona el archivo de taladros", filetypes=[("Archivos de Taladro", "*.drl *.txt *.xln *.gbr"), ("Todos los archivos", "*.*")])
        if not ruta: return

        self.coords_perforaciones.clear()

        try:
            with open(ruta, 'r') as f:
                lineas = f.readlines()

            # El divisor suele ser el mismo que el Gerber, pero en Excellon a veces varía. Usamos 100000.0 por defecto.
            divisor = 100000.0 
            for l in lineas:
                # Buscamos coordenadas X y Y en la misma línea
                mx = re.search(r'X([\+\-]?\d+)', l)
                my = re.search(r'Y([\+\-]?\d+)', l)
                
                if mx and my:
                    vx = float(mx.group(1)) / divisor
                    vy = float(my.group(1)) / divisor
                    self.coords_perforaciones.append((vx, vy))

            if self.coords_perforaciones:
                messagebox.showinfo("Éxito", f"Se leyeron {len(self.coords_perforaciones)} perforaciones.\nSe añadirán al G-Code y al visualizador.")
                self.generar_gcode_perforaciones()
                self.dibujar_perforaciones()
            else:
                messagebox.showwarning("Aviso", "No se detectaron coordenadas válidas en el archivo.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo de perforaciones: {e}")
    def configurar_z_perforacion(self):
        # Abre una pequeña ventana para pedir el valor al usuario
        nuevo_z = simpledialog.askfloat(
            "Profundidad de Perforación", 
            "Introduce la profundidad para atravesar la placa en mm (ej. -1.5):", 
            initialvalue=self.Z_PERFORACION
        )
        
        if nuevo_z is not None:
            self.Z_PERFORACION = nuevo_z
            messagebox.showinfo("Configurado", f"Profundidad de perforación ajustada a: {self.Z_PERFORACION} mm")
            
            # Si ya se habían cargado perforaciones, regeneramos el gcode para aplicar la nueva profundidad
            if self.coords_perforaciones:
                self.gcode_lista = [linea for linea in self.gcode_lista if not "PERFORACIONES" in linea and not "Ir al hueco" in linea] # Limpieza básica
                self.generar_gcode_perforaciones()

    def generar_gcode_perforaciones(self):
        if not self.coords_perforaciones: return

        # Recuperar el origen actual para que coincida con las pistas
        # Si no hay origen definido, usamos 0
        origen_x = self.pos_p_x if self.pos_p_x is not None else 0.0
        origen_y = self.pos_p_y if self.pos_p_y is not None else 0.0

        self.gcode_lista.append("(--- INICIO DE PERFORACIONES ---)")
        self.gcode_lista.append("M0 ; PAUSA - CAMBIA A BROCA DE TALADRO")
        self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD}")

        for x, y in self.coords_perforaciones:
            # RESTAMOS el origen para que el hueco se mueva junto con la placa
            x_relativo = x - origen_x
            y_relativo = y - origen_y
            
            self.gcode_lista.append(f"G0 X{x_relativo:.3f} Y{y_relativo:.3f} ; Ir al hueco")
            self.gcode_lista.append(f"G1 Z{self.Z_PERFORACION} F50 ; Perforar")
            self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD} ; Subir")

        self.calcular_dimensiones_gcode()

    def dibujar_perforaciones(self):
        if not hasattr(self, 'escala_ref') or not self.coords_perforaciones: return

        # Borrar taladros previos si existen para no duplicar
        self.canvas_ref.delete("taladros_naranjas")

        # El dibujo del canvas ya está centrado en el origen (0,0) del G-Code
        # Así que debemos dibujar las coordenadas RELATIVAS al origen
        origen_x = self.pos_p_x if self.pos_p_x is not None else 0.0
        origen_y = self.pos_p_y if self.pos_p_y is not None else 0.0

        r = 3 # Radio del punto
        
        for x, y in self.coords_perforaciones:
            # Calculamos la posición relativa al origen (igual que en el G-Code)
            x_rel = x - origen_x
            y_rel = y - origen_y

            # Convertimos a coordenadas de pantalla (píxeles)
            # Usamos el mismo cálculo que usa tu función de dibujar pistas
            x_px = (x_rel * self.escala_ref) + self.offset_x_ref
            y_px = self.offset_y_ref - (y_rel * self.escala_ref)

            self.canvas_ref.create_oval(
                x_px - r, y_px - r, x_px + r, y_px + r, 
                fill="orange", outline="white", tags="taladros_naranjas"
            )

    def generar_corte_borde(self):
        # 0. EL GUARDIA DE SEGURIDAD: Verificar que la cruz roja (origen) exista
        if not hasattr(self, 'pos_p_x') or self.pos_p_x is None:
            messagebox.showwarning("Falta el Origen", "⚠️ Primero debes establecer el punto de origen haciendo clic en el diseño (la cruz roja) antes de generar el borde.")
            return

        # 1. Verificamos que haya pistas cargadas para poder calcular el tamaño
        if not hasattr(self, 'coords_crudas') or not self.coords_crudas:
            messagebox.showwarning("Aviso", "Primero debes cargar un Gerber para que el programa calcule el tamaño de la placa.")
            return

        # 2. Encontrar los extremos de la placa (Bounding Box)
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for trazo in self.coords_crudas:
            for x, y in trazo:
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y

        # Ajustamos usando el origen que el usuario ya confirmó que existe
        min_x -= self.pos_p_x
        max_x -= self.pos_p_x
        min_y -= self.pos_p_y
        max_y -= self.pos_p_y

        # AÑADIMOS EL MARGEN
        margen = 2.0 
        min_x -= margen
        min_y -= margen
        max_x += margen
        max_y += margen

        # 3. Generar el G-Code
        self.gcode_lista.append("(--- INICIO DE CORTE DE BORDE ---)")
        self.gcode_lista.append("M0 ; PAUSA - CAMBIA A BROCA DE CORTE (Fresa plana/Maiz)")
        self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD} ; Subir seguro")

        # Configuración de las pasadas de corte
        z_actual = 0.0
        z_final = self.Z_PERFORACION 
        paso_z = 0.5 
        feedrate = 150 

        self.gcode_lista.append(f"G0 X{min_x:.3f} Y{min_y:.3f} ; Ir a la esquina inferior izquierda")

        # Bucle de corte progresivo
        while z_actual > z_final:
            z_actual -= paso_z
            if z_actual < z_final:
                z_actual = z_final 
            
            self.gcode_lista.append(f"G1 Z{z_actual:.3f} F50 ; Bajar broca despacio")
            self.gcode_lista.append(f"G1 X{max_x:.3f} Y{min_y:.3f} F{feedrate}") # Abajo
            self.gcode_lista.append(f"G1 X{max_x:.3f} Y{max_y:.3f} F{feedrate}") # Derecha
            self.gcode_lista.append(f"G1 X{min_x:.3f} Y{max_y:.3f} F{feedrate}") # Arriba
            self.gcode_lista.append(f"G1 X{min_x:.3f} Y{min_y:.3f} F{feedrate}") # Izquierda

        self.gcode_lista.append(f"G0 Z{self.Z_SEGURIDAD} ; Subir al terminar")
        
        # 4. Guardar el borde para poder dibujarlo
        self.coords_borde = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y), (min_x, min_y)]
        
        messagebox.showinfo("Éxito", "Corte de borde automático añadido al final del G-Code.")
        self.dibujar_borde()
        self.calcular_dimensiones_gcode()
    def dibujar_borde(self):
        if not hasattr(self, 'escala_ref') or not hasattr(self, 'coords_borde'): return

        origen_x = self.pos_p_x if hasattr(self, 'pos_p_x') and self.pos_p_x is not None else 0.0
        origen_y = self.pos_p_y if hasattr(self, 'pos_p_y') and self.pos_p_y is not None else 0.0

        puntos_pantalla = []
        for x, y in self.coords_borde:
            # Re-alineamos para que encaje con el dibujo general
            x_real = x + origen_x
            y_real = y + origen_y
            x_pantalla = (x_real * self.escala_ref) + self.offset_x_ref
            y_pantalla = self.offset_y_ref - (y_real * self.escala_ref)
            puntos_pantalla.extend([x_pantalla, y_pantalla])

        # Dibujar un rectángulo Cyan para mostrar por dónde pasará la broca
        self.canvas_ref.create_line(puntos_pantalla, fill="cyan", width=2, tags="borde_corte")
   # =========================================================================
    #                    EJECUCIÓN DE CÓDIGO
    # =========================================================================

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
            
            # Como el canvas RT escala dinámicamente, aseguramos evitar divisiones por cero
            if self.escala_rt <= 0: return
            
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
        self.btn_limpiar.config(state=tk.DISABLED) 
        self.ruteo_activo = True
        self.actualizar_estado_manual()
        self.txt_coordenadas.delete("1.0", tk.END)
        
        # Recalcular escala para Canvas RT basado en el G-Code final antes de iniciar
        coords_x, coords_y = [], []
        for l in self.gcode_lista:
            mx, my = re.search(r'X([\+\-]?\d+\.?\d*)', l), re.search(r'Y([\+\-]?\d+\.?\d*)', l)
            if mx: coords_x.append(float(mx.group(1)))
            if my: coords_y.append(float(my.group(1)))
        
        if coords_x and coords_y:
            min_x, max_x = min(coords_x), max(coords_x)
            min_y, max_y = min(coords_y), max(coords_y)
            rx, ry = (max_x - min_x) or 1, (max_y - min_y) or 1
            ancho_rt, alto_rt = self.canvas_rt.winfo_width(), self.canvas_rt.winfo_height()
            self.escala_rt = min((ancho_rt-60)/rx, (alto_rt-60)/ry)
            self.offset_x_rt = 30 - (min_x * self.escala_rt)
            self.offset_y_rt = alto_rt - 30 + (min_y * self.escala_rt)
            
        threading.Thread(target=self.hilo_enviar_gcode, daemon=True).start()

    def hilo_enviar_gcode(self):
        # --- 1. MENSAJE AL INICIAR EL MOVIMIENTO ---
        if hasattr(self, 'lbl_progreso'):
            self.root.after(0, lambda: self.lbl_progreso.config(text="Ejecutando G-Code... Máquina en movimiento.", fg="orange"))

        completado = True # Asumimos que todo saldrá bien
        
        for cmd in self.gcode_lista:
            if not self.ruteo_activo: 
                completado = False # Si lo cancelaste, cambiamos esto a Falso
                break 
                
            self.puerto_serial.write((cmd + '\n').encode('utf-8'))
            self.root.after(0, self.actualizar_cursor_tiempo_real, cmd)
            
            while self.ruteo_activo:
                res = self.puerto_serial.readline().decode('utf-8', errors='ignore').strip()
                if "ok" in res or "error" in res:
                    break
        
        # Apagamos el ruteo y reactivamos los botones
        self.ruteo_activo = False
        self.root.after(0, lambda: self.btn_iniciar.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.btn_limpiar.config(state=tk.NORMAL))
        self.root.after(0, self.actualizar_estado_manual)
        
        # --- 2. MENSAJE AL FINALIZAR CON ÉXITO ---
        if completado:
            if hasattr(self, 'lbl_progreso'):
                self.root.after(0, lambda: self.lbl_progreso.config(text="PROCESO TERMINADO CON ÉXITO", fg="green"))
            
            self.root.after(0, lambda: messagebox.showinfo("Listo", "El proceso de la placa ha finalizado con éxito."))

    def detener_ruteo(self):
        if self.conectado:
            self.ruteo_activo = False 
            self.puerto_serial.write(b'\x18') 
            time.sleep(0.5) 
            self.enviar_comando_grbl("$X", esperar_respuesta=False) 
            self.enviar_comando_grbl("G90", esperar_respuesta=False) 
            self.enviar_comando_grbl(f"G0 Z{self.Z_SEGURIDAD}", esperar_respuesta=False) 
            self.enviar_comando_grbl("G0 X0 Y0", esperar_respuesta=False) 
            self.enviar_comando_grbl("G0 Z0.5", esperar_respuesta=False) 
            
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_limpiar.config(state=tk.NORMAL)
            self.actualizar_estado_manual()
            
            messagebox.showwarning("Parada de Emergencia", "¡Se ha detenido la máquina!\nRegresando al origen X0 Y0, con Z elevado a +0.5")
   
    def reanudar_maquina(self):
        if self.conectado and self.puerto_serial:
            # Enviamos el comando de "Cycle Start" a GRBL para salir del M0
            self.puerto_serial.write(b"~\n")
            print("Comando de reanudación (~) enviado a la CNC.")
            
            # --- AQUÍ SE ACTUALIZA EL MENSAJE PARA QUITAR EL CONGELADO ---
            if hasattr(self, 'lbl_progreso'):
                self.lbl_progreso.config(text="Máquina en movimiento... Ejecutando proceso.", fg="green")
                self.root.update() # Obligamos a la interfaz a refrescarse

if __name__ == "__main__":
    tk_root = tk.Tk()
    app = CNCControlApp(tk_root)
    tk_root.mainloop()