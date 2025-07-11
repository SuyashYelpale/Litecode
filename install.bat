@echo off
python -m venv venv > nul
call venv\Scripts\activate > nul
pip install -r requirements.txt > nul
mkdir app\data 2> nul
wscript create_shortcut.vbs > nul
start run.bat