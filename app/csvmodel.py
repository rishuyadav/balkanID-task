import csv

# Function to create CSV file
def create_csv_file(query_fetched_data):

    try:
        with open('repos.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Owner ID', 'Owner Name', 'Owner Email',
                            'Repo ID', 'Repo Name', 'Status', 'Stars Count'])
            for data in query_fetched_data:
                writer.writerow(list(data))
        print("Data fetched and stored successfully.")
    except Exception as e:
        print(f"An error occurred while writing data to CSV: {e}")


