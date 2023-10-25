# Import necessary libraries

from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, jsonify

from flask_sqlalchemy import SQLAlchemy  # Import SQLAlchemy

import os

app = Flask(__name__)


app.config['SECRET_KEY'] = 'DIWI'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Define the path to the database

db = SQLAlchemy(app)  # Create an instance of the SQLAlchemy class
from app.models import Resume  # import the Resume model


import PyPDF2
import requests
from werkzeug.utils import secure_filename
import io
from shutil import copyfileobj

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


app.secret_key = 'DIWI'

# Your API key from OpenAI
api_key = "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"



@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profiles')
def profiles():
    #return render_template('profiles.html')
    pdfs = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
    return render_template('profiles.html', pdfs=pdfs)

#@app.route('/skill_search')
#def skill_search():
#    return render_template('skill_search.html')
@app.route('/pending_resume')
def pending_resume():
    return render_template('pending.html')

@app.route('/resume_upload', methods=['GET', 'POST'])
def resume_upload():
    if request.method == 'POST':
        # Handle file upload logic here
        uploaded_file = request.files['resume']

        if uploaded_file.filename != '':
            # Check if the uploaded file is a PDF
            if uploaded_file.filename.endswith('.pdf'):
                # Redirect to the same page with a success message
                return redirect(url_for('resume_upload', message='success'))
            else:
                # Redirect to the same page with an error message
                return redirect(url_for('resume_upload', message='error'))

    return render_template('resume_upload.html')


@app.route('/process_pdf', methods=['POST'])
#@app.route('/process_pdf', methods=['POST'])
def process_pdf():
    # Check if file is attached
    if 'resume' not in request.files:
        return jsonify(status='error', message='No file attached')
    
    pdf_file = request.files['resume']

    # Ensure the file is a PDF
    if not pdf_file.filename.endswith('.pdf'):
        return jsonify(status='error', message='File format not supported')
    
    # Create a copy of the file stream
    pdf_file_stream_copy = io.BytesIO()
    pdf_file.save(pdf_file_stream_copy)
    pdf_file_stream_copy.seek(0)  # go to the start of the file copy


    # Create a PDF reader object using the attached file
    pdf_reader = PyPDF2.PdfReader(pdf_file)

    # Initialize an empty string to store the extracted text
    extracted_text = ''

    # Extract text from each page in the PDF
    for page_number in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_number]
        page_text = page.extract_text()
        extracted_text += page_text

    # Append the statement to check if it's a resume
    extracted_text += "\nCheck if this is a resume or not. Just respond with 'Yes' or 'NO'"

    # API endpoint URL and key
    api_url = "https://api.openai.com/v1/chat/completions"
    api_key = "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"  # Store this securely, not in plain code

    # Split the extracted text into chunks for the API request
    text_chunks = [extracted_text[i:i+4000] for i in range(0, len(extracted_text), 4000)]
    reply = None

    for chunk in text_chunks:
        # Set up the API request
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": chunk}],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Make the API call
        response = requests.post(api_url, json=data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            reply = response_data["choices"][0]["message"]["content"]
            break  # Since we got a valid reply, no need to continue processing other chunks

    # Return a JSON response based on the ChatGPT reply
    if reply and reply.lower() == "yes":
        # Get the original filename without the extension
        original_filename = os.path.splitext(secure_filename(pdf_file.filename))[0]
        
        # Save the file temporarily to get the ID after adding to the database
        temp_filepath = os.path.join(UPLOAD_FOLDER, secure_filename(pdf_file.filename))
        with open(temp_filepath, 'wb') as out_file:
            pdf_file_stream_copy.seek(0)  # ensure we're at the start of the file copy
            copyfileobj(pdf_file_stream_copy, out_file)
        
        # Save content to database to get the ID
        extracted_text = extracted_text.replace("\nCheck if this is a resume or not. Just respond with 'Yes' or 'NO'", "")
        resume = Resume(filename=pdf_file.filename, content=extracted_text)
        db.session.add(resume)
        db.session.flush()  # This will generate an ID without committing the transaction
        
        # Rename the file with the ID
        new_filename = f"{original_filename}_RS_{resume.id}.pdf"
        new_filepath = os.path.join(UPLOAD_FOLDER, new_filename)
        os.rename(temp_filepath, new_filepath)
        
        # Update the filename in the database and commit the transaction
        resume.filename = new_filename
        db.session.commit()
        
        return jsonify(status='success')
    elif reply and reply.lower() == "no":
        return jsonify(status='not_a_resume')
    else:
        return jsonify(status='error', message='Error processing the file')

    
#@app.route('/pdfs')
#def list_pdfs():
 #   pdfs = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
  #  return render_template('profiles.html', pdfs=pdfs)

#@app.route('/uploads/<filename>')
#def serve_pdf(filename):
#    return send_from_directory(UPLOAD_FOLDER, filename) 

@app.route('/uploads/<filename>')
def serve_pdf(filename):
    uploads_path = 'C:\\Users\\Diwashmi\\SMARTHIRE\\backend\\uploads'
    return send_from_directory(uploads_path, filename)
#now
@app.route('/skill_search', methods=['GET', 'POST'])
def skill_search():
    if request.method == 'POST':
        skills = request.form.get('skills')  # get skills from form input
        skills_list = [s.strip() for s in skills.split(',')]  # convert comma-separated string into a list
        matched_resumes = search_for_skills(skills_list)  # call function to perform the search
        return render_template('skill_search.html', matched_resumes=matched_resumes)  # render results
     # For GET request, it should render the page without any matched resumes
    return render_template('skill_search.html')
def search_for_skills(skills):
    matches = []
    resumes = Resume.query.all()  # fetch all resumes from the database
    for resume in resumes:
        # Check how many skills are mentioned in each resume
        count = sum(1 for skill in skills if skill.lower() in resume.content.lower())
        if count > 0:
            matches.append({'filename': resume.filename, 'count': count})
            
    # Sort matches based on count
    matches.sort(key=lambda x: x['count'], reverse=True)
    return matches
#w
@app.route('/analyze', methods=['POST'])
def analyze():
    candidate_input = request.form.get('candidate_input')  # Get input for candidate selection

    # Call a function to analyze resumes and select the best candidate
    selected_candidate_filename = analyze_resumes(candidate_input)

    return render_template('skill_search.html', selected_candidate=selected_candidate_filename)

def analyze_resumes(candidate_input):
    # Call your function to filter resumes based on skill search
    matched_resumes = search_for_skills(candidate_input.split())  # Split input into skills and call search function

    if not matched_resumes:
        return "No matching candidates"  # Return a message if no matches are found

    # Sort the matched resumes by the number of matching skills (descending order)
    matched_resumes.sort(key=lambda x: x['count'], reverse=True)

    # Get the filename of the best candidate (the one with the most matching skills)
    best_candidate_filename = matched_resumes[0]['filename']

    # Append the message as instructed
    message = f'Looking for "{candidate_input}", choose the best candidates among the given resumes and provide only the filename. No additional information.'
    message_with_filename = f'{message}\n\nFilename: {best_candidate_filename}'

    # Send the content along with the message to ChatGPT through API
    api_url = "https://api.openai.com/v1/chat/completions"
    api_key = "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"

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message_with_filename},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(api_url, json=data, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        reply = response_data["choices"][0]["message"]["content"]
        return reply  # Return the response from ChatGPT

    return "Error processing the request"
if __name__ == '__main__':
    
    db.create_all()  # This will create the database if it doesn’t exist
    app.run()