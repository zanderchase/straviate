from flask import Flask, request, jsonify, redirect, render_template, session
import json
import requests
from langchain import OpenAI, ConversationChain, LLMChain, PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
import sys
import os

app = Flask(__name__)
app.secret_key = "my_secret_key"

CLIENT_ID = '65731'
CLIENT_SECRET = '1f90721f50e2eb89f733469b07d98bed82c6fd65'
API_URL = 'https://www.strava.com/api/v3'
REDIRECT_URL = 'http://127.0.0.1:5000/welcome_page'


AUTH_URL = 'https://www.strava.com/oauth/token'
GRANT_TYPE = 'authorization_code'

def extract_info(json):
    i = 1
    return_array = []
    for row in json:
        distance = str(row['distance'] / 1609)
        elapsed_time = str(row['moving_time'] / 60)
        sport_type = row['sport_type']
        start_date = row['start_date_local'][:10]
        total_elevation_gain = str(row['total_elevation_gain'] * 3.281)
        #average_heartrate = row['average_heartrate']
        return_array.append({"entry_number": i, "distance (miles)": distance, "elapsed_time (minutes)": elapsed_time, "sport": sport_type, "start date": start_date, "elevation_gain (feet)": total_elevation_gain})
        i+=1
    return return_array

def setup_langchain():
    template = """Strava assistant is a large language model trained by OpenAI and given information about an atheletes Strava account.

    Strava assistant is designed to help atheletes analyze their past runs and train towards their next big race. 

    As a language model, Strava Assistant is able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand.

    Answer the human like a coach would.

    {history}
    Human: {human_input}
    Assistant:"""

    prompt = PromptTemplate(
        input_variables=["history", "human_input"], 
        template=template
    )


    chatgpt_chain = LLMChain(
        llm=OpenAI(temperature=0), 
        prompt=prompt, 
        verbose=True, 
        memory=ConversationBufferWindowMemory(k=2),
    )

    return chatgpt_chain

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/authorize_button', methods=['POST'])
def authorize_button():
    return redirect(f'https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URL}&approval_prompt=force&scope=activity:read_all')


@app.route('/welcome_page')
def welcome_page():
    CODE = request.args.get('code')
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': CODE,
        'grant_type': GRANT_TYPE
    }
    response = requests.post(AUTH_URL, data=data)
    if response.status_code != 200:
        return jsonify(error=response.text), response.status_code
    response_dict = response.json()
    session["access_token"] = response_dict['access_token']
    return render_template('welcome.html')

@app.route('/athlete_activities', methods=['GET'])
def athlete_activities():
    print("athelete_activities")
    url = "https://www.strava.com/api/v3/athlete/activities"
    access_token = session.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    param = {'per_page':10, 'page':1}
    response = requests.get(url, headers=headers, params=param)
    if response.status_code != 200:
        return jsonify(error=response.text), response.status_code
    session["strava_data"] = extract_info(response.json())
    my_string = 'Strava data up to date!'
    return render_template('chatbot.html', my_string=my_string)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    return render_template('chatbot.html')

@app.route("/set-api-key", methods=['GET', 'POST'])
def set_api_key():
    print(request.form.get("api_key"))
    os.environ["OPENAI_API_KEY"] = request.form.get("api_key")
    api_string = 'OPENAI_API_KEY set'
    return render_template('chatbot.html', api_string=api_string)


@app.route('/dataviz', methods=['GET', 'POST'])
def dataviz():
    data = session.get("strava_data")
    print(type(data))
    return json.dumps(data)

@app.route('/langchain', methods=['GET', 'POST'])
def langchain():
    chain = setup_langchain()
    print("query")
    print(request.json.get('query'))
    input = request.json.get('query') + ". " + str(session.get("strava_data"))
    output = chain.predict(human_input=input)
    return output



if __name__ == '__main__':
    app.run(debug=True)