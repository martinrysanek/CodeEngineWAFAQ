from flask import Flask, request, jsonify
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import datetime
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
    
def wa_login():
    global authenticator
    global assistant
    global assistant_id
    global session_id
    global api_key
    global wa_url

    logger.debug("wa_login() new wa session start")
    authenticator = IAMAuthenticator(api_key)
    assistant = AssistantV2(
        version='2021-11-27',
        authenticator=authenticator)
    assistant.set_service_url(wa_url)
    session = assistant.create_session(assistant_id).get_result()
    session_id=session['session_id']
    logger.debug("wa_login() new wa session " + session_id)

def get_intent_text(intent_text):
      global logger  
      global assistant_id
      global session_id  
      global assistant
      
      result = assistant.message(
          assistant_id=assistant_id,
          session_id=session_id,
          input={
              'message_type': 'text',
              'text': '*',
              "intents": [
                  {
                      "intent": intent_text,
                      "confidence": 1
                  }
              ]
          }
      )
      if result.status_code == 200:
          response = result.get_result()
          if 'generic' in response['output']:
              #It is not random way to return text, for random need to be adjusted !!!
              return (response['output']['generic'][0]['text'])
          else:
              logger.error("get_intent_text: Return json does not include generic and text")
              return ("Error: get_intent_text: Return json does not include generic and text")
      else:
          logger.error("get_intent_text: Wa did not get text for intent")
          return ("Error: get_intent_text: Wa did not get text for intent")

# set up root route
@app.route("/log", methods=['GET'])
def log():
    global string_handler
    # Retrieve the log messages as a single string
    html_in = "<HTML><BODY>"
    html_out = "</BODY></HTML>"
    return (html_in + string_handler.log_output + html_out)

# set up root route
@app.route("/query", methods=['POST'])
def query_api():
  try:
      global logger  
      global assistant_id
      global session_id  
      global assistant
      global max_count 
      global authenticator
      
      logger.debug("/query POST")
      request_data = request.get_json()
      if 'query' not in request_data:
          logger.error("Query: missing query parameter")
          return jsonify({"error": "Missing 'query' parameter"}), 400
      query = request_data['query']
      if not (type(query) is str):
          logger.error("Query: Wrong parameter type: " + type(query))
          return jsonify({"error": "Wrong 'query' parameter type"}), 400
      else:
          logger.info("Query: parameter: " + query)
          
      #Create WA session if it is not opened yet

      while (True):
          try:
                if not authenticator:
                    wa_login()
                #Get Intents for Query
                result = assistant.message(
                  assistant_id=assistant_id,
                  session_id=session_id,
                  input={
                      'message_type': 'text',
                      'text': query,
                      "options": {
                      "alternate_intents": True        
                      }
                  }
                )
                response = result.get_result()
                if result.status_code == 200 and 'intents' in response["output"]:
                    response_data = []
                    intents = response["output"]['intents']
                    count = 0
                    for intent in intents:
                        count+=1
                        if count<=max_intents:
                            intent_text = intent['intent']
                            if intent_text.startswith("fallback"):
                                continue
                            logger.info("Query: intent " + intent_text)
                            out_text = get_intent_text(intent_text)
                            new_item = {
                                'intent': intent_text,
                                'text':  out_text,
                                'confidence' : intent['confidence']
                            }
                            response_data.append(new_item)          
                    logger.debug("/query return")
                    return jsonify(response_data)
                else:
                    logger.error("Query: Wa reponded with error")
                    return jsonify({"error": "Wa reponded with error"}), 400    
          except Exception as e:
              if hasattr(e, "code"):
                  if e.code == 404:
                     authenticator = None
                     continue
              authenticator = None
              return jsonify({"error": str(e)}), 400
  except Exception as e:
      return jsonify({"error": str(e)}), 400

# set up root route
@app.route("/selection", methods=['POST'])
def selection_api():
    global logger  
    global selection_log
    try:
      logger.debug("/selection POST")        
      request_data = request.get_json()
      if 'query' not in request_data:
          logger.error("Selection: missing query parameter")
          return jsonify({"error": "Missing 'query' parameter"}), 400    
      else:
          query = request_data['query']
          logger.info("Selection query: " + query)
      if 'selected_name' not in request_data:
          logger.error("Selection: missing selected_name parameter")
          return jsonify({"error": "Missing 'selected_name' parameter"}), 400  
      else:
          selected_name = request_data['selected_name']
          logger.info("Selection selected: " + selected_name)          
      if 'selected_confidence' not in request_data:
          logger.error("Selection: missing selected_confidence parameter")
          return jsonify({"error": "Missing 'selected_confidence' parameter"}), 400 
      else:
          selected_confidence = request_data['selected_confidence']
          logger.info("Selection confidence: " + str(selected_confidence))          
      if 'top_name' in request_data:
          top_name = request_data['top_name']
      else:
          top_name = ""
      if 'top_confidence' in request_data:
          top_confidence = request_data['top_confidence']
      else:
          top_confidence = -1   
      
      current_datetime = datetime.datetime.now()
      formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
      
      selection_log += "{}, {}, {}, {:.3f}, {}, {:.3f}<BR>".format(formatted_datetime, query, selected_name, selected_confidence, top_name, top_confidence)
      logger.debug("/selection return") 
      return '',200
    except Exception as e:
      return jsonify({"error": str(e)}), 400

# set up root route
@app.route("/selection_log", methods=['GET'])
def selection_web():
    global selection_log
    # Retrieve the log messages as a single string
    html_in = "<HTML><BODY>"
    html_out = "</BODY></HTML>"
    return (html_in + selection_log + html_out)

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

# Max Returned Intents
max_intents_str = os.getenv('MAX_INTENTS', '5')
max_intents = int(max_intents_str)
logger.debug("MAX_INTENTS = " + str(max_intents))

# Initiate Selection Log
selection_log =""

# Initiate WA connection
authenticator = None
assistant = None

if __name__ == "__main__":
	app.run(host='0.0.0.0',port=int(port))


