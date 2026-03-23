import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host='localhost',          
        user='root',       
        password='',   
        database='smart_classroom'    
    )
    if connection.is_connected():
        print("Connection established successfully")

except Error as e:
    print(f"Error connecting to MySQL database: {e}")

# finally:
#     # This block ensures the connection is closed even if an error occurs
#     if 'connection' in locals() and connection.is_connected():
#         connection.close()
#         print("Connection closed.")
def show_tables():
    try:
        cursor = connection.cursor()
        cursor.execute("show tables")
        tables = cursor.fetchall()
        print("Tables in the database:")
        for table in tables:
            print(table[0])
    except Error as e:
        print(f"Error showing schema: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")
def table_schema(table_name):
    try:
        cursor = connection.cursor()
        show_tables()
        cursor.execute(f"DESCRIBE {table_name}")
        schema = cursor.fetchall()
        print("Schema of the table:")
        for row in schema:
            print(row)
    except Error as e:
        print(f"Error showing schema: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")

def add_data_to_database():
    try:
        cursor = connection.cursor()
        table_name = input("Enter the table name: ")
        table_schema(table_name)
        insert_query = "INSERT INTO table_name VALUES (%s)"
        cursor.execute(insert_query, (data,))
        connection.commit()
        print(f"Data added successfully: {data}")
    except Error as e:
        print(f"Error adding data to database: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")


def get_data_from_database():
    try:
        cursor = connection.cursor()
        select_query = "SELECT * FROM test_table"
        cursor.execute(select_query)
        result = cursor.fetchall()
        print("Data retrieved successfully:")
        for row in result:
            print(row)
    except Error as e:
        print(f"Error retrieving data from database: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")

def update_data_in_database(data, id):
    try:
        cursor = connection.cursor()
        update_query = "UPDATE test_table SET name = %s WHERE id = %s"
        cursor.execute(update_query, (data, id))
        connection.commit()
        print(f"Data updated successfully: {data}")
    except Error as e:
        print(f"Error updating data in database: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")

def delete_data_from_database(id):
    try:
        cursor = connection.cursor()
        delete_query = "DELETE FROM test_table WHERE id = %s"
        cursor.execute(delete_query, (id,))
        connection.commit()
        print(f"Data deleted successfully: {id}")
    except Error as e:
        print(f"Error deleting data from database: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")

def get_data_from_database_by_id(id):
    try:
        cursor = connection.cursor()
        select_query = "SELECT * FROM test_table WHERE id = %s"
        cursor.execute(select_query, (id,))
        result = cursor.fetchone()
        print(f"Data retrieved successfully: {result}")
    except Error as e:
        print(f"Error retrieving data from database: {e}")
    finally:
        if 'cursor' in locals() and cursor.is_connected():
            cursor.close()
            print("Cursor closed.")


def main():
    while True:
        print("1. Add data to database")
        print("2. Get data from database")
        print("3. Update data in database")
        print("4. Delete data from database")
        print("5. Get data from database by id")
        print("6. Tables Schema")
        print("7. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            # data = input("Enter the data: ")
            add_data_to_database()
        elif choice == "2":
            get_data_from_database()
        elif choice == "3":
            data = input("Enter the data: ")
            id = input("Enter the id: ")
            update_data_in_database(data, id)
        elif choice == "4":
            id = input("Enter the id: ")
            delete_data_from_database(id)
        elif choice == "5":
            id = input("Enter the id: ")
            get_data_from_database_by_id(id)
        elif choice == "6":
            table_name = input("Enter the table name: ")
            table_schema(table_name)
        elif choice == "7":
            break
        else:
            print("Invalid choice")

__init__ = main()