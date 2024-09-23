import tkinter as tk
from tkinter import ttk
from tkinter import Checkbutton
import logging
import pyodbc
import csv
from datetime import datetime
import json
import os

with open('config.json') as f:
        config = json.load(f)

output_location = "T:\\Rework Requests\\"
def btn_click_send_to_rework(self, po_num, bottle_count):
    self.rework_canceled = True
    window = self.master
    rework_window = tk.Toplevel(window)
    rework_window.title("Send to Rework")
    rework_window.transient(window)

    checkbox_frame = tk.Frame(rework_window)
    checkbox_frame.pack(pady=20)

    canvas = tk.Canvas(checkbox_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(checkbox_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Configure the canvas to use the scrollbar
    canvas.configure(yscrollcommand=scrollbar.set)
    # Function to handle mouse wheel scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # Bind the mouse wheel event to the canvas
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    # Create another frame inside the canvas
    inner_frame = ttk.Frame(canvas)

    # Add the inner frame to the canvas window
    canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)

    bottle_frame = tk.Frame(inner_frame)
    ring_frame = tk.Frame(inner_frame)
    bottle_frame.pack(padx=20, side="left")
    ring_frame.pack(padx=20, side="right")

    # Function to resize the canvas scroll region
    def configure_canvas(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    # Bind the event to the function
    inner_frame.bind("<Configure>", configure_canvas)

    start_bottle = 0
    endbottle = 0
    if self.tote_var:
        start_bottle  = (self.tote_var *2 - 1)*12 - 12
        endbottle = start_bottle + 24
    if endbottle == 0 or endbottle > bottle_count:
         endbottle = bottle_count
    checkbox_btl = []
    checkbox_idr = []
    font_size = 14  # Adjust the font size as needed
    checkbox_height = 2
    checkbox_width = 8
    if bottle_count != "N/A":
        for i in range(start_bottle, endbottle):
                var = tk.BooleanVar(value=False)
                checkbox_btl.append(var)
                checkbox_Bottles = Checkbutton(bottle_frame, text=f"Bottle {i+1}", variable=var, font=("Helvetica", font_size), height=checkbox_height, width=checkbox_width)
                checkbox_Bottles.pack(anchor='w')
        for i in range(start_bottle, endbottle):
                var = tk.BooleanVar(value=False)
                checkbox_idr.append(var)
                checkbox_IDRings = Checkbutton(ring_frame, text=f"ID Ring {i+1}", variable=var, font=("Helvetica", font_size), height=checkbox_height, width=checkbox_width)
                checkbox_IDRings.pack(anchor='e')


    inner_frame.update_idletasks()

    # Update the canvas scroll region
    canvas.config(scrollregion=canvas.bbox("all"))

    # Send button
    send_button = tk.Button(rework_window, text="Send", command=lambda: send_action(self, rework_window, po_num, checkbox_btl, checkbox_idr, start_bottle), width=20, height=3, font=("Helvetica", 16))
    send_button.pack(pady=10)

    # Cancel button
    cancel_button = tk.Button(rework_window, text="Cancel", command=lambda: cancel_clicked(self, rework_window), width=20, height=3, font=("Helvetica", 16))
    cancel_button.pack(pady=10)
    rework_window.wait_window()

def cancel_clicked(self, root):
    self.rework_canceled = True
    root.destroy()

def send_action(self, root, po_num, checkbox_btl, checkbox_idr, start_bottle):
    print(checkbox_btl, "btl")
    print(checkbox_idr, "idr")
    skin_reworks = [start_bottle+i+1 for i, var in enumerate(checkbox_btl) if var.get()]
    idr_reworks = [start_bottle+i+1 for i, var in enumerate(checkbox_idr) if var.get()]
    print(skin_reworks, idr_reworks)
    page_num = [0,0]
    page_num1 = determine_page_numbers(skin_reworks)
    page_num2 = determine_page_numbers(idr_reworks)
    try:
        for i in range(len(page_num)):
            if page_num1[i]:
                page_num[i] = page_num1[i]
            if page_num2[i]:
                page_num[i] = page_num2[i]
    except Exception as e:
        logging.info(str(e))

    if page_num == [0,0]:
        cancel_clicked(self,root)
    rework_request(skin_reworks, idr_reworks, po_num, output_location,self.tote_var, self.machineID)
    input_notes = "\nSkins sent: " + str(skin_reworks) + "\nID Rings sent: " + str(idr_reworks)
    try:
        date = datetime.now()
        #Query for notes in DB
        query = "INSERT INTO T_Quality_Information (Machine_ID, Purchase_Order, Note_Desc, Dt_Submitted) VALUES (?, ?, ?, ?)"
        self.cursor.execute(query, ((self.machineID, po_num, input_notes, date)))
        self.conn.commit()

        sql_update = "INSERT INTO T_Rework_Info (Purchase_Order, Dt_Sent, Page_Num, Tote_ID, Bottle_Num, Rework_Count, Complete_Bool, Machine_ID, Part_Opt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        for skins in skin_reworks:
            self.cursor.execute(sql_update, (po_num,date, ((skins - 1) // 12) + 1, self.tote_var, skins, 1, False, self.machineID, "Skin",))
        self.conn.commit()

        for idr in idr_reworks:
            self.cursor.execute(sql_update, (po_num,date, ((idr - 1) // 12) + 1, self.tote_var, idr, 1, False, self.machineID, "ID Ring",))
        self.conn.commit()
        self.rework_canceled = False
        logging.info(str(datetime.now())+" Sent to rework: " + str(po_num))
        root.destroy()
    except pyodbc.Error as e:
        logging.error(str(datetime.now())+"SEND_ACTION(): "+str(e))
        print(e)

def determine_page_numbers(bottle_numbers, bottles_per_page=12):
    page_numbers = set()

    for bottle_number in bottle_numbers:
        page_number = (bottle_number - 1) // bottles_per_page + 1
        page_numbers.add(page_number)

    # Convert the set to a sorted list of unique page numbers
    unique_page_numbers = sorted(page_numbers)
    
    # If there are more than two page numbers, truncate the list to contain only the first two values
    unique_page_numbers = unique_page_numbers[:2]

    return unique_page_numbers


def rework_request(skin_reworks, IDring_reworks, PO_Number, output_location, tote_num, machine):
    timestamp = datetime.now().strftime("%Y-%m-%d %Hh%Mm%Ss")
    filename = f"ReworkRequest {PO_Number} {timestamp}.csv"
    if not os.path.exists(os.path.dirname(output_location)):
        os.makedirs(os.path.dirname(output_location))
    skin_reworks_with_zeros = [f"{num:02d}" for num in skin_reworks]
    IDrings_reworks_with_zeros = [f"{num:02d}" for num in IDring_reworks]
    file_location = output_location + filename
    machineID= str(machine)
    try:
        with open(file_location, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter= ",")
            writer.writerow(["Purchase Order: " + PO_Number])
            writer.writerow(["Timestamp: " + timestamp])
            writer.writerow(["Skins to rework: "])
            writer.writerow(skin_reworks_with_zeros)
            writer.writerow(["ID Rings to rework: "])
            writer.writerow(IDrings_reworks_with_zeros)
            writer.writerow(["Tote Number: "])
            writer.writerow([tote_num])
            writer.writerow(["MachineID: "])
            writer.writerow([machineID])
    except:
        logging.error(str(datetime.now())+" rework_request() file write fail: ")


