import os
from schema import Owner, Repo
from dotenv.main import load_dotenv
from flask import Flask, request, redirect, url_for, session, send_file, render_template
from flask_bootstrap import Bootstrap
import logging
import requests
import json
import psycopg2
from urllib.parse import urlencode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dataprocessing import normalize_data
from github_api import fetch_repos
from csvmodel import create_csv_file

load_dotenv()
# Create database connection
engine = create_engine(os.environ.get("DATABASE_URL"))
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Create Flask app
app = Flask(__name__)
bootstrap = Bootstrap(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# Github OAuth settings
CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
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
        "scope": "repo user:email"
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
    logging.info("Data fetching initiated.")

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

    try:
        session_ = Session()
        query = session_.query(Owner.id, Owner.name, Owner.email, Repo.id,
                               Repo.name, Repo.status, Repo.stars_count).join(Repo).all()
        create_csv_file(query)
        return render_template('result.html', download_csv=url_for('download_csv'))
    except Exception as e:
        logging.error("An error occurred while writing data to CSV: " + str(e))
        return "An error occurred while writing data to CSV: " + str(e)


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
            owner_obj = Owner(
                id=owner['id'], name=owner['name'], email=owner['email'])
            session.merge(owner_obj)

            # Upsert repos table
            repo_obj = Repo(id=repo['id'], name=repo['name'], status=repo['status'],
                            stars_count=repo['stars_count'], owner_id=owner['id'])
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

# Download CSV file
@app.route('/download_csv', methods=['GET', 'POST'])
def download_csv():
    return send_file('repos.csv', mimetype='text/csv', as_attachment=True, attachment_filename='repos.csv')


if __name__ == '__main__':
    app.run(debug=True)
