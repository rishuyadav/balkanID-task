# Github Stats


This repository contains the solution for the Engineering Internship Recruitment task.
The task involves creating a program that fetches data from the Github API using OAuth authentication and stores it in a Postgres database. The data should be normalized and deduplicated before being stored in the database.

## Features
* Github OAuth login
* Fetch repositories from Github API
* Normalizes and deduplicates data
* Store data in a Postgres database
* Generate a CSV file containing the data

## Tech Stack


**Language:** Python

**Web Framework:** Flask

**ORM:** SQLAlchemy

**Database:** Postgres

**API Integration:** Github API

**Data Processing:** Pandas

**Data Serialization:** CSV

**Deployment:** Local machine / Docker


## Demo

https://user-images.githubusercontent.com/72988817/230893426-2fc88f02-746f-4c44-a8ab-33360e21116b.mp4


## Prerequisites


Before installing the project, ensure that you have the following prerequisites:

* Python 3.7 or higher
* pip package manager
* Docker Desktop

## Installation



### 1. Clone the repository
Clone the repository using the following command:
```bash
git clone https://github.com/BalkanID-University/balkanid-summer-internship-vit-vellore-2023-rishuyadav
```

### 2. Set up a virtual environment
Navigate to the project directory and create a new virtual environment:
```bash
cd balkanid-summer-internship-vit-vellore-2023-rishuyadav
python3 -m venv venv

```
Activate the virtual environment:
```bash
source venv/bin/activate
```
### 3. Install dependencies
Install the project dependencies using pip:
```bash
pip install -r requirements.txt
```

### 4. Create a .env file in the root directory of the project and add the following variables:
```bash
FLASK_SECRET_KEY=<secret_key>
DATABASE_URL=<postgres_database_url>
GITHUB_CLIENT_ID=<github_client_id>
GITHUB_CLIENT_SECRET=<github_client_secret>
```

### 5. Set up the database
Create a new Postgres database and set the DATABASE_URL environment variable to the database URL. You can use ElephantSQL to create a free Postgres database.

```bash
export DATABASE_URL=postgres://username:password@host:port/database_name
```

### 6. Set up Github OAuth
To use the Github API, you need to set up Github OAuth. Follow these steps to set up Github OAuth:

* Create a new OAuth application on Github by going to https://github.com/settings/applications/new.

* Set the "Homepage URL" to http://localhost:5000/oauth/login
Set the "Authorization callback URL" to http://localhost:5000/oauth/callback.

* Note down the "Client ID" and "Client Secret" values for the application.
* Set the GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables to the "Client ID" and "Client Secret" values, respectively:

```bash
export GITHUB_CLIENT_ID=your_client_id
export GITHUB_CLIENT_SECRET=your_client_secret

```

### 7. Run the app
Run the app using the following command:
```bash
cd app
python3 app.py
```
The app should now be accessible at http://localhost:5000.

## You can also run the app using Docker.


### Follow these steps to run the app with Docker:

1. Build the Docker image:
```bash
docker build -t your-image-name .
```
2. Run the Docker container:
```bash
docker run -p 5000:5000 -e your-image-name
```
The app should now be accessible at http://localhost:5000


## Author

- [Rishu Yadav](https://www.github.com/rishuyadav)