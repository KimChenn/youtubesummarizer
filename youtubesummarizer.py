from pytube import YouTube, exceptions
import os
from youtubesearchpython import VideosSearch
from scenedetect import VideoManager
from scenedetect import SceneManager
from scenedetect.detectors import ContentDetector
import cv2
import easyocr
from PIL import Image, ImageTk, ImageSequence
import tkinter as tk

def setup_download_folder(folder_name="downloads"):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def parse_duration(duration_str):
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
    videos_search = VideosSearch(query, limit=10)
    results = videos_search.result()['result']
    for video in results:
        if video['duration']:
            duration_seconds = parse_duration(video['duration'])
            if duration_seconds < 600:
                return video
    return None

def download_video(url, download_folder):
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
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path)
    english_text = [detection[1] for detection in result if isinstance(detection[1], str) and detection[1].isascii()]
    return " ".join(english_text)

def add_watermark(image, text, position, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, color=(255, 255, 255), thickness=2):
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = position[0] - text_size[0] // 2
    text_y = position[1] - 10
    cv2.putText(image, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness+4, lineType=cv2.LINE_AA)
    cv2.putText(image, text, (text_x, text_y), font, font_scale, color, thickness, lineType=cv2.LINE_AA)

def detect_scenes(video_path, download_folder):
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0, min_scene_len=15))
    video_manager.start()
    image_paths, all_text = [], []
    try:
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()
        cap = cv2.VideoCapture(video_path)
        for i, scene in enumerate(scene_list):
            start_frame_num = scene[0].get_frames()
            end_frame_num = scene[1].get_frames()
            mid_frame = start_frame_num + (end_frame_num - start_frame_num) // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
            ret, frame_image = cap.read()
            if ret:
                image_path = os.path.join(download_folder, f'scene_{i}.jpg')
                cv2.imwrite(image_path, frame_image)
                detected_text = detect_text(image_path)
                all_text.append(detected_text)
                add_watermark(frame_image, "Kim Chen", (frame_image.shape[1] // 2, frame_image.shape[0] - 30))
                cv2.imwrite(image_path, frame_image)
                image_paths.append(image_path)
    finally:
        video_manager.release()
        cap.release()
    return image_paths, " ".join(all_text)

def create_gif(image_paths, output_path="output.gif", duration=100):
    images = [Image.open(image) for image in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:], optimize=False, duration=duration, loop=0)
    return output_path

def display_gif(gif_path):
    root = tk.Tk()
    gif = Image.open(gif_path)
    canvas = tk.Canvas(root, width=gif.width, height=gif.height) 
    canvas.pack()
    sequence = [ImageTk.PhotoImage(img) for img in ImageSequence.Iterator(gif)]
    image = canvas.create_image(0, 0, image=sequence[0], anchor=tk.NW)

    def update_frame(num):
        frame = sequence[num]
        canvas.itemconfig(image, image=frame)
        root.after(100, update_frame, (num+1) % len(sequence))

    update_frame(0)
    root.mainloop()


def main():
    download_folder = setup_download_folder()
    subject = input("Enter the subject to search: ").strip()
    video = search_videos(subject)
    if video:
        print(f"Downloading video: {video['title']} ({video['link']})")
        video_path = download_video(video['link'], download_folder)
        if video_path:
            print(f"Video downloaded successfully: {video_path}")
            image_paths, all_text = detect_scenes(video_path, download_folder)
            if image_paths:
                gif_path = os.path.join(download_folder, "scenes_animation.gif")
                gif_duration = 100 if len(image_paths) * 100 < 10000 else 10000 / len(image_paths)
                create_gif(image_paths, gif_path, int(gif_duration))
                print("Detected text:", all_text)
                display_gif(gif_path)
        else:
            print("Failed to download video.")
    else:
        print("No suitable video found under 10 minutes.")

if __name__ == "__main__":
    main()
