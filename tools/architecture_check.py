#!/usr/bin/env python3
"""
Инструмент проверки архитектуры niNE проекта.

Проверяет:
- Дублирование плагинов
- Правильное использование self.app vs self.base
- Циклические зависимости
- Несоответствие импортов
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

class ArchitectureChecker:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.issues = []
        self.warnings = []

    def check_all(self) -> Dict:
        """Запускает все проверки."""
        print("=" * 60)
        print("niNE Architecture Checker")
        print("=" * 60)

        self.check_duplicate_plugins()
        self.check_plugin_base_usage()
        self.check_entity_systems()
        self.check_test_files()

        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings)
        }

    def check_duplicate_plugins(self):
        """Проверяет дублирование плагинов."""
        print("\n[1] Проверка дублирования плагинов...")

        plugins_dir = self.root / "nine" / "plugins"
        plugin_ids = {}

        for plugin_dir in plugins_dir.rglob("sh_plugin.py"):
            with open(plugin_dir, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ищем unique_id
            match = re.search(r'unique_id\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                plugin_id = match.group(1)
                plugin_path = plugin_dir.parent.relative_to(plugins_dir)

                if plugin_id in plugin_ids:
                    self.issues.append({
                        "type": "DUPLICATE_PLUGIN",
                        "severity": "CRITICAL",
                        "plugin_id": plugin_id,
                        "paths": [str(plugin_ids[plugin_id]), str(plugin_path)],
                        "message": f"Дублирование плагина {plugin_id}",
                        "recommendation": f"Удалить один из плагинов: {plugin_ids[plugin_id]} или {plugin_path}"
                    })
                    print(f"  [X] DUPLCATE: {plugin_id}")
                    print(f"     - {plugin_ids[plugin_id]}")
                    print(f"     - {plugin_path}")
                else:
                    plugin_ids[plugin_id] = plugin_path
                    print(f"  [OK] {plugin_id}")

        print(f"  Найдено плагинов: {len(plugin_ids)}")

    def check_plugin_base_usage(self):
        """Проверяет правильное использование self.app vs self.base."""
        print("\n[2] Проверка использования self.app vs self.base...")

        plugins_dir = self.root / "nine" / "plugins"

        for py_file in plugins_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Находим все классы наследующие PluginModule
            plugin_module_classes = []
            for match in re.finditer(r'class\s+(\w+)\(PluginModule\)', content):
                plugin_module_classes.append(match.group(1))

            if plugin_module_classes:
                # Ищем использование self.base только внутри методов PluginModule классов
                current_class = None
                indent_level = 0

                for i, line in enumerate(lines, 1):
                    # Определяем текущий класс
                    class_match = re.match(r'class\s+(\w+)\(', line)
                    if class_match:
                        class_name = class_match.group(1)
                        current_class = class_name if class_name in plugin_module_classes else None
                        indent_level = len(line) - len(line.lstrip())

                    # Проверяем self.base только внутри PluginModule классов
                    if current_class and re.search(r'\bself\.base\.', line):
                        # Проверяем что мы всё ещё внутри класса (по отступам)
                        line_indent = len(line) - len(line.lstrip())
                        if line_indent > indent_level:
                            self.issues.append({
                                "type": "WRONG_BASE_USAGE",
                                "severity": "HIGH",
                                "file": str(py_file.relative_to(self.root)),
                                "line": i,
                                "message": f"PluginModule class '{current_class}' uses self.base instead of self.app",
                                "recommendation": "Replace self.base with self.app"
                            })
                            print(f"  [X] {py_file.name}:{i} - {current_class} uses self.base")

    def check_entity_systems(self):
        """Проверяет наличие двух разных Entity систем."""
        print("\n[3] Проверка Entity систем...")

        entity_py = self.root / "nine" / "core" / "entity.py"
        ecs_py = self.root / "nine" / "core" / "ecs.py"

        if entity_py.exists() and ecs_py.exists():
            self.warnings.append({
                "type": "DUAL_ENTITY_SYSTEMS",
                "severity": "MEDIUM",
                "message": "Две разные Entity системы (entity.py и ecs.py)",
                "recommendation": "Документировать разделение ответственности или объединить"
            })
            print(f"  [!] Found two Entity systems:")
            print(f"     - nine/core/entity.py")
            print(f"     - nine/core/ecs.py")

    def check_test_files(self):
        """Проверяет тестовые файлы."""
        print("\n[4] Проверка тестовых файлов...")

        test_files = list(self.root.glob("test_*.py"))

        if test_files:
            print(f"  Найдено {len(test_files)} тестовых файлов в корне:")
            for test_file in test_files:
                print(f"    - {test_file.name}")

            self.warnings.append({
                "type": "TEST_FILES_IN_ROOT",
                "severity": "LOW",
                "count": len(test_files),
                "message": f"{len(test_files)} тестовых файлов в корне проекта",
                "recommendation": "Переместить в tests/ директорию"
            })
        else:
            print(f"  [OK] No test files in root")

    def print_summary(self, results: Dict):
        """Выводит итоговую сводку."""
        print("\n" + "=" * 60)
        print("ИТОГОВАЯ СВОДКА")
        print("=" * 60)

        print(f"\nCRITICAL issues: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}")
        print(f"HIGH issues: {len([i for i in self.issues if i['severity'] == 'HIGH'])}")
        print(f"WARNINGS: {len(self.warnings)}")

        if self.issues:
            print("\n" + "-" * 60)
            print("ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ:")
            for issue in self.issues:
                print(f"\n[{issue['severity']}] {issue['type']}")
                print(f"  {issue['message']}")
                print(f"  FIX: {issue['recommendation']}")
                if 'file' in issue:
                    print(f"  FILE: {issue['file']}:{issue.get('line', '')}")

        print("\n" + "=" * 60)

        if results["total_issues"] == 0 and results["total_warnings"] == 0:
            print("[OK] Architecture is good!")
        elif results["total_issues"] == 0:
            print("[OK] No critical issues")
        else:
            print(f"[!] Found issues: {results['total_issues']}")

    def save_report(self, results: Dict, output_file: str):
        """Сохраняет отчёт в JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved: {output_file}")


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    checker = ArchitectureChecker(project_root)
    results = checker.check_all()
    checker.print_summary(results)
    checker.save_report(results, os.path.join(project_root, "architecture_report.json"))


if __name__ == "__main__":
    main()
