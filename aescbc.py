import cv2
import numpy as np
from tkinter import *
from tkinter import simpledialog
from PIL import Image, ImageTk
import face_recognition
import os
import json
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

# Direktori untuk menyimpan data
DATA_DIR = "biometric_data"
os.makedirs(DATA_DIR, exist_ok=True)

data_file = os.path.join(DATA_DIR, "users.json")

# Buat atau gunakan kunci enkripsi (panjang 32 byte untuk AES-256)
key_file = os.path.join(DATA_DIR, "key.key")
if not os.path.exists(key_file):
    key = os.urandom(32)  # Panjang 32 byte
    with open(key_file, "wb") as f:
        f.write(key)
else:
    with open(key_file, "rb") as f:
        key = f.read()

# Fungsi untuk mengenkripsi data menggunakan AES CBC
def encrypt_data_aes(data, key):
    iv = os.urandom(16)  # Inisialisasi vector 16-byte
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Padding data agar kelipatan 16-byte
    padding_length = 16 - (len(data) % 16)
    data += chr(padding_length) * padding_length
    
    encrypted_data = encryptor.update(data.encode()) + encryptor.finalize()
    return iv + encrypted_data  # Gabungkan IV dengan data terenkripsi

# Fungsi untuk mendekripsi data menggunakan AES CBC
def decrypt_data_aes(encrypted_data, key):
    iv = encrypted_data[:16]  # Ambil IV dari 16 byte pertama
    data = encrypted_data[16:]  # Data terenkripsi setelah IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    decrypted_data = decryptor.update(data) + decryptor.finalize()
    
    # Hapus padding
    padding_length = decrypted_data[-1]
    return decrypted_data[:-padding_length].decode()

# Fungsi untuk memuat data pengguna
def load_users():
    if os.path.exists(data_file):
        with open(data_file, "rb") as f:
            encrypted_data = f.read()
        try:
            json_data = decrypt_data_aes(encrypted_data, key)
            return json.loads(json_data)  # Parse JSON
        except Exception as e:
            print(f"Error: {e}")
            return {}
    return {}

# Fungsi untuk menyimpan data pengguna
def save_users(users):
    json_data = json.dumps(users)  # Konversi ke JSON
    encrypted_data = encrypt_data_aes(json_data, key)  # Enkripsi data sebelum disimpan
    with open(data_file, "wb") as f:
        f.write(encrypted_data)

# Inisialisasi database pengguna
users = load_users()

def register_user(frame, student_id):
    # Periksa apakah ID sudah terdaftar
    if student_id in users:
        print(f"ID {student_id} sudah terdaftar. Tidak dapat mendaftar ulang.")
        return False

    face_encodings = face_recognition.face_encodings(frame)
    if face_encodings:
        for encoding in face_encodings:
            for saved_id, saved_encoding in users.items():
                match = face_recognition.compare_faces([np.array(saved_encoding)], encoding)
                if match[0]:
                    print(f"Wajah sudah terdaftar dengan ID {saved_id}.")
                    return False
            
            # Simpan wajah pengguna baru
            users[student_id] = encoding.tolist()
            save_users(users)
            print(f"Pengguna dengan ID {student_id} berhasil didaftarkan.")
            return True
    else:
        print("Wajah tidak terdeteksi. Pastikan wajah terlihat jelas.")
        return False

# Fungsi untuk mencocokkan wajah
def match_face(frame):
    face_encodings = face_recognition.face_encodings(frame)
    if face_encodings:
        matched_ids = []
        for encoding in face_encodings:
            for student_id, saved_encoding in users.items():
                matches = face_recognition.compare_faces([np.array(saved_encoding)], encoding)
                if matches[0]:
                    matched_ids.append(student_id)  # Tambahkan ID yang cocok
        if matched_ids:
            return matched_ids  # Kembalikan ID pengguna yang cocok
    return None

# Fungsi untuk memulai proses registrasi
def start_registration():
    global student_id
    student_id = simpledialog.askstring("Pendaftaran", "Masukkan ID Mahasiswa:")
    if student_id:
        ret, frame = video_capture.read()
        if ret:
            success = register_user(frame, student_id)
            if success:
                print(f"Pendaftaran berhasil untuk {student_id}.")
            else:
                print("Pendaftaran gagal.")

# Fungsi untuk memulai proses absensi
def start_attendance():
    ret, frame = video_capture.read()
    if ret:
        matched_ids = match_face(frame)
        if matched_ids:
            for student_id in matched_ids:
                log_attendance(student_id)
            print(f"Absensi tercatat untuk {', '.join(matched_ids)}.")
        else:
            print("Wajah tidak dikenali. Silakan coba lagi.")

# Fungsi untuk mencatat absensi
def log_attendance(student_id):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = os.path.join(DATA_DIR, "attendance_log.txt")
    with open(log_file, "a") as f:
        f.write(f"{student_id},{timestamp}\n")
    print(f"Absensi tercatat untuk {student_id} pada {timestamp}.")

# Fungsi untuk menghapus pengguna berdasarkan ID
def delete_user(student_id):
    if student_id in users:
        del users[student_id]  # Hapus data pengguna
        save_users(users)  # Simpan data setelah dihapus
        print(f"Pengguna dengan ID {student_id} telah dihapus.")
    else:
        print(f"Pengguna dengan ID {student_id} tidak ditemukan.")

# Fungsi untuk menghapus pengguna berdasarkan pilihan ID
def prompt_delete_user():
    student_id = simpledialog.askstring("Hapus Pengguna", "Masukkan ID Pengguna yang ingin dihapus:")
    if student_id:
        delete_user(student_id)

# Fungsi untuk menghapus seluruh data pengguna
def delete_all_users():
    global users
    users = {}  # Kosongkan data pengguna
    save_users(users)  # Simpan data kosong
    print("Seluruh data pengguna telah dihapus.")

# Inisialisasi GUI
root = Tk()
root.title("Sistem Absensi Berbasis Biometrik")

video_capture = cv2.VideoCapture(0)
if not video_capture.isOpened():
    exit()

img_label = Label(root, text="Menunggu kamera...", width=600, height=400)
img_label.grid(row=0, column=0, padx=50, pady=50)

register_button = Button(root, text="Daftar Wajah", command=start_registration)
register_button.grid(row=1, column=0, padx=10, pady=10)

attendance_button = Button(root, text="Mulai Absen", command=start_attendance)
attendance_button.grid(row=2, column=0, padx=10, pady=10)

delete_button = Button(root, text="Hapus Pengguna", command=prompt_delete_user)
delete_button.grid(row=3, column=0, padx=10, pady=10)

# Tampilkan frame dari kamera
def show_frame():
    ret, frame = video_capture.read()
    if ret:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img = img.resize((640, 480))
        img_tk = ImageTk.PhotoImage(img)

        img_label.config(image=img_tk)
        img_label.image = img_tk

    img_label.after(10, show_frame)

show_frame()

root.mainloop()

video_capture.release()
cv2.destroyAllWindows()
