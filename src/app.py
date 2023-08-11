from flask import Flask, jsonify, render_template, request
import subprocess
import os


app = Flask(__name__, template_folder='.', static_folder='static')

@app.route('/', methods=['GET', 'POST'])
def index():
    api_response = ''

    print(request.args.get('flight_number', None))
    flight_number = request.args.get('flight_number', None)

    if flight_number == 0 or flight_number == None:
        return render_template('/index.html')

    response = subprocess.run(['python3', 'wimp.py', flight_number], capture_output=True)

    api_response = response.stdout.decode()
    print(f'api_response: {api_response}')

    if api_response.startswith('\\'):
        return render_template('/index.html', api_response=api_response)

    return render_template('/index.html')

