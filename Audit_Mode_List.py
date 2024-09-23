import tkinter as tk
from tkinter import ttk
import data_requests

def get_audit_list(self, root):
    # Create a new toplevel window
    second_window = tk.Toplevel(root)
    second_window.title("Audit List")

    # Fetch data from the database
    data = data_requests.get_IDring_compilation_data(self.cursor, self.conn,"all", 1)
    list_data = []
    for row in data:
        list_row = []
        list_row.append(row[0])
        list_row.append(row[1])
        list_row.append(row[4])
        list_row.append(row[5])
        list_data.append(list_row)

    # Display the number of values in the list
    num_values_label = tk.Label(second_window, text=f"Total: {len(data)}", font=("Helvetica", 20))
    num_values_label.pack()

    # Create a treeview widget to display the data in a scrollable list
    tree = ttk.Treeview(second_window)
    tree['columns'] = ('PO', 'Date Checked In', 'Rack Location', 'Tote Number')  # Adjust column names as needed
    tree.heading('#0', text='Index')  # Index column
    tree.heading('#1', text='PO')  # Adjust column names as needed
    tree.heading('#2', text='Date Checked In')  # Adjust column names as needed
    tree.heading('#3', text='Rack Location')  # Adjust column names as needed
    tree.heading('#4', text='Tote Number')  # Adjust column names as needed

    # Add data to the treeview
    for idx, row in enumerate(list_data):
        tree.insert('', idx, text=str(idx), values=row)

    # Add a scrollbar
    scrollbar = ttk.Scrollbar(second_window, orient='vertical', command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)

    # Pack the treeview widget
    tree.pack(expand=True, fill='both')

    cancel_button = tk.Button(second_window, text="Cancel", command=lambda: cancel_clicked(second_window), width=20, height=2, font=("Helvetica", 20))
    cancel_button.pack()
    
    cancel_and_end_button = tk.Button(second_window, text="Exit Audit", command=lambda: cancel_and_end(self, second_window), width=20, height=2, font=("Helvetica", 20))
    cancel_and_end_button.pack()
    second_window.wait_window()

def cancel_clicked(root):
    root.destroy()

def cancel_and_end(self, root):
    self.call_audit("<Return>")
    root.destroy()
