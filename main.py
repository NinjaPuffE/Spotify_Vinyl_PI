import json
from flask import Flask, request, redirect, g, render_template
import requests
from urllib.parse import quote
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import threading

app = Flask(__name__)

#  Client Keys
CLIENT_ID = "4978afcda565450fa1e480a2c560cc5e"
CLIENT_SECRET = "782c460280714350b0237f06e61c50d5"
# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8080
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "user-read-playback-state"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,   
    "scope": SCOPE,
    "client_id": CLIENT_ID
}

@app.route("/")
def index():
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)

@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)

    # Auth Step 5: Tokens are Returned to Application
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Create the Tkinter window
    window = tk.Tk()
    window.title("Spotify Album Cover")

    # Set the window size
    window.geometry("1000x1000")

    # Create a canvas to display the background and album cover
    canvas = tk.Canvas(window, width=1000, height=1000, highlightthickness=0)
    canvas.pack(expand=True, fill=tk.BOTH)

    # Load and display the background image
    background_image_path = "playerbackground.png"  # Replace with your background image file name
    background_image = Image.open(background_image_path)
    background_image = background_image.resize((1000, 1000))
    background_tk_image = ImageTk.PhotoImage(background_image)
    canvas.create_image(0, 0, anchor=tk.NW, image=background_tk_image)


    angle = 360
    tk_image = None
    circular_combined_image = None
    songName = None
    vinyl_path = "Gramophone_Vinyl_LP_Record_PNG_Transparent_Clip_Art_Image.png"
    vinyl_image = Image.open(vinyl_path).convert("RGBA")
    vinyl_image = vinyl_image.resize((1000, 1000))
    playing = False
    playPause = False

    play_image_path = "needleon.png"  # Replace with your play image file name
    pause_image_path = "needleoff.png"  # Replace with your pause image file name
    play_image = Image.open(play_image_path).convert("RGBA").resize((1000, 1000))
    pause_image = Image.open(pause_image_path).convert("RGBA").resize((1000, 1000))

    def fetch_album_cover():
        nonlocal circular_combined_image, songName, vinyl_image, playing, playPause, canvas, play_image, pause_image
        while True:
            user_currentSong_api_endpoint = "{}/me/player".format(SPOTIFY_API_URL)
            currentSong_response = requests.get(user_currentSong_api_endpoint, headers=authorization_header)
            active = (str(currentSong_response) == "<Response [200]>")
            if active:
                currentSong_data = json.loads(currentSong_response.text)
                changePlay = (playPause != currentSong_data['is_playing'])
                playPause = currentSong_data['is_playing']

                if songName != currentSong_data['item']['album']['name']:
                    # Fetch the album cover image
                    songName = currentSong_data['item']['album']['name']
                    response = requests.get(currentSong_data['item']['album']['images'][0]['url'])
                    image_data = response.content
                    album_image = Image.open(BytesIO(image_data))

                    # Ensure the image has no border
                    album_image = album_image.convert("RGBA").resize((324, 324))

                    # Create a circular mask
                    mask = Image.new("L", album_image.size, 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0) + album_image.size, fill=255)
                    
                    
                    # Apply the mask to the image
                    circular_album_image = Image.new("RGBA", album_image.size)
                    circular_album_image.paste(album_image, (0, 0), mask)

                    # Combine with vinyl image
                    combined_image = vinyl_image.copy()
                    combined_image.paste(circular_album_image, (339, 337), circular_album_image)
                    combined_image = combined_image.resize((675, 675))

                    combined_mask = Image.new("L", combined_image.size, 255)
                    draw_combined = ImageDraw.Draw(combined_mask)
                    draw_combined.ellipse((324, 324, 351, 351), fill=0)  # Adjust the coordinates and size as needed


                    circular_combined_image = Image.new("RGBA", combined_image.size)
                    circular_combined_image.paste(combined_image, (0, 0), combined_mask)

                playing = True
                if (changePlay):
                    overlay_image = play_image if playPause else pause_image
                    overlay_tk_image = ImageTk.PhotoImage(overlay_image)
                    canvas.delete("overlay_image")  # Clear previous overlay image
                    canvas.create_image(500, 500, image=overlay_tk_image, tags="overlay_image")  # Adjust coordinates as needed

            else:
                playing = False
            time.sleep(0.1)
        
    def update_album_cover():
        nonlocal angle, circular_combined_image, playing, canvas, tk_image
        if circular_combined_image and playing:
            # Rotate the existing image
            rotated_image = circular_combined_image.rotate(angle, resample=Image.BICUBIC, expand=False)

            # Convert the image to a format Tkinter can use
            tk_image = ImageTk.PhotoImage(rotated_image)

            # Clear the canvas and draw the new image
            canvas.delete("album_cover")
            canvas.create_image(446.3, 504.4, image=tk_image, tags="album_cover")  # Center the image
            canvas.tag_raise("overlay_image")  # Move the image to the background
            angle = (angle - 3) if (angle > 3) else (angle + 357)
        # Schedule the function to run again after 100 milliseconds
        window.after(1, update_album_cover)

    threading.Thread(target=fetch_album_cover, daemon=True).start()
    # Initial call to update the album cover
    update_album_cover()

    # Start the Tkinter event loop
    window.mainloop()
    
    return redirect("https://www.google.com/")

if __name__ == "__main__":
    app.run(debug=True, port=PORT)