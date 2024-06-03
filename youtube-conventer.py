import os
import subprocess
import sys
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from pytube import YouTube, Playlist
from moviepy.editor import AudioFileClip
import threading

# Global lists
downloaded_files = []
url_queue = []
playlist_videos = []

def download_youtube_video(youtube_url, output_path, file_type, update_timeline):
    yt = YouTube(youtube_url)
    update_timeline("Resolving YouTube link...", 10)

    if file_type == 'mp3':
        update_timeline("Selecting audio stream...", 20)
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
        update_timeline("Downloading audio stream...", 30)
        downloaded_file = audio_stream.download(output_path=output_path)
        base, ext = os.path.splitext(downloaded_file)
        mp3_file = base + '.mp3'
        update_timeline("Converting audio file...", 70)
        try:
            audio_clip = AudioFileClip(downloaded_file)
            audio_clip.write_audiofile(mp3_file)
            audio_clip.close()
            os.remove(downloaded_file)
            update_timeline("Process completed.", 100)
            return mp3_file
        except Exception as e:
            update_timeline(f"Error (Conversion): {str(e)}", 100)
            return None
    elif file_type == 'mp4':
        update_timeline("Selecting video stream...", 20)
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        update_timeline("Downloading video stream...", 70)
        try:
            mp4_file = video_stream.download(output_path=output_path)
            update_timeline("Process completed.", 100)
            return mp4_file
        except Exception as e:
            update_timeline(f"Error (Download): {str(e)}", 100)
            return None

def browse_directory():
    directory = filedialog.askdirectory()
    output_path_var.set(directory)

def update_progress(progress):
    progress_var.set(progress)
    root.update_idletasks()

def update_timeline(message, progress_increment):
    timeline_text.config(state=NORMAL)
    timeline_text.insert(END, message + "\n")
    timeline_text.config(state=DISABLED)
    timeline_text.yview(END)
    update_progress(progress_var.get() + progress_increment)

def start_download():
    youtube_url = url_var.get()
    output_path = output_path_var.get()
    file_type = file_type_var.get()

    if not youtube_url or not output_path:
        messagebox.showerror("Error", "Please fill in all fields.")
        return

    threading.Thread(target=download_and_convert, args=(youtube_url, output_path, file_type)).start()

def download_and_convert(youtube_url, output_path, file_type):
    try:
        update_progress(0)
        update_timeline("Download started.", 0)
        file_path = download_youtube_video(youtube_url, output_path, file_type, update_timeline)
        if file_path:
            update_timeline(f"File downloaded and converted: {file_path}", 100)
            downloaded_files.append((file_type, file_path, True))
        else:
            update_timeline("File could not be downloaded or converted.", 100)
            downloaded_files.append((file_type, "Could not be downloaded or converted", False))
        update_download_list()
    except Exception as e:
        update_timeline(f"Error: {str(e)}", 100)
        downloaded_files.append((file_type, str(e), False))
        update_download_list()
    finally:
        process_next_url()

def update_download_list():
    download_listbox.delete(0, END)
    for file_type, file_path, success in downloaded_files:
        if success:
            download_listbox.insert(END, f"{file_type.upper()}: {file_path}")
            download_listbox.itemconfig(END, {'fg': 'green'})
        else:
            download_listbox.insert(END, f"{file_type.upper()} ERROR: {file_path}")
            download_listbox.itemconfig(END, {'fg': 'red'})
    update_progress_label()

def on_listbox_select(event):
    selected_index = download_listbox.curselection()
    if selected_index:
        selected_file = downloaded_files[selected_index[0]][1]
        if os.path.exists(selected_file):
            open_file_location(selected_file)

def open_file_location(file_path):
    folder_path = os.path.dirname(file_path)
    if os.name == 'nt':  # Windows
        os.startfile(folder_path)
    elif os.name == 'posix':
        if sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', folder_path])
        else:  # Linux
            subprocess.Popen(['xdg-open', folder_path])

def add_url_to_queue():
    url = url_var.get()
    if url:
        url_queue.append(url)
        update_url_queue_list()
        url_var.set('')

def remove_url_from_queue():
    selected_index = url_queue_listbox.curselection()
    if selected_index:
        url_queue.pop(selected_index[0])
        update_url_queue_list()

def update_url_queue_list():
    url_queue_listbox.delete(0, END)
    for index, url in enumerate(url_queue, 1):
        url_queue_listbox.insert(END, f"{index}. {url}")

def start_queue_download():
    if url_queue:
        process_next_url()

def process_next_url():
    if url_queue:
        next_url = url_queue.pop(0)
        url_var.set(next_url)
        update_progress_label()
        start_download()
        update_url_queue_list()

def update_progress_label():
    total = len(downloaded_files) + len(url_queue)
    completed = len(downloaded_files)
    progress_label_var.set(f"{completed}/{total} Downloads Completed")
    current_url_label_var.set(f"Processing URL: {url_var.get()}" if url_var.get() else "")

def analyze_playlist():
    playlist_url = playlist_url_var.get()
    if playlist_url:
        playlist_loading_var.set("Loading...")
        threading.Thread(target=fetch_playlist_videos, args=(playlist_url,)).start()

def fetch_playlist_videos(playlist_url):
    try:
        pl = Playlist(playlist_url)
        playlist_videos.clear()
        for video in pl.videos:
            playlist_videos.append((video.watch_url, video.title))
        update_playlist_menu()
    except Exception as e:
        messagebox.showerror("Error", f"Could not access playlist: {str(e)}")
    finally:
        playlist_loading_var.set("")

def update_playlist_menu():
    playlist_menu_listbox.delete(0, END)
    for url, title in playlist_videos:
        playlist_menu_listbox.insert(END, title)

def add_selected_videos_to_queue():
    selected_indices = playlist_menu_listbox.curselection()
    for index in selected_indices:
        url_queue.append(playlist_videos[index][0])
    update_url_queue_list()

def cancel_queue():
    url_queue.clear()
    update_url_queue_list()
    messagebox.showinfo("Info", "Queue has been cancelled.")
    update_progress_label()

def stop_all():
    url_queue.clear()
    downloaded_files.clear()
    update_url_queue_list()
    update_download_list()
    messagebox.showinfo("Info", "All operations have been stopped and reset.")
    update_progress_label()

# Create GUI
root = Tk()
root.title("YouTube Converter")

# Set DPI awareness
if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print("DPI awareness could not be set:", e)


# Make the window size and layout dynamic
root.geometry("800x600")  # Initial size
root.resizable(True, True)  # Allow resizing

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(N, W, E, S))

# Grid configuration
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
frame.grid_rowconfigure(12, weight=1)
frame.grid_columnconfigure(1, weight=1)

# YouTube URL field
ttk.Label(frame, text="YouTube URL:").grid(row=0, column=0, sticky=W)
url_var = StringVar()
url_entry = ttk.Entry(frame, textvariable=url_var, width=50)
url_entry.grid(row=0, column=1, sticky=(W, E))
ttk.Button(frame, text="Add", command=add_url_to_queue).grid(row=0, column=2, sticky=W)
ttk.Button(frame, text="Remove", command=remove_url_from_queue).grid(row=0, column=3, sticky=W)

# Output directory selector
ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky=W)
output_path_var = StringVar()
output_path_entry = ttk.Entry(frame, textvariable=output_path_var, width=50)
output_path_entry.grid(row=1, column=1, sticky=(W, E))
ttk.Button(frame, text="Browse...", command=browse_directory).grid(row=1, column=2, sticky=W)

# File type selector
ttk.Label(frame, text="File Type:").grid(row=2, column=0, sticky=W)
file_type_var = StringVar(value='mp3')
ttk.Radiobutton(frame, text='MP3', variable=file_type_var, value='mp3').grid(row=2, column=1, sticky=W)
ttk.Radiobutton(frame, text='MP4', variable=file_type_var, value='mp4').grid(row=2, column=2, sticky=W)

# Start queue button
ttk.Button(frame, text="Start Queue", command=start_queue_download).grid(row=3, column=1, columnspan=2, sticky=(W, E))

# Progress status label
progress_label_var = StringVar()
ttk.Label(frame, textvariable=progress_label_var).grid(row=4, column=1, columnspan=2, sticky=W)

# Processing URL label
current_url_label_var = StringVar()
ttk.Label(frame, textvariable=current_url_label_var).grid(row=5, column=0, columnspan=4, sticky=W)

# Progress bar
ttk.Label(frame, text="Progress:").grid(row=6, column=0, sticky=W)
progress_var = DoubleVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
progress_bar.grid(row=6, column=1, columnspan=3, sticky=(W, E))

# Timeline text box
ttk.Label(frame, text="Timeline:").grid(row=7, column=0, sticky=W)
timeline_text = Text(frame, height=10, width=60, state=DISABLED)
timeline_text.grid(row=7, column=1, columnspan=3, sticky=(W, E))

# Downloaded files list
ttk.Label(frame, text="Downloaded Files:").grid(row=8, column=0, sticky=W)
download_listbox = Listbox(frame, height=10, width=60)
download_listbox.grid(row=8, column=1, columnspan=3, sticky=(W, E))
download_listbox.bind('<<ListboxSelect>>', on_listbox_select)

# URL queue list
ttk.Label(frame, text="URL Queue:").grid(row=9, column=0, sticky=W)
url_queue_listbox = Listbox(frame, height=10, width=60)
url_queue_listbox.grid(row=9, column=1, columnspan=3, sticky=(W, E))

# Cancel and stop queue buttons
ttk.Button(frame, text="Clear and Cancel Queue", command=cancel_queue).grid(row=10, column=1, columnspan=2, sticky=(W, E))

# Playlist analysis section
playlist_frame = ttk.LabelFrame(frame, text="Playlist Analysis", padding="10")
playlist_frame.grid(row=11, column=0, columnspan=4, sticky=(W, E))

# Playlist URL field
ttk.Label(playlist_frame, text="Playlist URL:").grid(row=0, column=0, sticky=W)
playlist_url_var = StringVar()
playlist_url_entry = ttk.Entry(playlist_frame, textvariable=playlist_url_var, width=50)
playlist_url_entry.grid(row=0, column=1, sticky=(W, E))
ttk.Button(playlist_frame, text="Analyze", command=analyze_playlist).grid(row=0, column=2, sticky=W)

# Playlist videos list
ttk.Label(playlist_frame, text="Playlist Videos:").grid(row=1, column=0, sticky=W)
playlist_menu_listbox = Listbox(playlist_frame, height=10, width=60, selectmode=MULTIPLE)
playlist_menu_listbox.grid(row=1, column=1, sticky=(W, E))
ttk.Button(playlist_frame, text="Add Selected", command=add_selected_videos_to_queue).grid(row=2, column=0, columnspan=2, sticky=(W, E))

# Playlist loading animation
playlist_loading_var = StringVar()
playlist_loading_label = ttk.Label(playlist_frame, textvariable=playlist_loading_var)
playlist_loading_label.grid(row=1, column=2, sticky=W)

# Scrollbars
download_listbox_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=download_listbox.yview)
download_listbox_scrollbar.grid(row=8, column=4, sticky=(N, S))
download_listbox.config(yscrollcommand=download_listbox_scrollbar.set)

url_queue_listbox_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=url_queue_listbox.yview)
url_queue_listbox_scrollbar.grid(row=9, column=4, sticky=(N, S))
url_queue_listbox.config(yscrollcommand=url_queue_listbox_scrollbar.set)

playlist_menu_listbox_scrollbar = ttk.Scrollbar(playlist_frame, orient='vertical', command=playlist_menu_listbox.yview)
playlist_menu_listbox_scrollbar.grid(row=1, column=3, sticky=(N, S))
playlist_menu_listbox.config(yscrollcommand=playlist_menu_listbox_scrollbar.set)

root.mainloop()
