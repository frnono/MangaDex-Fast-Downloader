import PIL.Image
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import requests
from urllib.request import urlopen
import json
import ssl
from io import BytesIO
from tkinter import *
from tkinter.filedialog import askdirectory
import customtkinter
import os
import ctypes
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import re
import zipfile
import glob


myappid = 'frnono.manga.downloader'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

ssl._create_default_https_context = ssl._create_unverified_context

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("Theme/pink.json") 
print("Short instructions\n")
print("For batch download, insert the manga id in the field, then press batch")
print("To download a single chapter, insert the chapter id in the field, then press go\n")
print("PDF(fast) is a lot faster, as the name implies. Highly recommended")
print("PDF(slow) this is pretty much useless, in some rare cases it looks better (a LOT slower)")
print("CBZ well, the name says it\n")

path = f"{os.environ['UserProfile']}/Downloads/"
mangadex_api = r"https://api.mangadex.org/at-home/server/"
chapter_id = ""
link = ""

def ChangeDirec():
    global path
    path = str(askdirectory(title='Select Folder') + "/")
    if path == "/":
        path = f"{os.environ['UserProfile']}/Downloads/"
    app.title(path)

def get_chap_id():
    global chapter_id, mangadex_api, link

    link = entry.get()
    chapter_id = link
    UrlToImg()

def batchUrlToImg():   
    global chapter_id, mangadex_api

    link = entry.get()
    manga_id = link
    chapter_list = get_chapter_list(manga_id)
    for i in range(len(chapter_list)): 
        os.system("cls")
        print(str(i + 1) + " / " + str(len(chapter_list)))   
        chapter_id = chapter_list[i]
        UrlToImg()

def download_image(url, image_path):
    response = requests.get(url)
    with open(image_path, 'wb') as f:
        f.write(response.content)

def UrlToImg():
    global chapter_id, mangadex_api
    try:
        manga_title, chapter_title, chapter_num = get_manga_title_from_chapter(chapter_id)
        print(manga_title)
        if chapter_title: print(chapter_title)
        mangadex_api = r"https://api.mangadex.org/at-home/server/" + chapter_id
        r = urlopen(mangadex_api)
        data_json = json.loads(r.read())
        result = data_json.get('result')
        baseUrl = data_json.get('baseUrl')
        chapter_hash = data_json.get('chapter', {}).get('hash')
        chapter_data = data_json.get('chapter', {}).get('data', [])
        chapter_dataSaver = data_json.get('chapter', {}).get('dataSaver', [])

        image_folder = os.path.join(path, str(manga_title), "Images", "Chapter " + str(chapter_num) + " Raw Images")
        os.makedirs(image_folder, exist_ok=True)

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            download_tasks = []

            print("Loading images...")
            app.title("Loading images...")
            for i, image_name in enumerate(chapter_data):
                linkimg = str(baseUrl) + "/data/" + str(chapter_hash) + "/" + str(image_name)
                image_path = os.path.join(image_folder, image_name)

                # Download the image
                download_task = executor.submit(download_image, linkimg, image_path)
                download_tasks.append(download_task)

            # Wait for all download tasks to complete
            print("Downloading images...")
            app.title("Downloading images...")
            for download_task in download_tasks:
                download_task.result()

            if file_PDF_fast.get() == 1:
                output_folder = os.path.join(path, str(manga_title), "PDF (Fast)")
                os.makedirs(output_folder, exist_ok=True)
                output_pdf_path = os.path.join(output_folder, f"Chapter {chapter_num} - {manga_title}.pdf")
                convert_images_to_pdf_fast(image_folder, output_pdf_path, chapter_title, chapter_num)

            if file_PDF_slow.get() == 1:
                output_folder = os.path.join(path, str(manga_title), "PDF (Slow)")
                os.makedirs(output_folder, exist_ok=True)
                output_pdf_path = os.path.join(output_folder, f"Chapter {chapter_num} - {manga_title}.pdf")
                convert_images_to_pdf_slow(image_folder, output_pdf_path, chapter_title, chapter_num)

            if file_CBZ.get() == 1:
                output_folder = os.path.join(path, str(manga_title), "CBZ")
                os.makedirs(output_folder, exist_ok=True)

                output_cbz_path = os.path.join(output_folder, f"Chapter {chapter_num} - {manga_title}.cbz")
                convert_images_to_cbz(image_folder, output_cbz_path, chapter_title, chapter_num)
        print("Finished!")
        app.title("Finished!")

    except Exception as e:
        print("Error:", e)

def get_manga_title_from_chapter(chapter_id):
    chapter_url = f"https://api.mangadex.org/chapter/{chapter_id}"
    headers = {
        "Accept": "application/vnd.api+json",
    }

    response = requests.get(chapter_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        for relationship in data["data"]["relationships"]:
            if relationship["type"] == "manga":
                manga_id = relationship["id"]
                break
        manga_title = get_manga_title(manga_id)
        chapter_title = data["data"]["attributes"]["title"]
        chapter_num = data["data"]["attributes"]["chapter"]
        return manga_title, chapter_title, chapter_num
    else:
        print(f"Error: {response.status_code}")
        return None

def get_manga_title(manga_id):
    manga_url = f"https://api.mangadex.org/manga/{manga_id}"
    headers = {
        "Accept": "application/vnd.api+json",
    }

    response = requests.get(manga_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        try:
            title = data["data"]["attributes"]["title"]["en"]
            return title
        except:
            title = data["data"]["attributes"]["title"]["ja-ro"]
            return title
    else:
        print(f"Error: {response.status_code}")
        return None
    
def get_chapter_list(manga_id, limit=500, offset=0, translatedLanguage="en", contentRating=["safe", "suggestive", "erotica", "pornographic"]):
    chapter_list = []

    url = f"https://api.mangadex.org/manga/{manga_id}/feed"
    headers = {
        "Accept": "application/vnd.api+json",
    }
    params = {
        "limit": limit,
        "offset": offset,
        "translatedLanguage[]": translatedLanguage,
        "contentRating[]": contentRating
    }

    seen_chapters = set()  # Keep track of seen chapter_num values

    while url:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()

            # Extract chapter IDs and add them to the chapter_list
            chapters_data = data.get("data", [])
            for chapter_data in chapters_data:
                chapter_id = chapter_data.get("id")
                chapter_num = chapter_data.get("attributes", {}).get("chapter")

                # Skip chapter if the same chapter_num has already been seen
                if chapter_num in seen_chapters:
                    continue

                chapter_list.append((chapter_id, chapter_num))
                seen_chapters.add(chapter_num)

            # Check if there are more pages to fetch
            next_page = data.get("links", {}).get("next")
            if next_page:
                url = next_page
            else:
                break

        else:
            print(f"Error: {response.status_code}")
            app.title("Something went wrong...")
            break

    # Sort chapter_list based on chapter number
    chapter_list.sort(key=lambda x: float(x[1]))

    # Extract sorted chapter IDs
    chapter_list = [chapter[0] for chapter in chapter_list]

    return chapter_list
      
def convert_images_to_pdf_fast(folder_path, output_path, chapter_title, chapter_num):

    print("Creating pdf (fast)...")
    app.title("Creating pdf (fast)...")
    
    image_files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

    image_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

    if chapter_title:
        ctitle=f"{chapter_title} - Chapter {chapter_num}"
    else:
        ctitle=f"{chapter_num}"

    images = []
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        img = PIL.Image.open(image_path)

        img.thumbnail((img.width, img.height))
        images.append(img)

    images[0].save(
        output_path,
        "PDF",
        resolution =100,
        save_all=True,
        append_images=images[1:],
        compress_level=0,
        title=ctitle
    )

    print(f"PDF created successfully at: {output_path}")

def convert_images_to_pdf_slow(folder_path, output_path, chapter_title, chatpter_num):

    print("Creating pdf (slow)...")
    app.title("Creating pdf (slow)...")

    image_files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

    image_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

    c = canvas.Canvas(output_path, pagesize=letter)

    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        img = PIL.Image.open(image_path)

        if file_PDF_slow.get() == 1:
            aspect_ratio = img.width / float(img.height)

            width = letter[0]
            height = width / aspect_ratio
    
            c.setPageSize((width, height))
            c.drawImage(image_path, 0, 0, width, height)
            c.showPage()

    if chapter_title:
        c.setTitle(chapter_title)
    else:
        c.setTitle(chatpter_num)
    c.save()

    print(f"PDF created successfully at: {output_path}")

def convert_images_to_cbz(folder_path, output_path, chapter_title, chapter_num):
    print("Creating CBZ...")
    app.title("Creating CBZ...")

    image_files = [f for f in glob.glob(os.path.join(folder_path, '*.png'))] + \
                  [f for f in glob.glob(os.path.join(folder_path, '*.jpg'))] + \
                  [f for f in glob.glob(os.path.join(folder_path, '*.jpeg'))]

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
        for image_file in image_files:
            cbz_file.write(image_file, os.path.basename(image_file))

    print(f"CBZ created successfully at: {output_path}")

app = customtkinter.CTk()
app.title(path)
app.resizable(width=False, height=False)
app.geometry(f"{600}x{200}")
app.iconbitmap("Icon/nerd.ico")

app.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
app.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)

file_PDF_fast = customtkinter.CTkSwitch(app, text="PDF (fast)", progress_color=("#ffed9c"))
file_PDF_fast.grid(row=0, column=0, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_PDF_slow = customtkinter.CTkSwitch(app, text="PDF (slow)", progress_color=("#ffed9c"))
file_PDF_slow.grid(row=0, column=1, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_CBZ = customtkinter.CTkSwitch(app, text="CBZ", progress_color=("#ffed9c"))
file_CBZ.grid(row=0, column=2, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

entry = customtkinter.CTkEntry(app, placeholder_text="Enter manga/chapter id...")
entry.grid(row=3, column=0, columnspan=3, padx=(20, 0), pady=(0, 20), sticky="swe")

main_button_1 = customtkinter.CTkButton(master=app, text="Change Directory", fg_color="transparent", hover_color=("#242323"), border_width=2, command=ChangeDirec)
main_button_1.grid(row=0, column=3, padx=(20, 0), pady=(10, 20), sticky="n")

main_button_2 = customtkinter.CTkButton(master=app, fg_color="transparent", text="Go!", hover_color=("#242323"), border_width=2, command=get_chap_id)
main_button_2.grid(row=3, column=3, padx=(20, 20), pady=(0, 20), sticky="se")

main_button_3 = customtkinter.CTkButton(master=app, fg_color="transparent", text="Batch", hover_color=("#242323"), border_width=2, command=batchUrlToImg)
main_button_3.grid(row=2, column=3, padx=(20, 20), pady=(0, 20), sticky="se")

# RUN APP
app.mainloop()