import subprocess
import sys
import os
import glob
import json
import time
import itertools
import threading
import yaml
import csv
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from file_handlers import get_file_handler

# Thêm các hằng số cho file tạm
TEMP_FILE = "temp_import_state.json"
TEMP_DIR = "temp"

def load_account_types() -> Dict:
    """Load account types from config file"""
    config_file = "account_types.yaml"
    if not os.path.exists(config_file):
        print(f"❌ Không tìm thấy file cấu hình {config_file}")
        print("Vui lòng tạo file cấu hình theo mẫu sau:")
        print("""
hotmail:
  title_prefix: "Hotmail:"
  url: "https://outlook.live.com"
  fields:
    - name: username
      type: text
      required: true
    - name: password
      type: password
      required: true
  parser:
    delimiter: "|"
    mapping:
      username: 0
      password: 1
        """)
        sys.exit(1)
        
    try:
        with open(config_file, 'r') as f:
            account_types = yaml.safe_load(f)
            if not account_types:
                print("❌ File cấu hình trống")
                sys.exit(1)
            return account_types
    except Exception as e:
        print(f"❌ Lỗi khi đọc file cấu hình: {str(e)}")
        sys.exit(1)

def run_op_command(cmd, timeout=30):
    """Run 1Password CLI command with timeout"""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"❌ Lệnh bị timeout sau {timeout} giây")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi thực thi lệnh: {str(e)}")
        return None

def check_1password_cli():
    """Check if 1Password CLI is installed and logged in"""
    try:
        version_result = run_op_command(["op", "--version"])
        if not version_result or version_result.returncode != 0:
            print("❌ 1Password CLI chưa được cài đặt")
            print("Vui lòng cài đặt theo hướng dẫn tại: https://1password.com/downloads/command-line/")
            sys.exit(1)
        
        whoami_result = run_op_command(["op", "whoami"])
        if whoami_result and whoami_result.returncode == 0:
            print("✅ Đã đăng nhập 1Password CLI")
            return True
            
        print("🔑 Chưa đăng nhập 1Password CLI. Đang thực hiện đăng nhập...")
        login_result = subprocess.run(["op", "signin"], capture_output=False, text=True)
        
        if login_result.returncode == 0:
            print("✅ Đăng nhập thành công")
            return True
        else:
            print("❌ Đăng nhập thất bại")
            print("Vui lòng đăng nhập thủ công bằng lệnh: op signin")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra 1Password CLI: {str(e)}")
        sys.exit(1)

def get_vault_list() -> List[Dict]:
    """Lấy danh sách vault từ 1Password"""
    try:
        result = run_op_command(["op", "vault", "list", "--format", "json"])
        if result and result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách vault: {str(e)}")
        return []

def get_vault_info() -> Optional[str]:
    """Lấy thông tin vault từ user"""
    global VAULT_LIST
    
    if not VAULT_LIST:
        VAULT_LIST = get_vault_list()
        if not VAULT_LIST:
            print("❌ Không thể lấy danh sách vault")
            return None
            
    print("\n🔐 Danh sách các vault có sẵn:")
    print("\nSTT | ID                            | NAME")
    print("-" * 70)
    
    for idx, vault in enumerate(VAULT_LIST, 1):
        print(f"{idx:3d} | {vault['id']:<30} | {vault['name']}")
    
    while True:
        try:
            choice = int(input("\nNhập số thứ tự vault để chọn (1-{}): ".format(len(VAULT_LIST))))
            if 1 <= choice <= len(VAULT_LIST):
                vault_id = VAULT_LIST[choice-1]['id']
                vault_name = VAULT_LIST[choice-1]['name']
                print(f"✅ Đã chọn vault: {vault_name}")
                return vault_id
            print("❌ Số thứ tự không hợp lệ")
        except ValueError:
            print("❌ Vui lòng nhập số")

def get_user_notes():
    """Get multiline notes from user"""
    print("\n📝 Nhập ghi chú cho các tài khoản:")
    print("- Nhập nội dung ghi chú của bạn, enter để xuống dòng")
    print("- Nhấn Ctrl+D (macOS/Linux) hoặc Ctrl+Z (Windows) để kết thúc\n")
    
    lines = []
    try:
        while True:
            try:
                line = input("> ").rstrip()
                if line:
                    lines.append(line)
            except EOFError:
                if lines:
                    print(f"\n✅ Đã lưu {len(lines)} dòng ghi chú")
                return "\n".join(lines)
    except KeyboardInterrupt:
        if lines:
            print(f"\n✅ Đã lưu {len(lines)} dòng ghi chú")
        return "\n".join(lines)

def parse_line(line: str, account_type: Dict) -> Optional[Dict]:
    """Parse a line based on account type config"""
    try:
        # Xử lý format mới
        if "format" in account_type:
            format_fields = account_type["format"].split(account_type.get("delimiter", "|"))
            delimiter = account_type.get("delimiter", "|")
            parts = line.strip().split(delimiter)
            
            if len(parts) < len(format_fields):
                return None, f"Thiếu dữ liệu. Cần {len(format_fields)} trường, chỉ có {len(parts)} trường"
                
            data = {}
            for i, field_name in enumerate(format_fields):
                if i < len(parts):
                    data[field_name] = parts[i].strip()
            
            # Validate required fields
            missing_fields = []
            for field in account_type["fields"]:
                if field["required"] and (field["name"] not in data or not data[field["name"]]):
                    missing_fields.append(field["name"])
            
            if missing_fields:
                return None, f"Thiếu các trường: {', '.join(missing_fields)}"
                
            return data, None
            
        return None, "Không tìm thấy định dạng trong cấu hình"
        
    except Exception as e:
        return None, f"Lỗi khi parse dữ liệu: {str(e)}"

def add_to_1password(data: Dict, account_type: Dict, vault: str, notes: str = "") -> tuple:
    """Add a single item to 1Password"""
    try:
        # Create base command
        cmd = [
            "op", "item", "create",
            "--category", account_type.get("category", "login"),  # Sử dụng category từ config
            "--vault", vault,
            "--format", "json"
        ]
        
        # Add title based on category
        title_field = "username"  # Mặc định là username
        if account_type.get("category") == "credit-card":
            title_field = "cardholder_name"
        elif account_type.get("category") == "bank-account":
            title_field = "account_name"
        elif account_type.get("category") == "identity":
            title_field = "full_name"
            
        title = data.get(title_field, "Unknown")
        cmd.append("--title")
        cmd.append(f"{account_type['title_prefix']} {title}")
        
        # Add URL if provided
        if "url" in account_type:
            cmd.append("--url")
            cmd.append(account_type["url"])
        
        # Add fields based on config
        for field in account_type["fields"]:
            field_name = field["name"]
            if field_name in data and data[field_name]:  # Only add if field has value
                value = data[field_name].replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                
                # Handle special fields
                if field["type"] == "otp":
                    cmd.append(f"totp={value}")
                elif field["type"] == "credit-card-number":
                    cmd.append(f"cardNumber={value}")
                elif field["type"] == "credit-card-type":
                    cmd.append(f"cardType={value}")
                elif field["type"] == "credit-card-expiry":
                    cmd.append(f"expiry={value}")
                elif field["type"] == "credit-card-cvv":
                    cmd.append(f"cvv={value}")
                else:
                    cmd.append(f"{field_name}[{field['type']}]={value}")
        
        # Add notes if provided
        if notes:
            cmd.append(f"notes[text]={notes}")
        
        result = run_op_command(cmd)
        
        if result and result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                print(f"✅ Đã thêm {title} vào 1Password")
                return True, response.get('id')
            except json.JSONDecodeError as e:
                print(f"❌ Không thể parse JSON response cho {title}")
                print(f"Response: {result.stdout}")
                return False, None
        else:
            print(f"❌ Không thể thêm {title}")
            if result:
                print(f"Lỗi: {result.stderr}")
            return False, None
            
    except Exception as e:
        print(f"❌ Lỗi khi thêm {title}: {str(e)}")
        return False, None

def ensure_directories():
    """Ensure input and output directories exist"""
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)

def get_input_files() -> List[str]:
    """Get all supported files from input directory"""
    input_files = []
    for ext in ['txt', 'csv', 'xlsx', 'xls']:
        input_files.extend(glob.glob(f"input/*.{ext}"))
    
    if not input_files:
        print("❌ Không tìm thấy file nào trong thư mục input!")
        print("Hỗ trợ các định dạng: .txt, .csv, .xlsx, .xls")
        sys.exit(1)
    return input_files

def detect_account_type(filename: str, account_types: Dict) -> Optional[str]:
    """Try to detect account type from filename"""
    basename = os.path.basename(filename).lower()
    for acc_type in account_types.keys():
        if acc_type.lower() in basename:
            return acc_type
    return None

def get_account_type_for_file(filename: str, account_types: Dict) -> Dict:
    """Get account type configuration for a file"""
    print(f"\n📄 File: {os.path.basename(filename)}")
    
    # Try to detect from filename
    detected_type = detect_account_type(filename, account_types)
    if detected_type:
        print(f"🔍 Đã phát hiện loại tài khoản: {detected_type.upper()}")
        if confirm_action("Bạn có muốn sử dụng loại tài khoản này không?"):
            return account_types[detected_type]
    
    # Let user select manually
    return select_account_type(account_types)

def process_file(filename: str, account_type: Dict, vault_id: str, notes: str) -> None:
    """Xử lý một file input và thêm các tài khoản vào 1Password"""
    try:
        # Lấy handler phù hợp cho file
        handler = get_file_handler(filename, account_type)
        if not handler:
            print(f"❌ Không hỗ trợ định dạng file: {filename}")
            return
            
        # Đọc dữ liệu từ file
        accounts = handler.read_data()
        if not accounts:
            print(f"❌ Không đọc được dữ liệu từ file: {filename}")
            return
            
        # Thêm từng tài khoản vào 1Password
        total = len(accounts)
        success = 0
        skipped = 0
        
        for idx, account in enumerate(accounts, 1):
            try:
                # Thêm tài khoản vào 1Password
                result, item_id = add_to_1password(account, account_type, vault_id, notes)
                if result:
                    success += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"❌ Lỗi khi xử lý tài khoản {idx}: {str(e)}")
                skipped += 1
                
        # Lưu kết quả vào file CSV
        output_file = os.path.join("output", f"{os.path.splitext(os.path.basename(filename))[0]}_result.csv")
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'status'])
            for account in accounts:
                writer.writerow([
                    account['username'],
                    account['password'],
                    'success' if account['username'] in [a['username'] for a in accounts[:success]] else 'skipped'
                ])
                
        print(f"\n✅ Hoàn thành: {success}/{total}")
        print(f"\n📝 Đã xuất kết quả ra file: {output_file}")
        
        # Lưu thông tin về file đã xử lý
        processed_files = []
        processed_lines = {}
        if os.path.exists(os.path.join(TEMP_DIR, TEMP_FILE)):
            with open(os.path.join(TEMP_DIR, TEMP_FILE), 'r') as f:
                state = json.load(f)
                processed_files = state.get('processed_files', [])
                processed_lines = state.get('processed_lines', {})
        
        if filename not in processed_files:
            processed_files.append(filename)
            processed_lines[filename] = idx  # Lưu số dòng đã xử lý
            save_import_state([], processed_files, processed_lines)
            
        print(f"\n📊 Kết quả xử lý file {filename}:")
        print(f"   - Tổng số dòng: {total}")
        print(f"   - Số tài khoản đã thêm: {success}")
        print(f"   - Số dòng bị bỏ qua: {skipped}")
        print(f"   - Đã xử lý đến dòng: {idx}")
        
    except Exception as e:
        print(f"❌ Có lỗi xảy ra: {str(e)}")
        raise

def select_account_type(account_types: Dict) -> Optional[Dict]:
    """Let user select account type"""
    print("\n📋 Các loại tài khoản có sẵn:")
    types_list = list(account_types.items())
    
    for idx, (name, config) in enumerate(types_list, 1):
        print(f"\n{idx}. {name.upper()}")
        print(f"   - URL: {config.get('url', 'N/A')}")
        print(f"   - Định dạng: {config.get('format', 'N/A')}")
        print("   - Các trường:")
        for field in config["fields"]:
            required = "(bắt buộc)" if field["required"] else "(tùy chọn)"
            print(f"     + {field['name']}: {field['type']} {required}")
    
    while True:
        print(f"\nChọn loại tài khoản (1-{len(types_list)}): ", end="")
        choice = input().strip()
        
        if not choice:
            print("❌ Vui lòng chọn loại tài khoản")
            continue
            
        try:
            idx = int(choice)
            if 1 <= idx <= len(types_list):
                selected_type = types_list[idx-1]
                print(f"✅ Đã chọn loại tài khoản: {selected_type[0].upper()}")
                return selected_type[1]
            else:
                print("❌ Lựa chọn không hợp lệ")
        except ValueError:
            print("❌ Vui lòng nhập số")
    
    return None

def confirm_action(prompt: str, default: bool = True) -> bool:
    """Ask for confirmation with default value"""
    yn = 'Y/n' if default else 'y/N'
    print(f"\n{prompt} ({yn}): ", end="")
    answer = input().strip().lower()
    if not answer:
        return default
    return answer.startswith('y')

def ensure_temp_dir():
    """Đảm bảo thư mục temp tồn tại"""
    os.makedirs(TEMP_DIR, exist_ok=True)

def save_import_state(file_configs: List[Dict], processed_files: List[str], processed_lines: Dict[str, int] = None) -> None:
    """Lưu trạng thái xử lý vào file tạm"""
    if processed_lines is None:
        processed_lines = {}
        
    state = {
        'file_configs': file_configs,
        'processed_files': processed_files,
        'processed_lines': processed_lines
    }
    
    with open(os.path.join(TEMP_DIR, TEMP_FILE), 'w') as f:
        json.dump(state, f, indent=2)

def load_import_state() -> Tuple[List[Dict], List[str], Dict[str, int]]:
    """Đọc trạng thái xử lý từ file tạm"""
    if not os.path.exists(os.path.join(TEMP_DIR, TEMP_FILE)):
        return None, None, None
        
    with open(os.path.join(TEMP_DIR, TEMP_FILE), 'r') as f:
        state = json.load(f)
        return (
            state.get('file_configs', []),
            state.get('processed_files', []),
            state.get('processed_lines', {})
        )

def clean_temp_files() -> None:
    """Xóa các file tạm"""
    try:
        temp_path = os.path.join(TEMP_DIR, TEMP_FILE)
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"\n🧹 Đã xóa file tạm: {temp_path}")
    except Exception as e:
        print(f"❌ Lỗi khi xóa file tạm: {str(e)}")

def process_input_files(input_files: List[str], account_types: Dict) -> None:
    """Xử lý từng file input và hỏi user về việc xử lý"""
    
    # Đảm bảo thư mục temp tồn tại
    ensure_temp_dir()
    
    # Thử đọc trạng thái trước đó
    file_configs, processed_files, processed_lines = load_import_state()
    if file_configs:
        print("\n📋 Tiếp tục xử lý từ trạng thái trước:")
        for idx, config in enumerate(file_configs, 1):
            if config['file'] not in processed_files:
                print(f"\n{idx}. File: {config['file']}")
                print(f"   - Loại tài khoản: {list(account_types.keys())[list(account_types.values()).index(config['account_type'])].upper()}")
                print(f"   - Vault: {config['vault_id']}")
                if config['notes']:
                    print(f"   - Ghi chú: {config['notes']}")
                if config['file'] in processed_lines:
                    print(f"   - Đã xử lý: {processed_lines[config['file']]} dòng")
    else:
        # Hiển thị danh sách file tìm thấy
        print("\n📁 Danh sách file tìm thấy:")
        for idx, file in enumerate(input_files, 1):
            print(f"{idx}. {file}")
        print()
        
        # Lưu thông tin xử lý cho từng file
        file_configs = []
        processed_files = []
        processed_lines = {}
        
        for file in input_files:
            print(f"\n{'='*50}")
            print(f"📄 Đang cấu hình file: {file}")
            print(f"{'='*50}")
            
            # Phát hiện loại tài khoản từ tên file
            account_type = get_account_type_for_file(file, account_types)
            if not account_type:
                print("⏭️  Bỏ qua file này")
                continue
                
            # Hiển thị thông tin file và hỏi user
            print(f"\n📝 Loại tài khoản: {list(account_types.keys())[list(account_types.values()).index(account_type)].upper()}")
            
            while True:
                choice = input("\nBạn có muốn xử lý file này không? (y/n): ").lower().strip()
                if choice in ['y', 'n']:
                    break
                print("❌ Vui lòng chọn 'y' hoặc 'n'")
                
            if choice == 'n':
                print("⏭️  Bỏ qua file này")
                continue
                
            # Lấy vault để lưu
            vault_id = get_vault_info()
            if not vault_id:
                print("⏭️  Bỏ qua file này")
                continue
                
            # Lấy ghi chú từ user
            notes = get_user_notes()
            
            # Lưu cấu hình
            file_configs.append({
                'file': file,
                'account_type': account_type,
                'vault_id': vault_id,
                'notes': notes
            })
            
            # Lưu trạng thái ngay sau khi lấy thông tin
            save_import_state(file_configs, processed_files, processed_lines)
            print(f"\n💾 Đã lưu thông tin cho file: {file}")
        
        # Hiển thị tóm tắt cấu hình
        if not file_configs:
            print("\n❌ Không có file nào được chọn để xử lý")
            return
            
        print("\n📋 Tóm tắt cấu hình:")
        for idx, config in enumerate(file_configs, 1):
            print(f"\n{idx}. File: {config['file']}")
            print(f"   - Loại tài khoản: {list(account_types.keys())[list(account_types.values()).index(config['account_type'])].upper()}")
            print(f"   - Vault: {config['vault_id']}")
            if config['notes']:
                print(f"   - Ghi chú: {config['notes']}")
        
        # Xác nhận trước khi xử lý
        if not confirm_action("\n⚠️ Bạn có muốn bắt đầu xử lý các file không?", default=True):
            print("❌ Đã hủy thao tác")
            return
    
    # Xử lý hàng loạt
    print("\n🔄 Bắt đầu xử lý hàng loạt...")
    try:
        for config in file_configs:
            if config['file'] in processed_files:
                print(f"\n⏭️  Bỏ qua file đã xử lý: {config['file']}")
                continue
                
            print(f"\n{'='*50}")
            print(f"📄 Đang xử lý file: {config['file']}")
            print(f"{'='*50}")
            
            # Xử lý file
            process_file(config['file'], config['account_type'], config['vault_id'], config['notes'])
            
            print(f"\n{'='*50}")
            print(f"✅ Hoàn thành xử lý file: {config['file']}")
            print(f"{'='*50}\n")
        
        print("\n✨ Đã hoàn thành xử lý tất cả các file!")
        
        # Xóa file tạm sau khi hoàn thành
        clean_temp_files()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Đã tạm dừng xử lý")
        print("💾 Đã lưu trạng thái để có thể tiếp tục sau")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Có lỗi xảy ra: {str(e)}")
        print("💾 Đã lưu trạng thái để có thể tiếp tục sau")
        sys.exit(1)

def main():
    """Hàm chính của chương trình"""
    global VAULT_LIST
    
    # Kiểm tra 1Password CLI
    if not check_1password_cli():
        return
        
    # Tạo các thư mục cần thiết
    ensure_directories()
    
    # Đọc cấu hình loại tài khoản
    account_types = load_account_types()
    if not account_types:
        return
        
    # Lấy danh sách file từ thư mục input
    input_files = get_input_files()
    if not input_files:
        return
        
    # Lấy danh sách vault ngay sau khi đăng nhập
    VAULT_LIST = get_vault_list()
    if not VAULT_LIST:
        print("❌ Không thể lấy danh sách vault")
        return
        
    # Xử lý từng file
    process_input_files(input_files, account_types)

if __name__ == "__main__":
    main() 