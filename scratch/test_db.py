import mysql.connector
from mysql.connector import Error
import os

def test_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        if connection.is_connected():
            print("Successfully connected to MySQL")
            connection.close()
    except Error as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection()
