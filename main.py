from api.index import app

if __name__ == '__main__':
    # For Docker and local development, bind to 0.0.0.0
    app.run(host='0.0.0.0', port=5000, debug=True)
