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

File `account_types.yaml` chứa cấu hình cho các loại tài khoản. Bạn có thể tùy chỉnh hoặc thêm mới các loại tài khoản bằng cách chỉnh sửa file này.

### Cấu trúc cơ bản
```yaml
account_type:
  category: "login"              # Loại item trong 1Password (login, password, credit-card, etc.)
  title_prefix: "Tên hiển thị:"  # Tiền tố hiển thị trong 1Password
  url: "https://example.com"      # URL đăng nhập của dịch vụ
  fields:                         # Danh sách các trường thông tin
    - name: field_name           # Tên trường
      type: field_type          # Loại trường (text, password, otp, url, etc.)
      required: true/false      # Bắt buộc hay không
      default: "giá trị"        # Giá trị mặc định (tùy chọn)
```

### Các loại item (category) được hỗ trợ:
- `login`: Đăng nhập website/dịch vụ
- `password`: Mật khẩu đơn giản
- `credit-card`: Thẻ tín dụng
- `bank-account`: Tài khoản ngân hàng
- `identity`: Thông tin cá nhân
- `secure-note`: Ghi chú bảo mật
- `software-license`: Giấy phép phần mềm
- `ssh-key`: Khóa SSH
- `database`: Thông tin cơ sở dữ liệu
- `api-credential`: Thông tin xác thực API
- `wifi`: Thông tin mạng WiFi

> Xem thêm danh sách đầy đủ các loại item và cách sử dụng trong [tài liệu chính thức của 1Password](https://developer.1password.com/docs/cli/reference/management-commands/itemtemplate#item-categories)

### Các loại trường (field_type) được hỗ trợ:
- `text`: Văn bản thông thường
- `password`: Mật khẩu (được mã hóa)
- `otp`: Mã xác thực 2 lớp (TOTP)
- `url`: Đường dẫn website
- `email`: Địa chỉ email
- `phone`: Số điện thoại
- `date`: Ngày tháng
- `number`: Số
- `multiline`: Văn bản nhiều dòng
- `address`: Địa chỉ
- `credit-card`: Thông tin thẻ tín dụng
- `bank-account`: Thông tin tài khoản ngân hàng
- `ssh-key`: Khóa SSH
- `note`: Ghi chú
- `concealed`: Dữ liệu được ẩn
- `menu`: Danh sách lựa chọn
- `string`: Chuỗi ký tự

> Xem thêm danh sách đầy đủ các loại trường và cách sử dụng trong [tài liệu chính thức của 1Password](https://developer.1password.com/docs/cli/reference/management-commands/itemtemplate#field-types)

### Ví dụ cấu hình cho các dịch vụ phổ biến:

```yaml
hotmail:
  category: "login"
  title_prefix: "Hotmail:"
  url: "https://outlook.live.com"
  fields:
    - name: username
      type: email
      required: true
    - name: password
      type: password
      required: true
    - name: otp
      type: otp
      required: false

gmail:
  category: "login"
  title_prefix: "Gmail:"
  url: "https://gmail.com"
  fields:
    - name: username
      type: email
      required: true
    - name: password
      type: password
      required: true
    - name: recovery_email
      type: email
      required: false
    - name: otp_secret
      type: otp
      required: false

credit_card:
  category: "credit-card"
  title_prefix: "Credit Card:"
  fields:
    - name: card_number
      type: credit-card-number
      required: true
    - name: card_type
      type: credit-card-type
      required: true
    - name: expiry
      type: credit-card-expiry
      required: true
    - name: cvv
      type: credit-card-cvv
      required: true
    - name: cardholder_name
      type: text
      required: true
```

## Định dạng file input

File input cần được đặt trong thư mục `input/` và đặt tên theo loại tài khoản (ví dụ: `hotmail_accounts.txt`, `gmail_list.txt`).

### Cấu trúc chung
- Mỗi dòng chứa thông tin của một tài khoản
- Các trường được phân tách bằng dấu phẩy (,) hoặc dấu gạch đứng (|)
- Thứ tự các trường phải khớp với cấu hình trong `account_types.yaml`

### Ví dụ cho các dịch vụ phổ biến:

#### Hotmail
```
email@hotmail.com|password123|refresh_token|client_id|otp_secret
```

#### Gmail
```
email@gmail.com,password123,recovery@gmail.com,otp_secret
```

### Thêm loại tài khoản mới

1. Thêm cấu hình mới vào file `account_types.yaml`
2. Tạo file input với định dạng tương ứng
3. Đặt tên file theo quy tắc: `[account_type]_accounts.txt`

### Lưu ý
- File input nên được mã hóa UTF-8
- Không sử dụng dấu phẩy hoặc dấu gạch đứng trong giá trị các trường
- Các trường bắt buộc phải được điền đầy đủ
- Các trường không bắt buộc có thể để trống

## License
Private repository - All rights reserved 