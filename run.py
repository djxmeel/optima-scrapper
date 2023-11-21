from web import app
from web import config

if __name__ == "__main__":
    app.run(debug=config.DEBUG)
