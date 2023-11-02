from flask import render_template, request
from . import app

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrapers')
def scrapers():
    return render_template('scrapers.html')

@app.route('/merge')
def merge():
    return render_template('merge.html')

@app.route('/imports')
def odoo_imports():
    return render_template('odoo_imports.html')


@app.route('/process', methods=['POST'])
def process():
    data = request.form.get('data')

    # Here's where you can integrate with your Python program
    # Let's say you have a function called process_data that processes the input
    result = data

    return f"Processed result: {result}"