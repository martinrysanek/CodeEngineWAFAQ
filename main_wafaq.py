from flask import Flask, request, jsonify
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import xml.etree.ElementTree as ET
import urllib.request
import os
import logging

app = Flask(__name__)

class StringHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_output = ""

    def emit(self, record):
        log_message = self.format(record)
        self.log_output += log_message + "\n"
        
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Get the current timestamp in a specific format
        timestamp = self.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S')
        # custom_format = f"[{timestamp}] [{record.levelname}] {record.name}: {record.getMessage()}"
        custom_format = f"[{timestamp}] [{record.levelname}]: {record.getMessage()} <BR>"
        return custom_format

# Function to traverse the entire XML tree and display attributes of a given tag name
def find_and_display_attributes(element, tag_name):
    if element.tag.endswith(tag_name):
        text = element.text
        if text:
            # print(f"{tag_name} text: {text}")                
            return text
        else:
            return "Unknown"
    for child in element:
        name = find_and_display_attributes(child, tag_name)  
        if name != "Unknown":
            return name
    return "Unknown"


# set up root route
@app.route("/log", methods=['GET'])
def log():
    global string_handler
    # Retrieve the log messages as a single string
    html_in = "<HTML><BODY>"
    html_out = "</BODY></HTML>"
    return (html_in + string_handler.log_output + html_out)

# set up root route
@app.route("/", methods=['GET'])
def aris():
  global logger
  
  logger.debug("GET /")
  # url = 'https://wwwinfo.mfcr.cz/cgi-bin/ares/darv_bas.cgi?ico=14890992'
  url = 'https://wwwinfo.mfcr.cz/cgi-bin/ares/darv_bas.cgi?ico='
  
  ico_string = request.args.get('ico')  
  if not (type(ico_string) is str and ico_string.isdigit()):
      return_name = "Not valid ICO format"
  else:
      logger.info("ICO: " + ico_string)
      response = urllib.request.urlopen(url+ico_string.strip())
      data = response.read()
      # Parse the XML string
      root = ET.fromstring(data)
      # Example: Display all attributes for the 'person' tag throughout the XML tree
      return_name = find_and_display_attributes(root, 'OF')
      
  logger.info("NAME: " + return_name )
  response_data = {'name': return_name }
  return jsonify(response_data)

# Configure logging with a custom log message format
logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Format for the timestamp
)

# Create a logger
logger = logging.getLogger(__name__)

# Create a custom formatter
custom_formatter = CustomFormatter()

# Create a custom logging handler to capture log messages in a string
string_handler = StringHandler()
string_handler.setFormatter(custom_formatter)
logger.addHandler(string_handler)

# Log some messages
logger.info("Custom Extension to get response from Watson Assistant")

# Get the PORT from environment
port = os.getenv('PORT', '8080')
# Get authenticate key
api_key = os.getenv('API_KEY', 'None')
logger.debug("API_KEY = " + api_key)
# Get authenticate key
wa_url = os.getenv('WA_URL', 'None')
logger.debug("WA_URL = " + wa_url)
# Get assistant_id
assistant_id = os.getenv('ASSISTANT_ID', 'None')
logger.debug("ASSISTANT_ID = " + assistant_id)

if __name__ == "__main__":
	app.run(host='0.0.0.0',port=int(port))


