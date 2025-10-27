"""
Sberbank HTML report parser
Extracts structured data from Sberbank broker reports
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import logging
from .base_parser import BaseHtmlParser

logger = logging.getLogger(__name__)


class SberHtmlParser(BaseHtmlParser):
    """Parser for Sberbank HTML broker reports"""
    
    def __init__(self):
        super().__init__()
        self.set_supported_broker('sber')
    
    def parse(self, html_content: str) -> Dict[str, Any]:
        """Parse HTML content and extract structured data"""
        try:
            # Use base class HTML loading
            if not self.load_html(html_content):
                raise ValueError("Failed to load HTML content")
            
            # Extract table structures (existing)
            cash_flows = self._extract_cash_flows()
            securities_portfolio = self._extract_securities_portfolio()
            trades = self._extract_trades()
            
            # Extract metadata
            metadata = self._extract_metadata()
            
            # Extract financial metrics
            financial_metrics = self._extract_financial_metrics()
            
            # Build result with all 34 fields using field logging
            result = {}
            
            # Parser version
            parser_version = self.get_parser_version()
            self.log_field("parser_version", parser_version, "parser")
            result["parser_version"] = parser_version
            
            # Tables (maintain existing structure)
            self.log_field("cash_flows", cash_flows, "extracted")
            result["cash_flows"] = cash_flows
            
            self.log_field("securities_portfolio", securities_portfolio, "extracted")
            result["securities_portfolio"] = securities_portfolio
            
            self.log_field("trades", trades, "extracted")
            result["trades"] = trades
            
            # Metadata fields (with null defaults)
            investor_name = metadata.get("investor_name")
            self.log_field("investor_name", investor_name, "metadata")
            result["investor_name"] = investor_name
            
            account_number = metadata.get("account_number")
            self.log_field("account_number", account_number, "metadata")
            result["account_number"] = account_number
            
            contract_date = metadata.get("contract_date")
            self.log_field("contract_date", contract_date, "metadata")
            result["contract_date"] = contract_date
            
            period_start = metadata.get("period_start")
            self.log_field("period_start", period_start, "metadata")
            result["period_start"] = period_start
            
            period_end = metadata.get("period_end")
            self.log_field("period_end", period_end, "metadata")
            result["period_end"] = period_end
            
            # Financial metrics
            portfolio_value = financial_metrics.get("portfolio_value")
            self.log_field("portfolio_value", portfolio_value, "financial")
            result["portfolio_value"] = portfolio_value
            
            cash_balance = financial_metrics.get("cash_balance")
            self.log_field("cash_balance", cash_balance, "financial")
            result["cash_balance"] = cash_balance
            
            total_assets = financial_metrics.get("total_assets")
            self.log_field("total_assets", total_assets, "financial")
            result["total_assets"] = total_assets
            
            balance_ending = self._extract_balance_ending()
            self.log_field("balance_ending", balance_ending, "extracted")
            result["balance_ending"] = balance_ending
            
            # Transaction details (aggregated from tables)
            currency = self._aggregate_currency()
            self.log_field("currency", currency, "aggregated")
            result["currency"] = currency
            
            isin = self._aggregate_isin()
            self.log_field("isin", isin, "aggregated")
            result["isin"] = isin
            
            instrument_name = self._aggregate_instrument_name()
            self.log_field("instrument_name", instrument_name, "aggregated")
            result["instrument_name"] = instrument_name
            
            description = self._aggregate_description()
            self.log_field("description", description, "aggregated")
            result["description"] = description
            
            platform = self._aggregate_platform()
            self.log_field("platform", platform, "aggregated")
            result["platform"] = platform
            
            cash_flow_date = self._aggregate_cash_flow_date()
            self.log_field("cash_flow_date", cash_flow_date, "aggregated")
            result["cash_flow_date"] = cash_flow_date
            
            credit = self._aggregate_credit()
            self.log_field("credit", credit, "aggregated")
            result["credit"] = credit
            
            debit = self._aggregate_debit()
            self.log_field("debit", debit, "aggregated")
            result["debit"] = debit
            
            quantity_start = self._aggregate_quantity_start()
            self.log_field("quantity_start", quantity_start, "aggregated")
            result["quantity_start"] = quantity_start
            
            quantity_end = self._aggregate_quantity_end()
            self.log_field("quantity_end", quantity_end, "aggregated")
            result["quantity_end"] = quantity_end
            
            quantity_change = self._aggregate_quantity_change()
            self.log_field("quantity_change", quantity_change, "aggregated")
            result["quantity_change"] = quantity_change
            
            price_start = self._aggregate_price_start()
            self.log_field("price_start", price_start, "aggregated")
            result["price_start"] = price_start
            
            price_end = self._aggregate_price_end()
            self.log_field("price_end", price_end, "aggregated")
            result["price_end"] = price_end
            
            value_start = self._aggregate_value_start()
            self.log_field("value_start", value_start, "aggregated")
            result["value_start"] = value_start
            
            value_end = self._aggregate_value_end()
            self.log_field("value_end", value_end, "aggregated")
            result["value_end"] = value_end
            
            value_change = self._aggregate_value_change()
            self.log_field("value_change", value_change, "aggregated")
            result["value_change"] = value_change
            
            nominal = self._aggregate_nominal()
            self.log_field("nominal", nominal, "aggregated")
            result["nominal"] = nominal
            
            nkd_start = self._aggregate_nkd_start()
            self.log_field("nkd_start", nkd_start, "aggregated")
            result["nkd_start"] = nkd_start
            
            nkd_end = self._aggregate_nkd_end()
            self.log_field("nkd_end", nkd_end, "aggregated")
            result["nkd_end"] = nkd_end
            
            # Computed fields
            active_instruments_count = self._compute_active_instruments_count()
            self.log_field("active_instruments_count", active_instruments_count, "computed")
            result["active_instruments_count"] = active_instruments_count
            
            total_income = self._compute_total_income()
            self.log_field("total_income", total_income, "computed")
            result["total_income"] = total_income
            
            # Legacy fields (maintain compatibility)
            account_open_date = self._extract_account_open_date()
            self.log_field("account_open_date", account_open_date, "extracted")
            result["account_open_date"] = account_open_date
            
            trade_count = trades["count"]
            self.log_field("trade_count", trade_count, "extracted")
            result["trade_count"] = trade_count
            
            instruments = self._extract_instruments()
            self.log_field("instruments", instruments, "extracted")
            result["instruments"] = instruments
            
            financial_result = self._extract_financial_result()
            self.log_field("financial_result", financial_result, "extracted")
            result["financial_result"] = financial_result
            
            # Validate output using base class
            if not self.validate_output(result):
                logger.warning("Parsed data validation failed, but continuing")
            
            logger.info("Successfully parsed Sberbank report v2.0")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse Sberbank report: {e}")
            raise
    
    def get_parser_version(self) -> str:
        """Get parser version string"""
        return "2.0"
    
    def _extract_balance_ending(self) -> float:
        """Extract ending balance from assets evaluation table"""
        try:
            # Find the table with "Торговая площадка" and "Оценка портфеля ЦБ, руб."
            tables = self.soup.find_all('table')
            for table in tables:
                # Check if this is the assets evaluation table
                header_cells = table.find_all('td', class_='c')
                if header_cells and any('Оценка портфеля ЦБ' in cell.get_text() for cell in header_cells):
                    # Find the "Итого" row
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if cells and 'Итого' in cells[0].get_text():
                            # Get the last cell (ending balance)
                            balance_text = cells[-1].get_text(strip=True)
                            # Remove spaces and convert to float
                            balance_value = float(balance_text.replace(' ', '').replace(',', '.'))
                            return balance_value
            return 0.0
        except Exception as e:
            logger.warning(f"Could not extract balance ending: {e}")
            return 0.0
    
    def _extract_account_open_date(self) -> Optional[str]:
        """Extract account opening date from contract text"""
        try:
            # Look for text pattern: "Договор на ведение индивидуального инвестиционного счета S000T49 от 13.08.2019"
            text_content = self.soup.get_text()
            
            # Pattern to match date after "от"
            pattern = r'от (\d{2}\.\d{2}\.\d{4})'
            match = re.search(pattern, text_content)
            
            if match:
                date_str = match.group(1)
                # Convert DD.MM.YYYY to YYYY-MM-DD
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                return date_obj.strftime('%Y-%m-%d')
            
            return None
        except Exception as e:
            logger.warning(f"Could not extract account open date: {e}")
            return None
    
    def _extract_trades(self) -> Dict[str, Any]:
        """Extract trade information from securities portfolio table"""
        try:
            trades = {
                "count": 0,
                "details": []
            }
            
            # Find the securities portfolio table
            tables = self.soup.find_all('table')
            for table in tables:
                if table.find('td', string=lambda x: x and 'Портфель Ценных Бумаг' in x):
                    # Find rows with position changes
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 13:  # Check if row has enough columns
                            # Look for quantity change column (index 12)
                            quantity_change = cells[12].get_text(strip=True)
                            if quantity_change and quantity_change != '0':
                                trades["count"] += 1
                                # Extract trade details
                                instrument_name = cells[0].get_text(strip=True) if cells[0] else ""
                                isin = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                                trades["details"].append({
                                    "instrument": instrument_name,
                                    "isin": isin,
                                    "quantity_change": quantity_change
                                })
            
            return trades
        except Exception as e:
            logger.warning(f"Could not extract trades: {e}")
            return {"count": 0, "details": []}
    
    def _extract_instruments(self) -> List[Dict[str, Any]]:
        """Extract list of instruments from securities portfolio"""
        try:
            instruments = []
            
            # Find the securities portfolio table
            tables = self.soup.find_all('table')
            for table in tables:
                # Look for table with "Наименование" and "ISIN" headers
                header_cells = table.find_all('td', class_='c')
                if header_cells and any('Наименование' in cell.get_text() for cell in header_cells):
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3 and cells[0].get_text(strip=True):
                            # Skip header rows and platform rows
                            if ('Наименование' in cells[0].get_text() or 
                                'Площадка' in cells[0].get_text() or
                                'Итого' in cells[0].get_text()):
                                continue
                            
                            instrument_name = cells[0].get_text(strip=True)
                            isin = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                            # Get quantity from the "Конец периода" column (index 8)
                            quantity = cells[8].get_text(strip=True) if len(cells) > 8 else "0"
                            
                            if instrument_name and not instrument_name.startswith('Итого'):
                                instruments.append({
                                    "name": instrument_name,
                                    "isin": isin,
                                    "quantity": int(quantity.replace(' ', '')) if quantity.replace(' ', '').isdigit() else 0
                                })
            
            return instruments
        except Exception as e:
            logger.warning(f"Could not extract instruments: {e}")
            return []
    
    def _extract_financial_result(self) -> float:
        """Extract financial result from cash flows table"""
        try:
            # Find the cash flows table
            tables = self.soup.find_all('table')
            for table in tables:
                # Look for table with "Дата" and "Сумма зачисления" headers
                header_cells = table.find_all('td', class_='c')
                if header_cells and any('Дата' in cell.get_text() for cell in header_cells):
                    # Find the total row
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if cells and 'Итого' in cells[0].get_text():
                            # Handle colspan case - look for the last two cells
                            if len(cells) >= 2:
                                # Get the last two cells (credits and debits)
                                credits = float(cells[-2].get_text(strip=True).replace(' ', '').replace(',', '.')) if cells[-2].get_text(strip=True) else 0
                                debits = float(cells[-1].get_text(strip=True).replace(' ', '').replace(',', '.')) if cells[-1].get_text(strip=True) else 0
                                return credits - debits
            return 0.0
        except Exception as e:
            logger.warning(f"Could not extract financial result: {e}")
            return 0.0
    
    def _extract_cash_flows(self) -> List[Dict[str, Any]]:
        """Extract cash flow details"""
        try:
            cash_flows = []
            
            # Find the cash flows table
            tables = self.soup.find_all('table')
            for table in tables:
                if table.find('td', string=lambda x: x and 'Движение денежных средств за период' in x):
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 6 and cells[0].get_text(strip=True):
                            # Skip header and total rows
                            if 'Дата' in cells[0].get_text() or 'Итого' in cells[0].get_text():
                                continue
                            
                            date = cells[0].get_text(strip=True)
                            platform = cells[1].get_text(strip=True)
                            description = cells[2].get_text(strip=True)
                            currency = cells[3].get_text(strip=True)
                            credit = cells[4].get_text(strip=True)
                            debit = cells[5].get_text(strip=True)
                            
                            cash_flows.append({
                                "date": date,
                                "platform": platform,
                                "description": description,
                                "currency": currency,
                                "credit": float(credit.replace(' ', '').replace(',', '.')) if credit else 0,
                                "debit": float(debit.replace(' ', '').replace(',', '.')) if debit else 0
                            })
            
            return cash_flows
        except Exception as e:
            logger.warning(f"Could not extract cash flows: {e}")
            return []
    
    def _extract_securities_portfolio(self) -> List[Dict[str, Any]]:
        """Extract detailed securities portfolio"""
        try:
            portfolio = []
            
            # Find the <p> tag containing "Портфель Ценных Бумаг"
            portfolio_p = None
            for p in self.soup.find_all('p'):
                if p.get_text() and 'Портфель Ценных Бумаг' in p.get_text():
                    portfolio_p = p
                    break
            
            if not portfolio_p:
                logger.warning("Could not find 'Портфель Ценных Бумаг' section")
                return []
            
            # Get the next table after the <p> tag
            portfolio_table = portfolio_p.find_next('table')
            if not portfolio_table:
                logger.warning("Could not find portfolio table after 'Портфель Ценных Бумаг'")
                return []
            
            rows = portfolio_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                
                # Skip rows with insufficient columns (need at least 14 for data rows)
                if len(cells) < 14:
                    continue
                
                # Skip header rows
                if (row.get('class') and ('table-header' in row.get('class') or 'rn' in row.get('class'))) or \
                   row.get('bgcolor') == '#C0C0C0':
                    continue
                
                # Skip colspan rows (like "Площадка: Фондовый рынок" or "Блокировано")
                if cells[0].get('colspan'):
                    continue
                
                # Extract instrument name and ISIN
                instrument_name = cells[0].get_text(strip=True)
                isin = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                
                # Skip rows without name or ISIN
                if not instrument_name or not isin or instrument_name.startswith('Итого'):
                    continue
                
                # Helper function to safely convert numeric values
                def safe_float(value_str):
                    if not value_str:
                        return None
                    try:
                        # Remove spaces and replace comma with dot
                        clean_value = str(value_str).replace(' ', '').replace(',', '.')
                        return float(clean_value)
                    except (ValueError, TypeError):
                        return None
                
                # Extract all fields with proper type conversion
                security = {
                    "name": instrument_name,
                    "isin": isin,
                    "currency": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                    "quantity_start": safe_float(cells[3].get_text(strip=True)) if len(cells) > 3 else None,
                    "nominal": safe_float(cells[4].get_text(strip=True)) if len(cells) > 4 else None,
                    "price_start": safe_float(cells[5].get_text(strip=True)) if len(cells) > 5 else None,
                    "value_start": safe_float(cells[6].get_text(strip=True)) if len(cells) > 6 else None,
                    "nkd_start": safe_float(cells[7].get_text(strip=True)) if len(cells) > 7 else None,
                    "quantity_end": safe_float(cells[8].get_text(strip=True)) if len(cells) > 8 else None,
                    "price_end": safe_float(cells[9].get_text(strip=True)) if len(cells) > 9 else None,
                    "value_end": safe_float(cells[10].get_text(strip=True)) if len(cells) > 10 else None,
                    "nkd_end": safe_float(cells[11].get_text(strip=True)) if len(cells) > 11 else None,
                    "quantity_change": safe_float(cells[12].get_text(strip=True)) if len(cells) > 12 else None,
                    "value_change": safe_float(cells[13].get_text(strip=True)) if len(cells) > 13 else None
                }
                
                portfolio.append(security)
            
            logger.info(f"Extracted {len(portfolio)} securities from portfolio table")
            return portfolio
            
        except Exception as e:
            logger.warning(f"Could not extract securities portfolio: {e}")
            return []
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata fields from header text"""
        try:
            metadata = {}
            text_content = self.soup.get_text()
            
            # Extract investor name: "Инвестор: [Name]"
            investor_match = re.search(r'Инвестор:\s*([^\n\r]+)', text_content)
            if investor_match:
                metadata["investor_name"] = investor_match.group(1).strip()
            
            # Extract account number: "Договор...S000T49"
            account_match = re.search(r'Договор.*?([A-Z0-9]+)', text_content)
            if account_match:
                metadata["account_number"] = account_match.group(1)
            
            # Extract contract date: "от [date]"
            contract_match = re.search(r'от\s+(\d{2}\.\d{2}\.\d{4})', text_content)
            if contract_match:
                date_str = contract_match.group(1)
                try:
                    date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    metadata["contract_date"] = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Extract period: "за период с [start] по [end]"
            period_match = re.search(r'за период с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})', text_content)
            if period_match:
                start_str = period_match.group(1)
                end_str = period_match.group(2)
                try:
                    start_date = datetime.strptime(start_str, '%d.%m.%Y')
                    end_date = datetime.strptime(end_str, '%d.%m.%Y')
                    metadata["period_start"] = start_date.strftime('%Y-%m-%d')
                    metadata["period_end"] = end_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            return metadata
        except Exception as e:
            logger.warning(f"Could not extract metadata: {e}")
            return {}
    
    def _extract_financial_metrics(self) -> Dict[str, Any]:
        """Extract financial metrics from assets evaluation table"""
        try:
            metrics = {}
            
            # Find the assets evaluation table
            tables = self.soup.find_all('table')
            for table in tables:
                header_cells = table.find_all('td', class_='c')
                if header_cells and any('Оценка портфеля ЦБ' in cell.get_text() for cell in header_cells):
                    # Find the "Итого" row
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if cells and 'Итого' in cells[0].get_text():
                            if len(cells) >= 4:
                                try:
                                    metrics["portfolio_value"] = float(cells[1].get_text(strip=True).replace(' ', '').replace(',', '.'))
                                    metrics["cash_balance"] = float(cells[2].get_text(strip=True).replace(' ', '').replace(',', '.'))
                                    metrics["total_assets"] = float(cells[3].get_text(strip=True).replace(' ', '').replace(',', '.'))
                                except (ValueError, IndexError):
                                    pass
                            break
            
            return metrics
        except Exception as e:
            logger.warning(f"Could not extract financial metrics: {e}")
            return {}
    
    def _aggregate_currency(self) -> Optional[str]:
        """Aggregate currency from tables"""
        try:
            # Get from securities portfolio
            portfolio = self._extract_securities_portfolio()
            if portfolio:
                currencies = [item.get("currency") for item in portfolio if item.get("currency")]
                if currencies:
                    return currencies[0]  # Return first currency found
            
            # Get from cash flows
            cash_flows = self._extract_cash_flows()
            if cash_flows:
                currencies = [item.get("currency") for item in cash_flows if item.get("currency")]
                if currencies:
                    return currencies[0]
            
            return None
        except Exception as e:
            logger.warning(f"Could not aggregate currency: {e}")
            return None
    
    def _aggregate_isin(self) -> Optional[List[str]]:
        """Aggregate ISIN codes from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            isins = [item.get("isin") for item in portfolio if item.get("isin")]
            return isins if isins else None
        except Exception as e:
            logger.warning(f"Could not aggregate ISIN: {e}")
            return None
    
    def _aggregate_instrument_name(self) -> Optional[List[str]]:
        """Aggregate instrument names from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            names = [item.get("name") for item in portfolio if item.get("name")]
            return names if names else None
        except Exception as e:
            logger.warning(f"Could not aggregate instrument names: {e}")
            return None
    
    def _aggregate_description(self) -> Optional[List[str]]:
        """Aggregate descriptions from cash flows"""
        try:
            cash_flows = self._extract_cash_flows()
            descriptions = [item.get("description") for item in cash_flows if item.get("description")]
            return descriptions if descriptions else None
        except Exception as e:
            logger.warning(f"Could not aggregate descriptions: {e}")
            return None
    
    def _aggregate_platform(self) -> Optional[List[str]]:
        """Aggregate platforms from cash flows"""
        try:
            cash_flows = self._extract_cash_flows()
            platforms = [item.get("platform") for item in cash_flows if item.get("platform")]
            return platforms if platforms else None
        except Exception as e:
            logger.warning(f"Could not aggregate platforms: {e}")
            return None
    
    def _aggregate_cash_flow_date(self) -> Optional[List[str]]:
        """Aggregate dates from cash flows"""
        try:
            cash_flows = self._extract_cash_flows()
            dates = [item.get("date") for item in cash_flows if item.get("date")]
            return dates if dates else None
        except Exception as e:
            logger.warning(f"Could not aggregate cash flow dates: {e}")
            return None
    
    def _aggregate_credit(self) -> Optional[List[float]]:
        """Aggregate credit amounts from cash flows"""
        try:
            cash_flows = self._extract_cash_flows()
            credits = [item.get("credit") for item in cash_flows if item.get("credit") is not None]
            return credits if credits else None
        except Exception as e:
            logger.warning(f"Could not aggregate credits: {e}")
            return None
    
    def _aggregate_debit(self) -> Optional[List[float]]:
        """Aggregate debit amounts from cash flows"""
        try:
            cash_flows = self._extract_cash_flows()
            debits = [item.get("debit") for item in cash_flows if item.get("debit") is not None]
            return debits if debits else None
        except Exception as e:
            logger.warning(f"Could not aggregate debits: {e}")
            return None
    
    def _aggregate_quantity_start(self) -> Optional[List[str]]:
        """Aggregate start quantities from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            quantities = [item.get("quantity_start") for item in portfolio if item.get("quantity_start")]
            return quantities if quantities else None
        except Exception as e:
            logger.warning(f"Could not aggregate start quantities: {e}")
            return None
    
    def _aggregate_quantity_end(self) -> Optional[List[str]]:
        """Aggregate end quantities from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            quantities = [item.get("quantity_end") for item in portfolio if item.get("quantity_end")]
            return quantities if quantities else None
        except Exception as e:
            logger.warning(f"Could not aggregate end quantities: {e}")
            return None
    
    def _aggregate_quantity_change(self) -> Optional[List[str]]:
        """Aggregate quantity changes from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            changes = [item.get("quantity_change") for item in portfolio if item.get("quantity_change")]
            return changes if changes else None
        except Exception as e:
            logger.warning(f"Could not aggregate quantity changes: {e}")
            return None
    
    def _aggregate_price_start(self) -> Optional[List[str]]:
        """Aggregate start prices from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            prices = [item.get("price_start") for item in portfolio if item.get("price_start")]
            return prices if prices else None
        except Exception as e:
            logger.warning(f"Could not aggregate start prices: {e}")
            return None
    
    def _aggregate_price_end(self) -> Optional[List[str]]:
        """Aggregate end prices from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            prices = [item.get("price_end") for item in portfolio if item.get("price_end")]
            return prices if prices else None
        except Exception as e:
            logger.warning(f"Could not aggregate end prices: {e}")
            return None
    
    def _aggregate_value_start(self) -> Optional[List[str]]:
        """Aggregate start values from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            values = [item.get("value_start") for item in portfolio if item.get("value_start")]
            return values if values else None
        except Exception as e:
            logger.warning(f"Could not aggregate start values: {e}")
            return None
    
    def _aggregate_value_end(self) -> Optional[List[str]]:
        """Aggregate end values from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            values = [item.get("value_end") for item in portfolio if item.get("value_end")]
            return values if values else None
        except Exception as e:
            logger.warning(f"Could not aggregate end values: {e}")
            return None
    
    def _aggregate_value_change(self) -> Optional[List[str]]:
        """Aggregate value changes from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            changes = [item.get("value_change") for item in portfolio if item.get("value_change")]
            return changes if changes else None
        except Exception as e:
            logger.warning(f"Could not aggregate value changes: {e}")
            return None
    
    def _aggregate_nominal(self) -> Optional[List[str]]:
        """Aggregate nominal values from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            nominals = [item.get("nominal") for item in portfolio if item.get("nominal")]
            return nominals if nominals else None
        except Exception as e:
            logger.warning(f"Could not aggregate nominals: {e}")
            return None
    
    def _aggregate_nkd_start(self) -> Optional[List[str]]:
        """Aggregate start NKD from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            nkds = [item.get("nkd_start") for item in portfolio if item.get("nkd_start")]
            return nkds if nkds else None
        except Exception as e:
            logger.warning(f"Could not aggregate start NKD: {e}")
            return None
    
    def _aggregate_nkd_end(self) -> Optional[List[str]]:
        """Aggregate end NKD from securities portfolio"""
        try:
            portfolio = self._extract_securities_portfolio()
            nkds = [item.get("nkd_end") for item in portfolio if item.get("nkd_end")]
            return nkds if nkds else None
        except Exception as e:
            logger.warning(f"Could not aggregate end NKD: {e}")
            return None
    
    def _compute_active_instruments_count(self) -> Optional[int]:
        """Compute count of active instruments (non-zero positions)"""
        try:
            portfolio = self._extract_securities_portfolio()
            active_count = 0
            for item in portfolio:
                quantity_end = item.get("quantity_end", "0")
                try:
                    if float(quantity_end.replace(' ', '')) > 0:
                        active_count += 1
                except (ValueError, TypeError):
                    pass
            return active_count if active_count > 0 else None
        except Exception as e:
            logger.warning(f"Could not compute active instruments count: {e}")
            return None
    
    def _compute_total_income(self) -> Optional[float]:
        """Compute total income from cash flows"""
        try:
            cash_flows = self._extract_cash_flows()
            total_income = 0.0
            for item in cash_flows:
                credit = item.get("credit", 0)
                debit = item.get("debit", 0)
                if isinstance(credit, (int, float)):
                    total_income += credit
                if isinstance(debit, (int, float)):
                    total_income -= debit
            return total_income if total_income != 0 else None
        except Exception as e:
            logger.warning(f"Could not compute total income: {e}")
            return None
