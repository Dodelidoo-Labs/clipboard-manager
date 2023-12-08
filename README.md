# Clipboard Manager

Clipboard Manager is a cross-platform compatible Python application that manages clipboard history. It is built with PyQt5 and allows users to view, search, and manage their clipboard contents in an easy and efficient way. The application is designed to be unobtrusive and runs in the background, ready to be invoked with a simple shortcut.

## Features

- Cross-platform compatibility (tested on Linux, untested on other OSes).
- Real-time clipboard monitoring and history management.
- Search functionality for quick retrieval of clipboard items.
- Fast-scrolling through clipboard items.
- Frameless window design for a sleek look.
- Ability to copy items back to the clipboard with a single click or keypress.
- Endless history stored in  SQLite Database.

## Installation

### From source

To install Clipboard Manager, you will need to have Python, PyQt5, qt-material and appdirs installed on your system. Follow the steps below to set up the application:

1. Clone the repository to your local machine:
   ```sh
   git clone https://github.com/your-username/clipboard-manager.git
   cd clipboard-manager
   ```

2. Install the required dependencies:
   ```sh
   pip install PyQt5 qt_material appdirs
   ```

3. Run the application:
   ```sh
   python clipboard_manager.py
   ```

### Using the precompiled App

1. Simply download the clipboard-manager file present in the `/dist` directory and place it in a location of your choice.

## Usage

Upon running the application, Clipboard Manager will start in the background. To bring up the Clipboard Manager window, you will need to create a system shortcut that triggers the provided shell script `open.sh`.

### Adding a Shortcut

On Linux systems, you can set up a keyboard shortcut via your desktop environment's settings. The command to use for the shortcut will be the path to the `open.sh` script, for example:

```sh
/path/to/clipboard-manager/open.sh
```

Replace `/path/to/clipboard-manager/` with the actual directory where you cloned the Clipboard Manager repository.

Typically the shortcut would be `ctrl+shift+v` but you can of course use whatever you like.

### Adding to Startup

You should also add the Clipboard Manager to your system's startup applications to ensure it runs automatically when you log in.

## Contributing

Contributions are welcome! Please open an issue for any bug reports or feature suggestions, or submit a pull request if you'd like to contribute code.

## License

Clipboard Manager is licensed under the GNU General Public License v3.0 (GPL-3.0). For more details, please see the LICENSE file included in the repository.

## Acknowledgments

Please note that while the application is designed to be cross-platform, it has only been tested on Linux. Users on other operating systems are encouraged to test the application and report any issues.

Enjoy managing your clipboard with Clipboard Manager!