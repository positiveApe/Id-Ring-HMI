import json
from tkinter import Tk
import pyodbc
from datetime import datetime
import logging
import win32print
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime
import math
import os
from zebrafy import ZebrafyImage

class DatabaseContextManager:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.close()

# FUNCTION: Called when pulling data from access database. 
def pull_po_data(cursor, conn, po_value):
    print("po_value", po_value)
    print('pull po data in data_request')
    with DatabaseContextManager(conn) as cursor:
        try:
            po_match_query = f"""
            SELECT Purchase_Order, Date_Created, File_Directory, Page_Total, Num_of_Bottles
            FROM T_Purchase_Order 
            WHERE Purchase_Order = ?;"""
            cursor.execute(po_match_query, (po_value,))
            po_match = cursor.fetchone()
            conn.commit()
            print(po_match)
            result_dict = {
                'po': po_match[0],
                'datecreated': po_match[1],
                'filedirectory': po_match[2],
                'pagetotal': po_match[3],
                'numofbottles': po_match[4]
            }
            # po_data.append(result_dict)
            if po_match == None:
                return False
            return result_dict
        except pyodbc.Error as e:
            logging.error(str(datetime.datetime.now())+" pull_po_data(): "+str(e))
            print(e)
            print("Oppsie whoopsie")
            conn.rollback()
            return str(e)
        
#Update the scan history of a PO with the machine ID of last scan
def update_scan_history(cursor, conn, machineID, po_num, rework_bool, print_bool,checkinout, process_num, tote_num):
    date_scanned = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    barcode_print = True
    part_opt = 'OptionXYZ'
    with DatabaseContextManager(conn) as cursor:
        try:
            # Construct the SQL UPDATE statement
            sql_insert = "INSERT INTO T_Scan_History (Machine_ID, Purchase_Order, Dt_Scanned, Rework_Bool, Barcode_Print_Bool, CheckInOut, Process_Num, Tote_Num) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            # Execute the SQL update statement with the provided values
            cursor.execute(sql_insert, (machineID, po_num, date_scanned, rework_bool, print_bool, checkinout, process_num,tote_num,))
            # Commit the transaction
            conn.commit()
        except Exception as e:
            logging.error(str(datetime.now())+" update_scan_history(): "+str(e))
            conn.rollback()
    
    
#Update the scan history of a PO with the machine ID of last scan
def get_scan_history(cursor, conn, po_num, tote_num):
    print("get scan history")
    with DatabaseContextManager(conn) as cursor:
        try:
            query = f"SELECT Purchase_Order, Machine_ID, Dt_Scanned, Rework_Bool, CheckInOut, Process_Num, Tote_Num, Barcode_Print_Bool FROM T_Scan_History WHERE Purchase_Order = ? AND Tote_Num = ? ORDER BY Dt_Scanned DESC"
            cursor.execute(query, (po_num,tote_num,))
            query_list = cursor.fetchall()
            conn.commit()
            return query_list
            
        except Exception as e:
            logging.error(str(datetime.now())+" get_scan_history(): "+str(e))
            conn.rollback()

# FUNCTION: Called when pulling rework data from access database. 
def pull_rework_data(cursor, conn, po_value):
    with DatabaseContextManager(conn) as cursor:
        try:
            print("pulling rework data")
            rework_match_query = f"""
            SELECT Purchase_Order, Dt_Sent, Page_Num, Tote_ID, Bottle_Num, Complete_Bool, Machine_ID, Part_Opt
            FROM T_Rework_Info 
            WHERE Purchase_Order = ?;"""
            cursor.execute(rework_match_query, (po_value,))
            po_match = cursor.fetchall()
            conn.commit()
            po_data = []
            for row in po_match:
                result_dict = {
                    'po': row[0],
                    'datesent': row[1],
                    'pagenum': row[2],
                    'toteid': row[3],
                    'bottlenum': row[4],
                    'completebool': row[5],
                    'machineid': row[6],
                    'partopt': row[7]
                }
                po_data.append(result_dict)
            if po_match == None:
                print('rework info - Did not find match.')
                return False
            else:
                print('Rework info - Data Extracted')
            print(po_data)
            return po_data
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" pull_rework_data(): "+str(e))
            print(e)
            conn.rollback()
            return str(e)
        
def pull_logiwa_data(cursor, conn, po_value):
    with DatabaseContextManager(conn) as cursor:
        try:
            print("pulling logiwa data")
            rework_match_query = f"""
            SELECT Purchase_Order, Order_Status, Order_Date, Planned_Quantity
            FROM T_Logiwa_Data 
            WHERE Purchase_Order = ?;"""
            cursor.execute(rework_match_query, (po_value,))
            po_match = cursor.fetchall()
            conn.commit()
            po_data = []
            for row in po_match:
                po_data.append(row)
            if po_match == None:
                print('PO Information - Did not find match.')
                return False
            else:
                print('PO Information - Data Extracted')

            return po_data
        except pyodbc.Error as e:
            print(e)
            logging.error(str(datetime.now())+" pull_logiwa_data(): "+str(e))
            return False
        
def set_rework_complete(cursor, conn, po_value):
    with DatabaseContextManager(conn) as cursor:
        try:
            print("pulling rework data")
            rework_match_query = f"""
            UPDATE T_Rework_Info SET Complete_Bool = True, Machine_ID = null
            WHERE Purchase_Order = ?;"""
            cursor.execute(rework_match_query, (po_value,))
            conn.commit()
    
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_rework_complete(): "+str(e))
            print(e)
            conn.rollback()
            return str(e)

def display_digit_image(digit_string, font_path, tote_num):
    if len(digit_string) == 10:
        codeType = 10
    elif len(digit_string) == 8:
        codeType = 8
    zpl_string = []
    page = 0
    secondPage = 0
    for i in range(tote_num):
        # Determine the number of characters to use based on codeType
        if codeType == 8:
            text_to_draw = digit_string[:8]
        elif codeType == 10:
            text_to_draw = digit_string[:10]
        else:
            text_to_draw = digit_string  # Fallback, in case of unexpected codeType values

        digit_string = text_to_draw + "T"+ f"{i+1:02d}"
        print(digit_string)
        # Create a blank image with a white background
        image_size = (400, 190)
        image = Image.new("RGB", image_size, "white")
        draw = ImageDraw.Draw(image)
        print("Drawn")
        # Load the specified font for the main digit
        digit_font = ImageFont.truetype(font_path, 26)
        digit_arial_font = ImageFont.truetype("arial.ttf", 36)
        # Load Arial font for date and time
        arial_font = ImageFont.truetype("arial.ttf", 22)
        # Draw the digit on the image
        draw.text((70, 10), '*' + digit_string + '*', font=digit_font, fill="black", align="center")
        draw.rectangle([(40,95),(400,120)], fill="White")
        draw.text((70, 105), text_to_draw, font=digit_arial_font, fill="black", align="center")
    
        # Get current date and time
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        start_date = datetime.strptime('2024-1-5',"%Y-%m-%d")
    
        # Date Functions
        delta = datetime.now() - start_date
        week_num = math.floor(delta.days / 7) + 1
        week_code = week_num - math.floor(week_num / 52) * 52
        day_code = delta.days - ((week_num - 1) * 7) + 1
    
        # Draw the current date and time using Arial font
        draw.text((70, 155), f"Tote: {i+1:02d}/{tote_num:02d}", font=arial_font, fill="Black", align="center")
        date = datetime.now()
        draw.text((185, 155), f"{str(date)[:10]}", font=arial_font, fill="Black", align="center")
        page += 1
        # Week/Day Symbol
        draw.polygon([(335, 115),(365, 115),(385, 150),(365, 185),(335, 185),(315, 150)], fill="White", outline="Black", width=3)
        draw.text((325,125),f"{week_code:02d}", font=ImageFont.truetype("arial.ttf", 48), fill="Black", align="center")
    
        # Save the image to the specified file location
        print("saving image to files")
        image.save("Live Barcode Printing"+str(i)+".png")
        zpl_string.append(ZebrafyImage(image,
        compression_type="A",
            invert=True,
            dither=False,
            threshold=128,
            width=0,
            height=0,
            pos_x=0,
            pos_y=0,
            complete_zpl=False,
        ).to_zpl())
    return zpl_string
 
def print_image_to_printer(zpl_stringList, printer_name):
    try:
        labels = []
        for i in zpl_stringList:

            labels.append("^XA" + i + "^XZ")
        # Create a printer job
        hprinter = win32print.OpenPrinter(printer_name)
        # Start a print job
        hjob = win32print.StartDocPrinter(hprinter, 1, ("Print Job", None, "RAW"))
        # Send the image to the printer
        
        for label in labels:
            win32print.StartPagePrinter(hprinter)
            #with open(output_path, 'rb') as f:
            win32print.WritePrinter(hprinter, label.encode())
            win32print.EndPagePrinter(hprinter)
        # End the print job
        win32print.EndDocPrinter(hprinter)
        # Close the printer handle
        logging.info(str(datetime.now())+" Label Printed")
        return True
    except Exception as e:
        logging.error(str(datetime.now())+" Error printing:"+str(e))
        print("Error printing: ", str(e))
        return False
    finally:
        win32print.ClosePrinter(hprinter)
 

#FUNCTION: Get image paths
def get_loaded_images(cursor, conn, po_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            po_image_query = f"SELECT Purchase_Order, File_Directory, Page_Total FROM T_Purchase_Order WHERE Purchase_Order = ? ORDER BY Dt_Saved DESC"
            cursor.execute(po_image_query, (po_num,))
            po_image_file = cursor.fetchone()
            directory_path = []
            conn.commit()
            data = {
                'po': po_image_file[0],
                'filedirectory': po_image_file[1],
                'pagetotal': po_image_file[2]
            }
            if data:
                print(data, "po_image_file")
                pagecount = int(data['pagetotal'])
                file_directory = data['filedirectory']
                for page in range(0,pagecount):
                    for i in range(2):
                        if i == 1:
                            part_txt = "IDring"
                        else: 
                            part_txt = "Skin"
                        path_string = f"{os.path.dirname(file_directory)}\\{os.path.basename(file_directory)}\\{os.path.basename(file_directory)}_{page+1:02d} of {pagecount:02d} merged_{part_txt}.jpg"
                        directory_path.append(path_string)
                return sorted(directory_path)
            else:
                return False  
        except Exception as e:
            logging.error(str(datetime.now())+" get_loaded_images():"+str(e))
            print("Error loading image: ", str(e))
            conn.rollback()
            return str(e)
    
#Make sure that we are checking that we are only pulling the latest PO info when pulling PO info
    
#FUNCTION: get shift info
def get_shift_info(cursor, conn, shiftID):
    with DatabaseContextManager(conn) as cursor:
        try:
            po_image_query = f"SELECT TOP 1 Shift_Date, Shift_Name, Shift_Lead, Completed_Count, Defect_Count, Rework_Count FROM T_Shift_History WHERE Shift_Name = ? ORDER BY Shift_Date DESC"
            cursor.execute(po_image_query, (shiftID,))
            shift_history = cursor.fetchone()
            return shift_history
            
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" get_shift_info():"+str(e))
            print(e)
            conn.rollback()
            return str(e)
        
def get_users(cursor, conn, shiftID):
    with DatabaseContextManager(conn) as cursor:
        try:
            po_image_query = f"SELECT user_name FROM T_Users WHERE Shift_ID = ?"
            cursor.execute(po_image_query, (shiftID,))
            shift_lead = cursor.fetchall()
            stringlist = []
            for i in shift_lead:
                stringlist.append(str(i[0]))
            return stringlist
            
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" get_users():"+str(e))
            print(e)
            conn.rollback()
            return str(e)

def set_shift_info(cursor, conn, date, current_shift, shift_lead, complete_count, reject_total, rework_count):
    with DatabaseContextManager(conn) as cursor:
        try:
            sql_insert = "INSERT INTO T_Shift_History (Shift_Date, Shift_Name, Shift_Lead, Completed_Count, Defect_Count, Rework_Count) VALUES (?, ?, ?, ?, ?, ?)"
            cursor.execute(sql_insert, (date, current_shift, shift_lead, complete_count, reject_total, rework_count,))
            conn.commit()

        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_shift_info():"+str(e))
            print(e)
            conn.rollback()


def get_IDring_compilation_data(cursor, conn, po_num, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            if po_num == "all":
                idring_comp_query = f"SELECT Purchase_Order, Dt_Checked, Dt_Compiled, Compiled_Bool, Shelf_ID,Tote_ID  FROM T_IDring_Comp WHERE Compiled_Bool = False"
                cursor.execute(idring_comp_query)
                idring_compilation = cursor.fetchall()
                return idring_compilation
            elif po_num == "compiled":
                idring_comp_query = f"SELECT Purchase_Order, Dt_Checked, Dt_Compiled, Compiled_Bool, Shelf_ID,Tote_ID  FROM T_IDring_Comp WHERE Compiled_Bool = True"
                cursor.execute(idring_comp_query)
                idring_compilation = cursor.fetchall()
                return idring_compilation
            elif po_num != "":
                idring_comp_query = f"SELECT Purchase_Order, Dt_Checked, Dt_Compiled, Compiled_Bool, Shelf_ID, Tote_ID FROM T_IDring_Comp WHERE Purchase_Order = ? AND Tote_ID = ?"
                cursor.execute(idring_comp_query, (po_num, tote_num,))
                idring_compilation = cursor.fetchall()
                return idring_compilation
            
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" get_IDring_compilation_data():"+str(e))
            return str(e)

def get_skin_compilation_data(cursor, conn, po_num, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            idring_comp_query = f"SELECT Purchase_Order, Dt_Checked, Dt_Compiled, Compiled_Bool, Shelf_ID FROM T_Skin_Comp WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(idring_comp_query, (po_num, tote_num,))
            idring_compilation = cursor.fetchall()
            return idring_compilation
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" get_skin_compilation_data():"+str(e))
            return str(e)
        
def get_compilation_data(cursor, conn, po_num, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            idring_comp_query = f"SELECT Purchase_Order, Dt_Checked, Dt_Compiled, Compiled_Bool, Shelf_ID FROM T_PO_Compile WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(idring_comp_query, (po_num, tote_num,))
            idring_compilation = cursor.fetchall()
            return idring_compilation
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" get_compilation_data():"+str(e))
            return str(e)
        
def set_IDring_compilation_data(cursor, conn, po_num, machine_id, shelf_id, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            comp_query = f"INSERT INTO T_IDring_Comp (Purchase_Order, Machine_ID, Dt_Checked, Shelf_ID, Tote_ID) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(comp_query, (po_num, machine_id, date, shelf_id, tote_num,))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_IDring_compilation_data():"+str(e))
            conn.rollback()
            return str(e)
        
def update_IDring_compilation_data(cursor, conn, po_num, shelf_id, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            comp_query = f"UPDATE T_IDring_Comp SET Shelf_ID = ? WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(comp_query, (shelf_id, po_num, tote_num,))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" update_IDring_compilation_data():"+str(e))
            conn.rollback()
            return str(e)

def set_skin_compilation_data(cursor, conn, po_num, machine_id, shelf_id, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            comp_query = f"INSERT INTO T_Skin_Comp (Purchase_Order, Machine_ID, Dt_Checked, Shelf_ID, Tote_ID) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(comp_query, (po_num, machine_id, date, shelf_id, tote_num,))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_skin_compilation_data():"+str(e))
            conn.rollback()
            return str(e)
        
def set_compilation_data(cursor, conn, po_num, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            comp_query = f"SELECT Purchase_Order, Dt_Checked, Dt_Complied, Compiled_Bool, Shelf_ID FROM T_PO_Compile WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(comp_query, (po_num, tote_num,))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_compilation_data():"+str(e))
            conn.rollback()
            return str(e)
        
def remove_compilation_data(cursor, conn, po_num, tote_num):
    with DatabaseContextManager(conn) as cursor:
        try:
            print(po_num, tote_num)
            comp_query = "DELETE FROM T_PO_Compile WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(comp_query, (po_num, tote_num,))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_compilation_data() insert for PO:"+str(e))
            conn.rollback()
            return str(e)
        try:
            comp_skin_query = "DELETE FROM T_Skin_Comp WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(comp_skin_query, (po_num, tote_num))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_compilation_data() update for skins:"+str(e))
            conn.rollback()
            return str(e)
        try:
            comp_lid_query = "DELETE FROM T_IDring_Comp WHERE Purchase_Order = ? AND Tote_ID = ?"
            cursor.execute(comp_lid_query, (po_num, tote_num))
            conn.commit()
        except pyodbc.Error as e:
            logging.error(str(datetime.now())+" set_compilation_data() update for lids:"+str(e))
            conn.rollback()
            return str(e)