import pyodbc
import json
import os
from datetime import datetime
import csv


with open('config.json') as f:
        config = json.load(f)

rework_path = "C:\\Users\\NicCornejo\\Documents\\CodeRepo\\NicActive\\IDR\\Rework Requests\\"
db_folder_path = config['local_files'] + config['databaseName']
connection_params = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};" + \
    rf"DBQ={db_folder_path};"
)

def connect_to_database(connection_params):
    # PROCEDURE: Creates a connection to the Access Database for Team Shop data.
    try: 
        conn = pyodbc.connect(connection_params)
    except pyodbc.Error as e:
        print("Error Connecting")
    return conn

# Function to process each CSV file
def process_csv(file_path):
    # Extract file name
    file_name = os.path.basename(file_path)
    print(f"Processing file: {file_name}")

    # Read CSV file
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=':')
        data = []
        for row in reader:
            data.append(row)

    # Extract required information
    purchase_order = data[0][1][1:]
    skins_to_rework = data[3]
    id_rings_to_rework = data[5]
    tote_number = data[7][0]
    machine_id = data[9][0]
    
    return purchase_order, skins_to_rework, id_rings_to_rework, tote_number, machine_id

    
def move_file(file_path):
    file_name = os.path.basename(file_path)
    processed_dir = os.path.join(os.path.dirname(file_path), 'Processed Rework')
    os.makedirs(processed_dir, exist_ok=True)
    new_file_path = os.path.join(processed_dir, file_name)
    if os.path.exists(new_file_path):
        base_name, extension = os.path.splitext(file_name)
        index = 1
        while True:
            new_file_path = os.path.join(processed_dir, f"{base_name}_{index}{extension}")
            if not os.path.exists(new_file_path):
                break
            index += 1
    os.rename(file_path, new_file_path)
    print(f"Moved file to: {new_file_path}")

    # Add a timestamp to the end of the CSV file
    with open(new_file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=':')
        writer.writerow([])
        writer.writerow(['Processed at', datetime.now()])
         

def process_rework(po_num, tote_num):
    conn = connect_to_database(connection_params=connection_params)
    for i in range(2):
        sql_update = "UPDATE T_Purchase_Order SET Rework_Bool = True, Sent_Rework = Null WHERE Purchase_Order = ? AND Current_Page = ?"
        if i == 0:
            tote = int(tote_num)*2
            print(tote)
            conn.cursor.execute(sql_update, (po_num,tote,))
            conn.commit()
        else:
            tote = (int(tote_num)*2)-1
            print(tote)
            conn.cursor.execute(sql_update, (po_num,tote,))
            conn.commit()

def runme():
    # Directory containing CSV files
    directory = rework_path

    # List all CSV files in the directory
    csv_files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.csv')]
    print("Rework processing started... \n")
    if csv_files == []:
        print("There are no Rework items to process")
    # Process each CSV file
    for file_path in csv_files:
        purchase_order, skins_to_rework, id_rings_to_rework, tote_number, machine_id = process_csv(file_path)
        process_rework(purchase_order, tote_number)
        move_file(file_path)


runme()