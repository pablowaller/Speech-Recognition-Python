import pyaudio
import wave
import requests
import json
import os
import base64
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://sense-bell-default-rtdb.firebaseio.com/'
})

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  
CHUNK = 1024
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

API_KEY = "YOUR_API_KEY"
GOOGLE_SPEECH_URL = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"

def record_audio():
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    print(f"Grabando por {RECORD_SECONDS} segundos...")
    frames = []
    
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    return WAVE_OUTPUT_FILENAME

def transcribe_and_send():
    audio_file = record_audio()
    
    with open(audio_file, 'rb') as f:
        audio_content = f.read()
    
    response = requests.post(
        GOOGLE_SPEECH_URL,
        headers={'Content-Type': 'application/json'},
        json={
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": RATE,
                "languageCode": "es-AR",
                "alternativeLanguageCodes": ["en-US", "fr-FR", "de-DE", "pt-BR"],
                "enableAutomaticPunctuation": True
            },
            "audio": {
                "content": base64.b64encode(audio_content).decode('utf-8')
            }
        }
    )
    
    result = response.json()['results'][0]
    transcript = result['alternatives'][0]['transcript']
    detected_language = result['languageCode'] if 'languageCode' in result else 'unknown'

    ref = db.reference('transcriptions')
    new_transcription = {
        "text": transcript,
        "language": detected_language,
        "timestamp": datetime.now().isoformat()  
    }
    
    ref.push(new_transcription)
    print(f"Transcripción enviada: {transcript}")

if __name__ == "__main__":
    try:
        transcribe_and_send()
    except Exception as e:
        print(f"Error: {str(e)}")

        db.reference('errors').push({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
