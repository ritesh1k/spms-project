import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

class AdminDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Admin Dashboard - EduTrack")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f5f5f5")
        
        # Configure grid weights
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Colors
        self.sidebar_bg = "#1a2b4c"
        self.sidebar_fg = "#ffffff"
        self.sidebar_hover = "#2a3b5c"
        self.card_bg = "#ffffff"
        self.primary_color = "#3498db"
        self.text_color = "#333333"
        
        # Fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=24, weight="bold")
        self.heading_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.normal_font = tkfont.Font(family="Segoe UI", size=11)
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create main containers
        self.sidebar = tk.Frame(self.root, bg=self.sidebar_bg, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        self.main_content = tk.Frame(self.root, bg="#f5f5f5")
        self.main_content.grid(row=0, column=1, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=0)
        self.main_content.grid_rowconfigure(1, weight=1)
        self.main_content.grid_rowconfigure(2, weight=0)
        
        # Setup sidebar and content
        self.create_sidebar()
        self.create_header()
        self.create_cards()
        self.create_footer()
        
    def create_sidebar(self):
        # Dashboard Title
        title_label = tk.Label(
            self.sidebar,
            text="Admin Dashboard",
            bg=self.sidebar_bg,
            fg=self.sidebar_fg,
            font=self.heading_font,
            pady=20
        )
        title_label.pack(fill="x")
        
        # Separator
        separator = tk.Frame(self.sidebar, bg="#3a4b6c", height=2)
        separator.pack(fill="x", padx=20, pady=10)
        
        # Sidebar menu items
        menu_items = [
            "Overview",
            "Manage Students",
            "Manage Teachers",
            "Manage Courses",
            "Manage Subjects",
            "Departments",
            "Publish Results",
            "Change Password"
        ]
        
        for item in menu_items:
            menu_button = tk.Button(
                self.sidebar,
                text=item,
                bg=self.sidebar_bg,
                fg=self.sidebar_fg,
                font=self.normal_font,
                bd=0,
                padx=20,
                pady=12,
                anchor="w",
                cursor="hand2",
                activebackground=self.sidebar_hover,
                activeforeground=self.sidebar_fg
            )
            menu_button.pack(fill="x", padx=5)
        
        # Logout at bottom of sidebar
        separator_bottom = tk.Frame(self.sidebar, bg="#3a4b6c", height=2)
        separator_bottom.pack(fill="x", padx=20, pady=(150, 10))
        
        logout_button = tk.Button(
            self.sidebar,
            text="Logout",
            bg=self.sidebar_bg,
            fg=self.sidebar_fg,
            font=self.normal_font,
            bd=0,
            padx=20,
            pady=12,
            anchor="w",
            cursor="hand2",
            activebackground=self.sidebar_hover,
            activeforeground=self.sidebar_fg
        )
        logout_button.pack(fill="x", padx=5)
        
    def create_header(self):
        header_frame = tk.Frame(self.main_content, bg="#f5f5f5")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        
        welcome_label = tk.Label(
            header_frame,
            text="Admin Dashboard",
            bg="#f5f5f5",
            fg=self.text_color,
            font=self.title_font
        )
        welcome_label.pack(side="left")
        
    def create_cards(self):
        cards_frame = tk.Frame(self.main_content, bg="#f5f5f5")
        cards_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        cards_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        # Card data
        cards_data = [
            ("Total Students", "0", "#3498db"),
            ("Total Teachers", "0", "#e74c3c"),
            ("Courses", "4", "#2ecc71"),
            ("Departments", "4", "#f39c12")
        ]
        
        for i, (title, value, color) in enumerate(cards_data):
            self.create_card(cards_frame, title, value, color, i)
            
    def create_card(self, parent, title, value, color, column):
        # Card container
        card = tk.Frame(
            parent,
            bg=self.card_bg,
            bd=1,
            relief="solid",
            highlightbackground="#e0e0e0",
            highlightthickness=1
        )
        card.grid(row=0, column=column, padx=10, pady=10, sticky="nsew")
        
        # Left color strip
        color_strip = tk.Frame(card, bg=color, width=5)
        color_strip.pack(side="left", fill="y")
        
        # Content frame
        content_frame = tk.Frame(card, bg=self.card_bg, padx=15, pady=15)
        content_frame.pack(side="left", fill="both", expand=True)
        
        # Title label
        title_label = tk.Label(
            content_frame,
            text=title,
            bg=self.card_bg,
            fg="#666666",
            font=self.normal_font
        )
        title_label.pack(anchor="w")
        
        # Value label
        value_label = tk.Label(
            content_frame,
            text=value,
            bg=self.card_bg,
            fg="#333333",
            font=self.title_font
        )
        value_label.pack(anchor="w")
        
    def create_footer(self):
        footer_frame = tk.Frame(self.main_content, bg="#ffffff", height=80)
        footer_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        footer_frame.grid_propagate(False)
        footer_frame.grid_columnconfigure(0, weight=1)
        
        # Top section - Links
        links_frame = tk.Frame(footer_frame, bg="#ffffff")
        links_frame.pack(pady=(10, 5))
        
        links = ["About", "Privacy", "Help", "Contact"]
        for i, link in enumerate(links):
            link_label = tk.Label(
                links_frame,
                text=link,
                bg="#ffffff",
                fg="#3498db",
                font=self.normal_font,
                cursor="hand2"
            )
            link_label.grid(row=0, column=i, padx=10)
            
            if i < len(links) - 1:
                separator = tk.Label(
                    links_frame,
                    text="|",
                    bg="#ffffff",
                    fg="#cccccc",
                    font=self.normal_font
                )
                separator.grid(row=0, column=i, padx=5, sticky="e")
        
        # Date and time
        current_date = datetime.now().strftime("%d %B %Y")
        current_time = datetime.now().strftime("%I:%M:%S %p").lower()
        
        datetime_label = tk.Label(
            footer_frame,
            text=f"{current_date} | {current_time}",
            bg="#ffffff",
            fg="#666666",
            font=self.small_font
        )
        datetime_label.pack(pady=2)
        
        # Copyright
        copyright_label = tk.Label(
            footer_frame,
            text="© 2024 EduTrack. Developed By Ritesh",
            bg="#ffffff",
            fg="#666666",
            font=self.small_font
        )
        copyright_label.pack(pady=(0, 10))

def main():
    root = tk.Tk()
    app = AdminDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()