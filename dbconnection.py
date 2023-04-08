from flask import Flask, request, redirect, url_for, session, send_file, render_template
from flask_bootstrap import Bootstrap
import logging
import requests
import json
import psycopg2
import csv
from tenacity import retry, stop_after_attempt, wait_fixed
from urllib.parse import urlencode
app = Flask(__name__)
bootstrap = Bootstrap(app)
app.secret_key = "my_secret_key"

# Github OAuth settings
CLIENT_ID = 'cb02994933b0febfa39c'
CLIENT_SECRET = '4e7410487747eed49943d1ba5881009f9a7c0cea'
AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)


# Home page
@app.route('/')
def home():
    logging.info("Home page accessed.")
    return render_template('home.html', oauth_url=url_for('oauth_login'))

# OAuth login


@app.route('/oauth/login')
def oauth_login():
    logging.info("OAuth login initiated.\n")
    # Redirect user to Github OAuth login page
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": url_for("oauth_callback", _external=True),
        "scope": "repo"
    }
    return redirect(AUTHORIZE_URL + "?" + urlencode(params))

# OAuth callback


@app.route('/oauth/callback')
def oauth_callback():
    logging.info("OAuth callback initiated.")
    # Exchange authorization code for access token
    code = request.args.get("code")
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code
    }
    response = requests.post(ACCESS_TOKEN_URL, params=params, headers={
                             "Accept": "application/json"})
    access_token = json.loads(response.text)["access_token"]

    # Store access token in session
    session["access_token"] = access_token

    # Redirect user to fetch data
    return redirect(url_for("fetch_data"))


@app.route('/fetch_data')
def fetch_data():
    logging.info("Data fetching initiated.\n")

    # Get access token from session
    access_token = session["access_token"]

    # Fetch repository data from Github API
    try:
        repos = fetch_repos(access_token)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return "Error fetching data. Please try again later."

    # Normalize data and deduplicate
    normalized_data = normalize_data(repos)

    # Store data in Postgres database
    try:
        store_data(normalized_data)
    except(Exception, psycopg2.Error) as error:
        logging.error("Error while connecting to database.", error)
        return "Error while storing data in database."

    # Create CSV file
    try:
        create_csv_file(normalized_data)
        return render_template('result.html', oauth_login=url_for('oauth_login'), download_csv=url_for('download_csv'))
    except Exception as e:
        logging.error("An error occurred while writing data to CSV: " + str(e))
        return "An error occurred while writing data to CSV: " + str(e)


# Function to fetch repository data from Github API
@retry(stop=stop_after_attempt(10), wait=wait_fixed(1))
def fetch_repos(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = "https://api.github.com/user/repos"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


# Function to normalize data and deduplicate
def normalize_data(repos):
    normalized_data = []
    seen = set()
    for repo in repos:
        owner = {
            'id': repo['owner']['id'],
            'name': repo['owner']['login'],
            'email': repo['owner'].get('email', '')
        }
        normalized_repo = {
            'id': repo['id'],
            'name': repo['name'],
            'status': 'Public' if repo['private'] == False else 'Private',
            'stars_count': repo['stargazers_count'],
            'owner_id': repo['owner']['id']
        }
        key = (normalized_repo['id'], normalized_repo['owner_id'])
        if key not in seen:
            seen.add(key)
            normalized_data.append({'owner': owner, 'repo': normalized_repo})
    return normalized_data


# Function to store data in Postgres database
def store_data(normalized_data):
    try:
        conn = psycopg2.connect(
            database="demo", user="postgres", password="postgres", host="127.0.0.1", port="5432")
        logging.info("Connected to database successfully.")

        # Create tables if they don't exist
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT
        );
    """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER,
            name TEXT,
            status TEXT,
            stars_count INTEGER,
            owner_id INTEGER REFERENCES owners(id),
            PRIMARY KEY (id, owner_id)
        );
    """)

        logging.info("Tables created successfully.")

        # Insert data into the tables
        for data in normalized_data:
            owner = data['owner']
            repo = data['repo']
            cursor.execute("""
        INSERT INTO owners (id, name, email) VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET name = excluded.name, email = excluded.email;
    """, (owner['id'], owner['name'], owner['email']))
            cursor.execute("""
        INSERT INTO repos (id, name, status, stars_count, owner_id) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id, owner_id) DO UPDATE SET name = excluded.name, status = excluded.status, stars_count = excluded.stars_count;
    """, (repo['id'], repo['name'], repo['status'], repo['stars_count'], repo['owner_id']))
            conn.commit()
    except(Exception, psycopg2.Error) as error:
        logging.error("Error while connecting to database.", error)

    finally:
        if(conn):
            cursor.close()
            conn.close()
            logging.info("Connection closed.")


# Function to create CSV file
def create_csv_file(normalized_data):
    try:
        with open('repos.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Owner ID', 'Owner Name', 'Owner Email',
                            'Repo ID', 'Repo Name', 'Status', 'Stars Count'])
            for data in normalized_data:
                owner = data['owner']
                repo = data['repo']
                writer.writerow([owner['id'], owner['name'], owner['email'],
                                repo['id'], repo['name'], repo['status'], repo['stars_count']])
        return "Data fetched and stored successfully."
    except Exception as e:
        logging.error("An error occurred while writing data to CSV: " + str(e))
        return "An error occurred while writing data to CSV: " + str(e)


# Download CSV file
@app.route('/download_csv', methods=['GET', 'POST'])
def download_csv():
    return send_file('repos.csv', mimetype='text/csv', as_attachment=True, attachment_filename='repos.csv')


if __name__ == '__main__':
    app.run(debug=True)
