from gtts import gTTS

def text_to_speech(text, lang="en"):
    tts = gTTS(text=text, lang=lang)
    file_path = "output.mp3"
    tts.save(file_path)
    return file_path
