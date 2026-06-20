import os

def speak(text):
    os.system(f'termux-tts-speak "{text}"')

def execute(command):

    command = command.lower()

    if "call" in command:

        number = command.replace("call", "").strip()

        os.system(f'termux-telephony-call {number}')

        speak("Calling now")

    elif "youtube" in command:

        os.system(
            'am start -a android.intent.action.VIEW -d https://youtube.com'
        )

        speak("Opening YouTube")

    elif "whatsapp" in command:

        os.system(
            'monkey -p com.whatsapp -c android.intent.category.LAUNCHER 1'
        )

        speak("Opening WhatsApp")

    elif "chrome" in command:

        os.system(
            'monkey -p com.android.chrome -c android.intent.category.LAUNCHER 1'
        )

        speak("Opening Chrome")

    elif "camera" in command:

        os.system(
            'monkey -p com.sec.android.app.camera -c android.intent.category.LAUNCHER 1'
        )

        speak("Opening camera")

    elif "time" in command:

        os.system("date")

    elif "battery" in command:

        os.system("termux-battery-status")

    elif "storage" in command:

        os.system("df -h")

    elif "wifi" in command:

        os.system("termux-wifi-connectioninfo")

    elif "exit" in command:

        speak("Goodbye")
        exit()

    else:

        speak("I do not understand")

speak("Jarvis online")

while True:

    cmd = input("You: ")

    execute(cmd)
with open("memory.txt", "a") as f:
    f.write(command + "\n")


if "hello" in command:
    print("Hello")

elif "send whatsapp" in command:
    print("Sending")
