import pyaudio
import wave
import requests
import json
import os
import base64

API_KEY = "YOUR_API_KEY"
GOOGLE_SPEECH_URL = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  
CHUNK = 1024
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

def select_microphone():
    """List and select microphone device"""
    p = pyaudio.PyAudio()
    print("\nAvailable audio devices:")
    input_devices = []
    
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            print(f"{len(input_devices)}: {dev['name']}")
            input_devices.append(i)
    
    if not input_devices:
        raise Exception("No input devices found!")
    
    for dev_index in input_devices:
        dev_info = p.get_device_info_by_index(dev_index)
        if "mic" in dev_info['name'].lower() or "microphone" in dev_info['name'].lower():
            print(f"\nAuto-selecting: {dev_info['name']}")
            return p, dev_index
    
    print("\nUsing first available input device")
    return p, input_devices[0]

def record_audio():
    """Record audio from selected microphone"""
    p, device_index = select_microphone()
    
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
        input_device_index=device_index
    )
    
    print(f"\nRecording for {RECORD_SECONDS} seconds... (speak now)")
    frames = []
    
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        except OSError as e:
            print(f"Audio error: {e}")
            break
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    if not frames:
        raise Exception("No audio captured - check microphone")
    
    # Save as WAV file
    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    print(f"Audio saved to {WAVE_OUTPUT_FILENAME}")
    return WAVE_OUTPUT_FILENAME

def transcribe_audio(file_path):
    """Send audio to Google Speech-to-Text API"""
    with open(file_path, 'rb') as f:
        audio_content = f.read()
    
    audio_b64 = base64.b64encode(audio_content).decode('utf-8')
    
    payload = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": RATE,
            "languageCode": "es-AR",
            "enableAutomaticPunctuation": True,
            "model": "default"
        },
        "audio": {
            "content": audio_b64
        }
    }
    
    try:
        response = requests.post(
            GOOGLE_SPEECH_URL,
            headers={'Content-Type': 'application/json'},
            json=payload,  
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"API Request Failed: {e}")
        if hasattr(e, 'response') and e.response:
            print("API Response:", e.response.text)
        raise

if __name__ == "__main__":
    try:
        print("=== Speech Recognition Test ===")
        
        audio_file = record_audio()
        
        if os.path.getsize(audio_file) < 1024:  
            raise Exception("Recording too small - microphone may not be working")
        
        print("\nSending to Google Speech API...")
        result = transcribe_audio(audio_file)
        
        print("\nRaw API Response:")
        print(json.dumps(result, indent=2))
        
        if not result.get('results'):
            raise Exception("No transcription results - check audio quality")
      
        transcripts = [
            alt['transcript']
            for res in result['results']
            for alt in res['alternatives']
        ]
        
        if not transcripts:
            raise Exception("Received empty transcription")
        
        print("\n=== Transcription ===")
        print("\n".join(transcripts))
        print("=" * 50)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Verify microphone works in other apps")
        print("2. Try speaking louder and closer to mic")
        print("3. Check API key permissions")
        print("4. Test with a pre-recorded WAV file")
        print("5. Try different microphone (device index)")
