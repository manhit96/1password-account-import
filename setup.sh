#!/bin/bash

# Màu sắc cho output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function để in thông báo
print_status() {
    echo -e "${YELLOW}➜${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Kiểm tra OS
check_os() {
    print_status "Kiểm tra hệ điều hành..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_success "Đang chạy trên macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_success "Đang chạy trên Linux"
    else
        print_error "Hệ điều hành không được hỗ trợ"
        exit 1
    fi
}

# Kiểm tra và cài đặt Homebrew trên macOS
setup_homebrew() {
    if [[ "$OS" != "macos" ]]; then
        return
    fi

    print_status "Kiểm tra Homebrew..."
    if ! command -v brew &> /dev/null; then
        print_status "Cài đặt Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        print_success "Đã cài đặt Homebrew"
    else
        print_success "Homebrew đã được cài đặt"
    fi
}

# Kiểm tra và cài đặt Python
setup_python() {
    print_status "Kiểm tra Python..."
    
    if ! command -v python3 &> /dev/null; then
        print_status "Cài đặt Python..."
        if [[ "$OS" == "macos" ]]; then
            brew install python
        elif [[ "$OS" == "linux" ]]; then
            if command -v apt &> /dev/null; then
                sudo apt update
                sudo apt install -y python3 python3-pip python3-venv
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip python3-virtualenv
            else
                print_error "Không thể cài đặt Python. Vui lòng cài đặt thủ công."
                exit 1
            fi
        fi
        print_success "Đã cài đặt Python"
    else
        print_success "Python đã được cài đặt"
    fi
}

# Kiểm tra 1Password CLI
setup_1password_cli() {
    print_status "Kiểm tra 1Password CLI..."
    
    if ! command -v op &> /dev/null; then
        print_error "1Password CLI chưa được kích hoạt"
        echo -e "\nHướng dẫn kích hoạt 1Password CLI:"
        echo "1. Mở ứng dụng 1Password"
        echo "2. Vào Settings/Preferences (⌘,)"
        echo "3. Chọn tab Developer"
        echo "4. Bật tùy chọn 'Connect with 1Password CLI'"
        echo "5. Khởi động lại terminal và chạy lại script"
        exit 1
    else
        print_success "1Password CLI đã được kích hoạt"
    fi
}

# Tạo và kích hoạt môi trường ảo
setup_venv() {
    print_status "Thiết lập môi trường ảo..."
    
    # Tạo môi trường ảo nếu chưa tồn tại
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Đã tạo môi trường ảo"
    else
        print_success "Môi trường ảo đã tồn tại"
    fi
    
    # Kích hoạt môi trường ảo
    source venv/bin/activate
    
    # Cài đặt các thư viện cần thiết
    print_status "Cài đặt các thư viện Python..."
    pip install --upgrade pip
    pip install pyyaml
    print_success "Đã cài đặt các thư viện cần thiết"
}

# Tạo cấu trúc thư mục
setup_directories() {
    print_status "Tạo cấu trúc thư mục..."
    
    # Tạo thư mục input và output nếu chưa tồn tại
    mkdir -p input output
    print_success "Đã tạo thư mục input và output"
    
    # Kiểm tra file cấu hình
    if [ ! -f "account_types.yaml" ]; then
        print_error "Không tìm thấy file account_types.yaml"
        exit 1
    fi
    
    # Kiểm tra script chính
    if [ ! -f "account_import.py" ]; then
        print_error "Không tìm thấy file account_import.py"
        exit 1
    fi
}

# Chạy script chính
run_main_script() {
    print_status "Chạy script chính..."
    python3 account_import.py
}

# Main
main() {
    echo "=== BẮT ĐẦU THIẾT LẬP ==="
    
    # Kiểm tra và thiết lập các thành phần
    check_os
    setup_homebrew
    setup_python
    setup_1password_cli
    setup_venv
    setup_directories
    
    echo "=== THIẾT LẬP HOÀN TẤT ==="
    
    # Hỏi người dùng có muốn chạy script không
    read -p "Bạn có muốn chạy script ngay bây giờ không? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_main_script
    else
        print_status "Để chạy script sau, sử dụng lệnh: ./setup.sh run"
    fi
}

# Kiểm tra tham số command line
if [ "$1" == "run" ]; then
    setup_venv
    run_main_script
else
    main
fi 