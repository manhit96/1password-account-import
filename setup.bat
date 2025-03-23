@echo off
echo 1Password Account Import Tool Setup
echo =================================

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3 chưa được cài đặt
    echo Vui lòng cài đặt Python 3 từ https://www.python.org/downloads/
    exit /b 1
)

REM Kiểm tra pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip chưa được cài đặt
    echo Vui lòng cài đặt pip từ https://pip.pypa.io/en/stable/installation/
    exit /b 1
)

REM Tạo môi trường ảo
echo 🔧 Đang tạo môi trường ảo...
python -m venv venv

REM Kích hoạt môi trường ảo
echo 🔧 Đang kích hoạt môi trường ảo...
call venv\Scripts\activate.bat

REM Cài đặt các thư viện cần thiết
echo 📦 Đang cài đặt các thư viện cần thiết...
pip install -r requirements.txt

REM Tạo thư mục input và output nếu chưa tồn tại
echo 📁 Đang tạo thư mục input và output...
mkdir input 2>nul
mkdir output 2>nul

REM Kiểm tra 1Password CLI
where op >nul 2>&1
if errorlevel 1 (
    echo ❌ 1Password CLI chưa được cài đặt
    echo Vui lòng cài đặt từ: https://1password.com/downloads/command-line/
    exit /b 1
)

echo ✅ Cài đặt hoàn tất!
echo Để sử dụng tool:
echo 1. Đặt file dữ liệu vào thư mục input/
echo 2. Chạy lệnh: setup.bat run 