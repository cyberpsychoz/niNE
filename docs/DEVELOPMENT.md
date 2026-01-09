# niNE Development Guide

## Overview
This document provides guidelines for developers working on the niNE game engine. It covers various aspects of development, from setting up your environment to contributing code and managing plugins.

## Getting Started
1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-repo/nine.git
   cd nine
   ```

2. **Install Dependencies**
   Ensure you have Python 3.8+ installed, then install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Your Environment**
   Configure your environment variables as needed for development.

## Contributing Code
1. **Fork the Repository**
   Fork the niNE repository on GitHub and clone your fork to your local machine.

2. **Create a New Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   Implement your changes, ensuring you follow the coding standards outlined below.

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add your descriptive message here"
   ```

5. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   Go to the niNE repository on GitHub, and create a pull request from your fork's branch.

## Coding Standards
- Follow PEP 8 for Python code.
- Use meaningful variable and function names.
- Write clear and concise comments where necessary.

## Plugin Development
1. **Plugin Structure**
   Plugins should be placed in the `nine/plugins/` directory. Each plugin should have its own subdirectory with a clear structure:
   ```
   nine/plugins/my_plugin/
       cl_module.py  # Client-side module
       sv_module.py  # Server-side module
       sh_config.py  # Shared configuration
       README.md     # Plugin documentation
   ```

2. **Plugin Lifecycle**
   - `on_load`: Called when the plugin is loaded.
   - `on_unload`: Called when the plugin is unloaded.

3. **Event Management**
   Use the `EventManager` to subscribe and post events between components.

## Adding New Features

### Dоработка плагина администрирования сервера
1. **Файлы для редактирования:**
   - nine/plugins/admin_manager/cl_ui.py
   - nine/plugins/admin_manager/sv_admin.py

2. **Описание изменений:**
   - Добавьте функциональность для управления администраторами.
   - Обновите UI для отображения и изменения прав администраторов.

3. **Шаги реализации:**
   - В `sv_admin.py` добавьте методы для добавления, удаления и проверки статуса администраторов.
   - В `cl_ui.py` создайте интерфейс для взаимодействия с сервером по управлению администраторами.

4. **Пример изменений:**
   ```python
   # nine/plugins/admin_manager/sv_admin.py
   def add_admin(self, player_id, admin_level=1):
       self.cursor.execute("INSERT INTO admins (player_id, admin_level) VALUES (?, ?)", (player_id, admin_level))
       self.conn.commit()

   def remove_admin(self, player_id):
       self.cursor.execute("DELETE FROM admins WHERE player_id = ?", (player_id,))
       self.conn.commit()

   def is_admin(self, player_id):
       self.cursor.execute("SELECT * FROM admins WHERE player_id = ?", (player_id,))
       return self.cursor.fetchone() is not None
   ```

   ```python
   # nine/plugins/admin_manager/cl_ui.py
   def toggle_admin_status(self, player_id):
       if self.is_admin(player_id):
           self.remove_admin(player_id)
       else:
           self.add_admin(player_id)

   def update_admin_list(self):
       admin_list = self.get_admin_list()
       for admin in admin_list:
           self.create_admin_entry(admin)
   ```

5. **Тестирование:**
   - Убедитесь, что добавление и удаление администраторов работают корректно.
   - Проверьте обновление UI после изменений.

6. **Документация:**
   - Обновите `README.md` в директории плагина с новыми функциями и инструкциями по использованию.

## Reporting Issues
If you encounter any issues or have suggestions for improvements, please create an issue on the GitHub repository.

## Contact
For further information or assistance, contact the niNE development team at [your-email@example.com].

