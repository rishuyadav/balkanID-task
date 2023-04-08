from flask import Flask, request, redirect, url_for, session, send_file, render_template
from flask_bootstrap import Bootstrap
import logging
import requests
import json
import psycopg2
import csv
from tenacity import retry, stop_after_attempt, wait_fixed
from urllib.parse import urlencode
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Create database connection
engine = create_engine('postgresql://postgres:password@mypostgres:5432/mydatabase')
Session = sessionmaker(bind=engine)

# Create declarative base
Base = declarative_base()

app = Flask(__name__)
bootstrap = Bootstrap(app)

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
        session_ = Session()
        query = session_.query(Owner.id, Owner.name, Owner.email, Repo.id, Repo.name, Repo.status, Repo.stars_count).join(Repo).all()
        create_csv_file(query)
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
    user_repos_url = "https://api.github.com/user/repos"
    response = requests.get(user_repos_url, headers=headers)
    user_repos = response.json()

    org_repos_url = "https://api.github.com/orgs/{org}/repos"
    org_name = "ACM-VIT"
    response = requests.get(org_repos_url.format(org=org_name), headers=headers)
    org_repos = response.json()
    # Return both user and organization repositories
    return user_repos + org_repos


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


# Define owners and repos tables
class Owner(Base):
    __tablename__ = 'owners'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

class Repo(Base):
    __tablename__ = 'repos'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)
    stars_count = Column(Integer)
    owner_id = Column(Integer, ForeignKey('owners.id'))

# Define function to store data
def store_data(normalized_data):
    try:
        # Create session
        session = Session()

        # Create tables if they don't exist
        Base.metadata.create_all(engine)

        # Insert data into the tables
        for data in normalized_data:
            owner = data['owner']
            repo = data['repo']

            # Upsert owners table
            owner_obj = Owner(id=owner['id'], name=owner['name'], email=owner['email'])
            session.merge(owner_obj)

            # Upsert repos table
            repo_obj = Repo(id=repo['id'], name=repo['name'], status=repo['status'], stars_count=repo['stars_count'], owner_id=owner['id'])
            session.merge(repo_obj)

        # Commit the changes to the database
        session.commit()
        logging.info("Data stored successfully.")

    except Exception as error:
        logging.error("Error while storing data.", error)

    finally:
        if session:
            session.close()
            logging.info("Session closed.")



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


# Download CSV file
@app.route('/download_csv', methods=['GET', 'POST'])
def download_csv():
    return send_file('repos.csv', mimetype='text/csv', as_attachment=True, attachment_filename='repos.csv')


if __name__ == '__main__':
    app.run(debug=True)
