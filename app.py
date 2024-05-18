from flask import Flask

app = Flask(__name__)
app.config["SECRET_KEY"] = "Sbjbdkcdkv762BSvfedJDV3"
from routes import *

def runApp():
    app.run(host="127.0.0.1", port=5500, debug=True)

if __name__ == "__main__":
   runApp()

