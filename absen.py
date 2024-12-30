import cv2
import numpy as np
from tkinter import *
from tkinter import simpledialog
from tkinter import filedialog
from PIL import Image, ImageTk
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os
from datetime import datetime

# Kunci AES 128-bit
key = b'16byte_secretkey'

# Variabel global
capture_taken = False
captured_face_path = "captured_face.jpg"
encrypted_file_path = "encrypted_face.bin"
decrypted_face_path = "decrypted_face.jpg"
video_capture = None
student_id = None
attendance_db = "attendance_log.txt"  # Nama file database absensi

# Fungsi enkripsi
def encrypt_image(image_path, key):
    with open(image_path, 'rb') as f:
        data = f.read()

    cipher = AES.new(key, AES.MODE_CBC)
    padded_data = pad(data, AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)

    encrypted_image = cipher.iv + encrypted_data
    return encrypted_image

# Fungsi dekripsi
def decrypt_image(encrypted_data, key):
    iv = encrypted_data[:16]
    encrypted_content = encrypted_data[16:]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_content), AES.block_size)

    with open(decrypted_face_path, 'wb') as f:
        f.write(decrypted_data)
    return decrypted_face_path

# Fungsi deteksi wajah
def detect_faces(frame):
    global capture_taken

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Ukuran minimum untuk wajah (batas jarak tertentu)
    min_face_size = 100

    for (x, y, w, h) in faces:
        if w < min_face_size or h < min_face_size:
            continue  # Abaikan wajah kecil

        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    return frame

# Enkripsi dan simpan hasil deteksi wajah
def encrypt_and_save(image_path, student_id):
    encrypted_image = encrypt_image(image_path, key)
    encrypted_image_path = f"encrypted_faces/{student_id}_encrypted.bin"

    # Pastikan folder untuk menyimpan file terenkripsi ada
    os.makedirs("encrypted_faces", exist_ok=True)

    with open(encrypted_image_path, "wb") as f:
        f.write(encrypted_image)

# Tampilkan frame dari kamera
def show_frame():
    global capture_taken
    ret, frame = video_capture.read()

    if not ret:
        return

    frame = detect_faces(frame)

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    img = img.resize((640, 480))
    img_tk = ImageTk.PhotoImage(img)

    img_label.config(image=img_tk)
    img_label.image = img_tk

    img_label.after(10, show_frame)

# Fungsi hitung mundur sebelum capture
def countdown_before_capture():
    global capture_taken
    capture_taken = False  # Reset status capture

    countdown(5)

def countdown(count):
    if count == 0:
        capture_face()
    else:
        img_label.config(text=f"Menangkap dalam {count} detik...", font=("Arial", 20))
        root.after(1000, countdown, count - 1)  # Lakukan hitung mundur setiap detik

# Fungsi untuk memulai capture
def start_capture():
    global student_id
    student_id = simpledialog.askstring("ID Mahasiswa", "Masukkan ID Mahasiswa:")
    if student_id:
        countdown_before_capture()
        capture_taken = False  # Reset capture status

# Fungsi untuk melakukan capture jika waktunya sudah tiba
def capture_face():
    global capture_taken
    if student_id and not capture_taken:
        ret, frame = video_capture.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            for (x, y, w, h) in faces:
                if w >= 100 and h >= 100:
                    face_image = frame[y:y+h, x:x+w]
                    cv2.imwrite(captured_face_path, face_image)
                    encrypt_and_save(captured_face_path, student_id)
                    log_attendance()  # Log attendance setelah capture wajah
                    capture_taken = True
                    break

# Aksi dekripsi
def decrypt_action():
    if student_id:
        encrypted_file_path = f"encrypted_faces/{student_id}_encrypted.bin"
        if os.path.exists(encrypted_file_path):
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()

            decrypted_image_path = decrypt_image(encrypted_data, key)
            load_image(decrypted_image_path)
    else:
        print("ID mahasiswa tidak valid.")

# Aksi dekripsi dengan pilihan file
def decrypt_action_with_file_selection():
    global student_id
    encrypted_file_path = filedialog.askopenfilename(
        title="Pilih File Enkripsi",
        filetypes=[("Binary Files", "*.bin")]
    )

    if encrypted_file_path:  # Jika file dipilih
        try:
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()

            decrypted_image_path = decrypt_image(encrypted_data, key)
            load_image(decrypted_image_path)
            print(f"File berhasil didekripsi dan ditampilkan: {decrypted_image_path}")
        except Exception as e:
            print(f"Kesalahan saat mendekripsi file: {e}")
    else:
        print("Tidak ada file yang dipilih untuk dekripsi.")
        
# Fungsi untuk mencatat absensi
def log_attendance():
    global student_id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Waktu absen
    if student_id:
        with open(attendance_db, "a") as f:
            f.write(f"{student_id},{timestamp},{captured_face_path}\n")
        print(f"Absensi untuk mahasiswa {student_id} tercatat pada {timestamp}.")

# Tampilkan gambar
def load_image(image_path):
    try:
        img = Image.open(image_path)
        img = img.resize((600, 400))
        img = ImageTk.PhotoImage(img)
        img_label.config(image=img)
        img_label.image = img
    except Exception as e:
        img_label.config(text="Gambar tidak dapat dibuka.")

# Inisialisasi GUI
root = Tk()
root.title("Sistem Absen Mahasiswa dengan Deteksi Wajah dan AES 128")

video_capture = cv2.VideoCapture(0)

if not video_capture.isOpened():
    exit()

img_label = Label(root, text="Menunggu kamera...", width=600, height=400)
img_label.grid(row=0, column=0, padx=50, pady=50)

start_button = Button(root, text="Mulai Absen", command=start_capture)
start_button.grid(row=1, column=0, padx=10, pady=10)

decrypt_button_with_file = Button(root, text="Dekripsi Pilih File", command=decrypt_action_with_file_selection)
decrypt_button_with_file.grid(row=4, column=0, padx=10, pady=10)

# Mulai deteksi wajah real-time
show_frame()

root.mainloop()

video_capture.release() 
cv2.destroyAllWindows()
