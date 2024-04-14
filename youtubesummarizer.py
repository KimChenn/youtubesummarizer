from pytube import YouTube, exceptions
import os
from youtubesearchpython import VideosSearch
from scenedetect import VideoManager
from scenedetect import SceneManager
from scenedetect.detectors import ContentDetector
import cv2  # Import OpenCV for image processing
import easyocr
from PIL import Image  # Import the Python Imaging Library

def setup_download_folder(folder_name="downloads"):
    """Ensure the download folder exists."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def parse_duration(duration_str):
    """Parse duration string formatted as 'hh:mm:ss' or 'mm:ss' into total seconds."""
    parts = duration_str.split(':')
    parts = [int(part) for part in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 1:
        return parts[0]
    return 0

def search_videos(query):
    """Search for videos and return the first result under 10 minutes."""
    videos_search = VideosSearch(query, limit=10)
    results = videos_search.result()['result']
    for video in results:
        if video['duration']:
            duration_seconds = parse_duration(video['duration'])
            if duration_seconds < 600:  # Less than 10 minutes
                return video
    return None

def download_video(url, download_folder):
    """Download the given video from YouTube."""
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if stream:
            video_path = stream.download(output_path=download_folder)
            return video_path
        else:
            print("No suitable stream found.")
            return None
    except exceptions.PytubeError as e:
        print(f"An error occurred: {str(e)}")
        return None

def detect_text(image_path):
    """Detect English text in the given image using EasyOCR."""
    reader = easyocr.Reader(['en'])  # Initialize EasyOCR with English as the language
    result = reader.readtext(image_path)
    english_text = []
    for detection in result:
        text = detection[1]  # Adjust to correct index for extracting text
        if isinstance(text, str) and text.isascii():
            english_text.append(text)
    return english_text

def add_watermark(image, text, position, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, color=(255, 255, 255), thickness=2):
    """Add a text watermark to an image with a black outline for better visibility."""
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = position[0] - text_size[0] - 10  # Adjust position for padding
    text_y = position[1] - 10  # Adjust position for padding
    cv2.putText(image, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness+4, lineType=cv2.LINE_AA)  # Black outline
    cv2.putText(image, text, (text_x, text_y), font, font_scale, color, thickness, lineType=cv2.LINE_AA)

def detect_scenes(video_path, download_folder):
    """Detects and saves scenes from the video."""
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0, min_scene_len=15))  # Adjusted threshold and min_scene_len
    
    video_manager.start()
    image_paths = []  # List to store image paths for GIF creation
    
    try:
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()

        cap = cv2.VideoCapture(video_path)  # Open video file with OpenCV
        for i, scene in enumerate(scene_list):
            start_frame, end_frame = scene
            start_frame_num = start_frame.get_frames()  # Extract frame number from FrameTimecode object
            end_frame_num = end_frame.get_frames()  # Extract frame number from FrameTimecode object
            mid_frame = start_frame_num + (end_frame_num - start_frame_num) // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)  # Set position to the middle frame of the scene
            ret, frame_image = cap.read()
            if ret:
                image_path = os.path.join(download_folder, f'scene_{i}.jpg')
                cv2.imwrite(image_path, frame_image)  # Temporarily save the image without watermark
                # Perform OCR on the image
                text = detect_text(image_path)
                if text:
                    print("English text detected:")
                    for line in text:
                        print(line)
                else:
                    print("No English text detected.")
                # Add watermark after OCR
                add_watermark(frame_image, "Kim Chen", (frame_image.shape[1], frame_image.shape[0]))
                cv2.imwrite(image_path, frame_image)  # Save the image with the watermark
                image_paths.append(image_path)
                print(f"Scene saved as {image_path}")
            else:
                print(f"Failed to save scene {i} at frame {mid_frame}")
    finally:
        video_manager.release()
        cap.release()
    return image_paths

def create_gif(image_paths, output_path="output.gif", duration=500):
    """Create an animated GIF from a list of image files."""
    images = [Image.open(image) for image in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:], optimize=False, duration=duration, loop=0)
    print(f"Animated GIF created at {output_path}")

def main():
    download_folder = setup_download_folder()  # Setup download folder
    subject = input("Enter the subject to search: ").strip()
    video = search_videos(subject)
    if video:
        print(f"Downloading video: {video['title']} ({video['link']})")
        video_path = download_video(video['link'], download_folder)
        if video_path:
            print(f"Video downloaded successfully: {video_path}")
            image_paths = detect_scenes(video_path, download_folder)  # Detect and save scenes
            if image_paths:
                gif_path = os.path.join(download_folder, "scenes_animation.gif")
                create_gif(image_paths, gif_path)
        else:
            print("Failed to download video.")
    else:
        print("No suitable video found under 10 minutes.")

if __name__ == "__main__":
    main()
