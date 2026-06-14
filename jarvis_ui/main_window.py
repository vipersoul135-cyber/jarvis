import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QPalette, QFont

class VoiceThread(QThread):
    # Signals to safely update UI from background thread
    status_signal = pyqtSignal(str, str)
    
    def __init__(self, voice_engine):
        super().__init__()
        self.voice_engine = voice_engine
        # Re-route voice engine callbacks to emit PyQt signals
        self.voice_engine.callback = self.handle_callback

    def handle_callback(self, event_type, data):
        self.status_signal.emit(event_type, data)

    def run(self):
        # Start the background listening loop
        self.voice_engine.start_background_listening()
        self.exec()

class JarvisMainWindow(QMainWindow):
    def __init__(self, core_system):
        super().__init__()
        self.core = core_system
        self.initUI()
        
        # Start Voice Engine Thread
        self.voice_thread = VoiceThread(self.core['voice'])
        self.voice_thread.status_signal.connect(self.update_ui_from_voice)
        self.voice_thread.start()
        
        # Update system stats
        self.sys_timer = QTimer()
        self.sys_timer.timeout.connect(self.update_system_stats)
        self.sys_timer.start(2000)

    def initUI(self):
        self.setWindowTitle('JARVIS - Core System')
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet("""
            #Sidebar {
                background-color: rgba(10, 15, 25, 230);
                border-right: 2px solid rgba(0, 242, 254, 0.3);
            }
        """)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        
        # Logo
        self.logo = QLabel("J.A.R.V.I.S.")
        self.logo.setStyleSheet("color: #00f2fe; font-size: 32px; font-weight: bold; letter-spacing: 4px;")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(self.logo)
        self.sidebar_layout.addSpacing(30)
        
        # Buttons
        nav_buttons = ["Dashboard", "AI Chat", "System Monitor", "Settings"]
        self.btn_group = []
        for btn_name in nav_buttons:
            btn = QPushButton(btn_name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #a09bab;
                    font-size: 16px;
                    text-align: left;
                    padding: 15px 20px;
                    border: none;
                    border-left: 3px solid transparent;
                }
                QPushButton:hover {
                    background-color: rgba(0, 242, 254, 0.1);
                    color: #00f2fe;
                    border-left: 3px solid #00f2fe;
                }
            """)
            self.sidebar_layout.addWidget(btn)
            self.btn_group.append(btn)
            
        self.sidebar_layout.addStretch()
        
        # System Stats in Sidebar
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_label.setStyleSheet("color: #00f2fe; font-size: 14px;")
        self.ram_label = QLabel("RAM: 0%")
        self.ram_label.setStyleSheet("color: #00f2fe; font-size: 14px;")
        
        self.sidebar_layout.addWidget(self.cpu_label)
        self.sidebar_layout.addWidget(self.ram_label)
        
        # Content Area
        self.content_area = QFrame()
        self.content_area.setObjectName("ContentArea")
        self.content_area.setStyleSheet("""
            #ContentArea {
                background-color: rgba(15, 20, 35, 220);
            }
        """)
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Arc Reactor / Status Visualizer
        self.status_display = QLabel("SYSTEM STANDBY")
        self.status_display.setStyleSheet("color: rgba(0, 242, 254, 0.8); font-size: 48px; font-weight: bold;")
        self.status_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.status_display)
        
        # Subtitle Status
        self.sub_status = QLabel("Awaiting wake word 'Jarvis'...")
        self.sub_status.setStyleSheet("color: #a09bab; font-size: 18px;")
        self.sub_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.sub_status)
        
        # Assembly
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)
        
        # Global Stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
        """)

    def update_system_stats(self):
        monitor = self.core['system']
        cpu = monitor.get_cpu_usage()
        ram = monitor.get_ram_usage()
        self.cpu_label.setText(f"CPU: {cpu}%")
        self.ram_label.setText(f"RAM: {ram}%")

    def update_ui_from_voice(self, event_type, data):
        if event_type == "wake":
            self.status_display.setText("LISTENING")
            self.status_display.setStyleSheet("color: #00f2fe; font-size: 48px; font-weight: bold; text-shadow: 0 0 20px #00f2fe;")
            self.sub_status.setText("Yes Sir?")
        elif event_type == "command":
            self.sub_status.setText(f"Command: {data}")
            self.status_display.setText("PROCESSING")
            self.status_display.setStyleSheet("color: #ff007f; font-size: 48px; font-weight: bold;")
        elif event_type == "speak":
            self.status_display.setText("SPEAKING")
            self.status_display.setStyleSheet("color: #9b51e0; font-size: 48px; font-weight: bold;")
            self.sub_status.setText(data)
        elif event_type == "system":
            self.sub_status.setText(f"System: {data}")
            if "Missing" in data:
                self.status_display.setText("API KEY REQ")
                self.status_display.setStyleSheet("color: #ffaa00; font-size: 48px; font-weight: bold;")
