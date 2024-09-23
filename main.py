import datetime
import logging
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from PIL import ImageTk, Image
import pyodbc
import threading
import data_requests
import Button_Send_Rework
import json
from win10toast import ToastNotifier
from pynput import keyboard
import sys
import winsound
import Audit_Mode_List

# Configure logging
logging.basicConfig(filename='app-main.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

with open('config.json') as f:
        config = json.load(f)
db_folder_path = config['local_files'] + config['databaseName']
connection_params = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};" + \
    rf"DBQ={db_folder_path};"
)

def connect_to_database(connection_params):
    # PROCEDURE: Creates a connection to the Access Database for Team Shop data.
    try: 
        print("trying to connect")
        conn = pyodbc.connect(connection_params)
    except Exception as e:
        print("Error Connecting")
        logging.error(str(datetime.datetime.now())+" connect_to_database(): "+str(e))
        conn = False
    return conn

def check_database_connection():
    global db_connection
    if db_connection is None:
        return False
    try:
        # Execute a simple query to check if the connection is alive
        with db_connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM T_Users")
            db_connection.commit()
        return True
    except pyodbc.Error as e:
        toaster = ToastNotifier()
        toaster.show_toast("Network Alert", "Network connection is down! Reconnecting now...", duration=15)
        return False
 
class TunePlayer:
    def __init__(self):
        # Define the notes and their frequencies
        #Dev notes: C# = c, Db = 9, D# = d, Eb = 8, F# = f, Gb = 7, G# = g, Ab = 6, A# = a,Bb = 5 
        self.notes = {
            'C': 261.63, 'c': 277.18, '9': 277.18,
            'D': 293.66, 'd': 311.13, '8': 311.13,
            'E': 329.63, 'F': 349.23, 'f': 369.99, '7': 369.99,
            'G': 392.00, 'g': 415.30, '6': 415.30,
            'A': 440.00, 'a': 466.16, '5': 466.16,
            'B': 493.88
        }
    def play_tune(self, tune, octave, timing):
        note_dur = 250
        for i, note in enumerate(tune):
            if note in self.notes:
                frequency = self.notes[note]
                if octave > 0:
                    winsound.Beep(int(frequency)*octave, note_dur*int(timing[i]))  # Play each note for 500 milliseconds
                if octave < 0:
                    winsound.Beep(int(frequency)/abs(octave), note_dur*int(timing[i]))
            else:
                time.sleep(note_dur*timing[i]//1000)  # Pause for 1/4 a second for rests

class DatabaseChecker(threading.Thread):
    def __init__(self, interval, connection_params, machineGUI, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval = interval
        self.connection_params = connection_params
        self.other_class_instance = machineGUI
        self.daemon = True

    def run(self):
        global db_connection
        while True:
            if not check_database_connection():
                # Re-establish the database connection
                db_connection = connect_to_database(self.connection_params)
                self.other_class_instance.set_db_connection(db_connection)
            time.sleep(self.interval)

class RackChecker(threading.Thread):
    def __init__(self, interval, machineGUI, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interval = interval
        self.other_class_instance = machineGUI
        self.daemon = True
    def run(self):
        while True:
            self.other_class_instance.update_ready_list(False)
            # Wait for the specified interval before checking again
            time.sleep(self.interval)
        
class MachineGUI:
    global player
    def __init__(self, master=None):
        self.selected_page = 1
        self.local_files = config['local_files']
        self.font_path = config['font_path']
        self.printer_name = config['printer_name']
        self.po_temp = [""]
        self.Defect = [""]
        self.machineID = config['machineID']
        self.processID = int(config['processID'])
        self.complete_count = 0
        self.reject_total = 0
        self.image = "None"
        # self.current_shift = "Shift"
        self.rework_per_shift_count = 0
        self.selected_options = []
        self.manual_button_pressed = False
        self.rework_bool = False
        self.password_required = False
        self.rework_canceled = False
        self.tote_var = 0
        global db_connection
        self.set_db_connection(db_connection)
        self.cursor = self.conn.cursor()
        self.keep_po = False
        self.tote_tot_count = 0
        self.readyToScan = True
        self.activePO = ""
        self.bottle_count = 0
        self.location_rack = [[0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0]]   
        self.audit_mode = False
        self.printed_bool = False
        self.readyToCompile = []
        self.update_ready_list(False)
        self.force_check = False

        self.master = master
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        self.master.title("TeamFlow: " + self.machineID)
        self.master.iconbitmap(self.local_files+"\\Technical-Response-Logo.ICO")
        self.master.attributes("-fullscreen", True)
        self.master.bind('<Escape>', self.exit_fullscreen)

        self.master.config(bg="white")

        self.startTime = datetime.datetime.now()

        # Top Panel - Scan Boxes for user input
        top_panel = tk.PanedWindow(self.master, bd=1, bg="white", relief=tk.GROOVE, height=1*screen_height // 8, orient="horizontal")
        top_panel.pack(side="top", fill="both", expand=True)

        # Top Subsection in Left Panel
        top_subsection = tk.Frame(top_panel, bg="white")
        top_panel.add(top_subsection)

        self.top_title = tk.Label(top_subsection, text="Scan ID Rings", font=("Helvetica", 14), bg="pink", relief=tk.GROOVE)
        self.top_title.pack(side="top", fill="x", expand=False)

        separator_left = ttk.Separator(top_subsection, orient="horizontal")
        separator_left.pack(pady=2, side="top", fill="x", expand=False)

        label_frame1 = tk.Frame(top_subsection, bg="white")
        label_frame1.pack()

        scan_label = tk.Label(label_frame1, text="New Scan:", font=("Helvetica", 16), bg = "white")
        scan_label.pack(side="left", fill="x", expand=False)

        self.scan_entry = tk.Entry(label_frame1, font=("Helvetica", 24),bg="#D3D3D3")
        self.scan_entry.bind("<Return>", self.po_scan)
        self.scan_entry.pack(side="right", fill="x", expand=False)

        label_frame2 = tk.Frame(top_subsection, bg="white")
        label_frame2.pack()
        self.update_ready_list(True)
        textrack = self.get_next_rack_location()
        self.rack_label = tk.Label(label_frame2, text="Rack: " + str(textrack), font=("Helvetica", 16), bg = "white")
        self.rack_label.pack(side="left", fill="x", expand=False)

        self.rack_entry = tk.Entry(label_frame2, font=("Helvetica", 24),bg="#D3D3D3")
        self.rack_entry.bind("<Return>", self.rack_scan)
        self.rack_entry.pack(side="right", fill="x", expand=False)
        
        # top_panel.add(self.top_title)
        top_panel.add(top_subsection)

        # Center Panel - PO Images
        center_frame = tk.PanedWindow(self.master, bd=2,relief=tk.GROOVE, height=11*screen_height // 16, orient="horizontal")
        center_frame.pack(side="top", fill="both", expand=True)

        #Center Frame
        self.center_frame_title = tk.Frame(center_frame)
        self.center_frame_title.config(relief=tk.GROOVE, bg="white")
        self.center_frame_title.pack(side="top", fill="x", expand=False)
        self.center_panel = tk.Canvas(center_frame, bd=2, relief=tk.GROOVE)
        self.center_panel.pack(side="top", fill="both", expand=True)

        #Page count Frame
        page_num_frame = tk.Frame(self.center_panel, bg="white")
        page_num_frame.pack(pady=10, padx=10, fill="x", side="bottom", anchor="s", expand=False)
        page = tk.Label(page_num_frame, text="page ", font=("Helvetica", 14),bg="white")
        page.pack(side="left")
        self.cur_page = tk.Label(page_num_frame, font=("Helvetica", 14),bg="#D3D3D3")
        self.cur_page.config(text="N/A", bg="#E6E6E6")
        self.cur_page.pack(padx=10, pady=10, side="left", fill="x", anchor="s", expand=False)
        of = tk.Label(page_num_frame, text=" of ", font=("Helvetica", 14),bg="white")
        of.pack(side="left")
        self.tot_page = tk.Label(page_num_frame, font=("Helvetica", 14),bg="#D3D3D3")
        self.tot_page.config(text="N/A", bg="#E6E6E6")
        self.tot_page.pack(padx=10, pady=10, side="left", fill="x", anchor="s",expand=False)

        # Page Turn Buttons
        next_page = tk.Button(page_num_frame, text="_",command=lambda: self.flip_page(1) ,font = ("Wingdings 3", 16))
        prev_page = tk.Button(page_num_frame, text="^",command=lambda: self.flip_page(0), font = ("Wingdings 3", 16))
        prev_page.pack(padx=15, side="left", fill="x", expand=False)
        next_page.pack(padx=15, side="left", fill="x", expand=False)

        # Option Buttons
        self.option_var = tk.StringVar()
        self.option_var.set("ID Rings")
        self.can_click = {"Skins": True, "ID Rings": False}
        self.skins_button = tk.Button(page_num_frame, text="Skins", command=lambda: self.toggle_option("Skins"), font = ("Helvetica", 16))
        self.id_rings_button = tk.Button(page_num_frame, text="ID Rings", command=lambda: self.toggle_option("ID Rings"), font = ("Helvetica", 16))
        self.skins_button.config(state=tk.NORMAL)
        self.id_rings_button.config(state=tk.DISABLED)
        self.skins_button.pack(padx=10, side="right", fill="x", expand=False)
        self.id_rings_button.pack(padx=10, side="right", fill="x", expand=False)

        #Add the CENTER FRAME to the paned window
        center_frame.add(self.center_frame_title)
        center_frame.add(self.center_panel)

        # Right Panel - PO Information
        bottom_panel = tk.PanedWindow(self.master, bd=2, relief=tk.GROOVE, height=screen_height // 16, orient="horizontal")
        bottom_panel.pack(side="bottom", fill="both", expand=True)
        
        # Top Subsection in Right Panel
        bottom_subsection = tk.Frame(bottom_panel, bg="white")
        bottom_subsection.pack(pady=20)

        self.cancel_button = tk.Button(bottom_subsection, text="Clear",font = ("Helvetica", 16))
        self.cancel_button.pack(padx=50, side="left", fill="none", expand=False)
        self.cancel_button.bind("<Button-1>", self.call_cancel)
        # keyboard.add_hotkey("Ctrl+Shift+c", self.call_cancel)

        self.send_rework_button = tk.Button(bottom_subsection, text="Send Rework", font = ("Helvetica", 16))
        self.send_rework_button.pack(padx=50, side="left", fill="none", expand=False)
        self.send_rework_button.bind("<Button-1>", self.call_rework)

        self.complete_button = tk.Button(bottom_subsection, text="Audit Mode", font = ("Helvetica", 16))
        self.complete_button.pack(padx=50, side="right", fill="none", expand=False)
        self.complete_button.bind("<Button-1>", self.call_audit)
        
        bottom_panel.add(bottom_subsection)
        self.scan_entry.config(state=tk.NORMAL)
        self.rack_entry.config(state=tk.DISABLED)
        self.scan_entry.focus_set()

    def exit_fullscreen(self, event):
        self.master.attributes('-fullscreen', False)

    def call_cancel(self, event):
        self.clear_loaded_po("Clearbutton")

    def call_rework(self, event):
        self.sendrework()

    def call_complete(self, event):
        self.complete_checkout("Completed", self.rework_bool)

    def call_audit(self, event):
        if self.complete_button.cget("text") == "Audit Mode" and self.audit_mode == False:
            self.complete_button.config(text="Exit Audit")
            self.scan_entry.config(state=tk.NORMAL)
            self.scan_entry.focus_set()
            self.scan_entry.insert(0, "AUDITMOD")
            self.po_scan("<Return>")
            Audit_Mode_List.get_audit_list(self, self.master)
        elif self.complete_button.cget("text") == "Exit Audit" and self.audit_mode:
            self.complete_button.config(text="Audit Mode")
            self.scan_entry.config(state=tk.NORMAL)
            self.scan_entry.focus_set()
            self.scan_entry.delete(0, tk.END)
            self.scan_entry.insert(0, "AUDITMOD")
            self.po_scan("<Return>")

    def set_db_connection(self, db_conn):
        print("New connection")
        try:
            self.conn = db_conn
            self.cursor = self.conn.cursor()
        except Exception as e:
            logging.error(str(datetime.datetime.now())+" Error setting db connection:"+str(e))
    
    def rack_scan(self, event):
        self.rack_num = self.rack_entry.get().upper()
        self.rack_entry.config(state=tk.DISABLED)
        try:
            if self.rack_num == "":
                self.rack_entry.config(state=tk.NORMAL)
                return
            if self.rack_num:
                if self.rack_num[0] == "L":
                    self.set_rack_location(self.rack_num)
                    if self.audit_mode == True and self.force_check == False:
                        #Add Code that will search for the PO then will update the rack location to the new location
                        data_requests.update_IDring_compilation_data(self.cursor, self.conn, self.activePO, self.rack_num, self.tote_var)
                        self.clear_loaded_po("Rack")
                        return
                    self.complete_checkout("Completed", self.rework_bool)
                    self.force_check = False
                else:
                    self.rack_num = ""
                    self.rack_entry.config(state=tk.NORMAL)
                    self.rack_entry.delete(0, tk.END)
                    self.rack_entry.config(state=tk.NORMAL)
                    return
        except Exception as e:
            print("rack scan", e)
            logging.info("rack scan error: "+str(e))
        self.update_color_status("Green")        

    def po_scan(self, event):
        textrack = self.get_next_rack_location()
        self.rack_label.config(text="Rack: " + textrack)
        self.activePO = self.scan_entry.get().upper()
        if (self.readyToScan == False):
            return
        self.scan_entry.config(state=tk.DISABLED)
        try:
            print(self.tote_tot_count, self.tote_var)
            if self.tote_tot_count !=0 or self.tote_var == self.tote_tot_count:
                self.keep_po = False
            if self.keep_po == False:
                self.readyToScan = False
                po_num = self.activePO
                print("PO: " + po_num)
                if po_num == "":
                    return

                if self.audit_mode == False and po_num == "AUDITMOD":
                    self.update_color_status("Red")
                    self.audit_mode = True
                    self.clear_loaded_po("Audit")
                    return
                elif self.audit_mode and po_num == "AUDITMOD":
                    self.update_color_status("Green")
                    self.audit_mode = False
                    self.clear_loaded_po("Audit")
                    return
                self.skins_button.config(state=tk.NORMAL)
                self.id_rings_button.config(state=tk.DISABLED)
                self.option_var.set("ID Rings")
                self.can_click = {"Skins": True, "ID Rings": False}
                self.selected_page = 1
                auto_on = False
                
                print("len(po_num): ", str(len(po_num)))
                if len(po_num) == 8:
                    self.activePO = po_num
                    tote_var = 0
                elif len(po_num) == 10:
                    self.activePO = po_num[:10]
                    tote_var = 0
                elif len(po_num) == 11:
                    self.activePO = po_num[:8]
                    tote_var = po_num[9:]
                elif len(po_num) == 13:
                    print("po_num: " + po_num)
                    self.activePO = po_num[:10]
                    tote_var = po_num[11:]
                else:
                    self.activePO = po_num
                    tote_var = 0
                print("Numbers",self.activePO, tote_var)
                if tote_var:
                    try:
                        self.tote_var = int(tote_var)
                        history = data_requests.get_scan_history(self.cursor, self.conn, self.activePO, self.tote_var)
                        if history:
                            for row in history:
                                if row[1] == self.machineID and row[7]:
                                    self.printed_bool = True
                                    break
                        
                    except Exception as e:
                        logging.info("tote number not valid " + str(e))
                        self.tote_var = 0
                else:
                    self.tote_var = 0

                if self.activePO and self.tote_var > 0:
                    po_data = self.pull_po_data(self.activePO)
                    
                    if po_data:
                        bot_num = int(po_data['numofbottles'])
                        self.tote_tot_count = self.get_tote_num(bot_num)
                    else:
                        self.tote_tot_count = 1
                    disp = self.display_data(po_data, self.activePO)
                    if disp == False:
                        return
                elif self.activePO and self.tote_var == 0:
                    self.no_tote_tag_process()
                    player.play_tune(['E'], 3, [1])
                    history = data_requests.get_scan_history(self.cursor, self.conn, self.activePO, self.tote_var)
                    if history:
                        for row in history:
                            if row[1] == self.machineID and row[7]:
                                self.printed_bool = True
                                break
                    po_data = self.pull_po_data(self.activePO)
                    if po_data:
                        bot_num = int(po_data['numofbottles'])
                        self.tote_tot_count = self.get_tote_num(bot_num)
                    else:
                        self.tote_tot_count = 1
                    disp = self.display_data(po_data, self.activePO)
                    if disp == False:
                        return
                else:
                    self.password_required = False
                    logging.info(str(datetime.datetime.now())+" No user input")
            elif self.keep_po and self.tote_var <= self.tote_tot_count:
                self.readyToScan = False
                po_data = self.pull_po_data(self.activePO)
                disp = self.display_data(po_data, self.activePO)
                if disp == False:
                    return

            compIDData = data_requests.get_IDring_compilation_data(self.cursor, self.conn, self.activePO, self.tote_var)
            if compIDData == None:
                self.force_check = True
            max_attempts = 3
            attempts = 0
            while attempts < max_attempts:
                if isinstance(compIDData, str):
                    attempts += 1
                    if attempts >= max_attempts:
                        logging.error(str(datetime.datetime.now())+" get ring compliation data Error1: Failed after 3 attempts to pull data")
                        break
                    compIDData = data_requests.get_IDring_compilation_data(self.cursor, self.conn, self.activePO, self.tote_var)
                else:
                    break  # Exit loop if no error detected and string received
            if compIDData and self.audit_mode == False:
                if compIDData[0][3] and self.rework_bool == False:
                    player.play_tune(['G'], 5, [1])
                    messagebox.showinfo("IDR", "Ring has been compiled")
                elif compIDData[0][1] and compIDData[0][4]:
                    player.play_tune(['G'], 5, [1])
                    messagebox.showinfo("IDR", f"Ring has been checked in at {compIDData[0][4]}")
                self.update_color_status("Blue")
                self.scan_entry.delete(0, 'end')
                self.scan_entry.config(state=tk.DISABLED)
                self.rack_entry.config(state=tk.DISABLED)
                self.readyToScan = True
                return

            self.rack_entry.config(state=tk.NORMAL)
            player.play_tune(['B'], 4, [1])
            self.rack_entry.focus_set()
            self.update_color_status("Rework")
        except Exception as e:
            logging.info(e)

    # FUNCTION: Called when PO Button is clicked
    def sendrework(self):
        if self.activePO != "" and self.top_title.cget("bg") != "blue":
            Button_Send_Rework.btn_click_send_to_rework(self, self.activePO, self.bottle_count)
            if self.rework_canceled:
                return
            self.update_color_status("Red")
            self.top_title.after(2000, self.complete_checkout, "Rework", True)
            defect_part_list_skin = []
            defect_part_list_bottles = []
            self.rework_per_shift_count += 1
        
    def display_data(self, po_data, user_po_text):
        try:
            logiwa_data = data_requests.pull_logiwa_data(self.cursor, self.conn, user_po_text)
            for logiwa in logiwa_data:
                if logiwa[1] == "Shipped":
                    messagebox.showerror("Error", str(user_po_text)+" has already been shipped.")
                    self.clear_loaded_po("Any")
                    return
                elif logiwa[1] == "Cancelled":
                    messagebox.showerror("Error", str(user_po_text)+" has already been cancelled.")
                    self.clear_loaded_po("Any")
                    return
            
            if po_data:
                if self.tote_var:
                    beginPage = self.tote_var *2 - 1
                    self.selected_page = beginPage
                self.password_required = False
                active = self.activePO
                date = po_data['datecreated']
                date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%b %d, %Y")
                bot_num = int(po_data['numofbottles'])
                rework = data_requests.pull_rework_data(self.cursor, self.conn, po_data['po'])
                page_count_total = po_data['pagetotal']
                self.bottle_count = bot_num
                self.cur_page.config(text=str(self.selected_page))
                self.tot_page.config(text=page_count_total)
                player.play_tune(['B'], 3, [1])
                self.po_image_grab(self.activePO)
                tote_is_rework = self.get_rework_status(rework)
                if tote_is_rework:
                    self.rework_bool = True
                    data_requests.remove_compilation_data(self.cursor, self.conn, self.activePO, self.tote_var)
                    # toaster = ToastNotifier()
                    print("Rework: This PO has been sent to rework by ", rework[0]['machineid'])
                    messagebox.showinfo("IDR", f"This PO has been sent to rework by {rework[0]['machineid']}")
                if self.tote_var > 1:
                    return True
                elif self.tote_var == 1:
                    self.print_label(po_data['po'], bot_num)
            else:
                bot_num = 1
                self.activePO = self.scan_entry.get().upper()
                self.cur_page.config(text=str(1))
                self.tot_page.config(text="N/A")
                self.paths_to_images = []
                self.update_color_status("Rework")
                
                response = messagebox.askyesno("Error", user_po_text+" is not found in database. Would you like to proceed anyway?", default='no')
                if response:

                    self.print_label(user_po_text, 1)
                else:
                    self.keep_po = True
                    self.scan_entry.delete(0, tk.END)
                    self.scan_entry.config(state=tk.NORMAL)
                    self.clear_loaded_po("None")
                    return False
            return True
        except Exception as e:
            print(e)
        
    #FUNCTION: Option buttons for the image display
    def toggle_option(self, option):
        if self.activePO != "" and len(self.paths_to_images) > 0:
            if self.option_var.get() != option and self.can_click[option]:
                self.option_var.set(option)
                # Disable the clicked button and enable the other button
                if option == "Skins":
                    self.skins_button.config(state=tk.DISABLED)
                    self.id_rings_button.config(state=tk.NORMAL)
                    if self.activePO != "":
                        self.load_image(self.paths_to_images[self.selected_page-1])
                elif option == "ID Rings":
                    self.skins_button.config(state=tk.NORMAL)
                    self.id_rings_button.config(state=tk.DISABLED)
                    self.center_panel.delete("all")
                    if self.activePO != "":
                        self.load_image(self.paths_to_images[self.selected_page-1])
                # Update the state variable to allow the other button to be clicked next
                self.can_click["Skins"] = not self.can_click["Skins"]
                self.can_click["ID Rings"] = not self.can_click["ID Rings"]

    # FUNCTION: Called when pulling PO Image
    def po_image_grab(self, po_value):
        self.paths_to_images = data_requests.get_loaded_images(self.cursor, self.conn, po_value)
        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            if isinstance(self.paths_to_images, str):
                attempts += 1
                if attempts >= max_attempts:
                    logging.error(str(datetime.datetime.now())+" Pull_PO_Data Error1: Failed after 3 attempts to pull data")
                    break
                self.paths_to_images = data_requests.get_loaded_images(self.cursor, self.conn, po_value)
            else:
                break
        
        if len(self.paths_to_images) > 0:
            imagesLoaded = self.load_image(self.paths_to_images[self.selected_page-1])
        else:
            logging.warning(str(datetime.datetime.now())+"Images not Found")
            messagebox.showwarning("Warning:", "Images not found")


    #FUNCTION: load the images from the database onto the canvas
    def load_image(self, page_path):
        part_option = ["Skin", "IDring"]
        if self.option_var.get() == "Skins":
            if page_path.endswith("_"+part_option[1]+".jpg"):
                mod_path = page_path[:-len("_"+part_option[1]+".jpg")] + "_"+part_option[0]+".jpg"
            else:
                mod_path = page_path
        elif self.option_var.get() == "ID Rings":
            if page_path.endswith("_"+part_option[0]+".jpg"):
                mod_path = page_path[:-len("_"+part_option[0]+".jpg")] + "_"+part_option[1]+".jpg"
            else:
                mod_path = page_path
        self.center_panel.delete("all")
        try:
            image = Image.open(mod_path)
            img_width, img_height = image.size
            canvas_height = self.center_panel.winfo_height()-60
            canvas_width = self.center_panel.winfo_width()
            ratio_width = canvas_width / img_width
            ratio_height = canvas_height / img_height

            new_width = int(img_width*ratio_width)
            new_height = int(img_height*ratio_height)
            image_tk = ImageTk.PhotoImage(image.resize(size = [new_width,canvas_height]))
            
            self.image_on_canvas = self.center_panel.create_image(0, 0, anchor="nw", image=image_tk)
        except Exception as e:
            logging.warning(str(datetime.datetime.now())+"Images not Found"+str(e))
            return False
        
        self.image = image_tk
        return True

    # FUNCTION: Flip a page
    def flip_page(self, direction):
        if self.activePO != "":
            pageNum = len(self.paths_to_images)
            if direction == 1 and self.selected_page < pageNum:
                self.selected_page += 1
                self.load_image(self.paths_to_images[self.selected_page-1])
            elif direction == 0 and self.selected_page > 1:
                self.selected_page = self.selected_page - 1
                self.load_image(self.paths_to_images[self.selected_page-1])
            self.cur_page.config(text=str(self.selected_page))

    #FUNCTION: Print the label from the entered PO
    def print_label(self, user_po_num, bot_num):
        barcodeNum = bot_num // 24
        printed = False
        if bot_num % 24 != 0:
            barcodeNum += 1
            try:
                zpl_string = data_requests.display_digit_image(user_po_num, self.font_path, barcodeNum)
                printed = data_requests.print_image_to_printer(zpl_string, self.printer_name)
            except Exception as e: 
                logging.info("Error Printing: " + str(e))
        if printed:
            return
        else:
            toaster = ToastNotifier()
            toaster.show_toast("Printing", "Label was not printed", duration=15, threaded=True)

    #FUNCTION: Update the color of the backgrounds on the top row of active PO panels    
    def update_color_status(self, status):
        if status == "Green":
            self.top_title.config(bg="green")
        elif status == "Rework":
            self.top_title.config(bg="yellow")
        elif status == "Red":
            self.top_title.configure(bg="red")
        elif status == "Blue":
            self.top_title.configure(bg="blue") 
        else:
            self.top_title.config(bg="white")
            self.scan_entry.delete(0, tk.END)
    
    #FUNCTION: Clear the information from the loaded PO
    def clear_loaded_po(self, text):
        self.scan_entry.config(state=tk.NORMAL)
        self.rack_entry.config(state=tk.NORMAL)
        self.activePO = ""
        self.cur_page.config(text="N/A")
        self.tot_page.config(text="N/A")
        self.update_color_status("Clear")
        self.tote_var = 0
        if text != "None":
            self.center_panel.delete("all")
        self.scan_entry.focus_set()
        self.keep_po = False
        self.selected_page = 1
        self.activePO = ""
        self.bottle_count = 0
        self.rack_entry.delete(0, 'end')
        self.scan_entry.delete(0, 'end')
        self.scan_entry.config(state=tk.NORMAL)
        self.rack_entry.config(state=tk.DISABLED)
        self.readyToScan = True
        self.printed_bool = False
        print(text)

    #FUNCTION: Complete the checkout process
    def complete_checkout(self, process, rework_bool):
        if self.activePO != "" and self.top_title.cget("bg") != "blue":
            self.complete_count = self.complete_count + 1
            tote_num = 1
            if self.tote_var:
                tote_num = self.tote_var
            if self.tote_var == self.tote_tot_count:
                self.scan_entry.config(state=tk.NORMAL)
                self.keep_po = False

            if process == "Scan":
                #Update history with checkout marker.
                data_requests.set_IDring_compilation_data(self.cursor, self.conn, self.activePO, self.machineID, self.rack_num, self.tote_var)
                data_requests.update_scan_history(self.cursor, self.conn, self.machineID, self.activePO, rework_bool, True, "Completed", self.processID, tote_num)
                self.clear_loaded_po("Image")
            elif process == "Rework":
                data_requests.update_scan_history(self.cursor, self.conn, self.machineID, self.activePO, rework_bool, True, "Completed", self.processID, tote_num)
                if self.keep_po:
                    self.tote_var += 1
                    #Load next segment of the PO
                    user_po_text = self.activePO
                    po_data = self.pull_po_data(user_po_text)
                    self.display_data(po_data, user_po_text)
                else:
                    self.clear_loaded_po("Image")
            elif process == "Completed":
                #Update hisotry with checkout marker.
                print(self.activePO)
                data_requests.set_IDring_compilation_data(self.cursor, self.conn, self.activePO, self.machineID, self.rack_num, self.tote_var)
                data_requests.update_scan_history(self.cursor, self.conn, self.machineID, self.activePO, rework_bool, True, "Completed", self.processID, tote_num)
                if self.keep_po:
                    self.tote_var += 1
                    #load next segment of the PO
                    user_po_text = self.activePO
                    po_data = self.pull_po_data(user_po_text)
                    self.display_data(po_data, user_po_text)
                    self.rack_num = ""
                    self.rack_entry.config(state=tk.NORMAL)
                    self.rack_entry.delete(0, 'end')
                    self.rack_entry.focus_set()
                    self.rack_scan("<Configure>")
                else:
                    self.clear_loaded_po("Completed")
        player.play_tune(['G'], 4, [2])
        
    def get_tote_num(self, bot_num):
        tote_tot = bot_num // 24
        if bot_num % 24 != 0:
            tote_tot += 1
        return int(tote_tot)
    
    def update_ready_list(self, start):
        all_po = data_requests.get_IDring_compilation_data(self.cursor, self.conn, "all",1)
        if isinstance(all_po, str):
            return
        self.location_rack = [[0,0,0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0]]  
        for po in all_po:
            self.set_rack_location(po[4])        
        
    def get_lid_rack_location(self, po_num):
        if self.tote_var == 0:
            tote = 1
        else:
            tote = self.tote_var
        lid_data = data_requests.get_IDring_compilation_data(self.cursor, self.conn, po_num, tote)
        if lid_data and len(lid_data) == 1:
            rack_location = lid_data[0][4]
        else:
            rack_location = "Unknown"
        return rack_location
    
    def get_next_rack_location(self):
        mapa = ["C","B","A"]
        rack_string = "is Full"
        for sublist_index, sublist in enumerate(self.location_rack):
            for element_index, element in enumerate(sublist):
                if element <8:
                    rack_string = "L"+mapa[sublist_index]+str(element_index+1)
        return rack_string
                
    def set_rack_location(self, rack_num):
        mapa = ["C","B","A"]
        part2 = rack_num[1:2]
        part3 = rack_num[2:]
        self.location_rack[mapa.index(part2)][int(part3)-1] += 1

    def remove_rack_location(self, rack_num):
        mapa = ["C","B","A"]
        part2 = rack_num[1:2]
        part3 = rack_num[2:]
        self.location_rack[mapa.index(part2)][int(part3)-1] -= 1

    def no_tote_tag_process(self):
        self.keep_po = True
        self.scan_entry.config(state=tk.DISABLED)
        self.tote_var = 1
        
    def get_rework_status(self, rework):
        val = False
        for row in rework:
            if int(row['toteid']) == self.tote_var and row['completebool'] == False and row['machineid'] == self.machineID:
                val = True
                break
            else:
                val = False
        return val
    
    #FUNCTION: Pull the Purchse Order data from the database. Called by get_ready_list()
    def pull_po_data(self, po_num):
        try:
            po_data = data_requests.pull_po_data(self.cursor, self.conn, po_num)
            max_attempts = 3
            attempts = 0
            while attempts < max_attempts:
                if isinstance(po_data, str):
                    attempts += 1
                    if attempts >= max_attempts:
                        logging.error(str(datetime.datetime.now())+" Pull_PO_Data Error1: Failed after 3 attempts to pull data")
                        break
                    po_data = data_requests.pull_po_data(self.cursor, self.conn, self.machineID, po_num)
                else:
                    break  # Exit loop if unexpected data type received
            return po_data
        except Exception as e:
            print(e)
        

def on_key_press(key):
    global is_ctrl_pressed
    global is_shift_pressed
    try:
        if key == keyboard.Key.f13.name.upper():
            app.call_cancel("<keyboard.Key.f13>")
        elif key == keyboard.Key.f14.name.upper():
            app.call_rework("<keyboard.Key.f14>")
        elif key == keyboard.Key.f15.name.upper():
            app.call_complete("<keyboard.Key.f15>")
        elif key.char == 'c' and is_ctrl_pressed:
            sys.exit()
    except AttributeError:
        pass

def on_key_release(key):
    global is_ctrl_pressed
    global is_shift_pressed
    if key == keyboard.Key.ctrl_l:
        is_ctrl_pressed = False
    elif key == keyboard.Key.shift:
        is_shift_pressed = False

def main():
    global player
    player = TunePlayer()
    global db_connection
    global app
    db_connection = connect_to_database(connection_params)
    root = tk.Tk()
    app = MachineGUI(root)
    root.bind("<Key>", lambda event: on_key_press(event.keysym))
    root.bind("<KeyRelease>", lambda event: on_key_release(event.keysym))
    if db_connection:
        checker_thread = DatabaseChecker(interval=30, connection_params=connection_params, machineGUI=app)
        checker_thread.start()
    rack_checker_thread = RackChecker(interval=20, machineGUI=app)
    rack_checker_thread.start()
    global is_ctrl_pressed
    global is_shift_pressed
    is_ctrl_pressed = False
    is_shift_pressed = False
    root.mainloop()

if __name__ == "__main__":
    main()
