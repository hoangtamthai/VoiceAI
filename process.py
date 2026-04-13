import io
from multiprocessing import Process, Queue
from os import getenv, remove
from os.path import join
from tempfile import mkdtemp

import click
import numpy as np
import speech_recognition as sr
import torch
from dotenv import load_dotenv
from pydub import AudioSegment
from whisper import Whisper, load_model

from modules.coqui_tts import get_tts
from modules.sound import play_to_output
from modules.tkinter_text import start_app
from modules.translate import translate

load_dotenv()

INPUT_DEVICE_INDEX = int(getenv("INPUT_DEVICE_INDEX", 3))
ENERGY = int(getenv("ENERGY", 1000))
PAUSE = float(getenv("PAUSE", 0.8))
DYNAMIC_ENERGY = bool(getenv("DYNAMIC_ENERGY", "True").lower() == "true")
SAVE_FILE = bool(getenv("SAVE_FILE", "True").lower() == "true")
TEMP_DIR = mkdtemp() if SAVE_FILE else None
RECORD_TIMEOUT = int(getenv("RECORD_TIMEOUT", 3))
ENGLISH = bool(getenv("ENGLISH", "False").lower() == "true")
VERBOSE = bool(getenv("VERBOSE", "False").lower() == "true")
TRANSLATION_DESTINATION_LANGUAGE = str(getenv("TRANSLATION_DESTINATION_LANGUAGE", "en"))
MODEL = str(getenv("MODEL", "base"))
DUBBING = bool(getenv("DUBBING", "False").lower() == "true")
SUBTITLES = bool(getenv("SUBTITLES", "True").lower() == "true")


def main():
    try:
        audio_queue = Queue()
        result_queue = Queue()
        translation_queue = Queue()
        processes = []
        record_process = Process(
            target=record_audio,
            args=([audio_queue]),
        )
        processes.append(record_process)
        transcribing_process = Process(
            target=transcribe_forever,
            args=(audio_queue, result_queue),
        )
        processes.append(transcribing_process)
        translating_process = Process(
            target=translate,
            args=(result_queue, translation_queue),
        )
        processes.append(translating_process)
        if DUBBING:
            output_audio_process = Process(
                target=play_translated_audio, args=([translation_queue])
            )
            processes.append(output_audio_process)
        for p in processes:
            p.start()
        if SUBTITLES:
            start_app(translation_queue)
    except Exception as e:
        print(e)


def record_audio(
    audio_queue,
):
    # load the speech recognizer and set the initial energy threshold and pause threshold
    r = sr.Recognizer()
    r.energy_threshold = ENERGY
    r.pause_threshold = PAUSE
    r.dynamic_energy_threshold = DYNAMIC_ENERGY
    r.operation_timeout = RECORD_TIMEOUT
    # r.non_speaking_duration = 0.05

    with sr.Microphone(device_index=INPUT_DEVICE_INDEX) as source:
        # print("Adjusting for ambient noise...")
        # r.adjust_for_ambient_noise(source, duration=5)
        # print("Finish adjusting")
        i = 0
        print("Start recording thread...")
        while True:
            # get and save audio to wav file
            print("Listening...") if VERBOSE else None
            audio = r.listen(source, phrase_time_limit=RECORD_TIMEOUT)
            if SAVE_FILE:
                data = io.BytesIO(audio.get_wav_data())
                audio_clip = AudioSegment.from_file(data)
                filename = join(TEMP_DIR, f"temp{i}.wav")
                print(filename) if VERBOSE else None
                audio_clip.export(filename, format="wav")
                audio_data = filename
            else:
                torch_audio = torch.from_numpy(
                    np.frombuffer(audio.get_raw_data(), np.int16)
                    .flatten()
                    .astype(np.float32)
                    / 32768.0
                )
                audio_data = torch_audio
            print("Audio recored") if VERBOSE else None
            audio_queue.put_nowait(audio_data)
            i += 1


# @click.pass_context
def transcribe_forever(audio_queue: Queue, result_queue: Queue):
    model = MODEL
    # there are no english models for large
    if model != "large" and ENGLISH:
        model = model + ".en"
    print("CUDA availability:", torch.cuda.is_available())
    print("Load model...")
    # devices = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    audio_model: Whisper = load_model(model)
    print("Start transcribing thread...")
    while True:
        audio_data = audio_queue.get()
        print("Transcribing...") if VERBOSE else None
        if ENGLISH:
            result = audio_model.transcribe(
                audio_data, no_speech_threshold=0.4, language="english"
            )
        else:
            result = audio_model.transcribe(
                audio_data,
                no_speech_threshold=0.4,
                # logprob_threshold=-0.5,
                beam_size=5,
            )
        predicted_text = result["text"]
        result_queue.put_nowait(predicted_text)
        if VERBOSE:
            print(result)
        if SAVE_FILE:
            remove(audio_data)


def play_translated_audio(translation_queue):
    print("Start audio thread...")
    while True:
        output = translation_queue.get()
        translation_queue.put(output)
        output_sentence = output["text"]
        print("You say:", output_sentence)
        if output_sentence != "":
            audio, frame_rate = get_tts(output_sentence)
            play_to_output(audio, frame_rate)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
