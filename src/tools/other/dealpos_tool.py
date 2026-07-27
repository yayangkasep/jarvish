import requests
from datetime import datetime

class DealPOSTool:
    def __init__(self):
        self.ToolName = "DealPOSTool"
        self.Schema = {
            "type": "function",
            "function": {
                "name": self.ToolName,
                "description": "Tool untuk berinteraksi dengan API DealPOS toko (Raja Susu - Pamulang2). Digunakan untuk login dan mengekstrak data penjualan.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Aksi yang akan dilakukan: 'login_test' atau 'get_sales_summary'."
                        },
                        "date": {
                            "type": "string",
                            "description": "Tanggal untuk ditarik datanya (format YYYY-MM-DD). Opsional, default hari ini."
                        }
                    },
                    "required": ["action"],
                },
            },
        }

    def Execute(self, Arguments):
        action = Arguments.get("action")
        date_str = Arguments.get("date")
        
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        login_url = "https://rajasusu.dealpos.net/api/Login/Web"
        login_payload = {
            "GetMenu": True,
            "Name": "Pamulang2",
            "Password": "Pamulang1"
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if action == "login_test":
            try:
                response = requests.post(login_url, json=login_payload, headers=headers, timeout=15)
                try:
                    return f"Status: {response.status_code}\nData JSON: {response.json()}"
                except:
                    return f"Status: {response.status_code}\nResponse Text: {response.text}"
            except Exception as e:
                return f"Error saat menghubungi API: {str(e)}"
                
        elif action == "get_sales_summary":
            # 1. Login to get token
            try:
                login_resp = requests.post(login_url, json=login_payload, headers=headers, timeout=15)
                login_data = login_resp.json()
                token = login_data.get("Token")
                
                if not token:
                    return "Gagal mendapatkan Token dari response login."
                    
                # 2. Fetch Report Summary
                report_url = "https://rajasusu.dealpos.net/api/Report/ReportSummary"
                report_headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                
                report_payload = {
                    "From": f"{date_str}T00:00:00.000",
                    "To": f"{date_str}T00:00:00.000",
                    "FromTime": None,
                    "ToTime": None,
                    "CreatorID": "00000000-0000-0000-0000-000000000000",
                    "CurrencyID": 0,
                    "CustomerID": None,
                    "DefaultFilterColumn": 1,
                    "ExportPageNumber": 1,
                    "ExportRowCount": 10000,
                    "ListIDs": [],
                    "PageNumber": 1,
                    "RowCount": 10000
                }
                
                report_resp = requests.post(report_url, json=report_payload, headers=report_headers, timeout=15)
                try:
                    return f"Data Penjualan ({date_str}):\n{report_resp.json()}"
                except:
                    return f"Status: {report_resp.status_code}\nResponse: {report_resp.text}"
                    
            except Exception as e:
                return f"Error saat mengambil data penjualan: {str(e)}"
        
        return f"Aksi '{action}' tidak dikenal."
