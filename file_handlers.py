from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Optional, Tuple
import csv

class FileHandler(ABC):
    """Base class for file handlers"""
    
    def __init__(self, filename: str, account_type: Dict):
        self.filename = filename
        self.account_type = account_type
    
    @abstractmethod
    def read_data(self) -> List[Dict]:
        """Read data from file and return list of dictionaries"""
        pass
    
    @abstractmethod
    def write_results(self, results: List[Tuple[str, str]], output_file: str):
        """Write results to output file"""
        pass

    def validate_data(self, data: List[Dict], account_type: Dict) -> Tuple[List[Dict], List[Tuple[int, str, str]]]:
        """Validate data against account type configuration"""
        valid_data = []
        errors = []
        
        for idx, row in enumerate(data, 1):
            # Check required fields
            missing_fields = []
            for field in account_type["fields"]:
                if field["required"] and (field["name"] not in row or not row[field["name"]]):
                    missing_fields.append(field["name"])
            
            if missing_fields:
                errors.append((idx, str(row), f"Thiếu các trường: {', '.join(missing_fields)}"))
                continue
                
            valid_data.append(row)
            
        return valid_data, errors

    def _create_custom_field(self, field_name: str) -> Dict:
        """Tạo custom field mới với tên tương ứng"""
        return {
            "name": field_name,
            "type": "text",  # Mặc định là text
            "required": False,
            "custom": True  # Đánh dấu là custom field
        }

class TextFileHandler(FileHandler):
    """Handler for text files"""
    
    def read_data(self) -> List[Dict]:
        data = []
        try:
            # Kiểm tra format và delimiter trong account_type
            if "format" not in self.account_type or not self.account_type["format"]:
                print("❌ Thiếu cấu hình format cho file text")
                return []
                
            delimiter = self.account_type.get("delimiter", "|")
            format_fields = self.account_type["format"].split(delimiter)
            
            with open(self.filename, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        parts = line.strip().split(delimiter)
                        
                        # Kiểm tra số lượng trường
                        if len(parts) < len(format_fields):
                            print(f"❌ Dòng {line_num}: Thiếu dữ liệu - cần {len(format_fields)} trường nhưng chỉ có {len(parts)} trường")
                            continue
                        
                        # Map dữ liệu theo format
                        row_data = {}
                        for i, field in enumerate(format_fields):
                            row_data[field] = parts[i].strip()
                            
                        data.append(row_data)
                        
            return data
            
        except Exception as e:
            print(f"❌ Lỗi khi đọc file text: {str(e)}")
            return []
    
    def write_results(self, results: List[Tuple[str, str]], output_file: str):
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Title', '1Password UUID'])
            writer.writerows(results)

class ExcelFileHandler(FileHandler):
    """Handler for Excel files"""
    
    def read_data(self) -> List[Dict]:
        try:
            # Đọc file Excel với pandas
            df = pd.read_excel(self.filename)
            
            # Tạo custom field cho các cột chưa được khai báo
            existing_fields = [f["name"] for f in self.account_type["fields"]]
            for column in df.columns:
                if column not in existing_fields:
                    self.account_type["fields"].append(self._create_custom_field(str(column)))
            
            # Kiểm tra các cột bắt buộc
            required_fields = [f["name"] for f in self.account_type["fields"] if f["required"]]
            missing_columns = [field for field in required_fields if field not in df.columns]
            if missing_columns:
                print(f"❌ Thiếu các cột bắt buộc: {', '.join(missing_columns)}")
                return []
            
            # Xử lý từng dòng dữ liệu
            data = []
            for idx, row in df.iterrows():
                item = {}
                for field in self.account_type["fields"]:
                    field_name = field["name"]
                    if field_name in df.columns:
                        value = row[field_name]
                        # Chuyển đổi tất cả giá trị thành string và loại bỏ khoảng trắng
                        item[field_name] = str(value).strip() if pd.notna(value) else ""
                    else:
                        item[field_name] = ""
                data.append(item)
            
            return data
            
        except Exception as e:
            print(f"❌ Lỗi khi đọc file Excel: {str(e)}")
            return []
    
    def write_results(self, results: List[Tuple[str, str]], output_file: str):
        # Chuyển đổi kết quả thành DataFrame
        df = pd.DataFrame(results, columns=['Title', '1Password UUID'])
        # Lưu ra file Excel
        df.to_excel(output_file, index=False)

class CSVFileHandler(FileHandler):
    """Handler for CSV files"""
    
    def read_data(self) -> List[Dict]:
        try:
            # Đọc file CSV với pandas
            df = pd.read_csv(self.filename)
            
            # Tạo custom field cho các cột chưa được khai báo
            existing_fields = [f["name"] for f in self.account_type["fields"]]
            for column in df.columns:
                if column not in existing_fields:
                    self.account_type["fields"].append(self._create_custom_field(str(column)))
            
            # Kiểm tra các cột bắt buộc
            required_fields = [f["name"] for f in self.account_type["fields"] if f["required"]]
            missing_columns = [field for field in required_fields if field not in df.columns]
            if missing_columns:
                print(f"❌ Thiếu các cột bắt buộc: {', '.join(missing_columns)}")
                return []
            
            # Xử lý từng dòng dữ liệu
            data = []
            for idx, row in df.iterrows():
                item = {}
                for field in self.account_type["fields"]:
                    field_name = field["name"]
                    if field_name in df.columns:
                        value = row[field_name]
                        # Chuyển đổi tất cả giá trị thành string và loại bỏ khoảng trắng
                        item[field_name] = str(value).strip() if pd.notna(value) else ""
                    else:
                        item[field_name] = ""
                data.append(item)
            
            return data
            
        except Exception as e:
            print(f"❌ Lỗi khi đọc file CSV: {str(e)}")
            return []
    
    def write_results(self, results: List[Tuple[str, str]], output_file: str):
        # Chuyển đổi kết quả thành DataFrame
        df = pd.DataFrame(results, columns=['Title', '1Password UUID'])
        # Lưu ra file CSV
        df.to_csv(output_file, index=False)

def get_file_handler(filename: str, account_type: Dict) -> Optional[FileHandler]:
    """Factory function to get appropriate file handler"""
    ext = filename.lower().split('.')[-1]
    
    if ext == 'txt':
        return TextFileHandler(filename, account_type)
    elif ext == 'csv':
        return CSVFileHandler(filename, account_type)
    elif ext in ['xlsx', 'xls']:
        return ExcelFileHandler(filename, account_type)
    else:
        print(f"❌ Không hỗ trợ định dạng file: {ext}")
        return None 