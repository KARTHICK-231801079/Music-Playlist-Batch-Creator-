from pymongo import MongoClient
import pymongo

# MongoDB Configuration
MONGODB_URL = "Enter your MongoDB URL"  # Replace with your MongoDB URL
DATABASE_NAME = 'Music'  # Replace with your database name
COLLECTION_NAME = 'User_Details'  # Replace with your collection name

client = pymongo.MongoClient(MONGODB_URL)
db = client[DATABASE_NAME]
users_collection = db[COLLECTION_NAME]

def register_user():
    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = input("Enter password: ")
    age = input("Enter age: ")
    dob = input("Enter date of birth (YYYY-MM-DD): ")
    
    # Check if username or email already exists
    if users_collection.find_one({'username': username}):
        print("Username already exists")
        return
    if users_collection.find_one({'email': email}):
        print("Email already exists")
        return
    
    user_data = {
        'first_name': first_name,
        'last_name': last_name,
        'username': username,
        'email': email,
        'password': password,
        'age': age,
        'dob': dob
    }
    
    try:
        user_id = users_collection.insert_one(user_data).inserted_id
        print(f"User registered successfully with ID: {user_id}")
    except Exception as e:
        print(f"Error inserting user: {e}")

def login_user():
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    user = users_collection.find_one({'username': username})
    
    if user and user['password'] == password:
        print("Login successful")
    else:
        print("Invalid username or password")

if __name__ == "__main__":
    while True:
        print("\n1. Register User")
        print("2. Login User")
        print("3. Exit")
        choice = input("Enter your choice: ")
        
        if choice == '1':
            register_user()
        elif choice == '2':
            login_user()
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")