from pytube import YouTube, exceptions
import os
from youtubesearchpython import VideosSearch
from scenedetect import VideoManager
from scenedetect import SceneManager
from scenedetect.detectors import ContentDetector
import cv2  # Import OpenCV for image processing
import easyocr

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

def download_video(url):
    """Download the given video from YouTube."""
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if stream:
            video_path = stream.download()
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

def detect_scenes(video_path):
    """Detects and saves scenes from the video."""
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0, min_scene_len=15))  # Adjusted threshold and min_scene_len
    
    video_manager.start()
    
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
                image_path = f'scene_{i}.jpg'
                cv2.imwrite(image_path, frame_image)
                print(f"Scene saved as {image_path}")
                # Detect text in the scene image
                text = detect_text(image_path)
                if text:
                    print("English text detected:")
                    for line in text:
                        print(line)
                else:
                    print("No English text detected.")
            else:
                print(f"Failed to save scene {i} at frame {mid_frame}")
    finally:
        video_manager.release()
        cap.release()

def main():
    subject = input("Enter the subject to search: ").strip()
    video = search_videos(subject)
    if video:
        print(f"Downloading video: {video['title']} ({video['link']})")
        video_path = download_video(video['link'])
        if video_path:
            print(f"Video downloaded successfully: {video_path}")
            detect_scenes(video_path)  # Detect and save scenes
        else:
            print("Failed to download video.")
    else:
        print("No suitable video found under 10 minutes.")

if __name__ == "__main__":
    main()
