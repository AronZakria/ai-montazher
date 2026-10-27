#!/bin/sh
# Собирает вспомогательные программы на macOS Vision из .swift (нужен Xcode Command Line Tools: xcode-select --install).
# face и eyes montazh.py собирает и сам при первом запуске; остальные нужны режиссёру и оператору.
set -e
cd "$(dirname "$0")"
for t in face eyes gaze razmyt; do swiftc -O "$t.swift" -o "$t"; echo "собрано: tools/$t"; done
swiftc -O ekran/okna.swift -o ekran/okna && echo "собрано: tools/ekran/okna"
