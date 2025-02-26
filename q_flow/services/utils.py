# Description: Utility functions
from random import randint
from uuid import uuid4
from flask import Request, json

from q_flow.exceptions import Keys_Not_Found, MissingData

def check_required(data: dict, fields: list) -> bool:
    '''Check if the required fields are present in the data'''
    missing_fields = []
    for field in fields:
        if field not in data:
            missing_fields.append(field)
        elif not data.get(field):
        # or data.get(field) == '' or \
        #     data.get(field) == [] or data.get(field) == {} or \
        #     data.get(field) == 0 or data.get(field) == '0' or \
        #     data.get(field) == '0.0'
            missing_fields.append(field)
    if missing_fields:
        raise MissingData(f"Missing fields: {missing_fields}")
    return True

def rnd_6():
    return randint(100000, 999999)

def rnd_color():
    """
    Returns a random dark color in hexadecimal format.
    A dark color has low values for R, G, and B components.
    """
    max_value = 120
    min_value = 20
    
    r = randint(min_value, max_value)
    g = randint(min_value, max_value)
    b = randint(min_value, max_value)
    
    # Convert the RGB values to hexadecimal format.
    dark_color = f'#{r:02x}{g:02x}{b:02x}'
    
    return dark_color

def gen_id():
    return str(uuid4())

def read_data(req: Request):
    if req.method == 'GET':
        return req.args
    if req.is_json:
        return req.get_json()
    if req.form:
        return req.form.to_dict()
    if req.data:
        return req.data
    return None


def get_env(file_path: str) -> dict:
    '''
    Load the secret keys from the env.json file
    '''
    print(f"trying to load env.json file from {file_path}")
    try:
        with open(file_path, 'r') as f:
            raw_data = f.read()
            try:
                data: dict = json.loads(raw_data)
            except ValueError:
                raise ValueError("Invalid JSON format in env.json file")
    except FileNotFoundError:
        raise Keys_Not_Found("env.json file not found")
    return data
