#!/usr/bin/env python3
"""
UI System Checker for niNE

Проверяет UI компоненты на распространённые проблемы:
- Неправильное позиционирование
- Некорректные frameSize
- Проблемы с масштабированием
- Конфликты элементов
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class UIChecker:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.issues = []
        self.warnings = []

    def check_all(self) -> Dict:
        """Запускает все проверки UI."""
        print("=" * 60)
        print("niNE UI System Checker")
        print("=" * 60)

        self.check_button_positioning()
        self.check_frame_sizes()
        self.check_hardcoded_positions()
        self.check_font_configuration()

        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "total_issues": len(self.issues),
            "total_warnings": len(self.warnings)
        }

    def check_button_positioning(self):
        """Проверяет позиционирование кнопок."""
        print("\n[1] Checking button positioning...")

        # Проверка character select
        char_select = self.root / "nine" / "plugins" / "dnd" / "cl_character_select.py"
        if char_select.exists():
            with open(char_select, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Проверяем delete button
            for i, line in enumerate(lines, 1):
                # Ищем проблемные паттерны
                if 'DirectButton' in line or 'BG1Button' in line:
                    # Проверяем следующие 20 строк на проблемы
                    block = '\n'.join(lines[i:min(i+20, len(lines))])

                    # Проблема: scale слишком маленький с большим frameSize
                    scale_match = re.search(r'scale\s*=\s*([0-9.]+)', block)
                    frame_match = re.search(r'frameSize\s*=\s*\(([^)]+)\)', block)

                    if scale_match and frame_match:
                        scale = float(scale_match.group(1))
                        frame_str = frame_match.group(1)
                        frame_vals = [float(x.strip()) for x in frame_str.split(',')]

                        if len(frame_vals) == 4:
                            width = (frame_vals[1] - frame_vals[0]) * scale
                            height = (frame_vals[3] - frame_vals[2]) * scale

                            # Слишком маленькая кнопка
                            if width < 0.02 or height < 0.02:
                                self.warnings.append({
                                    "type": "SMALL_BUTTON",
                                    "file": str(char_select.relative_to(self.root)),
                                    "line": i,
                                    "message": f"Button too small: {width:.3f}x{height:.3f}",
                                    "scale": scale,
                                    "frameSize": frame_str
                                })
                                print(f"  [!] Line {i}: Button may be too small ({width:.3f}x{height:.3f})")

        print(f"  Checked {char_select.name}")

    def check_frame_sizes(self):
        """Проверяет корректность frameSize."""
        print("\n[2] Checking frameSize values...")

        ui_files = list((self.root / "nine" / "ui").rglob("*.py"))
        plugin_ui = list((self.root / "nine" / "plugins").rglob("cl_*.py"))

        all_files = ui_files + plugin_ui
        problematic = 0

        for ui_file in all_files:
            with open(ui_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ищем frameSize с экстремальными значениями
            for match in re.finditer(r'frameSize\s*=\s*\(([^)]+)\)', content):
                frame_str = match.group(1)
                try:
                    vals = [float(x.strip()) for x in frame_str.split(',')]
                    if len(vals) == 4:
                        # Проверяем на слишком большие значения (> 10.0)
                        if any(abs(v) > 10.0 for v in vals):
                            problematic += 1
                            print(f"  [!] {ui_file.name}: Large frameSize values {frame_str}")
                except:
                    pass

        print(f"  Checked {len(all_files)} UI files, found {problematic} potential issues")

    def check_hardcoded_positions(self):
        """Проверяет хардкодированные позиции."""
        print("\n[3] Checking for hardcoded positions...")

        # Проверяем Combat UI
        combat_files = [
            self.root / "nine" / "plugins" / "combat" / "cl_action_bar.py",
            self.root / "nine" / "plugins" / "combat" / "cl_initiative_display.py",
        ]

        hardcoded_count = 0
        for combat_file in combat_files:
            if not combat_file.exists():
                continue

            with open(combat_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                # Ищем pos= с абсолютными значениями вне функций масштабирования
                if 'pos=' in line and '(' in line:
                    # Проверяем что это не использует UIConfig или ScaledValue
                    if 'UIConfig' not in line and 'ScaledValue' not in line:
                        pos_match = re.search(r'pos\s*=\s*\(([^)]+)\)', line)
                        if pos_match:
                            pos_str = pos_match.group(1)
                            # Проверяем есть ли литеральные числа
                            if re.search(r'-?[0-9]+\.[0-9]+', pos_str):
                                hardcoded_count += 1
                                self.warnings.append({
                                    "type": "HARDCODED_POSITION",
                                    "file": str(combat_file.relative_to(self.root)),
                                    "line": i,
                                    "position": pos_str
                                })
                                print(f"  [!] {combat_file.name}:{i} hardcoded pos={pos_str}")

        print(f"  Found {hardcoded_count} hardcoded positions")

    def check_font_configuration(self):
        """Проверяет конфигурацию шрифтов."""
        print("\n[4] Checking font configuration...")

        manager_file = self.root / "nine" / "ui" / "manager.py"
        theme_file = self.root / "nine" / "ui" / "theme.py"

        issues = []

        # Проверяем manager.py
        if manager_file.exists():
            with open(manager_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Проверяем что fallback использует те же параметры
            if 'setPixelsPerUnit(100)' in content and 'NineTheme.FONT_PIXELS_PER_UNIT' in content:
                issues.append("manager.py: Fallback font uses different setPixelsPerUnit")
                print(f"  [!] Fallback font configuration mismatch")

        # Проверяем theme.py
        if theme_file.exists():
            with open(theme_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'FONT_USE_NEAREST' in content:
                print(f"  [OK] FONT_USE_NEAREST defined in theme.py")
            else:
                issues.append("theme.py: FONT_USE_NEAREST not defined")
                print(f"  [!] FONT_USE_NEAREST not found")

        if not issues:
            print(f"  [OK] Font configuration looks good")

    def print_summary(self, results: Dict):
        """Выводит итоговую сводку."""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        print(f"\nIssues: {results['total_issues']}")
        print(f"Warnings: {results['total_warnings']}")

        if results["total_issues"] == 0 and results["total_warnings"] == 0:
            print("\n[OK] UI system looks good!")
        else:
            print(f"\n[!] Found {results['total_issues'] + results['total_warnings']} potential issues")

    def save_report(self, results: Dict, output_file: str):
        """Сохраняет отчёт в JSON."""
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved: {output_file}")


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    checker = UIChecker(project_root)
    results = checker.check_all()
    checker.print_summary(results)
    checker.save_report(results, os.path.join(project_root, "ui_check_report.json"))


if __name__ == "__main__":
    main()
