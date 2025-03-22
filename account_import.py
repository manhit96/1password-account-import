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
from datetime import datetime
from typing import Dict, List, Optional

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

def get_vault_info():
    """Get vault information from user"""
    print("\n🔐 Danh sách các vault có sẵn:")
    try:
        result = run_op_command(["op", "vault", "list", "--format=json"])
        if result and result.returncode == 0:
            vaults = json.loads(result.stdout)
            print("\nSTT | ID                            | NAME")
            print("-" * 70)
            for idx, vault in enumerate(vaults, 1):
                print(f"{idx:3} | {vault['id']:<30} | {vault['name']}")
            
            while True:
                print("\nNhập số thứ tự vault để chọn (1-{0}): ".format(len(vaults)), end="")
                choice = input().strip()
                
                if not choice:
                    print("❌ Vui lòng nhập số thứ tự vault")
                    continue
                
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(vaults):
                        selected_vault = vaults[idx-1]
                        print(f"✅ Đã chọn vault: {selected_vault['name']}")
                        return selected_vault['id']
                    else:
                        print("❌ Số thứ tự không hợp lệ")
                except ValueError:
                    print("❌ Vui lòng nhập số")
        else:
            print("❌ Không thể lấy danh sách vault")
            if result:
                print(result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách vault: {str(e)}")
        sys.exit(1)

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
        parts = line.strip().split(account_type["parser"]["delimiter"])
        data = {}
        
        # Map fields according to config
        for field_name, index in account_type["parser"]["mapping"].items():
            if index < len(parts):
                data[field_name] = parts[index].strip()
        
        # Validate required fields
        missing_fields = []
        for field in account_type["fields"]:
            if field["required"] and (field["name"] not in data or not data[field["name"]]):
                missing_fields.append(field["name"])
        
        if missing_fields:
            return None, f"Thiếu các trường: {', '.join(missing_fields)}"
            
        return data, None
        
    except Exception as e:
        return None, f"Lỗi khi parse dữ liệu: {str(e)}"

def add_to_1password(data: Dict, account_type: Dict, vault: str, notes: str = "") -> tuple:
    """Add a single item to 1Password"""
    try:
        # Create base command
        cmd = [
            "op", "item", "create",
            "--category", "login",
            "--title", f"{account_type['title_prefix']} {data['username']}",
            "--vault", vault,
            "--url", account_type["url"],
            "--format", "json"
        ]
        
        # Add fields based on config
        for field in account_type["fields"]:
            field_name = field["name"]
            if field_name in data and data[field_name]:  # Only add if field has value
                value = data[field_name].replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                
                # Handle OTP field differently
                if field["type"] == "otp":
                    cmd.append(f"totp={value}")
                else:
                    cmd.append(f"{field_name}[{field['type']}]={value}")
        
        # Add notes if provided
        if notes:
            cmd.append(f"notes[text]={notes}")
        
        result = run_op_command(cmd)
        
        if result and result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                print(f"✅ Đã thêm {data['username']} vào 1Password")
                return True, response.get('id')
            except json.JSONDecodeError as e:
                print(f"❌ Không thể parse JSON response cho {data['username']}")
                print(f"Response: {result.stdout}")
                return False, None
        else:
            print(f"❌ Không thể thêm {data['username']}")
            if result:
                print(f"Lỗi: {result.stderr}")
            return False, None
            
    except Exception as e:
        print(f"❌ Lỗi khi thêm {data['username']}: {str(e)}")
        return False, None

def ensure_directories():
    """Ensure input and output directories exist"""
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)

def get_input_files() -> List[str]:
    """Get all txt files from input directory"""
    input_files = glob.glob("input/*.txt")
    if not input_files:
        print("❌ Không tìm thấy file txt nào trong thư mục input!")
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

def process_file(filename: str, account_type: Dict, vault: str, notes: str = ""):
    """Process a single file"""
    print(f"\n📄 Đang xử lý file: {filename}")
    skipped_lines = []
    processed_count = 0
    total_lines = 0
    successful_items = []
    
    try:
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                if not line.strip():
                    continue
                
                # Parse and validate line
                data, error = parse_line(line, account_type)
                if error:
                    skipped_lines.append((line_num, line.strip(), error))
                    continue
                
                # Add to 1Password
                success, uuid = add_to_1password(data, account_type, vault, notes)
                if success:
                    successful_items.append((data["username"], uuid))
                    processed_count += 1
        
        print(f"\n✅ Hoàn thành: {processed_count}/{total_lines}")
        
        # Export results to CSV
        if successful_items:
            base_filename = os.path.splitext(os.path.basename(filename))[0]
            csv_filename = f"output/{base_filename}_result.csv"
            with open(csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Email', '1Password UUID'])
                writer.writerows(successful_items)
            print(f"\n📝 Đã xuất kết quả ra file: {csv_filename}")
    
    except FileNotFoundError:
        print(f"❌ File {filename} không tồn tại")
        return
    except Exception as e:
        print(f"❌ Lỗi khi xử lý file {filename}: {str(e)}")
        return
    
    # Print summary
    print(f"\n📊 Kết quả xử lý file {filename}:")
    print(f"   - Tổng số dòng: {total_lines}")
    print(f"   - Số tài khoản đã thêm: {processed_count}")
    print(f"   - Số dòng bị bỏ qua: {len(skipped_lines)}")
    
    if skipped_lines:
        print("\n⚠️ Các dòng bị bỏ qua:")
        for line_num, line, reason in skipped_lines:
            print(f"   Dòng {line_num}: {reason}")
            print(f"   Nội dung: {line}")
            print()

def select_account_type(account_types: Dict) -> Optional[Dict]:
    """Let user select account type"""
    print("\n📋 Các loại tài khoản có sẵn:")
    types_list = list(account_types.items())
    
    for idx, (name, config) in enumerate(types_list, 1):
        print(f"\n{idx}. {name.upper()}")
        print(f"   - URL: {config['url']}")
        print(f"   - Định dạng: {config['parser']['delimiter'].replace('|', 'dấu |')}")
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

def main():
    try:
        # Check 1Password CLI
        check_1password_cli()
        
        # Ensure directories exist
        ensure_directories()
        
        # Load account types
        account_types = load_account_types()
        
        # Get vault information
        vault = get_vault_info()
        
        # Get input files
        input_files = get_input_files()
        
        # Get notes from user
        notes = get_user_notes()
        
        # Show summary
        print(f"\n📋 Tóm tắt:")
        print(f"   - Vault đích: {vault}")
        print(f"   - Số file sẽ xử lý: {len(input_files)}")
        print(f"   - Các file: {', '.join(os.path.basename(f) for f in input_files)}")
        if notes:
            print(f"   - Ghi chú: {notes}")
        
        if not confirm_action("⚠️ Bạn có muốn tiếp tục không?", default=True):
            print("❌ Đã hủy thao tác")
            sys.exit(0)
        
        # Process each file
        print(f"\n🔍 Bắt đầu xử lý {len(input_files)} file:")
        for filename in input_files:
            # Get account type for this file
            account_type = get_account_type_for_file(filename, account_types)
            if not account_type:
                print(f"❌ Bỏ qua file {filename} do không xác định được loại tài khoản")
                continue
                
            # Process file
            process_file(filename, account_type, vault, notes)
            
    except KeyboardInterrupt:
        print("\n\n❌ Đã hủy thao tác bởi người dùng")
        sys.exit(0)

if __name__ == "__main__":
    main() 