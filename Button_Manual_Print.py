import tkinter as tk
import data_requests
import subprocess
import pyautogui

class DatabaseContextManager:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.close()

def btn_click_manualprint(self):
    self.password_required = True
    pw_popup = tk.Toplevel(self.master)
    pw_popup.title("Confirmation Password")
    pw_popup.transient(self.master)
    label = tk.Label(pw_popup, text="Please enter the confirmation password:", font=("Helvetica", 18))
    #keyboard_process = subprocess.Popen("osk.exe", shell=True)
    password_entry = tk.Entry(pw_popup, width=9, font=("Helvetica", 30), bg="#D3D3D3")
    password_entry.bind("<Return>", lambda event: password_submit(self, pw_popup, password_entry))
    label.pack(padx=20, pady=10)
    password_entry.pack(padx=20, pady=10)
    password_entry.focus_set()
    pw_popup.wait_window()

def password_submit(self, pw_Window, password_entry):
    with DatabaseContextManager(self.conn) as cursor:
        if data_requests.get_use_pword(cursor, self.conn, password_entry.get(), self.shift_lead): 
            pw_Window.destroy()
            po_popup = tk.Toplevel(self.master)
            po_popup.title("Manually Print Barcode")
            po_popup.transient(self.master)
            po_label = tk.Label(po_popup, text="Please enter a purchase order number to print:", font=("Helvetica", 18))
            po_entry = tk.Entry(po_popup, width=9, font=("Helvetica", 30), bg="#D3D3D3")
            po_entry.bind("<Return>", lambda event: print_po(self, po_popup, po_entry.get()))
            po_label.pack(padx=20, pady=10)
            po_entry.pack(padx=20, pady=10)
            po_entry.focus_set()
            po_popup.wait_window()
        else:
            if hasattr(pw_Window, "incorrect"):
                pw_Window.incorrect.destroy()
            password_entry.delete(0, tk.END)
            pw_Window.incorrect = tk.Toplevel(pw_Window)
            pw_Window.incorrect.title = 'Incorrect Password'
            pw_Window.incorrect.transient(pw_Window)
            label = tk.Label(pw_Window.incorrect, text="Incorrect password. Please try again.", font=("Helvetica", 14))
            label.pack(padx=20, pady=10)

def print_po(self, po_popup, user_po):
    self.password_required = False
    po_popup.destroy()
    self.po_temp[0] = user_po


    

