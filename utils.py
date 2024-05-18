import os
import gc
from transformers import pipeline
from typing import Iterator, TextIO

from googletrans import Translator
import re

def split_into_parts_of_four(input_list):
    return [input_list[i:i + 4] for i in range(0, len(input_list), 4)]

def combine_srt(input_file, output_file, target_language):
    with open(input_file, 'r', encoding='utf-8') as file:
        srt_content = file.readlines()

    translated_content = []
    for line in srt_content:
        if re.match(r'^\d{1,3}$', line.strip()) or re.match(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', line.strip()) or line.strip() == '':
            translated_content.append(line)
        else:
            translated_content.append(line.strip() + '\n')

    sentences = []

    parts = split_into_parts_of_four(translated_content)

    cur_beg = None
    cur_end = None
    cur_sent = ''

    for part in parts:
        if cur_beg is None:
            cur_beg = part[1].split(' --> ')[0]
        
        if part[2].strip()[-1] in ('!', '?', '.'):
            cur_end = part[1].split(' --> ')[1]
        
        cur_sent += (' ' if len(cur_sent) else '') + part[2].strip()

        if cur_end:
            sentences.append(f'{len(sentences) + 1}\n{cur_beg} --> {cur_end}{cur_sent}\n\n')
            cur_beg = None
            cur_end = None
            cur_sent = ''

    with open(output_file, 'w', encoding='utf-8') as file:
        file.writelines(sentences)

def translate_srt(input_file, output_file, target_language):
    # Initialize the translator
    translator = Translator()

    with open(input_file, 'r', encoding='utf-8') as file:
        srt_content = file.readlines()

    translated_content = []
    for line in srt_content:
        # Check if the line is a subtitle text line
        if re.match(r'^\d{1,3}$', line.strip()) or re.match(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', line.strip()) or line.strip() == '':
            # Append unchanged line (index or timestamp or blank)
            translated_content.append(line)
        else:
            # Translate the subtitle text
            translated_line = translator.translate(line.strip(), dest=target_language).text
            translated_content.append(translated_line + '\n')

    # Write the translated content to a new .srt file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.writelines(translated_content)

def srt_format_timestamp(seconds: float):
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000
    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000
    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000
    return (f"{hours}:") + f"{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def write_srt(transcript: Iterator[dict], file: TextIO):
    count = 0
    for segment in transcript:
        count +=1
        print(
            f"{count}\n"
            f"{srt_format_timestamp(segment['timestamp'][0])} --> {srt_format_timestamp(segment['timestamp'][1])}\n"
            f"{segment['text'].replace('-->', '->').strip()}\n",
            file=file,
            flush=True,
        )


def subtitles(source_language, target_language, audio, timestamps='sentence'):
    os.system('huggingface-cli login --token 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 --add-to-git-credential')

    model = 'openai/whisper-large-v3'
    if source_language == 'tt':
        model = 'mcronomus/whisper-small-tt'

    try:
        pipe = pipeline(
            model=model,
            device='cuda',
            return_timestamps=timestamps
        )
    except:
        pipe = pipeline(
            model=model,
            return_timestamps=timestamps
        )

    result = pipe(audio)

    initial_filename = 'init.srt'
    final_filename = 'subtitles.srt'

    with open(initial_filename, 'w') as f:
        write_srt(result['chunks'], f)

    combine_srt(initial_filename, initial_filename, target_language)

    # translate_srt(initial_filename, final_filename, target_language)
    os.system(f'translatesubs {initial_filename} {final_filename} --to_lang {target_language}')

    del model
    del pipe
    gc.collect()

    return os.path.abspath(final_filename), result


def transcribe(source_language, audio, timestamps='sentence'):
    os.system('huggingface-cli login --token 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 --add-to-git-credential')

    model = 'openai/whisper-large-v3'
    if source_language == 'tt':
        model = 'mcronomus/whisper-small-tt'

    try:
        pipe = pipeline(
            model=model,
            device='cuda',
            return_timestamps=timestamps
        )
    except:
        pipe = pipeline(
            model=model,
            return_timestamps=timestamps
        )

    result = pipe(audio)

    del model
    del pipe
    gc.collect()

    return result['text']