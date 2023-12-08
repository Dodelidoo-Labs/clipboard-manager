import sqlite3
import sys
import re
import os
from PyQt5.QtCore import Qt, QEvent, QCoreApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QSlider, QGroupBox, QHBoxLayout, QWidget, QScrollArea, QLineEdit
from qt_material import apply_stylesheet
from urllib.parse import urlparse
import threading

from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtCore import Qt
import appdirs

def get_app_file_path(file_name):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, file_name)
    # user_data_dir = appdirs.user_data_dir("clipboard-manager", appauthor='Beda Schmid')
    # if not os.path.exists(user_data_dir):
    #     os.makedirs(user_data_dir)
    # return os.path.join(user_data_dir, file_name)

def get_db_file_path(file_name):
    user_data_dir = appdirs.user_data_dir("clipboard-manager", appauthor='Beda Schmid')
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    return os.path.join(user_data_dir, file_name)

class FastScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super(FastScrollArea, self).__init__(parent)
        self.setWidgetResizable(True)
        self.scroll_multiplier = 100  # Adjust this value to get the desired scroll speed

    def wheelEvent(self, event):
        delta = event.angleDelta().x()  # Get the horizontal component of the wheel movement
        if delta != 0:
            # Adjust the scroll speed
            steps = delta // 120  # Each step is 120 units (use integer division)
            new_value = self.horizontalScrollBar().value() - (steps * self.scroll_multiplier)
            self.horizontalScrollBar().setValue(int(new_value))  # Cast to int to avoid TypeError
            event.accept()  # Indicate that the event has been handled
        else:
            super(FastScrollArea, self).wheelEvent(event)

class ClipboardManager(QWidget):
    def __init__(self):
        super().__init__()

        # SQLite database setup
        self.conn = sqlite3.connect(get_db_file_path('clipboard.db'))
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clipboard
                              (data text)''')

        # Initialize clipboard data list
        self.clipboard_data = []
        self.search_indices = []

        # Set up the main layout
        self.mainLayout = QVBoxLayout()

        # Set up the search bar
        self.searchBar = QLineEdit()
        self.searchBar.textChanged.connect(self.search_clipboard_data)
        self.mainLayout.addWidget(self.searchBar)

        # Set up the slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.setFocusPolicy(Qt.StrongFocus)
		
        self.slider.valueChanged.connect(self.highlight_and_scroll)
        self.mainLayout.addWidget(self.slider)
        self.slider.setTickPosition(QSlider.TicksBelow)

        
        self.scrollArea = FastScrollArea()
        self.scrollAreaWidget = QWidget()
        self.scrollArea.setWidget(self.scrollAreaWidget)
        self.mainLayout.addWidget(self.scrollArea)

        # Add content to the scroll area
        self.box_layout = QHBoxLayout(self.scrollAreaWidget)

        # Finalize the window setup
        self.setLayout(self.mainLayout)
        screen_geometry = QApplication.desktop().screenGeometry()
        window_width = screen_geometry.width()
        window_height = 830
        x_position = 0
        y_position = screen_geometry.height() - window_height
        self.setGeometry(x_position, y_position, window_width, window_height)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(window_width, window_height)  # Set fixed window size to disable resize
        #self.setGeometry(0, 0, QApplication.desktop().screenGeometry().width(), 830)


        # Load initial clipboard data
        self.load_clipboard_data()

        # Connect signals
        QApplication.clipboard().dataChanged.connect(self.copy_clipboard_data)
        self.installEventFilter(self)
    
        apply_stylesheet(self, 'dark_lightgreen.xml', css_file=get_app_file_path('style.css'))
        self.start_listening_for_commands()
    
    def start_listening_for_commands(self):
        self.pipe_path = "/tmp/clipboard_manager_pipe"
        if not os.path.exists(self.pipe_path):
            os.mkfifo(self.pipe_path)
        self.listen_thread = threading.Thread(target=self.listen_for_commands, daemon=True)
        self.listen_thread.start()

    def listen_for_commands(self):
        while True:
            with open(self.pipe_path, "r") as pipe:
                for line in pipe:
                    command = line.strip()
                    if command == 'show':
                        self.show_window_command()

    def show_window_command(self):
		# Make sure to execute GUI operations in the main thread
        if self.isHidden():
            self.show()


    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                # Focus the slider before sending the event
                self.slider.setFocus()
                QCoreApplication.sendEvent(self.slider, event)
                return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.copy_active_content_to_clipboard()
            self.hide()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self.searchBar.setFocus()
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_active_content_from_database() 
        elif event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
            
    def delete_active_content_from_database(self):
        if not self.clipboard_data or self.active_box_index is None:
            return
        
        actual_index = self.active_box_index
        if self.search_indices:
            actual_index = self.search_indices[actual_index]
        
        if actual_index < len(self.clipboard_data):
            content = self.clipboard_data.pop(actual_index)
            self.cursor.execute("DELETE FROM clipboard WHERE data = ?", (content,))
            self.conn.commit()
            self.search_indices = [idx for idx in self.search_indices if idx != actual_index]
            self.search_indices = [idx - 1 if idx > actual_index else idx for idx in self.search_indices]
            self.update_display_after_deletion()

    def update_display_after_deletion(self):
        self.slider.setMaximum(len(self.clipboard_data) - 1)
        self.active_box_index = max(0, min(self.active_box_index, self.slider.maximum()))  # Ensure active_box_index is valid
        self.display_clipboard_data()
        self.highlight_and_scroll(self.active_box_index)

    def copy_active_content_to_clipboard(self):
    # Check if there is any data in the clipboard list
        if not self.clipboard_data or self.active_box_index is None:
            return
        
        actual_index = self.active_box_index
		# Get the active item's content based on the slider's current value
        if self.search_indices:
            actual_index = self.search_indices[actual_index]

        if actual_index < len(self.clipboard_data):
            content = self.clipboard_data[actual_index]
            clipboard = QApplication.clipboard()
            clipboard.dataChanged.disconnect(self.copy_clipboard_data) 
            clipboard.setText(content)
            clipboard.dataChanged.connect(self.copy_clipboard_data)
            
    def on_box_clicked(self, event, index):
        if event.button() == Qt.LeftButton:
            self.active_box_index = index  # Update the active index to the clicked box's index
            self.highlight_and_scroll(index)  # Call the highlighting function
            self.copy_active_content_to_clipboard()  # Copy the content to the clipboard
            event.accept()
            self.hide()

    def create_box(self, data_string, index):
        label = QLabel()
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        box = QGroupBox()
        box.setFixedSize(600, 600)
        box_layout_inner = QVBoxLayout() # Create a new layout for each box
        box_layout_inner.addWidget(label)
        box.setLayout(box_layout_inner)
        if self.is_color(data_string):
            box.setStyleSheet(f"background-color: {data_string};")
            label.setText(data_string)

        elif self.is_url(data_string):
            box.setStyleSheet("background-color: rgba(0,0,255,0.16);")
            label.setText(data_string)

        elif re.search(r'.(jpg|jpeg|png|gif)$', data_string):
            pixmap = QPixmap()
            pixmap.load(data_string)
            if pixmap.width() >= 600 and pixmap.height() >= 600:
                x = (pixmap.width() - 600) // 2
                y = (pixmap.height() - 600) // 2
                pixmap = pixmap.copy(x, y, 600, 600)
                label.setPixmap(pixmap)
            box_layout_inner.addWidget(label)

        else:
            label.setText(data_string)
            
        box.mousePressEvent = lambda event, idx=index: self.on_box_clicked(event, idx)          
        self.box_layout.addWidget(box)

    def highlight_and_scroll(self, value):
        self.active_box_index = value
        # Highlight the active box
        for i in range(self.box_layout.count()):
            box = self.box_layout.itemAt(i).widget()
            if i == value:
                box.setStyleSheet("background-color: rgba(0,255,0,0.16);")
                # Scroll the box into view
                self.scrollArea.ensureWidgetVisible(box)
            else:
                box.setStyleSheet("background-color: rgba(0,0,0,0.16);")

    def load_clipboard_data(self):
        self.cursor.execute("SELECT * FROM clipboard")
        data = self.cursor.fetchall()
        data.reverse()

        for row in data:
            self.clipboard_data.append(row[0])

        self.slider.setMaximum(len(self.clipboard_data) - 1)
        self.slider.setValue(0)
        self.display_clipboard_data()
        self.highlight_and_scroll(self.slider.value())

    def is_color(self, code):
        if len(code) == 6:
            try:
                int(code, 16)
                return True
            except ValueError:
                return False 
        elif len(code) == 7 and code[0] == '#':
            try:
                int(code[1:], 16)
                return True
            except ValueError:
                return False
        else:
            return False

    def is_url(self, s):
        return bool(urlparse(s).netloc)

    def copy_clipboard_data(self):
        clipboard = QApplication.clipboard()
        data = clipboard.text()
        if data.strip() == "":
            return
        self.clipboard_data.insert(0, data)

        self.cursor.execute("INSERT INTO clipboard VALUES (?)", (data,))
        self.conn.commit()
        
        self.slider.setMaximum(len(self.clipboard_data) - 1)
        self.display_clipboard_data()
        self.highlight_and_scroll(self.slider.value())  # Add this line to call the new function

    def display_clipboard_data(self):
        self.cursor.execute("SELECT * FROM clipboard")
        data = self.cursor.fetchall()
        data.reverse()
        # Clear the layout
        while self.box_layout.count():
            item = self.box_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add boxes
        for i in range(len(self.clipboard_data)):
            if i < len(data):
                data_string = str(data[i][0])
                self.create_box(data_string, i)

        self.scrollArea.setWidget(self.scrollAreaWidget)

    def search_clipboard_data(self):
        search_text = self.searchBar.text().lower()  # Get the text from the search bar and convert to lower case for case insensitive search
        self.cursor.execute("SELECT * FROM clipboard")
        data = self.cursor.fetchall()
        data.reverse()
        # Clear the layout
        while self.box_layout.count():
            item = self.box_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.search_indices = []  # Reset the search_indices list
    
        for i, row in enumerate(data):  # Enumerate over the data to get indices
            data_string = str(row[0])
            if search_text in data_string.lower():
                self.create_box(data_string, i)
                self.search_indices.append(i)
                
        num_boxes = self.box_layout.count()
        self.slider.setMaximum(max(0, num_boxes - 1))  # Ensure the maximum value is not negative
        self.slider.setValue(0)
        
        self.scrollArea.setWidget(self.scrollAreaWidget)
        self.highlight_and_scroll(self.slider.value())  # Highlight the first result

# Initialize and run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClipboardManager()
    #window.show()
    sys.exit(app.exec_())