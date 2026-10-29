import csv
import os
import sqlite3
import time
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import customtkinter as ctk
except ImportError:
    raise SystemExit("Install CustomTkinter: pip install customtkinter")

try:
    import cv2
except ImportError:
    raise SystemExit("Install OpenCV: pip install opencv-contrib-python")

import database


# -------------------- THEME --------------------
CREAM = "#F6F0E6"
CREAM_DARK = "#E9DFCF"
WHITE = "#FFFFFF"
NAVY = "#0B1F3A"
NAVY_2 = "#143B63"
BLUE = "#1E5A91"
BLUE_HOVER = "#174A78"
TEXT = "#162334"
MUTED = "#6D7B8C"
BORDER = "#D9D2C7"
GREEN = "#238B5A"
ORANGE = "#C87922"
RED = "#B83A3A"
LIGHT_BLUE = "#EAF2FB"
LIGHT_GREEN = "#EAF7EF"
LIGHT_ORANGE = "#FFF4E4"
LIGHT_RED = "#FDEEEE"
SOFT_NAVY = "#EEF3F8"
PANEL = "#F8FAFC"

FACES_DIR = Path(__file__).resolve().parent / "faces"
ATTENDANCE_DIR = Path(__file__).resolve().parent / "attendance"
MODEL_FILE = Path(__file__).resolve().parent / "face_model.yml"
FACES_DIR.mkdir(exist_ok=True)
ATTENDANCE_DIR.mkdir(exist_ok=True)

SAMPLE_TARGET = 40
FACE_SIZE = (200, 200)
# Stricter recognition settings to reduce false matches.
RECOGNITION_THRESHOLD = 52.0
RECOGNITION_MARGIN = 8.0
DUPLICATE_FACE_THRESHOLD = 48.0
DUPLICATE_MIN_MATCHES = 10
DUPLICATE_MATCH_RATIO = 0.35
STABLE_MATCH_FRAMES = 7
ATTENDANCE_COOLDOWN = 8.0


def safe_filename(value):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SBBSU | Face Attendance System")
        self.geometry("1280x760")
        self.minsize(1100, 680)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.entries = {}
        self.selected_student_id = None
        self.clock_var = tk.StringVar()
        self.current_page = "Login"
        self.last_attendance_date = datetime.now().strftime("%Y-%m-%d")
        self.login()

    # -------------------- LOGIN --------------------
    def login(self):
        self.login_frame = ctk.CTkFrame(self, fg_color=CREAM, corner_radius=0)
        self.login_frame.pack(fill="both", expand=True)

        left = ctk.CTkFrame(self.login_frame, fg_color=NAVY, corner_radius=0, width=510)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ctk.CTkLabel(
            left, text="SBBSU", font=("Segoe UI Black", 48), text_color=WHITE
        ).pack(anchor="w", padx=55, pady=(150, 0))
        ctk.CTkLabel(
            left, text="FACE ATTENDANCE", font=("Segoe UI Bold", 20), text_color="#DCE8F4"
        ).pack(anchor="w", padx=58, pady=(4, 0))
        ctk.CTkLabel(
            left,
            text="Student identification • Face registration •\nAutomatic attendance",
            font=("Segoe UI", 12), text_color="#AFC3D8", justify="left"
        ).pack(anchor="w", padx=58, pady=(18, 0))

        right = ctk.CTkFrame(self.login_frame, fg_color=CREAM, corner_radius=0)
        right.pack(side="right", fill="both", expand=True)

        card = ctk.CTkFrame(
            right, fg_color=WHITE, corner_radius=18,
            border_width=1, border_color=BORDER, width=430, height=420
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(
            card, text="Administrator Login",
            font=("Segoe UI Bold", 25), text_color=TEXT
        ).pack(anchor="w", padx=42, pady=(45, 5))
        ctk.CTkLabel(
            card, text="Sign in to manage attendance",
            font=("Segoe UI", 11), text_color=MUTED
        ).pack(anchor="w", padx=42, pady=(0, 30))

        ctk.CTkLabel(card, text="Username", font=("Segoe UI Semibold", 11), text_color=TEXT).pack(
            anchor="w", padx=42, pady=(0, 5)
        )
        self.user_entry = ctk.CTkEntry(
            card, height=42, corner_radius=8, border_color=BORDER,
            placeholder_text="Enter username"
        )
        self.user_entry.pack(fill="x", padx=42)

        ctk.CTkLabel(card, text="Password", font=("Segoe UI Semibold", 11), text_color=TEXT).pack(
            anchor="w", padx=42, pady=(18, 5)
        )
        self.pass_entry = ctk.CTkEntry(
            card, height=42, corner_radius=8, show="●", border_color=BORDER,
            placeholder_text="Enter password"
        )
        self.pass_entry.pack(fill="x", padx=42)

        self.show_password_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="Show password", variable=self.show_password_var,
                           command=self.toggle_password, font=("Segoe UI", 9), text_color=MUTED).pack(
            anchor="w", padx=42, pady=(7, 0)
        )

        ctk.CTkButton(
            card, text="SIGN IN", height=44, corner_radius=9,
            fg_color=NAVY, hover_color=NAVY_2,
            font=("Segoe UI Bold", 12), command=self.do_login
        ).pack(fill="x", padx=42, pady=(25, 0))

        ctk.CTkLabel(
            card, text="Enter your login credentials to continue",
            font=("Segoe UI", 9), text_color=MUTED
        ).pack(pady=(12, 0))

        self.user_entry.focus_set()
        self.bind("<Return>", lambda e: self.do_login())

    def toggle_password(self):
        self.pass_entry.configure(show="" if self.show_password_var.get() else "●")

    def do_login(self):
        if self.user_entry.get().strip() == "amitjamwal" and self.pass_entry.get() == "amit2729":
            self.unbind("<Return>")
            self.login_frame.destroy()
            self.build_main()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    # -------------------- MAIN LAYOUT --------------------
    def build_main(self):
        self.configure(fg_color=CREAM)

        self.sidebar = ctk.CTkFrame(self, width=235, fg_color=NAVY, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main = ctk.CTkFrame(self, fg_color=CREAM, corner_radius=0)
        self.main.pack(side="right", fill="both", expand=True)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(30, 30))
        logo_row = ctk.CTkFrame(brand, fg_color="transparent")
        logo_row.pack(fill="x")
        ctk.CTkLabel(logo_row, text="S", width=42, height=42, corner_radius=12,
                     fg_color=BLUE, text_color=WHITE, font=("Segoe UI Black", 22)).pack(side="left")
        logo_text = ctk.CTkFrame(logo_row, fg_color="transparent")
        logo_text.pack(side="left", padx=10)
        ctk.CTkLabel(logo_text, text="SBBSU", font=("Segoe UI Black", 24), text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(logo_text, text="Face Attendance", font=("Segoe UI", 10), text_color="#B7C8D9").pack(anchor="w")

        ctk.CTkLabel(brand, text="SMART CAMPUS • ADMIN PANEL", font=("Segoe UI Bold", 8),
                     text_color="#7890A8").pack(anchor="w", pady=(16,0))

        self.nav_buttons = {}
        self.add_nav("⌂", "Dashboard", self.show_dashboard)
        self.add_nav("▣", "Students", self.show_students)
        self.add_nav("◉", "Face Registration", self.show_face_registration)
        self.add_nav("✓", "Attendance", self.show_attendance)
        self.add_nav("▤", "Reports", self.show_reports)

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#29425F").pack(fill="x", padx=20, pady=22)
        ctk.CTkLabel(
            self.sidebar, text="SYSTEM", font=("Segoe UI Bold", 9), text_color="#8096AD"
        ).pack(anchor="w", padx=25, pady=(0, 8))
        self.add_nav("⚙", "Settings", self.show_settings)

        ctk.CTkButton(
            self.sidebar, text="LOGOUT", height=38, fg_color="#17324F",
            hover_color="#244A70", font=("Segoe UI Bold", 10),
            command=self.logout
        ).pack(side="bottom", fill="x", padx=22, pady=24)

        self.topbar = ctk.CTkFrame(
            self.main, height=78, fg_color=WHITE, corner_radius=0,
            border_width=0
        )
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        title_wrap = ctk.CTkFrame(self.topbar, fg_color="transparent")
        title_wrap.pack(side="left", padx=28, pady=10)
        self.page_title = ctk.CTkLabel(
            title_wrap, text="Dashboard", font=("Segoe UI Bold", 21), text_color=TEXT
        )
        self.page_title.pack(anchor="w")
        ctk.CTkLabel(title_wrap, text="SBBSU • Student & Attendance Management",
                     font=("Segoe UI", 8), text_color=MUTED).pack(anchor="w")

        clock_card = ctk.CTkFrame(self.topbar, fg_color=SOFT_NAVY, corner_radius=10)
        clock_card.pack(side="right", padx=24, pady=17)
        ctk.CTkLabel(clock_card, text="●  SYSTEM TIME", font=("Segoe UI Bold", 8), text_color=GREEN).pack(side="left", padx=(10,4), pady=7)
        self.clock_label = ctk.CTkLabel(
            clock_card, textvariable=self.clock_var,
            font=("Segoe UI Semibold", 10), text_color=TEXT
        )
        self.clock_label.pack(side="left", padx=(0,10))

        self.after(100, self.update_clock)
        self.after(1500, self.check_attendance_date_rollover)
        self.show_dashboard()

    def add_nav(self, icon, text, command):
        btn = ctk.CTkButton(
            self.sidebar, text=f"  {icon}    {text}", anchor="w",
            height=46, corner_radius=10, fg_color="transparent",
            hover_color="#17324F", text_color="#D7E3EE",
            font=("Segoe UI Semibold", 11), command=command
        )
        btn.pack(fill="x", padx=15, pady=3)
        self.nav_buttons[text] = btn

    def set_active(self, active):
        for name, btn in self.nav_buttons.items():
            btn.configure(fg_color="#1F5D91" if name == active else "transparent",
                          text_color=WHITE if name == active else "#D7E3EE")

    def update_clock(self):
        if self.winfo_exists():
            self.clock_var.set(datetime.now().strftime("%d %b %Y   •   %I:%M:%S %p"))
            self.after(1000, self.update_clock)

    def check_attendance_date_rollover(self):
        """Automatically refresh today's attendance after midnight."""
        if not self.winfo_exists():
            return

        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.last_attendance_date:
            self.last_attendance_date = today
            if self.current_page == "Attendance":
                self.show_attendance()
            elif self.current_page == "Dashboard":
                self.show_dashboard()

        self.after(15000, self.check_attendance_date_rollover)

    def clear_page(self):
        for widget in self.main.winfo_children():
            if widget is not self.topbar:
                widget.destroy()

    def page(self, title):
        self.clear_page()
        self.page_title.configure(text=title)
        frame = ctk.CTkScrollableFrame(self.main, fg_color=CREAM, corner_radius=0)
        frame.pack(fill="both", expand=True, padx=22, pady=20)
        return frame

    # -------------------- DASHBOARD --------------------
    def show_dashboard(self):
        self.current_page = "Dashboard"
        self.last_attendance_date = datetime.now().strftime("%Y-%m-%d")
        self.set_active("Dashboard")
        page = self.page("Dashboard")

        hero = ctk.CTkFrame(page, fg_color=NAVY, corner_radius=18)
        hero.pack(fill="x", padx=8, pady=(0, 16))
        hero_left = ctk.CTkFrame(hero, fg_color="transparent")
        hero_left.pack(side="left", fill="x", expand=True, padx=24, pady=20)
        ctk.CTkLabel(hero_left, text="Attendance Command Center", font=("Segoe UI Bold", 25), text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(hero_left, text="Manage students, face registration and daily attendance from one place.",
                     font=("Segoe UI", 10), text_color="#C5D5E5").pack(anchor="w", pady=(4,0))
        ctk.CTkLabel(hero, text="●  SYSTEM READY", font=("Segoe UI Bold", 9), text_color="#75E3A8",
                     fg_color="#17324F", corner_radius=10, width=125, height=30).pack(side="right", padx=24, pady=20)

        cards = ctk.CTkFrame(page, fg_color="transparent")
        cards.pack(fill="x", padx=4)
        today_present = database.attendance_count_today()
        today_absent = max(0, database.active_student_count() - today_present)
        values = [
            ("TOTAL STUDENTS", database.student_count(), BLUE, "All student profiles"),
            ("ACTIVE STUDENTS", database.active_student_count(), GREEN, "Currently active"),
            ("REGISTERED FACES", len(database.get_face_profiles()), NAVY_2, "Ready for recognition"),
            ("TODAY PRESENT", today_present, GREEN, "Attendance marked"),
            ("TODAY ABSENT", today_absent, RED, "Not marked yet"),
        ]
        for i, (label, value, accent, hint) in enumerate(values):
            card = ctk.CTkFrame(cards, fg_color=WHITE, corner_radius=14, border_width=1, border_color=BORDER)
            card.grid(row=0, column=i, sticky="ew", padx=6)
            cards.grid_columnconfigure(i, weight=1)
            ctk.CTkFrame(card, width=5, height=78, fg_color=accent, corner_radius=3).pack(side="left", padx=(16,13), pady=16)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", pady=14)
            ctk.CTkLabel(inner, text=label, font=("Segoe UI Bold", 8), text_color=MUTED).pack(anchor="w")
            ctk.CTkLabel(inner, text=str(value), font=("Segoe UI Black", 24), text_color=TEXT).pack(anchor="w")
            ctk.CTkLabel(inner, text=hint, font=("Segoe UI", 8), text_color=MUTED).pack(anchor="w")

        actions = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        actions.pack(fill="x", padx=10, pady=(20, 15))
        ctk.CTkLabel(actions, text="Quick Actions", font=("Segoe UI Bold", 16), text_color=TEXT).pack(anchor="w", padx=20, pady=(17,2))
        ctk.CTkLabel(actions, text="Choose what you want to do next", font=("Segoe UI", 9), text_color=MUTED).pack(anchor="w", padx=20, pady=(0,12))
        row = ctk.CTkFrame(actions, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0,18))
        quick = [("＋  ADD STUDENT", self.show_students, BLUE), ("◉  REGISTER FACE", self.show_face_registration, NAVY_2), ("✓  START ATTENDANCE", self.show_attendance, GREEN), ("▤  VIEW REPORTS", self.show_reports, ORANGE)]
        for text, cmd, color in quick:
            ctk.CTkButton(row, text=text, height=44, corner_radius=10, fg_color=color, hover_color=NAVY_2,
                          font=("Segoe UI Bold", 10), command=cmd).pack(side="left", fill="x", expand=True, padx=5)

        recent = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        recent.pack(fill="both", expand=True, padx=10, pady=5)
        head = ctk.CTkFrame(recent, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16,6))
        ctk.CTkLabel(head, text=f"Today's Attendance  •  {datetime.now().strftime('%d %b %Y')}",
                     font=("Segoe UI Bold", 16), text_color=TEXT).pack(side="left")
        ctk.CTkButton(head, text="↻  REFRESH", height=30, width=105, corner_radius=8,
                      fg_color=SOFT_NAVY, hover_color="#DCE7F2", text_color=NAVY,
                      font=("Segoe UI Bold", 8), command=self.show_dashboard).pack(side="right", padx=(8,0))
        ctk.CTkLabel(head, text=f"{database.attendance_count_today()} student(s) present", font=("Segoe UI Semibold", 9),
                     text_color=GREEN, fg_color=LIGHT_GREEN, corner_radius=8, padx=10, pady=5).pack(side="right")
        self.make_table(recent, columns=("student_id","name","roll","course","time","status"),
                        headings=("Student ID","Student Name","Roll No.","Course","Time","Status"),
                        rows=[(r["student_id"],r["name"],r["roll_no"],r["course"],r["attendance_time"],r["status"]) for r in database.attendance_today()], height=8)

    # -------------------- STUDENTS --------------------
    def show_students(self):
        self.set_active("Students")
        page = self.page("Students")

        # ---------- PAGE HEADER ----------
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.pack(fill="x", padx=8)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            title_box, text="Student Management",
            font=("Segoe UI Bold", 26), text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text="Add, update, search and manage complete student profiles.",
            font=("Segoe UI", 11), text_color=MUTED
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            header, text="＋  New Student", width=150, height=40,
            corner_radius=9, fg_color=NAVY, hover_color=NAVY_2,
            font=("Segoe UI Bold", 11), command=self.clear_form
        ).pack(side="right", pady=(2, 0))

        # ---------- MAIN CONTENT ----------
        body = ctk.CTkFrame(page, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=(16, 0))

        # ================================================================
        # LEFT: STUDENT FORM
        # ================================================================
        form = ctk.CTkFrame(
            body, fg_color=WHITE, corner_radius=16,
            border_width=1, border_color=BORDER, width=505
        )
        form.pack(side="left", fill="y", padx=(0, 14))
        form.pack_propagate(False)

        # Form title / status indicator
        form_head = ctk.CTkFrame(form, fg_color="transparent")
        form_head.pack(fill="x", padx=20, pady=(17, 10))

        head_left = ctk.CTkFrame(form_head, fg_color="transparent")
        head_left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            head_left, text="Student Details",
            font=("Segoe UI Bold", 18), text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            head_left,
            text="Fill the information below to create a complete profile.",
            font=("Segoe UI", 9), text_color=MUTED
        ).pack(anchor="w", pady=(2, 0))

        self.form_mode_label = ctk.CTkLabel(
            form_head, text="NEW",
            width=62, height=27, corner_radius=14,
            fg_color=LIGHT_BLUE, text_color=NAVY,
            font=("Segoe UI Bold", 9)
        )
        self.form_mode_label.pack(side="right", anchor="n", pady=2)

        fs = ctk.CTkScrollableFrame(
            form, fg_color="#FBFAF7", corner_radius=11,
            border_width=1, border_color="#EEE7DC"
        )
        fs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.entries = {}

        def section(parent, title, subtitle, accent):
            card = ctk.CTkFrame(
                parent, fg_color=WHITE, corner_radius=10,
                border_width=1, border_color=BORDER
            )
            card.pack(fill="x", padx=7, pady=(8, 5))
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(9, 5))
            ctk.CTkFrame(top, width=4, height=28, fg_color=accent, corner_radius=2).pack(
                side="left", padx=(0, 8)
            )
            text_box = ctk.CTkFrame(top, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                text_box, text=title,
                font=("Segoe UI Bold", 11), text_color=TEXT
            ).pack(anchor="w")
            ctk.CTkLabel(
                text_box, text=subtitle,
                font=("Segoe UI", 8), text_color=MUTED
            ).pack(anchor="w")
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=9, pady=(0, 9))
            content.grid_columnconfigure(0, weight=1)
            content.grid_columnconfigure(1, weight=1)
            return content

        def add_field(parent, row, col, key, label, ph, required=False):
            box = ctk.CTkFrame(parent, fg_color="transparent")
            box.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
            label_text = label + ("  *" if required else "")
            ctk.CTkLabel(
                box, text=label_text,
                font=("Segoe UI Semibold", 9),
                text_color=TEXT if not required else NAVY
            ).pack(anchor="w", pady=(0, 3))
            e = ctk.CTkEntry(
                box, height=35, corner_radius=7,
                border_color=BORDER, fg_color=WHITE,
                placeholder_text=ph
            )
            e.pack(fill="x")
            self.entries[key] = e
            return e

        # Basic identity
        c = section(fs, "1  Basic Identity", "Main student identification details", BLUE)
        add_field(c, 0, 0, "student_id", "Student ID", "STU001", True)
        add_field(c, 0, 1, "roll_no", "Roll Number", "e.g. 24BCS101", True)
        add_field(c, 1, 0, "name", "Student Name", "Full name", True)
        add_field(c, 1, 1, "father_name", "Father Name", "Father's name")

        # Academic information
        c = section(fs, "2  Academic Information", "Course, department and current session", NAVY_2)
        add_field(c, 0, 0, "department", "Department", "e.g. Computer Science")
        add_field(c, 0, 1, "course", "Course / Program", "e.g. BCA")
        add_field(c, 1, 0, "semester", "Semester", "e.g. 3rd")
        add_field(c, 1, 1, "academic_year", "Academic Year", "e.g. 2026-27")

        # Contact information
        c = section(fs, "3  Contact Information", "Student and emergency contact details", GREEN)
        add_field(c, 0, 0, "phone", "Phone Number", "10-digit mobile number")
        add_field(c, 0, 1, "alternate_phone", "Alternate Phone", "Optional")
        add_field(c, 1, 0, "email", "Email Address", "student@example.com")
        add_field(c, 1, 1, "guardian_name", "Guardian Name", "Parent / guardian")
        add_field(c, 2, 0, "guardian_phone", "Guardian Phone", "Emergency contact")
        add_field(c, 2, 1, "gender", "Gender", "Male / Female / Other")

        # Personal information
        c = section(fs, "4  Personal Information", "Personal and admission details", ORANGE)
        add_field(c, 0, 0, "dob", "Date of Birth", "DD-MM-YYYY")
        add_field(c, 0, 1, "blood_group", "Blood Group", "e.g. B+")
        add_field(c, 1, 0, "admission_date", "Admission Date", "DD-MM-YYYY")

        status_box = ctk.CTkFrame(c, fg_color="transparent")
        status_box.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkLabel(
            status_box, text="Student Status",
            font=("Segoe UI Semibold", 9), text_color=TEXT
        ).pack(anchor="w", pady=(0, 3))
        self.status_var = tk.StringVar(value="Active")
        ctk.CTkOptionMenu(
            status_box, variable=self.status_var,
            values=["Active", "Inactive", "Passed Out"],
            height=35, corner_radius=7,
            fg_color=NAVY, button_color=NAVY,
            button_hover_color=NAVY_2,
            dropdown_fg_color=WHITE,
            dropdown_hover_color=LIGHT_BLUE
        ).pack(fill="x")

        # Address
        c = section(fs, "5  Address", "Current residential address", RED)
        address_box = ctk.CTkFrame(c, fg_color="transparent")
        address_box.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        ctk.CTkLabel(
            address_box, text="Complete Address",
            font=("Segoe UI Semibold", 9), text_color=TEXT
        ).pack(anchor="w", pady=(0, 3))
        address_entry = ctk.CTkEntry(
            address_box, height=38, corner_radius=7,
            border_color=BORDER, fg_color=WHITE,
            placeholder_text="House / Street / Village / City / State"
        )
        address_entry.pack(fill="x")
        self.entries["address"] = address_entry

        # Help note
        ctk.CTkLabel(
            fs,
            text="* Required: Student ID, Roll Number and Student Name",
            font=("Segoe UI", 8), text_color=MUTED
        ).pack(anchor="w", padx=14, pady=(7, 3))

        # Action buttons
        btn_area = ctk.CTkFrame(form, fg_color="transparent")
        btn_area.pack(fill="x", padx=12, pady=(0, 13))

        ctk.CTkButton(
            btn_area, text="SAVE STUDENT", height=40, corner_radius=8,
            fg_color=GREEN, hover_color="#1C744B",
            font=("Segoe UI Bold", 10), command=self.save_student
        ).pack(fill="x", pady=(0, 6))

        action_row = ctk.CTkFrame(btn_area, fg_color="transparent")
        action_row.pack(fill="x")
        ctk.CTkButton(
            action_row, text="↻  UPDATE", height=36, corner_radius=8,
            fg_color=LIGHT_BLUE, hover_color="#D7E6F5",
            text_color=NAVY, font=("Segoe UI Bold", 9),
            command=self.update_student
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(
            action_row, text="✕  DELETE", height=36, corner_radius=8,
            fg_color="#FCECEC", hover_color="#F5D6D6",
            text_color=RED, font=("Segoe UI Bold", 9),
            command=self.delete_student
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ================================================================
        # RIGHT: STUDENT DIRECTORY
        # ================================================================
        right = ctk.CTkFrame(
            body, fg_color=WHITE, corner_radius=16,
            border_width=1, border_color=BORDER
        )
        right.pack(side="right", fill="both", expand=True)

        directory_head = ctk.CTkFrame(right, fg_color="transparent")
        directory_head.pack(fill="x", padx=20, pady=(17, 8))
        ctk.CTkLabel(
            directory_head, text="Student Directory",
            font=("Segoe UI Bold", 18), text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            directory_head,
            text="Select a student to view or edit their complete details.",
            font=("Segoe UI", 9), text_color=MUTED
        ).pack(anchor="w", pady=(2, 0))

        search_row = ctk.CTkFrame(right, fg_color="#F7F9FC", corner_radius=10)
        search_row.pack(fill="x", padx=18, pady=(3, 12))
        ctk.CTkLabel(
            search_row, text="⌕", font=("Segoe UI Bold", 17), text_color=BLUE
        ).pack(side="left", padx=(12, 2))
        self.student_search = ctk.CTkEntry(
            search_row, height=38, corner_radius=7,
            border_width=0, fg_color="transparent",
            placeholder_text="Search by ID, name, roll no., course or department..."
        )
        self.student_search.pack(side="left", fill="x", expand=True, padx=2, pady=4)
        ctk.CTkButton(
            search_row, text="SEARCH", width=92, height=34,
            corner_radius=7, fg_color=NAVY, hover_color=NAVY_2,
            font=("Segoe UI Bold", 9), command=self.refresh_student_table
        ).pack(side="right", padx=(4, 6), pady=4)

        # Small instruction strip
        info = ctk.CTkFrame(right, fg_color=LIGHT_BLUE, corner_radius=8)
        info.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkLabel(
            info,
            text="Tip: Click any student row → details load on the left → use UPDATE or DELETE.",
            font=("Segoe UI Semibold", 9), text_color=NAVY
        ).pack(anchor="w", padx=12, pady=8)

        table_wrap = ctk.CTkFrame(right, fg_color="transparent")
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.student_table = self.make_table(
            table_wrap,
            columns=("student_id", "name", "roll", "department", "course", "semester", "phone", "status"),
            headings=("Student ID", "Student Name", "Roll No.", "Department", "Course", "Sem.", "Phone", "Status"),
            rows=[],
            height=18
        )
        self.student_table.bind("<<TreeviewSelect>>", self.select_student)
        self.refresh_student_table()

    def clear_form(self):
        self.selected_student_id = None
        for e in getattr(self, "entries", {}).values():
            e.delete(0, "end")
        if hasattr(self, "status_var"):
            self.status_var.set("Active")
        if hasattr(self, "form_mode_label"):
            self.form_mode_label.configure(text="NEW", fg_color=LIGHT_BLUE, text_color=NAVY)

    def form_data(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        data["status"] = self.status_var.get()
        return data

    def save_student(self):
        data = self.form_data()
        if not data["student_id"] or not data["name"]:
            messagebox.showwarning("Required", "Student ID and Student Name are required.")
            return
        try:
            database.add_student(data)
            messagebox.showinfo("Saved", "Student added successfully.")
            self.clear_form()
            self.refresh_student_table()
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate Student ID", "This Student ID already exists. Please use a unique Student ID.")
        except Exception as exc:
            messagebox.showerror("Save Error", f"Unable to save student.\n\n{exc}")

    def update_student(self):
        if not self.selected_student_id:
            messagebox.showwarning("Select Student", "Select a student from the table first.")
            return

        data = self.form_data()
        if not data["student_id"] or not data["name"]:
            messagebox.showwarning("Required", "Student ID and Student Name are required.")
            return

        try:
            if database.update_student(self.selected_student_id, data):
                self.selected_student_id = data["student_id"]
                if hasattr(self, "form_mode_label"):
                    self.form_mode_label.configure(text="EDIT", fg_color="#FFF1DC", text_color=ORANGE)
                messagebox.showinfo(
                    "Student Updated",
                    f"{data['name']}\n\nStudent details have been updated successfully."
                )
                self.refresh_student_table()
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Duplicate Student ID",
                "This Student ID is already assigned to another student.\n\nPlease use a unique Student ID."
            )
        except Exception as exc:
            messagebox.showerror("Update Error", f"Unable to update student.\n\n{exc}")

    def delete_student(self):
        if not self.selected_student_id:
            messagebox.showwarning("Select Student", "Select a student from the table first.")
            return

        sid = self.selected_student_id
        row = database.get_student(sid)
        name = row["name"] if row else sid
        has_face = database.get_face_profile(sid) is not None

        warning = (
            f"Are you sure you want to delete this student?\n\n"
            f"Student: {name}\n"
            f"Student ID: {sid}\n\n"
            "This will remove the student record."
        )
        if has_face:
            warning += "\nTheir registered face data will also be removed."
        warning += "\n\nThis action cannot be undone."

        if not messagebox.askyesno("Confirm Student Deletion", warning, icon="warning"):
            return

        try:
            deleted = database.delete_student(sid)
            if not deleted:
                messagebox.showwarning("Not Found", "Student record was not found.")
                self.refresh_student_table()
                return

            # Remove this student's local face-training images as well.
            student_dir = FACES_DIR / safe_filename(sid)
            if student_dir.exists():
                for image_file in student_dir.glob("*.jpg"):
                    try:
                        image_file.unlink()
                    except OSError:
                        pass
                try:
                    student_dir.rmdir()
                except OSError:
                    pass

            # Rebuild the LBPH model so the deleted student's face is no longer recognized.
            try:
                if database.get_face_profiles():
                    self.train_model()
                elif MODEL_FILE.exists():
                    MODEL_FILE.unlink()
            except Exception:
                # Student deletion itself already succeeded; model can be rebuilt later.
                pass

            self.clear_form()
            self.refresh_student_table()
            messagebox.showinfo(
                "Student Deleted",
                f"{name} ({sid}) has been deleted successfully.\n\n"
                "Student record and registered face files were removed."
            )
        except Exception as exc:
            messagebox.showerror("Delete Error", f"Unable to delete student.\n\n{exc}")

    def select_student(self, event=None):
        if not self.student_table.selection():
            return
        values = self.student_table.item(self.student_table.selection()[0], "values")
        if not values:
            return
        sid = values[0]
        row = database.get_student(sid)
        if not row:
            return
        self.selected_student_id = sid
        if hasattr(self, "form_mode_label"):
            self.form_mode_label.configure(text="EDIT", fg_color="#FFF1DC", text_color=ORANGE)
        for key, e in self.entries.items():
            e.delete(0, "end")
            e.insert(0, row[key] or "")
        self.status_var.set(row["status"] or "Active")

    def refresh_student_table(self):
        if not hasattr(self, "student_table"):
            return
        search = self.student_search.get().strip() if hasattr(self, "student_search") else ""
        rows = database.get_students(search)
        self.fill_table(
            self.student_table,
            [(r["student_id"], r["name"], r["roll_no"], r["department"], r["course"],
              r["semester"], r["phone"], r["status"]) for r in rows]
        )

    # -------------------- CAMERA HELPERS --------------------
    def open_camera(self):
        """Open a Windows webcam using a verified, non-black frame.

        The project previously worked with DirectShow, so keep that backend as
        the primary path instead of silently switching to MSMF. Some Windows
        webcam drivers return a valid-looking but completely black frame when
        the wrong pixel format/resolution is negotiated. We therefore try a
        few safe modes and reject frames that are effectively black.
        """
        configured = self.get_camera_index()
        indexes = [configured] + [i for i in (0, 1, 2, 3) if i != configured]

        # DirectShow is the backend that was verified to deliver frames on this
        # machine. CAP_ANY is only a final fallback.
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
        modes = [(640, 480), (1280, 720), (800, 600)]

        for index in indexes:
            for backend in backends:
                for width, height in modes:
                    cap = None
                    try:
                        cap = cv2.VideoCapture(index, backend)
                        if not cap.isOpened():
                            if cap is not None:
                                cap.release()
                            continue

                        # MJPG is important for many USB webcams on Windows.
                        # If unsupported, OpenCV simply keeps the driver's mode.
                        try:
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                        except Exception:
                            pass
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        try:
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        except Exception:
                            pass

                        # Throw away startup frames. Many cameras need a short
                        # warm-up after VideoCapture() before exposing an image.
                        good_frame = None
                        for _ in range(20):
                            ok, frame = cap.read()
                            if ok and frame is not None and getattr(frame, "size", 0) > 0:
                                # Reject an all/near-black frame. A real webcam
                                # image will have measurable pixel variation.
                                gray_probe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                                mean = float(gray_probe.mean())
                                std = float(gray_probe.std())
                                if mean > 3.0 and std > 2.0:
                                    good_frame = frame
                                    break
                            time.sleep(0.05)

                        if good_frame is not None:
                            return cap, index

                        cap.release()
                    except Exception:
                        if cap is not None:
                            try:
                                cap.release()
                            except Exception:
                                pass

        raise RuntimeError(
            "Camera opened but did not provide a usable image. "
            "Close Camera/Teams/Zoom, check Windows Camera permission, "
            "and try Camera Index 1 in Settings if another webcam is connected."
        )

    @staticmethod
    def prepare_camera_window(name):
        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(name, 960, 720)
        cv2.waitKey(30)

    @staticmethod
    def close_camera_window(name):
        try:
            cv2.destroyWindow(name)
        except cv2.error:
            pass
        cv2.destroyAllWindows()
        cv2.waitKey(30)

    # -------------------- FACE REGISTRATION --------------------
    def show_face_registration(self):
        self.set_active("Face Registration")
        page = self.page("Face Registration")

        hero = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        hero.pack(fill="x", padx=8, pady=(0,15))
        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=22, pady=17)
        ctk.CTkLabel(left, text="Face Registration", font=("Segoe UI Bold", 24), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Register a student's face before automatic attendance can recognize them.",
                     font=("Segoe UI",10), text_color=MUTED).pack(anchor="w", pady=(3,0))
        ctk.CTkLabel(hero, text="STEP 1  •  IDENTIFY STUDENT", font=("Segoe UI Bold",8), text_color=BLUE,
                     fg_color=LIGHT_BLUE, corner_radius=9, width=180, height=30).pack(side="right", padx=22)

        card = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=10)
        ctk.CTkLabel(card, text="1  Select Student", font=("Segoe UI Bold",15), text_color=TEXT).pack(anchor="w", padx=22, pady=(18,2))
        ctk.CTkLabel(card, text="Enter the Student ID, then verify the name and course shown below.",
                     font=("Segoe UI",9), text_color=MUTED).pack(anchor="w", padx=22, pady=(0,12))

        top = ctk.CTkFrame(card, fg_color=PANEL, corner_radius=11)
        top.pack(fill="x", padx=18, pady=(0,12))
        ctk.CTkLabel(top, text="STUDENT ID", font=("Segoe UI Bold",8), text_color=BLUE).pack(side="left", padx=(14,6))
        self.face_sid = ctk.CTkEntry(top, width=230, height=38, corner_radius=8, placeholder_text="e.g. STU001", border_color=BORDER)
        self.face_sid.pack(side="left", padx=4, pady=9)
        ctk.CTkButton(top, text="CHECK STUDENT", height=38, width=145, corner_radius=8, fg_color=NAVY,
                      hover_color=NAVY_2, font=("Segoe UI Bold",9), command=self.check_face_student).pack(side="left", padx=8)

        info_card = ctk.CTkFrame(card, fg_color=LIGHT_BLUE, corner_radius=10)
        info_card.pack(fill="x", padx=18, pady=(0,16))
        self.face_student_info = ctk.CTkLabel(info_card, text="ℹ  Enter a Student ID and click CHECK STUDENT.",
                                              font=("Segoe UI Semibold",9), text_color=NAVY)
        self.face_student_info.pack(anchor="w", padx=14, pady=10)

        step2 = ctk.CTkFrame(card, fg_color=LIGHT_GREEN, corner_radius=12)
        step2.pack(fill="x", padx=18, pady=(0,18))
        text_box = ctk.CTkFrame(step2, fg_color="transparent")
        text_box.pack(side="left", fill="x", expand=True, padx=16, pady=14)
        ctk.CTkLabel(text_box, text="2  Capture Face Samples", font=("Segoe UI Bold",14), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(text_box, text="Keep one face visible • good lighting • look toward the camera • 35 samples captured automatically.",
                     font=("Segoe UI",9), text_color="#456252", justify="left", wraplength=650).pack(anchor="w", pady=(3,0))
        ctk.CTkButton(step2, text="START FACE CAPTURE  →", height=42, width=200, corner_radius=9, fg_color=GREEN,
                      hover_color="#1B724A", font=("Segoe UI Bold",10), command=self.start_registration).pack(side="right", padx=16, pady=16)

        profiles = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        profiles.pack(fill="both", expand=True, padx=10, pady=(18,0))
        ph = ctk.CTkFrame(profiles, fg_color="transparent")
        ph.pack(fill="x", padx=20, pady=(15,6))
        ctk.CTkLabel(ph, text="Registered Faces", font=("Segoe UI Bold",16), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(ph, text=f"{len(database.get_face_profiles())} registered", font=("Segoe UI Semibold",9), text_color=GREEN,
                     fg_color=LIGHT_GREEN, corner_radius=8, padx=10, pady=5).pack(side="right")
        self.face_table = self.make_table(profiles, columns=("student_id","name","roll","course","samples","registered"),
                                          headings=("Student ID","Student Name","Roll No.","Course","Samples","Registered"), rows=[], height=12)
        self.fill_table(self.face_table, [(r["student_id"],r["name"],r["roll_no"],r["course"],r["sample_count"],r["registered_at"]) for r in database.get_face_profiles()])

    def check_face_student(self):
        sid = self.face_sid.get().strip()
        row = database.get_student(sid)
        if not row:
            self.face_student_info.configure(text="Student not found.", text_color=RED)
            return
        profile = database.get_face_profile(sid)
        status = "Face already registered." if profile else "No face registered yet."
        self.face_student_info.configure(
            text=f"{row['name']}  •  {row['course']}  •  {status}",
            text_color=GREEN if profile else TEXT
        )

    def start_registration(self):
        sid = self.face_sid.get().strip()
        student = database.get_student(sid)
        if not student:
            messagebox.showwarning("Student Not Found", "Enter a valid Student ID first.")
            return
        if student["status"] != "Active":
            if not messagebox.askyesno("Inactive Student", "This student is not Active. Register face anyway?"):
                return

        if not messagebox.askyesno(
            "Start Camera",
            f"Register face for:\n\n{student['name']} ({sid})\n\n"
            "The camera window will open. Keep one face visible."
        ):
            return

        # Keep OpenCV HighGUI on the main thread; this is much more reliable on Windows.
        self.capture_face_samples(sid)

    def capture_face_samples(self, sid):
        window_name = "SBBSU | Face Registration | Q = Cancel"
        cap = None
        count = 0
        last_save = 0.0
        student_dir = FACES_DIR / safe_filename(sid)

        try:
            cap, camera_index = self.open_camera()
            self.prepare_camera_window(window_name)

            detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            if detector.empty():
                raise RuntimeError("OpenCV face detector could not be loaded.")

            student_dir.mkdir(parents=True, exist_ok=True)

            # Re-registration intentionally replaces the old training samples.
            for old_file in student_dir.glob("*.jpg"):
                try:
                    old_file.unlink()
                except OSError:
                    pass

            while count < SAMPLE_TARGET:
                ok, frame = cap.read()
                if not ok or frame is None or getattr(frame, "size", 0) == 0:
                    cv2.waitKey(1)
                    continue
                # If a driver briefly emits a black startup frame, skip it
                # instead of displaying a black preview.
                probe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if float(probe.mean()) <= 2.0 and float(probe.std()) <= 2.0:
                    cv2.waitKey(1)
                    continue

                # Mirror the preview so it feels like a normal webcam.
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)
                faces = detector.detectMultiScale(
                    gray, scaleFactor=1.12, minNeighbors=5, minSize=(100, 100)
                )

                display = frame.copy()
                cv2.rectangle(display, (0, 0), (display.shape[1], 78), (11, 31, 58), -1)
                cv2.putText(display, f"SBBSU  |  FACE REGISTRATION", (18, 29),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
                cv2.putText(display, f"Student: {sid}    Samples: {count}/{SAMPLE_TARGET}", (18, 58),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.60, (220, 235, 250), 2)

                if len(faces) == 1:
                    x, y, w, h = faces[0]
                    cv2.rectangle(display, (x, y), (x + w, y + h), (50, 220, 90), 3)
                    cv2.putText(display, "FACE DETECTED - CAPTURING", (x, max(105, y - 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (50, 220, 90), 2)

                    now = time.time()
                    if now - last_save >= 0.16:
                        face_img = gray[y:y + h, x:x + w]
                        if face_img.size:
                            face_img = cv2.resize(face_img, FACE_SIZE, interpolation=cv2.INTER_AREA)
                            count += 1
                            filename = student_dir / f"{count:03d}.jpg"
                            if cv2.imwrite(str(filename), face_img):
                                last_save = now
                            else:
                                count -= 1
                elif len(faces) == 0:
                    cv2.putText(display, "Move into the camera frame", (18, display.shape[0] - 48),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (60, 210, 255), 2)
                else:
                    cv2.putText(display, "Only ONE face should be visible", (18, display.shape[0] - 48),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (60, 80, 255), 2)

                cv2.putText(display, f"Camera: {camera_index}   |   Press Q to cancel",
                            (18, display.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (235, 235, 235), 2)

                # IMPORTANT: show the window every frame and process HighGUI events.
                # Keep the camera stream itself at the webcam's native/safe
                # capture mode; only resize the displayed image if necessary.
                preview = display
                if display.shape[1] > 960:
                    scale = 960.0 / display.shape[1]
                    preview = cv2.resize(display, (960, int(display.shape[0] * scale)), interpolation=cv2.INTER_AREA)
                cv2.imshow(window_name, preview)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                # Detect the OpenCV window's X/Close button immediately.
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error:
                    break

        except Exception as exc:
            messagebox.showerror("Face Registration Error", str(exc))
            return
        finally:
            if cap is not None:
                cap.release()
            self.close_camera_window(window_name)

        if count >= 10:
            try:
                # A face may belong to only ONE Student ID. Before saving a new
                # profile, compare its captured samples against all other IDs.
                duplicate_sid, duplicate_matches, duplicate_total = self.find_duplicate_face(sid, student_dir)
                if duplicate_sid is not None:
                    duplicate_student = database.get_student(duplicate_sid)
                    duplicate_name = duplicate_student["name"] if duplicate_student else duplicate_sid
                    messagebox.showerror(
                        "Duplicate Face Detected",
                        f"This face is already registered to another Student ID.\n\n"
                        f"Existing ID: {duplicate_sid}\n"
                        f"Student: {duplicate_name}\n\n"
                        f"Matching samples: {duplicate_matches}/{duplicate_total}\n\n"
                        "Registration for this ID has been rejected. The face cannot be assigned to two Student IDs."
                    )
                    return

                existing = database.get_face_profile(sid)
                model_label = existing["model_label"] if existing else database.next_face_label()
                database.save_face_profile(sid, count, model_label)
                if not self.train_model():
                    raise RuntimeError("Face samples were captured, but the recognition model could not be trained.")

                messagebox.showinfo(
                    "Registration Complete",
                    f"Face registered successfully!\n\nStudent: {sid}\nSamples captured: {count}\n\n"
                    "You can now start Automatic Attendance."
                )
                self.show_face_registration()
            except Exception as exc:
                messagebox.showerror("Registration Save Error", f"Samples were captured but could not be saved/trained.\n\n{exc}")
        else:
            messagebox.showwarning(
                "Registration Cancelled",
                f"Only {count} sample(s) were captured. At least 10 are required.\n\n"
                "Keep your face clearly visible and try again."
            )

    def find_duplicate_face(self, sid, student_dir):
        """Check whether the newly captured face is already registered to another student."""
        profiles = [p for p in database.get_face_profiles() if p["student_id"] != sid]
        if not profiles or not hasattr(cv2, "face"):
            return None, 0, 0

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        train_faces, train_labels = [], []

        for profile in profiles:
            folder = FACES_DIR / safe_filename(profile["student_id"])
            label = int(profile["model_label"])
            for img_path in folder.glob("*.jpg"):
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    train_faces.append(cv2.resize(img, FACE_SIZE))
                    train_labels.append(label)

        if not train_faces:
            return None, 0, 0

        recognizer.train(train_faces, __import__("numpy").array(train_labels))
        label_to_sid = {int(p["model_label"]): p["student_id"] for p in profiles}

        scores = {}
        total = 0
        for img_path in student_dir.glob("*.jpg"):
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            img = cv2.resize(img, FACE_SIZE)
            label, distance = recognizer.predict(img)
            matched_sid = label_to_sid.get(int(label))
            total += 1
            if matched_sid is not None and float(distance) <= DUPLICATE_FACE_THRESHOLD:
                scores[matched_sid] = scores.get(matched_sid, 0) + 1

        if not scores or total == 0:
            return None, 0, total

        duplicate_sid, matches = max(scores.items(), key=lambda item: item[1])
        ratio = matches / total
        if matches >= DUPLICATE_MIN_MATCHES and ratio >= DUPLICATE_MATCH_RATIO:
            return duplicate_sid, matches, total
        return None, matches, total

    # -------------------- MODEL --------------------
    def train_model(self):
        if not hasattr(cv2, "face"):
            raise RuntimeError(
                "cv2.face is missing. Install opencv-contrib-python and remove opencv-python first."
            )

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        faces, labels = [], []

        for profile in database.get_face_profiles():
            sid = profile["student_id"]
            label = int(profile["model_label"])
            folder = FACES_DIR / safe_filename(sid)
            for img_path in folder.glob("*.jpg"):
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, FACE_SIZE)
                    faces.append(img)
                    labels.append(label)

        if not faces:
            return False

        recognizer.train(faces, __import__("numpy").array(labels))
        recognizer.write(str(MODEL_FILE))
        return True

    def get_camera_index(self):
        try:
            return int(database.get_setting("camera_index", "0"))
        except ValueError:
            return 0

    # -------------------- ATTENDANCE --------------------
    def show_attendance(self):
        self.current_page = "Attendance"
        self.last_attendance_date = datetime.now().strftime("%Y-%m-%d")
        self.set_active("Attendance")
        page = self.page("Attendance")

        hero = ctk.CTkFrame(page, fg_color=NAVY, corner_radius=16)
        hero.pack(fill="x", padx=8, pady=(0,15))
        hleft = ctk.CTkFrame(hero, fg_color="transparent")
        hleft.pack(side="left", fill="x", expand=True, padx=22, pady=17)
        ctk.CTkLabel(hleft, text="Automatic Face Attendance", font=("Segoe UI Bold",24), text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(hleft, text="Scan up to 5 recognized students together in one camera frame.", font=("Segoe UI",10), text_color="#C5D5E5").pack(anchor="w", pady=(3,0))
        ctk.CTkLabel(hero, text="●  READY TO SCAN", font=("Segoe UI Bold",9), text_color="#75E3A8",
                     fg_color="#17324F", corner_radius=9, width=145, height=30).pack(side="right", padx=22)

        control = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        control.pack(fill="x", padx=10, pady=(0,15))
        ctk.CTkLabel(control, text="HOW IT WORKS", font=("Segoe UI Bold",8), text_color=BLUE,
                     fg_color=LIGHT_BLUE, corner_radius=8, width=105, height=28).pack(side="left", padx=(18,10), pady=17)
        ctk.CTkLabel(control, text="Recognize first  →  verify stable face  →  capture & freeze  →  mark Present",
                     font=("Segoe UI Semibold",10), text_color=TEXT).pack(side="left", pady=17)
        ctk.CTkButton(control, text="▶  START CAMERA", height=42, width=190, corner_radius=9, fg_color=GREEN,
                      hover_color="#1B724A", font=("Segoe UI Bold",10), command=self.start_attendance).pack(side="right", padx=18, pady=10)

        tips = ctk.CTkFrame(page, fg_color=LIGHT_ORANGE, corner_radius=11)
        tips.pack(fill="x", padx=10, pady=(0,15))
        ctk.CTkLabel(tips, text="TIP", font=("Segoe UI Bold",8), text_color=ORANGE, fg_color="#FFE8C5", corner_radius=7, width=45, height=24).pack(side="left", padx=12, pady=9)
        ctk.CTkLabel(tips, text="For classroom scanning, ask 4–5 students to face the camera together. Once Present, their captured photo stays fixed.",
                     font=("Segoe UI Semibold",9), text_color="#6F4A1C").pack(side="left", padx=(0,12))

        today = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        today.pack(fill="both", expand=True, padx=10)
        th = ctk.CTkFrame(today, fg_color="transparent")
        th.pack(fill="x", padx=20, pady=(15,5))
        ctk.CTkLabel(th, text=f"Today's Attendance  •  {datetime.now().strftime('%d %b %Y')}",
                     font=("Segoe UI Bold",16), text_color=TEXT).pack(side="left")
        ctk.CTkButton(th, text="↻  REFRESH", height=32, width=105, corner_radius=8,
                      fg_color=SOFT_NAVY, hover_color="#DCE7F2", text_color=NAVY,
                      font=("Segoe UI Bold",8), command=self.show_attendance).pack(side="right", padx=(8,0))
        ctk.CTkButton(th, text="RESET TODAY", height=32, width=115, corner_radius=8,
                      fg_color="#FCECEC", hover_color="#F8D6D6", text_color=RED,
                      font=("Segoe UI Bold",8), command=self.reset_today_attendance).pack(side="right", padx=(8,0))
        ctk.CTkButton(th, text="EXPORT CSV", height=32, width=115, corner_radius=8, fg_color=NAVY,
                      hover_color=NAVY_2, font=("Segoe UI Bold",8), command=self.export_attendance).pack(side="right")
        self.att_table = self.make_table(today, columns=("id","name","roll","course","time","status"),
                                         headings=("Student ID","Student Name","Roll No.","Course","Time","Status"), rows=[], height=15)
        self.fill_table(self.att_table, self.today_attendance_rows())

    def start_attendance(self):
        if not database.get_face_profiles():
            messagebox.showwarning("No Faces", "Register at least one student's face first.")
            return
        if not MODEL_FILE.exists():
            try:
                self.train_model()
            except Exception as exc:
                messagebox.showerror("Model Error", str(exc))
                return
        # Keep OpenCV HighGUI on the main thread for reliable Windows camera display.
        self.attendance_camera()

    def attendance_camera(self):
        """Multi-face attendance: recognize up to 5 people at once.

        A student is frozen only AFTER the identity has been accepted for
        STABLE_MATCH_FRAMES consecutive observations. After that, a snapshot
        of the recognized face stays on screen and that student is no longer
        re-processed, so head movement does not cancel the attendance.
        """
        if not MODEL_FILE.exists():
            messagebox.showwarning(
                "Model Missing",
                "No trained face model found. Register at least one face first."
            )
            return

        window_name = "SBBSU | 5-Face Automatic Attendance | Q = Stop"
        cap = None
        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(str(MODEL_FILE))
        except Exception as exc:
            messagebox.showerror("Recognition Error", str(exc))
            return

        detector = cv2.CascadeClassifier(
            str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        )
        if detector.empty():
            messagebox.showerror("Detector Error", "OpenCV face detector could not be loaded.")
            return

        profiles = database.get_face_profiles()
        label_map = {int(r["model_label"]): r["student_id"] for r in profiles}
        if not label_map:
            messagebox.showwarning("No Faces", "Register at least one student's face first.")
            return

        # SID -> number of consecutive accepted recognition frames.
        # Recognition must happen first; only then does a student become frozen.
        candidate_hits = {}
        frozen = {}
        last_marked = {}
        MAX_FACES = 5

        try:
            cap, camera_index = self.open_camera()
            self.prepare_camera_window(window_name)

            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)
                faces = detector.detectMultiScale(
                    gray, scaleFactor=1.05, minNeighbors=5, minSize=(60, 60)
                )

                # Process the five largest faces when more than five are detected.
                faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)[:MAX_FACES]
                display = frame.copy()

                cv2.rectangle(display, (0, 0), (display.shape[1], 82), (11, 31, 58), -1)
                cv2.putText(display, "SBBSU  |  5-FACE AUTOMATIC ATTENDANCE", (18, 27),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 255, 255), 2)
                cv2.putText(display,
                            f"Detected: {len(faces)}/{MAX_FACES}  |  Present: {len(frozen)}  |  Registered: {len(label_map)}",
                            (18, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 235, 250), 2)

                seen_sids = set()
                live_unknown = 0
                # Keep this frame's verified faces separate so that several
                # students can be captured/frozen together in the SAME frame.
                frame_verified = []
                frame_boxes = []

                for x, y, w, h in faces:
                    roi = gray[y:y + h, x:x + w]
                    if roi.size == 0:
                        continue
                    roi = cv2.resize(roi, FACE_SIZE, interpolation=cv2.INTER_AREA)
                    label, confidence = recognizer.predict(roi)
                    sid = label_map.get(int(label))

                    # Once a student is frozen, do NOT recognize/replace that
                    # student's result again. Their captured image remains fixed.
                    if sid in frozen:
                        continue

                    accepted = sid is not None and float(confidence) <= RECOGNITION_THRESHOLD

                    if accepted:
                        seen_sids.add(sid)
                        candidate_hits[sid] = candidate_hits.get(sid, 0) + 1
                        student = database.get_student(sid)
                        name = student["name"] if student else sid

                        if candidate_hits[sid] >= STABLE_MATCH_FRAMES:
                            # Do NOT freeze immediately here. First finish
                            # recognizing every face in this frame, then capture
                            # all verified students together.
                            face_snapshot = frame[y:y + h, x:x + w].copy()
                            if face_snapshot.size:
                                face_snapshot = cv2.resize(face_snapshot, (150, 150), interpolation=cv2.INTER_AREA)
                            frame_verified.append((sid, name, float(confidence), face_snapshot))
                            label_text = f"RECOGNIZED: {name}"
                            box_color = (50, 220, 90)
                        else:
                            label_text = f"VERIFYING: {name} | {candidate_hits[sid]}/{STABLE_MATCH_FRAMES}"
                            box_color = (255, 190, 50)
                    else:
                        live_unknown += 1
                        if sid is not None:
                            label_text = f"UNKNOWN FACE | {float(confidence):.1f}"
                        else:
                            label_text = "UNKNOWN FACE"
                        box_color = (60, 80, 255)

                    frame_boxes.append((x, y, w, h, label_text, box_color))

                # Capture/freeze every verified student from this frame together.
                # Recognition still has to be stable first, so false/partial
                # detections are not frozen as attendance.
                batch_marked = False
                for sid, name, confidence, face_snapshot in frame_verified:
                    if sid in frozen:
                        continue
                    now = time.time()
                    if now - last_marked.get(sid, 0) >= ATTENDANCE_COOLDOWN:
                        database.mark_attendance(sid)
                        last_marked[sid] = now
                    frozen[sid] = {
                        "name": name,
                        "confidence": confidence,
                        "image": face_snapshot,
                    }
                    candidate_hits.pop(sid, None)
                    batch_marked = True

                if batch_marked:
                    self.refresh_attendance_if_open()

                for x, y, w, h, label_text, box_color in frame_boxes:
                    cv2.rectangle(display, (x, y), (x + w, y + h), box_color, 3)
                    cv2.putText(display, label_text, (x, max(98, y - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.54, box_color, 2)

                # Forget verification counters for identities that disappeared,
                # but never remove an already frozen/present student.
                for sid in list(candidate_hits):
                    if sid not in seen_sids:
                        candidate_hits[sid] = max(0, candidate_hits[sid] - 1)
                        if candidate_hits[sid] == 0:
                            candidate_hits.pop(sid, None)

                # Fixed capture area: once recognized, the student's photo stays
                # in its slot even if they turn/move away from the live camera position.
                if frozen:
                    slot_w, slot_h = 170, 155
                    gap = 8
                    total_w = len(frozen) * slot_w + max(0, len(frozen) - 1) * gap
                    panel_x = max(10, (display.shape[1] - total_w) // 2)
                    panel_y = display.shape[0] - slot_h - 42
                    cv2.putText(display, "CAPTURED / PRESENT", (panel_x, panel_y - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (50, 220, 90), 2)

                    for i, (sid, info) in enumerate(list(frozen.items())[:5]):
                        sx = panel_x + i * (slot_w + gap)
                        snap = info.get("image")
                        if snap is not None and snap.size:
                            thumb = cv2.resize(snap, (slot_w, slot_h - 28), interpolation=cv2.INTER_AREA)
                            display[panel_y:panel_y + slot_h - 28, sx:sx + slot_w] = thumb
                        cv2.rectangle(display, (sx, panel_y),
                                      (sx + slot_w, panel_y + slot_h - 28), (50, 220, 90), 2)
                        cv2.putText(display, f"{info['name']} | PRESENT", (sx + 5, panel_y + slot_h - 9),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (50, 220, 90), 1)

                cv2.putText(display,
                            "Recognize first -> capture/freeze -> attendance stays marked  |  Q / ESC = Stop",
                            (18, display.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                            (235, 235, 235), 2)

                # Keep the camera stream itself at the webcam's native/safe
                # capture mode; only resize the displayed image if necessary.
                preview = display
                if display.shape[1] > 960:
                    scale = 960.0 / display.shape[1]
                    preview = cv2.resize(display, (960, int(display.shape[0] * scale)), interpolation=cv2.INTER_AREA)
                cv2.imshow(window_name, preview)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error:
                    break

        except Exception as exc:
            messagebox.showerror("Attendance Camera Error", str(exc))
        finally:
            if cap is not None:
                cap.release()
            self.close_camera_window(window_name)
            self.refresh_attendance_if_open()

    def today_attendance_rows(self):
        attendance = {r["student_id"]: r for r in database.attendance_today()}
        rows = []
        for student in database.get_students():
            if str(student["status"] or "").strip().lower() != "active":
                continue
            r = attendance.get(student["student_id"])
            rows.append((
                student["student_id"], student["name"], student["roll_no"],
                student["course"], r["attendance_time"] if r else "—",
                r["status"] if r else "Absent"
            ))
        return rows

    def refresh_attendance_if_open(self):
        if hasattr(self, "att_table") and self.att_table.winfo_exists():
            self.fill_table(self.att_table, self.today_attendance_rows())

    def reset_today_attendance(self):
        """Delete only today's attendance; historical records remain untouched."""
        today = datetime.now().strftime("%Y-%m-%d")
        if not messagebox.askyesno(
            "Reset Today's Attendance",
            f"Delete ALL attendance records for {datetime.now().strftime('%d %b %Y')}?\n\n"
            "Previous dates will not be affected.",
        ):
            return

        try:
            with database.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM attendance WHERE attendance_date = ?",
                    (today,)
                )
                conn.commit()
                deleted = cursor.rowcount
        except Exception as exc:
            messagebox.showerror("Reset Failed", str(exc))
            return

        self.last_attendance_date = today
        messagebox.showinfo(
            "Reset Complete",
            f"Today's attendance has been cleared.\n\nRecords removed: {max(0, deleted)}"
        )
        self.show_attendance()

    def export_attendance(self):
        rows = database.get_attendance()
        if not rows:
            messagebox.showinfo("No Data", "There is no attendance data to export.")
            return

        default = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            title="Export Attendance",
            defaultextension=".csv",
            initialfile=default,
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Student ID", "Name", "Roll No.", "Department", "Course", "Date", "Time", "Status", "Method"])
            for r in rows:
                writer.writerow([
                    r["student_id"], r["name"], r["roll_no"], r["department"],
                    r["course"], r["attendance_date"], r["attendance_time"],
                    r["status"], r["method"]
                ])
        messagebox.showinfo("Export Complete", f"Attendance exported to:\n{path}")

    # -------------------- REPORTS --------------------
    def get_report_rows_for_date(self, date_text):
        attendance = {r["student_id"]: r for r in database.get_attendance(date_text)}
        rows = []
        for student in database.get_students():
            if str(student["status"] or "").strip().lower() != "active":
                continue
            r = attendance.get(student["student_id"])
            rows.append((
                student["student_id"], student["name"], student["roll_no"],
                student["course"], date_text,
                r["attendance_time"] if r else "—",
                r["status"] if r else "Absent",
                r["method"] if r else "—"
            ))
        return rows

    def show_reports(self):
        self.set_active("Reports")
        page = self.page("Reports")

        hero = ctk.CTkFrame(page, fg_color=NAVY, corner_radius=16)
        hero.pack(fill="x", padx=8, pady=(0, 15))
        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=22, pady=17)
        ctk.CTkLabel(left, text="Attendance Reports", font=("Segoe UI Bold", 24), text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(left, text="Check daily attendance, monthly summaries and attendance percentages.",
                     font=("Segoe UI", 10), text_color="#C5D5E5").pack(anchor="w", pady=(3, 0))
        ctk.CTkLabel(hero, text="REPORT CENTER", font=("Segoe UI Bold", 8), text_color=NAVY,
                     fg_color="#EAF2FB", corner_radius=8, width=115, height=28).pack(side="right", padx=22)

        filters = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        filters.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkLabel(filters, text="Daily Report", font=("Segoe UI Bold", 15), text_color=TEXT).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(filters, text="Select a date. Students without an attendance record are shown as Absent.",
                     font=("Segoe UI", 9), text_color=MUTED).pack(anchor="w", padx=20, pady=(0, 12))

        row = ctk.CTkFrame(filters, fg_color=PANEL, corner_radius=11)
        row.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkLabel(row, text="DATE", font=("Segoe UI Bold", 8), text_color=BLUE).pack(side="left", padx=(14, 8), pady=11)
        self.report_date_entry = ctk.CTkEntry(row, width=145, height=36, corner_radius=8, border_color=BORDER,
                                              placeholder_text="YYYY-MM-DD")
        self.report_date_entry.pack(side="left", pady=8)
        self.report_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkButton(row, text="LOAD REPORT", height=36, width=125, fg_color=NAVY, hover_color=NAVY_2,
                      font=("Segoe UI Bold", 9), command=self.load_daily_report).pack(side="left", padx=8)
        ctk.CTkButton(row, text="EXPORT DAILY CSV", height=36, width=145, fg_color=GREEN, hover_color="#1B724A",
                      font=("Segoe UI Bold", 9), command=self.export_daily_report).pack(side="left", padx=4)

        daily_card = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        daily_card.pack(fill="both", expand=True, padx=10, pady=(0, 15))
        ctk.CTkLabel(daily_card, text="Daily Attendance Details", font=("Segoe UI Bold", 15), text_color=TEXT).pack(anchor="w", padx=20, pady=(16, 8))
        self.report_table = self.make_table(
            daily_card,
            columns=("id", "name", "roll", "course", "date", "time", "status", "method"),
            headings=("Student ID", "Student Name", "Roll No.", "Course", "Date", "Time", "Status", "Method"),
            rows=[], height=10
        )
        self.load_daily_report()

        monthly = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        monthly.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        ctk.CTkLabel(monthly, text="Monthly Student Summary", font=("Segoe UI Bold", 15), text_color=TEXT).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(monthly, text="Attendance % is calculated against the number of recorded attendance days in the selected month.",
                     font=("Segoe UI", 9), text_color=MUTED).pack(anchor="w", padx=20, pady=(0, 10))
        mrow = ctk.CTkFrame(monthly, fg_color=PANEL, corner_radius=11)
        mrow.pack(fill="x", padx=18, pady=(0, 12))
        ctk.CTkLabel(mrow, text="MONTH", font=("Segoe UI Bold", 8), text_color=BLUE).pack(side="left", padx=(14, 8), pady=11)
        self.report_month_entry = ctk.CTkEntry(mrow, width=120, height=36, corner_radius=8, border_color=BORDER,
                                               placeholder_text="YYYY-MM")
        self.report_month_entry.pack(side="left", pady=8)
        self.report_month_entry.insert(0, datetime.now().strftime("%Y-%m"))
        ctk.CTkButton(mrow, text="LOAD MONTH", height=36, width=115, fg_color=BLUE, hover_color=BLUE_HOVER,
                      font=("Segoe UI Bold", 9), command=self.load_monthly_report).pack(side="left", padx=8)
        ctk.CTkButton(mrow, text="EXPORT MONTHLY CSV", height=36, width=150, fg_color=ORANGE, hover_color="#A85F16",
                      font=("Segoe UI Bold", 9), command=self.export_monthly_report).pack(side="left", padx=4)

        self.month_table = self.make_table(
            monthly,
            columns=("id", "name", "roll", "present", "absent", "days", "percent"),
            headings=("Student ID", "Student Name", "Roll No.", "Present", "Absent", "Recorded Days", "Attendance %"),
            rows=[], height=8
        )
        self.load_monthly_report()

    def load_daily_report(self):
        if not hasattr(self, "report_date_entry") or not self.report_date_entry.winfo_exists():
            return
        date_text = self.report_date_entry.get().strip()
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid Date", "Use date format YYYY-MM-DD.")
            return
        self.fill_table(self.report_table, self.get_report_rows_for_date(date_text))

    def export_daily_report(self):
        if not hasattr(self, "report_date_entry"):
            return
        date_text = self.report_date_entry.get().strip()
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid Date", "Use date format YYYY-MM-DD.")
            return
        rows = self.get_report_rows_for_date(date_text)
        path = filedialog.asksaveasfilename(
            title="Export Daily Attendance",
            defaultextension=".csv",
            initialfile=f"attendance_{date_text}.csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Student ID", "Name", "Roll No.", "Course", "Date", "Time", "Status", "Method"])
            writer.writerows(rows)
        messagebox.showinfo("Export Complete", f"Daily report exported to:\n{path}")

    def get_monthly_summary(self, month_text):
        try:
            datetime.strptime(month_text, "%Y-%m")
        except ValueError:
            raise ValueError("Use month format YYYY-MM.")

        all_rows = [r for r in database.get_attendance() if str(r["attendance_date"]).startswith(month_text)]
        recorded_days = sorted({r["attendance_date"] for r in all_rows})
        day_count = len(recorded_days)
        present_by_student = {}
        for r in all_rows:
            if str(r["status"]).strip().lower() == "present":
                present_by_student[r["student_id"]] = present_by_student.get(r["student_id"], 0) + 1

        summary = []
        for student in database.get_students():
            if str(student["status"] or "").strip().lower() != "active":
                continue
            present = present_by_student.get(student["student_id"], 0)
            absent = max(0, day_count - present)
            percent = (present / day_count * 100) if day_count else 0.0
            summary.append((student["student_id"], student["name"], student["roll_no"], present, absent,
                            day_count, f"{percent:.1f}%"))
        return summary

    def load_monthly_report(self):
        if not hasattr(self, "report_month_entry") or not self.report_month_entry.winfo_exists():
            return
        month_text = self.report_month_entry.get().strip()
        try:
            rows = self.get_monthly_summary(month_text)
        except ValueError as exc:
            messagebox.showwarning("Invalid Month", str(exc))
            return
        self.fill_table(self.month_table, rows)

    def export_monthly_report(self):
        if not hasattr(self, "report_month_entry"):
            return
        month_text = self.report_month_entry.get().strip()
        try:
            rows = self.get_monthly_summary(month_text)
        except ValueError as exc:
            messagebox.showwarning("Invalid Month", str(exc))
            return
        path = filedialog.asksaveasfilename(
            title="Export Monthly Attendance",
            defaultextension=".csv",
            initialfile=f"attendance_month_{month_text}.csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Student ID", "Name", "Roll No.", "Present", "Absent", "Recorded Days", "Attendance %"])
            writer.writerows(rows)
        messagebox.showinfo("Export Complete", f"Monthly report exported to:\n{path}")

    # -------------------- SETTINGS --------------------
    def show_settings(self):
        self.set_active("Settings")
        page = self.page("Settings")

        hero = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        hero.pack(fill="x", padx=8, pady=(0,15))
        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=22, pady=17)
        ctk.CTkLabel(left, text="System Settings", font=("Segoe UI Bold",24), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Configure the camera used by face registration and automatic attendance.", font=("Segoe UI",10), text_color=MUTED).pack(anchor="w", pady=(3,0))
        ctk.CTkLabel(hero, text="SYSTEM CONFIG", font=("Segoe UI Bold",8), text_color=NAVY, fg_color=SOFT_NAVY, corner_radius=8, width=115, height=28).pack(side="right", padx=22)

        card = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=10)
        ctk.CTkLabel(card, text="Camera Configuration", font=("Segoe UI Bold",15), text_color=TEXT).pack(anchor="w", padx=22, pady=(20,2))
        ctk.CTkLabel(card, text="Which camera should the application open?  0 is normally the built-in/default webcam.",
                     font=("Segoe UI",9), text_color=MUTED).pack(anchor="w", padx=22, pady=(0,14))

        field = ctk.CTkFrame(card, fg_color=PANEL, corner_radius=11)
        field.pack(fill="x", padx=18, pady=(0,15))
        ctk.CTkLabel(field, text="CAMERA INDEX", font=("Segoe UI Bold",8), text_color=BLUE).pack(side="left", padx=(14,8), pady=12)
        self.camera_entry = ctk.CTkEntry(field, width=150, height=38, corner_radius=8, border_color=BORDER)
        self.camera_entry.pack(side="left", pady=9)
        self.camera_entry.insert(0, database.get_setting("camera_index", "0"))
        ctk.CTkLabel(field, text="Try 1 or 2 if your preferred camera is not opening.", font=("Segoe UI",9), text_color=MUTED).pack(side="left", padx=12)

        note = ctk.CTkFrame(card, fg_color=LIGHT_BLUE, corner_radius=10)
        note.pack(fill="x", padx=18, pady=(0,15))
        ctk.CTkLabel(note, text="ℹ", font=("Segoe UI Bold",14), text_color=BLUE).pack(side="left", padx=(12,7), pady=9)
        ctk.CTkLabel(note, text="After changing the camera index, save settings and restart the camera screen.",
                     font=("Segoe UI Semibold",9), text_color=NAVY).pack(side="left", pady=9)

        setting_buttons = ctk.CTkFrame(card, fg_color="transparent")
        setting_buttons.pack(anchor="w", padx=18, pady=(0,20))
        ctk.CTkButton(setting_buttons, text="SAVE SETTINGS", height=42, width=175, corner_radius=9, fg_color=NAVY,
                      hover_color=NAVY_2, font=("Segoe UI Bold",10), command=self.save_settings).pack(side="left", padx=(0,8))
        ctk.CTkButton(setting_buttons, text="TEST CAMERA", height=42, width=145, corner_radius=9, fg_color=BLUE,
                      hover_color=BLUE_HOVER, font=("Segoe UI Bold",10), command=self.test_camera).pack(side="left")

        backup = ctk.CTkFrame(page, fg_color=WHITE, corner_radius=16, border_width=1, border_color=BORDER)
        backup.pack(fill="x", padx=10, pady=(15, 0))
        ctk.CTkLabel(backup, text="Data Protection", font=("Segoe UI Bold",15), text_color=TEXT).pack(anchor="w", padx=22, pady=(18,2))
        ctk.CTkLabel(backup, text="Create a single ZIP backup containing the SQLite database, face samples, attendance files and trained model.",
                     font=("Segoe UI",9), text_color=MUTED).pack(anchor="w", padx=22, pady=(0,12))
        ctk.CTkButton(backup, text="CREATE FULL BACKUP", height=42, width=190, corner_radius=9, fg_color=GREEN,
                      hover_color="#1B724A", font=("Segoe UI Bold",10), command=self.create_full_backup).pack(anchor="w", padx=18, pady=(0,18))

        status = ctk.CTkFrame(page, fg_color=LIGHT_GREEN, corner_radius=12)
        status.pack(fill="x", padx=10, pady=18)
        ctk.CTkLabel(status, text="✓  SYSTEM READY", font=("Segoe UI Bold",9), text_color=GREEN).pack(side="left", padx=14, pady=12)
        ctk.CTkLabel(status, text="Student database, face profiles and attendance records are stored locally in the project.",
                     font=("Segoe UI",9), text_color="#456252").pack(side="left", pady=12)

    def test_camera(self):
        window_name = "SBBSU | Camera Test | Q = Close"
        cap = None
        try:
            cap, camera_index = self.open_camera()
            self.prepare_camera_window(window_name)
            started = time.time()
            while time.time() - started < 3.0:
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                frame = cv2.flip(frame, 1)
                cv2.putText(frame, f"SBBSU CAMERA TEST  |  Index: {camera_index}", (18, 32),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, "Camera is working  |  Q / ESC = Close", (18, 62),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 230, 120), 2)
                preview = frame
                if frame.shape[1] > 960:
                    scale = 960.0 / frame.shape[1]
                    preview = cv2.resize(frame, (960, int(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)
                cv2.imshow(window_name, preview)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error:
                    break
        except Exception as exc:
            messagebox.showerror("Camera Test Failed", str(exc))
        finally:
            if cap is not None:
                cap.release()
            self.close_camera_window(window_name)

    def save_settings(self):
        value = self.camera_entry.get().strip()
        try:
            int(value)
        except ValueError:
            messagebox.showwarning("Invalid", "Camera Index must be a number.")
            return
        database.set_setting("camera_index", value)
        messagebox.showinfo("Saved", "Settings saved.")

    def create_full_backup(self):
        target_dir = filedialog.askdirectory(title="Choose Backup Folder")
        if not target_dir:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = Path(target_dir) / f"SBBSU_Backup_{stamp}.zip"
        try:
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                db_path = Path(database.DB_PATH)
                if db_path.exists():
                    zf.write(db_path, arcname="student_management.db")
                if MODEL_FILE.exists():
                    zf.write(MODEL_FILE, arcname="face_model.yml")
                for folder in (FACES_DIR, ATTENDANCE_DIR):
                    if folder.exists():
                        for file_path in folder.rglob("*"):
                            if file_path.is_file():
                                zf.write(file_path, arcname=str(file_path.relative_to(Path(__file__).resolve().parent)))
            messagebox.showinfo("Backup Complete", f"Full backup created successfully:\n\n{zip_path}")
        except Exception as exc:
            messagebox.showerror("Backup Error", f"Could not create backup.\n\n{exc}")

    # -------------------- TABLE HELPERS --------------------
    def make_table(self, parent, columns, headings, rows, height=10):
        wrap = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=11, border_width=1, border_color="#E5EAF0")
        wrap.pack(fill="both", expand=True, padx=15, pady=(0,15))

        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT,
                        rowheight=36, font=("Segoe UI",9), borderwidth=0)
        style.configure("Treeview.Heading", background=NAVY, foreground=WHITE,
                        font=("Segoe UI Bold",9), padding=(8,10), relief="flat")
        style.map("Treeview", background=[("selected", "#DDEAF6")], foreground=[("selected", TEXT)])

        # Status badges are represented by row colors in the Treeview.
        # Present = green, Absent = red, Active = green, Inactive = red.
        tree.tag_configure("present", background="#EAF7EF", foreground="#17633F")
        tree.tag_configure("absent", background="#FDEEEE", foreground="#A62E2E")
        tree.tag_configure("active", background="#F3FAF6", foreground="#17633F")
        tree.tag_configure("inactive", background="#FFF4F4", foreground="#A62E2E")
        tree.tag_configure("normal", background=WHITE, foreground=TEXT)

        for col, heading in zip(columns, headings):
            tree.heading(col, text=heading)
            width = 120
            if col in ("name", "department", "course"):
                width = 165
            elif col in ("student_id", "roll"):
                width = 125
            tree.column(col, width=width, minwidth=85, anchor="w")

        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        self.fill_table(tree, rows)
        return tree

    @staticmethod
    def fill_table(tree, rows):
        for item in tree.get_children():
            tree.delete(item)

        # Find a status column once so every table that has Status gets
        # consistent green/red highlighting without changing its data.
        status_index = None
        try:
            cols = list(tree["columns"])
            lowered = [str(c).lower() for c in cols]
            if "status" in lowered:
                status_index = lowered.index("status")
        except Exception:
            pass

        for row in rows:
            tag = "normal"
            if status_index is not None and status_index < len(row):
                value = str(row[status_index] or "").strip().lower()
                if value == "present":
                    tag = "present"
                elif value == "absent":
                    tag = "absent"
                elif value == "active":
                    tag = "active"
                elif value == "inactive":
                    tag = "inactive"
            tree.insert("", "end", values=row, tags=(tag,))

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to logout?"):
            for widget in self.winfo_children():
                widget.destroy()
            self.entries = {}
            self.selected_student_id = None
            self.login()


if __name__ == "__main__":
    try:
        database.init_db()
    except Exception as exc:
        messagebox.showerror("Database Error", f"Unable to initialize database.\n\n{exc}")
        raise
    app = App()
    app.mainloop()
