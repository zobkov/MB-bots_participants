"""Google Sheets manager for syncing debate registration data"""

import logging
import json
import os
from typing import Any, List, Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """Manages synchronization with Google Sheets"""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, credentials_path: str, spreadsheet_id: str, coach_spreadsheet_id: Optional[str] = None):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.coach_spreadsheet_id = coach_spreadsheet_id or spreadsheet_id
        self.service = None

    def _ensure_sheet(self, sheet_name: str, spreadsheet_id: str) -> int:
        """Ensure sheet exists, return its sheetId."""

        sheet_metadata = self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        for sheet in sheet_metadata.get("sheets", []):
            if sheet["properties"]["title"] == sheet_name:
                return sheet["properties"].get("sheetId", 0)

        request_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name,
                        }
                    }
                }
            ]
        }

        response = self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body,
        ).execute()

        sheet_id = (
            response.get("replies", [{}])[0]
            .get("addSheet", {})
            .get("properties", {})
            .get("sheetId", 0)
        )
        logger.info("Created new sheet '%s' in spreadsheet %s", sheet_name, spreadsheet_id)
        return sheet_id
        
    async def init(self):
        """Initialize Google Sheets service"""
        try:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"Google credentials file not found: {self.credentials_path}")
            
            # Load credentials
            credentials = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.SCOPES
            )
            
            # Build service
            self.service = build('sheets', 'v4', credentials=credentials)
            
            logger.info("Google Sheets service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            raise
    
    async def sync_debate_data(self, users_data: List[Dict], db_counts: Dict[int, int]) -> bool:
        """
        Sync debate registration data to Google Sheets
        
        Args:
            users_data: List of user dictionaries with registration info
            db_counts: Current registration counts by case
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.service:
                await self.init()
            
            # Prepare data for the sheet
            sheet_data = self._prepare_sheet_data(users_data, db_counts)
            
            # Clear and update the MAIN sheet
            await self._clear_sheet("MAIN")
            await self._write_to_sheet("MAIN", sheet_data)
            
            logger.info(f"Successfully synced {len(users_data)} user records to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync data to Google Sheets: {e}")
            return False
    
    def _prepare_sheet_data(self, users_data: List[Dict], db_counts: Dict[int, int]) -> List[List]:
        """Prepare data in format suitable for Google Sheets"""
        
        # Header row
        headers = [
            "ID пользователя",
            "Username", 
            "Видимое имя",
            "Кейс регистрации",
            "Название кейса",
            "Дата обновления"
        ]
        
        # Data rows
        data_rows = []
        
        case_names = {
            1: "ВТБ",
            2: "Алабуга",
            3: "Б1", 
            4: "Северсталь",
            5: "Альфа"
        }
        
        # Add user data
        for user in users_data:
            row = [
                str(user['id']),
                f"@{user['username']}" if user['username'] else "—",
                user['visible_name'] or f"User {user['id']}",
                str(user['debate_reg']) if user['debate_reg'] else "Не зарегистрирован",
                case_names.get(user['debate_reg'], "—") if user['debate_reg'] else "—",
                user.get('updated_at', "—")
            ]
            data_rows.append(row)
        
        # Combine headers and data (without statistics)
        return [headers] + data_rows
    
    async def _clear_sheet(self, sheet_name: str, clear_range: str = "A:ZZZ", spreadsheet_id: Optional[str] = None):
        """Clear all data from a sheet"""
        try:
            spreadsheet_id = spreadsheet_id or self.spreadsheet_id
            # Ensure sheet exists
            self._ensure_sheet(sheet_name, spreadsheet_id)

            # Clear existing data
            range_name = f"{sheet_name}!{clear_range}"
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            logger.info(f"Cleared sheet: {sheet_name}")
                
        except HttpError as e:
            logger.error(f"Error clearing sheet {sheet_name}: {e}")
            raise
    
    async def _write_to_sheet(self, sheet_name: str, data: List[List], spreadsheet_id: Optional[str] = None):
        """Write data to a sheet"""
        try:
            spreadsheet_id = spreadsheet_id or self.spreadsheet_id
            range_name = f"{sheet_name}!A1"
            
            body = {
                'values': data,
                'majorDimension': 'ROWS'
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            updated_cells = result.get('updatedCells', 0)
            logger.info(f"Updated {updated_cells} cells in sheet {sheet_name}")
            
        except HttpError as e:
            logger.error(f"Error writing to sheet {sheet_name}: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test connection to Google Sheets"""
        try:
            if not self.service:
                await self.init()
            
            # Try to get spreadsheet metadata
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            title = result.get('properties', {}).get('title', 'Unknown')
            logger.info(f"Successfully connected to Google Sheets: '{title}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False

    @staticmethod
    def prepare_event_registration_payload(registrations: List[Dict[str, Any]]) -> List[List[str]]:
        """Prepare timetable registrations for export without sending data to Google."""
        headers = [
            "ID пользователя",
            "Видимое имя",
            "Username",
            "Мероприятие",
            "Параллель (дата/время)",
            "Статус",
            "Время регистрации",
        ]

        rows: List[List[str]] = []
        for record in registrations:
            rows.append([
                str(record.get("user_id", "")),
                record.get("visible_name", ""),
                record.get("username", ""),
                record.get("event_title", ""),
                record.get("group_label", ""),
                record.get("status", "Активна"),
                record.get("registered_at", ""),
            ])

        return [headers] + rows

    async def sync_event_registration_matrix(
        self,
        headers: List[Any],
        rows: List[List[Any]],
        sheet_name: str = "main",
    ) -> bool:
        """Write 0/1 registration matrix to Google Sheets."""

        try:
            if not self.service:
                await self.init()

            dataset = [headers] + rows
            await self._clear_sheet(sheet_name)
            await self._write_to_sheet(sheet_name, dataset)
            logger.info(
                "Event registration matrix synced: rows=%s, columns=%s, sheet=%s",
                len(dataset),
                len(headers),
                sheet_name,
            )
            return True
        except Exception as exc:
            logger.error("Failed to sync event registration matrix: %s", exc)
            return False

    async def append_coach_session_entry(
        self,
        headers: List[str],
        row: List[Any],
        sheet_name: str = "Лист1",
    ) -> bool:
        """Append coach session application to dedicated spreadsheet."""

        target_spreadsheet_id = self.coach_spreadsheet_id or self.spreadsheet_id

        try:
            if not self.service:
                await self.init()

            self._ensure_sheet(sheet_name, target_spreadsheet_id)

            # Ensure headers present when sheet empty
            existing = self.service.spreadsheets().values().get(
                spreadsheetId=target_spreadsheet_id,
                range=f"{sheet_name}!A1:Z1",
            ).execute()

            if not existing.get("values"):
                await self._write_to_sheet(sheet_name, [headers], spreadsheet_id=target_spreadsheet_id)

            body = {
                "values": [row],
                "majorDimension": "ROWS",
            }

            self.service.spreadsheets().values().append(
                spreadsheetId=target_spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()

            logger.info("Coach session entry appended to sheet %s", target_spreadsheet_id)
            return True
        except Exception as exc:
            logger.error("Failed to append coach session entry: %s", exc)
            return False