import os
import gc
from transformers import pipeline
from typing import Iterator, TextIO

from googletrans import Translator
import re

from transformers import AutoTokenizer, AutoModelWithLMHead


def utils_split_into_parts_of_four(input_list):
    return [input_list[i:i + 4] for i in range(0, len(input_list), 4)]


def utils_combine_srt(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        srt_content = file.readlines()

    translated_content = []
    for line in srt_content:
        if re.match(r'^\d{1,3}$', line.strip()) or re.match(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', line.strip()) or line.strip() == '':
            translated_content.append(line)
        else:
            translated_content.append(line.strip() + '\n')

    sentences = []

    parts = utils_split_into_parts_of_four(translated_content)

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


def utils_write_srt(transcript: Iterator[dict], file: TextIO):
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


def utils_subtitles(source_language, target_language, audio, final_filename, timestamps='word'):
    # model = 'openai/whisper-large-v3'
    model = 'openai/whisper-small'
    if source_language == 'tt':
        model = 'mcronomus/whisper-small-tt'

    try:
        pipe = pipeline(
            model=model,
            device='cuda',
            return_timestamps=timestamps,
        )
    except:
        pipe = pipeline(
            model=model,
            return_timestamps=timestamps
        )

    result = pipe(audio)

    os.makedirs('subtitles', exist_ok=True)

    initial_filename = 'subtitles/init.srt'

    with open(initial_filename, 'w') as f:
        utils_write_srt(result['chunks'], f)

    utils_combine_srt(initial_filename, initial_filename)

    os.system(f'translatesubs {initial_filename} {final_filename} --to_lang {target_language}')

    del model
    del pipe
    for _ in range(3):
        gc.collect()

    return os.path.abspath(final_filename)


def utils_transcribe(source_language, audio, timestamps='sentence'):
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
    for _ in range(3):
        gc.collect()

    return result['text']


def utils_summarize(text, target_language):
    translator = Translator()
    text_en = translator.translate(text.strip(), dest='en').text

    tokenizer = AutoTokenizer.from_pretrained('T5-base')
    model = AutoModelWithLMHead.from_pretrained('T5-base', return_dict=True)

    inputs = tokenizer.encode("sumarize: " + text_en, return_tensors='pt', max_length=512, truncation=True)
    output = model.generate(inputs, min_length=len(text.split()) // 3, max_length=len(text.split()))

    del model
    for i in range(3):
        gc.collect()

    summary = tokenizer.decode(output[0], skip_special_tokens=True)

    try:
        return translator.translate(summary.strip(), dest=target_language).text
    except:
        return translator.translate(summary.strip(), dest='ru').text


def utils_add_subtitles(subtitles_file, input_file, target_file):
    os.system(f'ffmpeg -i {input_file} -vf subtitles={subtitles_file} {target_file} -y')
    return target_file