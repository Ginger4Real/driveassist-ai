import pyttsx3
import webbrowser
import re
import openai
import asyncio
from googletrans import Translator, LANGUAGES
import pyaudio
import speech_recognition as sr
from datetime import datetime
import requests

# Set your OpenAI API key
openai.api_key = 'Your OpenAI API key'

# Initialize the text-to-speech engine
engine = pyttsx3.init()

# Initialize the translator
translator = Translator()

def speak_text(text):
    """Speaks the given text using the text-to-speech engine."""
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Error in speaking text: {e}")

def get_default_microphone():
    """Returns the index of the default input microphone."""
    try:
        p = pyaudio.PyAudio()
        default_device_index = p.get_default_input_device_info()['index']
        p.terminate()
        return default_device_index
    except Exception as e:
        print(f"Error getting default microphone: {e}")
        return None

def evaluate_expression(expression):
    """Evaluates the given arithmetic expression."""
    try:
        expression = expression.replace('x', '*').replace('plus', '+').replace('minus', '-').replace('divided by', '/')
        expression = re.sub(r'[^0-9+\-*/().]', '', expression)
        return eval(expression)
    except Exception as e:
        print(f"Error in arithmetic operation: {e}")
        return None

def search_google_maps(address, route=False):
    """Opens Google Maps with the given address and optionally starts the route."""
    if route:
        search_query = f"https://www.google.com/maps/dir/?api=1&destination={address.replace(' ', '+')}"
    else:
        search_query = f"https://www.google.com/maps/search/?api=1&query={address.replace(' ', '+')}"
    
    try:
        webbrowser.open(search_query)
        speak_text(f"Opening Google Maps for {address}.")
    except Exception as e:
        print(f"Failed to open Google Maps: {e}")
        speak_text("Failed to open Google Maps.")

async def translate_text(text, target_language='en'):
    """Translates the given text to the target language using OpenAI."""
    try:
        response = await openai.Completion.create(
            model="text-davinci-003",
            prompt=f"Translate this text to {LANGUAGES[target_language]}: {text}",
            max_tokens=60
        )
        translation = response.choices[0].text.strip()
        return translation
    except Exception as e:
        print(f"Error in translation: {e}")
        return text

async def recognize_speech_from_mic(recognizer, microphone):
    """Recognizes speech from the microphone."""
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Listening...")
            audio = recognizer.listen(source, timeout=5)
        try:
            response = recognizer.recognize_google(audio, language='nl-NL').lower()
            print(f"Recognized speech: {response}")
            return response
        except sr.UnknownValueError:
            return "unintelligible"
        except sr.RequestError as e:
            print(f"API was unreachable or unresponsive: {e}")
            return None
    except Exception as e:
        print(f"Error in speech recognition: {e}")
        return None

async def process_instruction(instruction, recognizer, microphone):
    """Process the given instruction."""
    instruction = instruction.lower()  # Ensure lowercase for consistent matching
    
    if 'english' in instruction or 'dutch' in instruction:
        target_language = 'nl' if 'dutch' in instruction else 'en'
        translation = await translate_text(instruction, target_language)
        print(f"Translation: {translation}")
        speak_text(f"Translated text: {translation}")
        instruction = translation

    if "home" in instruction:
        # Open Google Maps with the specific address and start the route
        address = "Your home adress"
        search_google_maps(address, route=True)
    elif "school" in instruction:
        # Open Google Maps with the specific address and start the route
        address = "Your school adress"
        search_google_maps(address, route=True)
    elif "google maps" in instruction:
        speak_text("Please provide the address including city and house number.")
        print("Say the address slowly and clearly so I can understand it better!")
        address_audio = await recognize_speech_from_mic(recognizer, microphone)
        if address_audio:
            search_google_maps(address_audio)
        else:
            speak_text("I didn't catch the address. Please try again.")
    elif "time" in instruction:
        try:
            response = requests.get("http://worldtimeapi.org/api/ip")
            data = response.json()
            current_time = data['datetime']
            timezone = data['timezone']
            speak_text(f"The current time is {current_time} in {timezone}.")
            print(f"Current time: {current_time} Timezone: {timezone}")
        except Exception as e:
            print(f"Failed to get the time: {e}")
            speak_text("Failed to get the current time.")
    else:
        speak_text("Sorry, I didn't understand that.")
        print(f"Didn't understand the instruction: {instruction}")

async def main():
    """Main function to run the application."""
    recognizer = sr.Recognizer()
    microphone_index = get_default_microphone()
    if microphone_index is None:
        print("No microphone found.")
        return

    microphone = sr.Microphone(device_index=microphone_index)
    activated = False
    failed_attempts = 0

    while True:
        if not activated:
            # Listen for wake word "hey computer"
            command = await recognize_speech_from_mic(recognizer, microphone)
            if command == "unintelligible":
                failed_attempts += 1
                if failed_attempts >= 5:
                    print("Repeatedly failed to understand speech. Please check your microphone and try again.")
                    speak_text("I am having trouble understanding. Please check your microphone and try again.")
                    failed_attempts = 0
            elif command and "hey computer" in command:
                print("Wake word detected!")
                speak_text("Hey , what can I do for you?")
                activated = True
                failed_attempts = 0
            else:
                print("Listening for wake word...")
        else:
            # Listen for instructions
            instruction = await recognize_speech_from_mic(recognizer, microphone)
            if instruction == "unintelligible":
                failed_attempts += 1
                if failed_attempts >= 5:
                    print("Repeatedly failed to understand speech. Please check your microphone and try again.")
                    speak_text("I am having trouble understanding. Please check your microphone and try again.")
                    failed_attempts = 0
            elif instruction:
                print(f"Instruction received: {instruction}")

                # Process the instruction asynchronously
                await process_instruction(instruction, recognizer, microphone)

                activated = False
                failed_attempts = 0

                # Clear cache or reset variables if necessary
                await asyncio.sleep(0)  # Allows other tasks to run and clears the event loop

if __name__ == "__main__":
    asyncio.run(main())
