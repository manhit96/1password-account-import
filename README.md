# 1Password Account Import Tool

Tool để import tài khoản vào 1Password với các tính năng:
- Hỗ trợ nhiều loại tài khoản (Hotmail, Gmail, ...)
- Tự động phát hiện loại tài khoản từ tên file
- Xử lý hàng loạt file cùng lúc
- Export kết quả ra file CSV

## Yêu cầu
- Python 3.8+
- 1Password Desktop với CLI được kích hoạt

## Cài đặt

### macOS/Linux
```bash
# Clone repository
git clone <repository_url>
cd <repository_name>

# Chạy script setup
./setup.sh
```

### Windows
```batch
# Clone repository
git clone <repository_url>
cd <repository_name>

# Chạy script setup
setup.bat
```

## Kích hoạt 1Password CLI

1. Mở ứng dụng 1Password
2. Vào Settings/Preferences (⌘,)
3. Chọn tab Developer
4. Bật tùy chọn "Connect with 1Password CLI"
5. Khởi động lại terminal

## Sử dụng

1. Đặt file dữ liệu vào thư mục `input/`
   - Đặt tên file theo loại tài khoản để tự động phát hiện
   - Ví dụ: `hotmail_accounts.txt`, `gmail_list.txt`

2. Chạy script:
   ```bash
   # macOS/Linux
   ./setup.sh run
   
   # Windows
   setup.bat run
   ```

3. Kết quả sẽ được lưu vào thư mục `output/`

## Cấu hình loại tài khoản

File `account_types.yaml` chứa cấu hình cho các loại tài khoản:
```yaml
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
    - name: otp
      type: otp
      required: false
```

## Định dạng file input

### Hotmail
```
email|password|refresh_token|client_id|otp_secret
```

### Gmail
```
email,password,recovery_email,otp_secret
```

## License
Private repository - All rights reserved 