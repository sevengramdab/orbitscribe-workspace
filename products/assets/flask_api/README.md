# Flask API Boilerplate

This is a production-ready Flask API boilerplate that includes JWT authentication, rate limiting, and OpenAPI documentation.

## Features

* JWT Authentication using PyJWT library
* Rate Limiting using Flask-Limiter library
* OpenAPI Documentation using Flask-API library

## Requirements

* Python 3.8 or higher
* Flask 2.0 or higher
* PyJWT 2.3 or higher
* Flask-Limiter 2.1 or higher
* Flask-API 0.7 or higher

## Usage

1. Clone this repository and install dependencies using pip: `pip install -r requirements.txt`
2. Create a new file named `config.py` to store your application configuration
3. Update the `config.py` file with your database credentials, JWT secret key, etc.
4. Run the application using `python app.py`
5. Access OpenAPI documentation at `http://localhost:5000/docs`
6. Test API endpoints by sending requests to `http://localhost:5000/endpoint_name`