import os
import sys
import yaml
import shutil
import threading

from classes.notifications import Notificator

from PyQt5.QtCore import QObject, pyqtSignal


class Model(QObject):
    progress_changed = pyqtSignal(int) # Progress bar value change signal
    process_changed = pyqtSignal(str) # QLabel 'Процесс' text change signal
    update_complited = pyqtSignal(bool) # Update completion signal


    def __init__(self):
        """Initializes the Model."""
        super().__init__()

        self.current_program_path = self.__get_base_path() # Get the current program path
        self.config_data = self.__get_config_data() # Get data from the configuration file
        self.server_program_version = self.__get_server_program_version() # Get the server program version

    def __get_base_path(self):
        """Returns the base path of the executable or script.

        Returns:
            str: The absolute path to the program's base directory.
        """
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable) # Path for a compiled .exe file
        else:
            # Path for a regular .py script (project root)
            return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    def __get_config_data(self):
        """Reads and returns data from the configuration file (config.yaml).

        Returns:
            dict: A dictionary containing the configuration data.

        Raises:
            FileNotFoundError: If the config.yaml file is not found.
            IOError: If there is an error reading the configuration file.
        """
        config_file_path = os.path.join(self.current_program_path, "config.yaml") # The Way to the Config file

        if not os.path.exists(config_file_path): # ПRover the existence of a configuration file
            notification_text = f"Файл конфигурации не найден.\nПуть: {config_file_path}" # Notification text
            # We display a notification
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise FileNotFoundError(f"Файл конфигурации не найден. Путь: {config_file_path}")

        config_data = self.__read_yaml_file(config_file_path)
        if config_data is None:
            notification_text = f"Не удалось прочитать файл конфигурации.\nПуть: {config_file_path}"
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise IOError(f"Не удалось прочитать файл конфигурации: {config_file_path}")
        return config_data

    def __read_yaml_file(self, file_path):
        """Reads a YAML file with multiple encodings.

        Args:
            file_path (str): The path to the YAML file.

        Returns:
            dict: The loaded YAML data, or None if reading fails.
        """
        encodings = ['utf-8', 'cp1251', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as config_file:
                    return yaml.safe_load(config_file)
            except (UnicodeDecodeError, yaml.YAMLError):
                continue
        return None
        
    def __get_server_program_version(self):
        """Retrieves the program version from the server's configuration file.

        Returns:
            str: The version number of the program on the server.

        Raises:
            ValueError: If the server configuration file is not found or cannot be read.
        """
        server_config_file_path = os.path.join(self.config_data.get("server_program_path"), "config.yaml") # The path to the config file

        if not os.path.exists(server_config_file_path): # Check the existence of the config file
            notification_text = f"Файл конфигурации на сервере не найден.\nПуть: {server_config_file_path}"
            
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise ValueError(f"Файл конфигурации на сервере не найден.\nПуть: {server_config_file_path}")
        
        server_config_data = self.__read_yaml_file(server_config_file_path)
        if server_config_data is None:
            notification_text = f"Не удалось прочитать файл конфигурации на сервере.\nПуть: {server_config_file_path}"
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise ValueError(f"Не удалось прочитать файл конфигурации на сервере: {server_config_file_path}")
        
        return server_config_data.get("program_version_number") # Get the server program version
        
    def __perform_update(self):
        """Performs the program update by deleting old files and copying new ones.

        Raises:
            ValueError: If current_program_path or server_program_path are not set.
            FileNotFoundError: If current_program_path or server_program_path do not exist.
        """
        # Check that the current program path is set
        if not self.current_program_path or self.current_program_path is None:
            notification_text = "Текущий путь программы не установлен"
            # We display a notification
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise ValueError("Текущий путь программы не установлен")
        
        server_program_path = self.config_data.get("server_program_path") # Get the path to the program on the server

        # Check that the path to the program on the server is set
        if not server_program_path or server_program_path is None:
            notification_text = "Путь к программе на сервере не установлен"
            # We display a notification
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise ValueError("Путь к программе на сервере не установлен")
        
        if not os.path.exists(self.current_program_path): # We check the existence of the current path to the program
            notification_text = f"Текущий путь к программе не найден.\nПуть: {self.current_program_path}"
            # We display a notification
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise FileNotFoundError(f"Текущий путь к программе не найден. Путь: {self.current_program_path}")
        
        if not os.path.exists(server_program_path): # Check the existence of the path to the program on the server
            notification_text = f"Путь к прогамме на сервере не найден.\nПуть: {server_program_path}"
            # We display a notification
            Notificator.show_notification(notify_type="error", notify_title="Ошибка", notify_text=notification_text)
            raise FileNotFoundError(f"Путь к прогамме на сервере не найден. Путь: {server_program_path}")
        
        try:
            # Get the list of files in the current program path
            current_program_files = os.listdir(self.current_program_path)
            server_program_files = os.listdir(server_program_path) # Get the list of files in the program path on the server

            total_files = len(current_program_files) + len(server_program_files) # Total number of files
            files_processed = 0 # Number of processed files

            if total_files == 0: # If the number of files is 0, exit
                return

            # Delete old program files
            for file in current_program_files:

                if file == 'updater.exe': # Check that the file is not updater.exe
                    continue
                
                file_path = os.path.join(self.current_program_path, file)
                if os.path.isfile(file_path): # Check if it's a file
                    os.remove(file_path) # Delete the file

                elif os.path.isdir(file_path): # Check if it's a directory
                    shutil.rmtree(file_path) # Delete the directory

                files_processed += 1
                progress = int((files_processed / total_files) * 100)
                self.progress_changed.emit(progress) # Progress bar value change signal

                self.process_changed.emit(f"удаление файла - {file}") # Update text in QLabel 'Процесс'

            # Copy new program files
            if server_program_files: # Check if there are files in the program path on the server
                for file in server_program_files:
                    if file == 'updater.exe': # Check that the file is not updater.exe
                        continue

                    source_path = os.path.join(server_program_path, file)
                    destination_path = os.path.join(self.current_program_path, file)
                    
                    if os.path.isfile(source_path): # Check if it's a file
                        shutil.copy2(source_path, destination_path) # Copy the file

                    elif os.path.isdir(source_path): # Check if it's a directory
                        shutil.copytree(source_path, destination_path, dirs_exist_ok=True) # Copy the directory

                    files_processed += 1
                    progress = int((files_processed / total_files) * 100)
                    self.progress_changed.emit(progress) # A signal for changing the value of the progress bar
                    
                    self.process_changed.emit(f"копирование файла - {file}") # We update the text in QLabel 'Процесс'

            self.progress_changed.emit(100) # Fully fill the progress bar
            self.process_changed.emit("Программа успешно обновлена") # Update text in QLabel 'Процесс'

            self.update_complited.emit(True) # Update completion signal

        except Exception as e:
            self.update_complited.emit(False) # Update completion signal
        
    def perform_update_in_thread(self):
        """Launches the program update in a separate thread.

        Returns:
            threading.Thread: The created thread object.
        """
        thread = threading.Thread(target=self.__perform_update) # Create a thread
        thread.daemon = True
        thread.start()
        return thread
