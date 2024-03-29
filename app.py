from selenium import webdriver
from time import sleep
from selenium.webdriver.common.by import By
import mysql.connector
import os
from datetime import datetime

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# log file name
log_filename = "speedface_log"
# script directory
script_path = os.path.dirname(os.path.realpath(__file__))
log_file_path = script_path + "/" + log_filename

# function to print messages to terminal and log them in a file
def print_and_log(message):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = open(log_file_path, "a")
    log_file.write("[" + current_time + "] " + message + "\n")
    log_file.close()



mysql_ip = os.getenv("MYSQL_HOST")
mysql_user = os.getenv("MYSQL_USER")
mysql_pass = os.getenv("MYSQL_PASS")
mysql_db = os.getenv("MYSQL_DB")
mysql_table = os.getenv("MYSQL_TABLE")
turnstile_url = os.getenv("TURNSTILE_URL")

# Function to scrape data using Selenium
def selenium_speedface():
    try:
        # Initialize Chrome WebDriver
        option = webdriver.ChromeOptions()
        option.add_argument("--headless")
        option.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=option)
        driver.set_window_size(1500,800)

        # Open the specified URL
        driver.get(turnstile_url)

        sleep(5)
        # Find the username input field and enter the username
        element_username = driver.find_element(By.ID, "username") 
        element_username.send_keys("selenium")

        # Find the password input field and enter the password
        element_password = driver.find_element(By.ID, "password") 
        element_password.send_keys("Selenium2024")

        # Find the login button and click it
        button_login = driver.find_element(By.ID, "test") 
        button_login.click()

        # Wait for 5 seconds for the page to load
        sleep(5)

        # Find and click on the account menu
        click_accmenu = driver.find_element(By.ID, "AccMenu") 
        click_accmenu.click()

        # Wait for 5 seconds for the menu to expand
        sleep(5)

        # Find and click on the specific image element
        element_img = driver.find_element(By.XPATH, "//img[@src='public/images/menuTree/comm_reports.png']")
        element_img.click()

        # Wait for 5 seconds for the page to load
        sleep(5)

        # Find and click on the specific span element with text 'Events From Today'
        element_span = driver.find_element(By.XPATH, "//span[text()='Events From Today']")
        element_span.click()

        # Wait for 5 seconds for the page to load
        sleep(5)

        # Find the table with class name 'objbox'
        table = driver.find_elements(By.CLASS_NAME, "objbox")

        # If the table is found, select the first one
        first_tr = table[0]
        # Find all rows in the table
        rows = first_tr.find_elements(By.TAG_NAME, "tr")
        data_list = []
        
        if len(rows) > 1:
            # Loop through each row and extract data from specific columns
            for row in rows:
                columns = row.find_elements(By.TAG_NAME, "td")
                column_list = []
                
                # Check if columns are not empty
                if columns:
                    column_list.append(columns[1].text)  # Assuming second column holds desired data
                    column_list.append(columns[7].text)  # Assuming eighth column holds desired data
                    if columns[3].text == "chek inn":
                        column_list.append(0)
                    elif columns[3].text == "chek out":
                        column_list.append(1)
                    

                # Check if column list is not empty before appending to data list
                if column_list:
                    data_list.append(column_list)

            # Return the extracted data
            return data_list
        
        else:
            # Print and log a message if no data is found in the table
            # print_and_log("No Found Data in Today's table")
            driver.quit()
            exit()

    except Exception as e:
        # Print and log an error message if an exception occurs
        print_and_log(f"An error occurred: {str(e)}")
        driver.quit()
        exit()

    finally:
        # Always quit the WebDriver in the finally block to ensure it's closed properly
        driver.quit()

# Call the function to scrape data
data_list = selenium_speedface()

try:
    # MySQL connection
    db = mysql.connector.connect(
        host=mysql_ip,
        user=mysql_user,
        password=mysql_pass,
        database=mysql_db
    )
    db.get_warnings = False
    cursor = db.cursor()

    # print_and_log("Connected successfully to MySQL on %s" % mysql_ip)

    # Loop through the data list and insert data into the database
    for data in data_list:
        insert_value = f"INSERT IGNORE INTO `turnstile_records` (date_time, card_number, in_out_state) VALUES ('{data[0]}', '{data[1]}', {data[2]}) ON DUPLICATE KEY UPDATE id=id"
        cursor.execute(insert_value)
        db.commit()

except mysql.connector.Error as e:
    # Print and log an error message if a MySQL error occurs
    print_and_log("Error connecting to MySQL: {}".format(e))
    exit()

except Exception as e:
    # Print and log an error message if any other exception occurs
    print_and_log("An error occurred: {}".format(e))
    exit()

finally:
    # Close the database connection in the finally block
    if 'db' in locals() or 'db' in globals():
        db.close()
