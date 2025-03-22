@echo off
setlocal enabledelayedexpansion

:: Màu sắc cho output
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "NC=[0m"

:: Function để in thông báo
:print_status
echo %YELLOW%➜%NC% %~1
exit /b

:print_success
echo %GREEN%✓%NC% %~1
exit /b

:print_error
echo %RED%✗%NC% %~1
exit /b

:: Kiểm tra Python
:check_python
call :print_status "Kiểm tra Python..."
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_status "Tải xuống Python..."
    curl -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    if %ERRORLEVEL% neq 0 (
        call :print_error "Không thể tải xuống Python"
        exit /b 1
    )
    
    call :print_status "Cài đặt Python..."
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    if %ERRORLEVEL% neq 0 (
        call :print_error "Không thể cài đặt Python"
        exit /b 1
    )
    del python_installer.exe
    call :print_success "Đã cài đặt Python"
) else (
    call :print_success "Python đã được cài đặt"
)
exit /b 0

:: Kiểm tra 1Password CLI
:check_1password
call :print_status "Kiểm tra 1Password CLI..."
op --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    call :print_error "1Password CLI chưa được kích hoạt"
    echo.
    echo Hướng dẫn kích hoạt 1Password CLI:
    echo 1. Mở ứng dụng 1Password
    echo 2. Vào Settings/Preferences
    echo 3. Chọn tab Developer
    echo 4. Bật tùy chọn 'Connect with 1Password CLI'
    echo 5. Khởi động lại terminal và chạy lại script
    exit /b 1
) else (
    call :print_success "1Password CLI đã được kích hoạt"
)
exit /b 0

:: Thiết lập môi trường ảo
:setup_venv
call :print_status "Thiết lập môi trường ảo..."

if not exist venv (
    python -m venv venv
    call :print_success "Đã tạo môi trường ảo"
) else (
    call :print_success "Môi trường ảo đã tồn tại"
)

call venv\Scripts\activate.bat

call :print_status "Cài đặt các thư viện Python..."
python -m pip install --upgrade pip
pip install pyyaml
call :print_success "Đã cài đặt các thư viện cần thiết"
exit /b 0

:: Tạo cấu trúc thư mục
:setup_directories
call :print_status "Tạo cấu trúc thư mục..."

if not exist input mkdir input
if not exist output mkdir output
call :print_success "Đã tạo thư mục input và output"

if not exist account_types.yaml (
    call :print_error "Không tìm thấy file account_types.yaml"
    exit /b 1
)

if not exist account_import.py (
    call :print_error "Không tìm thấy file account_import.py"
    exit /b 1
)
exit /b 0

:: Chạy script chính
:run_main_script
call :print_status "Chạy script chính..."
python account_import.py
exit /b 0

:: Main
:main
echo === BẮT ĐẦU THIẾT LẬP ===

call :check_python
if %ERRORLEVEL% neq 0 exit /b 1

call :check_1password
if %ERRORLEVEL% neq 0 exit /b 1

call :setup_venv
if %ERRORLEVEL% neq 0 exit /b 1

call :setup_directories
if %ERRORLEVEL% neq 0 exit /b 1

echo === THIẾT LẬP HOÀN TẤT ===

set /p REPLY="Bạn có muốn chạy script ngay bây giờ không? (y/N) "
if /i "%REPLY%"=="y" (
    call :run_main_script
) else (
    call :print_status "Để chạy script sau, sử dụng lệnh: setup.bat run"
)
exit /b 0

:: Entry point
if "%1"=="run" (
    call :setup_venv
    call :run_main_script
) else (
    call :main
) 