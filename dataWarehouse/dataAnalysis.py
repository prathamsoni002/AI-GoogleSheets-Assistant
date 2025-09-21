
import os
import pandas as pd
import json
from typing import Dict, List, Any, Optional
from core.openai_api import get_ai_response

class ProductMasterAnalyzer:
    """
    Analyzes product master data across multiple sheets and generates comprehensive reports
    """

    def __init__(self, workbook_name: str):
        self.workbook_name = workbook_name
        self.dataframe_path = f"./core/dataframes/{workbook_name}"
        self.dictionary_path = "./sap_data_dictionary.csv"
        self.product_data = {}
        self.field_mappings = {}

    def load_sap_dictionary(self) -> pd.DataFrame:
        """Load SAP data dictionary for field descriptions"""
        try:
            if os.path.exists(self.dictionary_path):
                return pd.read_csv(self.dictionary_path)
            else:
                print(f"⚠️ SAP dictionary not found at {self.dictionary_path}")
                return pd.DataFrame()
        except Exception as e:
            print(f"❌ Error loading SAP dictionary: {e}")
            return pd.DataFrame()

    def get_available_sheets(self) -> List[str]:
        """Get list of available CSV files (sheets) for the workbook"""
        sheets = []
        if os.path.exists(self.dataframe_path):
            for file in os.listdir(self.dataframe_path):
                if file.endswith('.csv'):
                    sheet_name = file.replace('.csv', '')
                    sheets.append(sheet_name)
            print(f"📁 Found {len(sheets)} sheets: {', '.join(sheets[:5])}{'...' if len(sheets) > 5 else ''}")
        else:
            print(f"❌ Directory not found: {self.dataframe_path}")
        return sheets

    def debug_product_search(self, product_number: str) -> Dict[str, Any]:
        """Debug function to find product data with detailed logging"""
        debug_info = {
            'search_term': product_number,
            'sheets_checked': 0,
            'sheets_with_product_column': 0,
            'unique_products_found': set(),
            'sample_products': [],
            'sheets_with_data': []
        }

        available_sheets = self.get_available_sheets()
        debug_info['sheets_checked'] = len(available_sheets)

        print(f"🔍 DEBUG: Searching for product '{product_number}'")
        print(f"📊 Checking {len(available_sheets)} sheets in {self.dataframe_path}")

        for sheet_name in available_sheets:
            try:
                file_path = os.path.join(self.dataframe_path, f"{sheet_name}.csv")
                df = pd.read_csv(file_path)

                print(f"\n📋 Sheet: {sheet_name}")
                print(f"   - Rows: {len(df)}, Columns: {len(df.columns)}")
                print(f"   - Columns: {list(df.columns)}")

                # Check if PRODUCT column exists
                if 'PRODUCT' in df.columns:
                    debug_info['sheets_with_product_column'] += 1

                    # Get unique product values
                    unique_products = df['PRODUCT'].dropna().unique()
                    debug_info['unique_products_found'].update(unique_products)

                    print(f"   - Products found: {len(unique_products)}")

                    # Show sample products
                    sample_products = list(unique_products)[:10]
                    debug_info['sample_products'].extend([(sheet_name, p) for p in sample_products])
                    print(f"   - Sample products: {sample_products}")

                    # Try exact match
                    exact_match = df[df['PRODUCT'] == product_number]
                    if not exact_match.empty:
                        print(f"   - ✅ EXACT MATCH FOUND: {len(exact_match)} records")
                        debug_info['sheets_with_data'].append(sheet_name)
                    else:
                        # Try case-insensitive match
                        case_insensitive = df[df['PRODUCT'].str.upper() == product_number.upper()]
                        if not case_insensitive.empty:
                            print(f"   - ⚠️ CASE-INSENSITIVE MATCH: {len(case_insensitive)} records")

                        # Try partial match
                        partial_match = df[df['PRODUCT'].str.contains(product_number, case=False, na=False)]
                        if not partial_match.empty:
                            print(f"   - 🔍 PARTIAL MATCH: {len(partial_match)} records")
                        else:
                            print(f"   - ❌ No match found")
                else:
                    print(f"   - ⚠️ No 'PRODUCT' column")

            except Exception as e:
                print(f"   - ❌ Error: {e}")

        return debug_info

    def extract_product_data(self, product_number: str) -> Dict[str, pd.DataFrame]:
        """Extract data for specific product across all sheets with enhanced search"""
        product_data = {}
        available_sheets = self.get_available_sheets()

        print(f"🔍 Searching for product '{product_number}' in {len(available_sheets)} sheets...")

        # First, run debug to understand the data
        debug_info = self.debug_product_search(product_number)

        for sheet_name in available_sheets:
            try:
                file_path = os.path.join(self.dataframe_path, f"{sheet_name}.csv")
                df = pd.read_csv(file_path)

                # Check if PRODUCT column exists
                if 'PRODUCT' in df.columns:
                    # Try exact match first
                    product_rows = df[df['PRODUCT'] == product_number]

                    # If no exact match, try case-insensitive
                    if product_rows.empty:
                        product_rows = df[df['PRODUCT'].str.upper() == product_number.upper()]
                        if not product_rows.empty:
                            print(f"📝 Note: Found case-insensitive match in '{sheet_name}'")

                    if not product_rows.empty:
                        product_data[sheet_name] = product_rows
                        print(f"✅ Found {len(product_rows)} records in '{sheet_name}'")
                    else:
                        print(f"⚪ No data for product '{product_number}' in '{sheet_name}'")
                else:
                    print(f"⚠️ No 'PRODUCT' column in '{sheet_name}'")

            except Exception as e:
                print(f"❌ Error processing sheet '{sheet_name}': {e}")

        # If no data found, provide helpful suggestions
        if not product_data:
            print(f"\n🔍 DEBUGGING SUGGESTIONS:")
            print(f"📊 Total sheets checked: {debug_info['sheets_checked']}")
            print(f"📋 Sheets with PRODUCT column: {debug_info['sheets_with_product_column']}")
            print(f"🎯 Total unique products found: {len(debug_info['unique_products_found'])}")

            if debug_info['sample_products']:
                print(f"\n📝 Sample products from your data:")
                for sheet, product in debug_info['sample_products'][:15]:
                    print(f"   - {product} (in {sheet})")

                # Check for similar products
                similar_products = [p for _, p in debug_info['sample_products'] 
                                  if product_number.lower() in str(p).lower() or 
                                     str(p).lower() in product_number.lower()]

                if similar_products:
                    print(f"\n🔍 Similar products found:")
                    for similar in similar_products[:5]:
                        print(f"   - {similar}")

        return product_data

    def map_field_descriptions(self, sheet_name: str, columns: List[str]) -> Dict[str, str]:
        """Map column names to their field descriptions using SAP dictionary"""
        dictionary_df = self.load_sap_dictionary()
        field_mappings = {}

        if dictionary_df.empty:
            return field_mappings

        # Filter dictionary for the specific sheet
        sheet_dict = dictionary_df[dictionary_df['Sheet Name'] == sheet_name]

        for column in columns:
            # Try to find mapping by SAP Field
            mapping = sheet_dict[sheet_dict['SAP Field'] == column]

            if not mapping.empty:
                field_desc = mapping.iloc[0]['Field Description']
                importance = mapping.iloc[0].get('Importance', '')
                field_mappings[column] = {
                    'description': field_desc,
                    'importance': importance,
                    'type': mapping.iloc[0].get('Type', ''),
                    'length': mapping.iloc[0].get('Length', ''),
                    'group_name': mapping.iloc[0].get('Group Name', '')
                }
            else:
                field_mappings[column] = {
                    'description': column,
                    'importance': 'unknown',
                    'type': 'unknown',
                    'length': '',
                    'group_name': ''
                }

        return field_mappings

    def create_structured_data_summary(self, product_number: str, product_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Create structured summary of product data with field descriptions"""
        summary = {
            'product_number': product_number,
            'workbook_name': self.workbook_name,
            'sheets_found': list(product_data.keys()),
            'total_sheets': len(product_data),
            'detailed_data': {}
        }

        for sheet_name, df in product_data.items():
            # Get field mappings for this sheet
            field_mappings = self.map_field_descriptions(sheet_name, df.columns.tolist())

            sheet_summary = {
                'sheet_name': sheet_name,
                'record_count': len(df),
                'fields': {}
            }

            # Process each field with its value and description
            for column in df.columns:
                values = df[column].dropna().unique().tolist()

                # Limit values to prevent overwhelming output
                if len(values) > 5:
                    displayed_values = values[:5] + [f"... and {len(values)-5} more"]
                else:
                    displayed_values = values

                field_info = field_mappings.get(column, {})

                sheet_summary['fields'][column] = {
                    'values': displayed_values,
                    'description': field_info.get('description', column),
                    'importance': field_info.get('importance', 'unknown'),
                    'type': field_info.get('type', 'unknown'),
                    'group_name': field_info.get('group_name', ''),
                    'non_null_count': df[column].notna().sum()
                }

            summary['detailed_data'][sheet_name] = sheet_summary

        return summary

    def generate_ai_report(self, structured_data: Dict[str, Any]) -> str:
        """Generate AI-powered analysis report"""

        # Create a comprehensive prompt for AI analysis
        prompt = f"""
You are an SAP Material Master Data expert. Analyze the following product master data and provide a comprehensive business report.

PRODUCT ANALYSIS REQUEST:
Product Number: {structured_data['product_number']}
Workbook: {structured_data['workbook_name']}
Sheets Available: {', '.join(structured_data['sheets_found'])}
Total Data Sheets: {structured_data['total_sheets']}

DETAILED DATA ANALYSIS:
"""

        # Add detailed data for each sheet
        for sheet_name, sheet_data in structured_data['detailed_data'].items():
            prompt += f"""

=== {sheet_name.upper()} SHEET ===
Records Found: {sheet_data['record_count']}

Key Fields Analysis:
"""

            # Group fields by importance and type
            mandatory_fields = []
            optional_fields = []

            for field_name, field_info in sheet_data['fields'].items():
                field_summary = f"• {field_name}: {field_info['description']}"
                if field_info['values']:
                    field_summary += f" | Values: {', '.join(map(str, field_info['values']))}"

                if 'mandatory' in str(field_info['importance']).lower():
                    mandatory_fields.append(field_summary)
                else:
                    optional_fields.append(field_summary)

            if mandatory_fields:
                prompt += "\nMANDATORY FIELDS:\n" + "\n".join(mandatory_fields[:10])

            if optional_fields:
                prompt += "\nOPTIONAL FIELDS:\n" + "\n".join(optional_fields[:10])

        prompt += f"""

ANALYSIS REQUIREMENTS:
Please provide a comprehensive business analysis including:

1. **Product Profile Summary**
   - Product identification and basic attributes
   - Business significance and classification
   - Key characteristics (dimensions, weight, etc.)

2. **Data Completeness Assessment**
   - Which views/sheets have data vs missing
   - Critical missing information that could impact go-live
   - Data quality observations

3. **Business Impact Analysis**
   - Sales and distribution readiness
   - Manufacturing and planning implications  
   - Financial and valuation setup
   - Compliance and regulatory considerations

4. **Configuration Insights**
   - MRP and planning behavior analysis
   - Storage and warehouse implications
   - Tax and legal compliance status

5. **Migration Readiness Score**
   - Overall completeness percentage
   - Critical gaps requiring attention
   - Recommendations for next steps

6. **Risk Assessment**
   - What could go wrong if migrated as-is
   - Business processes that might be affected
   - Recommended validations before go-live

Format the response as a professional business report with clear sections and actionable insights.
Use bullet points and clear formatting for readability.
"""

        print("🤖 Generating AI analysis report...")
        ai_response = get_ai_response(prompt)

        return ai_response

    def analyze_product(self, product_number: str) -> str:
        """Main method to analyze a product and generate report"""
        try:
            print(f"📊 Starting analysis for product '{product_number}' in workbook '{self.workbook_name}'")

            # Step 1: Extract product data from all sheets
            product_data = self.extract_product_data(product_number)

            if not product_data:
                # Provide enhanced error message with suggestions
                error_msg = f"❌ No data found for product '{product_number}' in workbook '{self.workbook_name}'\n"
                error_msg += f"\n🔍 Troubleshooting suggestions:\n"
                error_msg += f"1. Check if the workbook name is correct: '{self.workbook_name}'\n"
                error_msg += f"2. Verify the product number exists in your data\n"
                error_msg += f"3. Check if CSV files were properly generated in ./core/dataframe/{self.workbook_name}/\n"
                error_msg += f"4. Ensure the PRODUCT column exists in your sheets\n"
                error_msg += f"\n💡 Try running the workbook analysis first: '{self.workbook_name} ready'"

                return error_msg

            # Step 2: Create structured summary with field descriptions
            structured_data = self.create_structured_data_summary(product_number, product_data)

            # Step 3: Generate AI-powered report
            ai_report = self.generate_ai_report(structured_data)

            # Step 4: Combine technical summary with AI analysis
            final_report = f"""
# PRODUCT MASTER ANALYSIS REPORT

## Technical Summary
- **Product Number:** {product_number}
- **Workbook:** {self.workbook_name}
- **Sheets with Data:** {len(product_data)}
- **Total Records:** {sum(len(df) for df in product_data.values())}

## Data Coverage
{', '.join(product_data.keys())}

---

## AI Business Analysis

{ai_report}

---

## Technical Data Details
"""

            # Add technical details for reference
            for sheet_name, df in product_data.items():
                final_report += f"""
### {sheet_name}
- Records: {len(df)}
- Fields: {len(df.columns)}
- Non-empty fields: {df.notna().sum().sum()}
"""

            return final_report

        except Exception as e:
            error_msg = f"❌ Error analyzing product '{product_number}': {str(e)}"
            print(error_msg)
            return error_msg

def generate_product_report(workbook_name: str, product_number: str) -> str:
    """
    Main function to generate product master report

    Args:
        workbook_name: Name of the workbook containing the data
        product_number: Product number to analyze

    Returns:
        Formatted report string
    """
    try:
        analyzer = ProductMasterAnalyzer(workbook_name)
        report = analyzer.analyze_product(product_number)
        return report

    except Exception as e:
        return f"❌ Report generation failed: {str(e)}"
