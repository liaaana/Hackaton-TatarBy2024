import json
from flask import Flask, request, jsonify
import os
from flask import Response, render_template, request, redirect, url_for, flash
from flask import render_template, request
from app import app
import json
import secrets
from utils import * 
import pysrt
from datetime import datetime as dt
import requests
import xml.etree.ElementTree as ET
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


@app.route('/transcription_audio', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'Нет файла для обработки'}), 400
    random_name = secrets.token_hex(8)
    audio_file = request.files['audio']
    audio_file_path = f'uploads/{random_name}.mp3'
    audio_file.save(audio_file_path)
    print(request.form['audio_language'])
    text = utils_transcribe(request.form['audio_language'], audio_file_path)
    os.remove(audio_file_path)
    return jsonify({'success': True, 'text': text}), 200

def translate_text(text, pair_id):
    sentences = sent_tokenize(text)
    request_data = {'text_array': sentences}
    print(sentences)
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"https://translate.tatar/translate_array?lang={pair_id}", json=request_data, headers=headers)
    if response.status_code != 200:
        return text
    xml_response = response.text
    root = ET.fromstring(xml_response)
    translations = root.findall('translation')
    translated_sentences = [translation.text for translation in translations]
    translated_text = ' '.join(translated_sentences)
    return translated_text


def summarize_text(source, target, text):
    summarized_text = utils_summarize(text, target)
    return summarized_text

@app.route('/summarize', methods=['POST'])
def summarize():
    source_language = request.form['source_language']
    target_language = request.form['target_language']
    text = request.form['input_text']
    print('debug', text)
    if source_language == 'tt' and target_language != 'tt':
        translated_text = translate_text(text, 1) 
        summarized_text = summarize_text(source='ru', target=target_language, text=translated_text)
    elif source_language != 'tt' and target_language == 'tt':
        summarized_text = summarize_text(source=source_language, target='ru', text=text)
        summarized_text = translate_text(summarized_text, 0) 
    elif source_language == 'tt' and target_language == 'tt':
        translated_text = translate_text(text, 1)  
        summarized_text = summarize_text(source='ru', target='ru', text=translated_text)
        summarized_text = translate_text(summarized_text, 0) 
    else:
        summarized_text = summarize_text(source=source_language, target=target_language, text=text)
    return jsonify({'text': summarized_text})

@app.route('/subtitles_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'Нет файла для обработки'}), 400
    random_name = secrets.token_hex(8)
    video_file = request.files['video']
    video_file_path = f'uploads/{random_name}.mp4'
    video_file.save(video_file_path)

    subtitles_path = f'subtitles/tatar.srt'
    video_language = request.form["video_language"]
    subtitles_language = request.form["subtitles_language"]

    # TODO: if subtitles_language == 'tt': change it to 'ru' and then somehow translate the file
    subtitles_path = utils_subtitles(video_language, subtitles_language, video_file_path, subtitles_path, timestamps='word')

    subs = pysrt.open(subtitles_path)
    subtitles = []
    for sub in subs:
        subtitle_data = {
            'id': sub.index,
            'start_time': sub.start.to_time().strftime("%H:%M:%S,%f")[:-3], 
            'end_time': sub.end.to_time().strftime("%H:%M:%S,%f")[:-3], 
            'text': sub.text
        }
        subtitles.append(subtitle_data)

    return jsonify({'success': True, 'subtitles': subtitles, 'video_path': video_file_path, 'subtitles_path': subtitles_path}), 200

@app.route('/generate_subtitles', methods=['POST'])
def generate_subtitles():
    video_file = request.files['video']
    video_path = request.form['video_path']
    subtitles_path = request.form['subtitles_path']
    subtitles = json.loads(request.form['subtitles'])

    def convert_time(time_str):
        time_obj = dt.strptime(time_str, '%H:%M:%S,%f')
        return time_obj.strftime('%H:%M:%S,%f')[:-3]

    srt_text = ''
    for subtitle in subtitles:
        start_time = convert_time(subtitle['start_time'])
        end_time = convert_time(subtitle['end_time'])
        text = subtitle['text']
        srt_text += f"{subtitle['id']}\n{start_time} --> {end_time}\n{text}\n\n"

    with open(subtitles_path, 'w', encoding='utf-8') as f:
        f.write(srt_text)

    
    return jsonify({"success": False, "error": str(212)})


@app.route("/summary")
def summary():
    return render_template("summary.html")

@app.route("/transcription")
def transcription():
    return render_template("transcription.html")

@app.route("/subtitles")
def subtitles():
    return render_template("subtitles.html")
