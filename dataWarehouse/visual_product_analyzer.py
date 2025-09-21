import os
import pandas as pd
import json
import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend to prevent errors in server environments
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import seaborn as sns
import networkx as nx
from datetime import datetime
import base64
import io
from typing import Dict, List, Any, Optional
from core.openai_api import get_ai_response
import warnings
warnings.filterwarnings('ignore')


# Set up matplotlib for better output
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.style.use('default')


class ProductMasterVisualizer:
    """
    Creates interactive visualizations for SAP Product Master data analysis
    """

    def __init__(self, workbook_name: str):
        self.workbook_name = workbook_name
        # --- PATH CORRECTION: Use absolute path for robustness ---
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.dataframe_path = os.path.join(project_root, 'core', 'dataframes', workbook_name)
        self.dictionary_path = os.path.join(project_root, 'sap_data_dictionary.csv')
        # ---------------------------------------------------------
        self.product_data = {}
        self.field_mappings = {}
        self.visualizations = []

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
        return sheets

    def extract_product_data(self, product_number: str) -> Dict[str, pd.DataFrame]:
        """Extract data for specific product across all sheets with enhanced search"""
        product_data = {}
        available_sheets = self.get_available_sheets()

        print(f"🔍 Extracting data for product '{product_number}' from {len(available_sheets)} sheets...")

        for sheet_name in available_sheets:
            try:
                file_path = os.path.join(self.dataframe_path, f"{sheet_name}.csv")
                df = pd.read_csv(file_path)

                if 'PRODUCT' in df.columns:
                    # Try exact match first, then case-insensitive
                    product_rows = df[df['PRODUCT'] == product_number]
                    if product_rows.empty:
                        product_rows = df[df['PRODUCT'].str.upper() == product_number.upper()]

                    if not product_rows.empty:
                        product_data[sheet_name] = product_rows

            except Exception as e:
                print(f"❌ Error processing sheet '{sheet_name}': {e}")

        return product_data

    def create_product_hierarchy_tree(self, product_data: Dict[str, pd.DataFrame], product_number: str) -> str:
        """Create a hierarchical tree visualization of product structure"""
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        # Get basic data
        basic_data = product_data.get('Basic Data', pd.DataFrame())
        if basic_data.empty:
            ax.text(5, 5, 'No Basic Data Available', ha='center', va='center', fontsize=16)
            return self._save_plot_as_base64(fig, 'product_hierarchy')

        # Center product node
        product_box = FancyBboxPatch((4, 4.5), 2, 1, boxstyle="round,pad=0.1", 
                                    facecolor='lightblue', edgecolor='navy', linewidth=2)
        ax.add_patch(product_box)
        ax.text(5, 5, f"PRODUCT\n{product_number}", ha='center', va='center', 
                fontweight='bold', fontsize=12)

        # Product Type (top)
        if 'MTART' in basic_data.columns:
            product_type = basic_data['MTART'].iloc[0] if not basic_data['MTART'].isna().iloc[0] else 'N/A'
            type_box = FancyBboxPatch((4, 7), 2, 0.8, boxstyle="round,pad=0.1", 
                                     facecolor='lightgreen', edgecolor='darkgreen')
            ax.add_patch(type_box)
            ax.text(5, 7.4, f"Type: {product_type}", ha='center', va='center', fontweight='bold')

            # Connection line
            ax.plot([5, 5], [5.5, 7], 'k-', linewidth=2)

        # Base UoM (bottom left)
        if 'MEINS' in basic_data.columns:
            base_uom = basic_data['MEINS'].iloc[0] if not basic_data['MEINS'].isna().iloc[0] else 'N/A'
            uom_box = FancyBboxPatch((1, 3), 2, 0.8, boxstyle="round,pad=0.1", 
                                    facecolor='lightyellow', edgecolor='orange')
            ax.add_patch(uom_box)
            ax.text(2, 3.4, f"Base UoM\n{base_uom}", ha='center', va='center', fontweight='bold')

            # Connection line
            ax.plot([4, 3], [4.8, 3.8], 'k-', linewidth=1)

        # Product Group (bottom right)
        if 'MATKL' in basic_data.columns:
            prod_group = basic_data['MATKL'].iloc[0] if not basic_data['MATKL'].isna().iloc[0] else 'N/A'
            group_box = FancyBboxPatch((7, 3), 2, 0.8, boxstyle="round,pad=0.1", 
                                      facecolor='lightcoral', edgecolor='darkred')
            ax.add_patch(group_box)
            ax.text(8, 3.4, f"Group\n{prod_group}", ha='center', va='center', fontweight='bold')

            # Connection line
            ax.plot([6, 7], [4.8, 3.8], 'k-', linewidth=1)

        # Division (left)
        if 'SPART' in basic_data.columns:
            division = basic_data['SPART'].iloc[0] if not basic_data['SPART'].isna().iloc[0] else 'N/A'
            div_box = FancyBboxPatch((0.5, 4.5), 2, 0.8, boxstyle="round,pad=0.1", 
                                    facecolor='lightsteelblue', edgecolor='steelblue')
            ax.add_patch(div_box)
            ax.text(1.5, 4.9, f"Division\n{division}", ha='center', va='center', fontweight='bold')

            # Connection line
            ax.plot([2.5, 4], [4.9, 5], 'k-', linewidth=1)

        # Alternative UoMs (right side)
        alt_uom_data = product_data.get('Alternative Units of Measure', pd.DataFrame())
        if not alt_uom_data.empty:
            y_pos = 6
            for idx, row in alt_uom_data.iterrows():
                if idx < 3:  # Limit to 3 alternative UoMs
                    alt_uom = row.get('MEINH', 'N/A')
                    ratio = f"{row.get('UMREN', 'N/A')}:{row.get('UMREZ', 'N/A')}"

                    alt_box = FancyBboxPatch((7.5, y_pos), 2, 0.6, boxstyle="round,pad=0.05", 
                                            facecolor='lavender', edgecolor='purple')
                    ax.add_patch(alt_box)
                    ax.text(8.5, y_pos + 0.3, f"{alt_uom}\n({ratio})", ha='center', va='center', fontsize=9)

                    # Connection line
                    ax.plot([6, 7.5], [5, y_pos + 0.3], 'k--', linewidth=1, alpha=0.7)
                    y_pos -= 1

        ax.set_title(f'Product Master Hierarchy - {product_number}', fontsize=16, fontweight='bold', pad=20)

        return self._save_plot_as_base64(fig, 'product_hierarchy')

    def create_organizational_coverage_chart(self, product_data: Dict[str, pd.DataFrame], product_number: str) -> str:
        """Create visualization showing organizational coverage (plants, sales orgs, warehouses)"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Plant Coverage
        plant_data = product_data.get('Plant Data', pd.DataFrame())
        if not plant_data.empty and 'WERKS' in plant_data.columns:
            plants = plant_data['WERKS'].dropna().unique()
            ax1.bar(range(len(plants)), [1] * len(plants), color='lightblue')
            ax1.set_xticks(range(len(plants)))
            ax1.set_xticklabels(plants, rotation=45)
            ax1.set_title('Plant Coverage', fontweight='bold')
            ax1.set_ylabel('Configured')
        else:
            ax1.text(0.5, 0.5, 'No Plant Data', ha='center', va='center', transform=ax1.transAxes)
            ax1.set_title('Plant Coverage', fontweight='bold')

        # 2. Sales Organization Coverage  
        dist_data = product_data.get('Distribution Chains', pd.DataFrame())
        if not dist_data.empty and 'VKORG' in dist_data.columns:
            sales_orgs = dist_data['VKORG'].dropna().unique()
            dist_channels = dist_data['VTWEG'].dropna().unique() if 'VTWEG' in dist_data.columns else []

            # Create a matrix showing sales org x distribution channel
            if len(dist_channels) > 0:
                matrix_data = []
                for so in sales_orgs:
                    for dc in dist_channels:
                        if not dist_data[(dist_data['VKORG'] == so) & (dist_data['VTWEG'] == dc)].empty:
                            matrix_data.append([so, dc, 1])
                        else:
                            matrix_data.append([so, dc, 0])

                if matrix_data:
                    df_matrix = pd.DataFrame(matrix_data, columns=['Sales Org', 'Dist Channel', 'Configured'])
                    pivot_matrix = df_matrix.pivot(index='Sales Org', columns='Dist Channel', values='Configured')
                    sns.heatmap(pivot_matrix, annot=True, cmap='Blues', ax=ax2, cbar_kws={'label': 'Configured'})
            else:
                ax2.bar(range(len(sales_orgs)), [1] * len(sales_orgs), color='lightgreen')
                ax2.set_xticks(range(len(sales_orgs)))
                ax2.set_xticklabels(sales_orgs, rotation=45)

            ax2.set_title('Sales Organization Coverage', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'No Distribution Data', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Sales Organization Coverage', fontweight='bold')

        # 3. Warehouse Coverage
        wh_product = product_data.get('Warehouse Product', pd.DataFrame())
        wh_storage = product_data.get('Warehouse Product Storage Type', pd.DataFrame())

        warehouses = []
        if not wh_product.empty and 'LGNUM' in wh_product.columns:
            warehouses.extend(wh_product['LGNUM'].dropna().unique())
        if not wh_storage.empty and 'LGNUM' in wh_storage.columns:
            warehouses.extend(wh_storage['LGNUM'].dropna().unique())

        warehouses = list(set(warehouses))  # Remove duplicates

        if warehouses:
            # Count storage types per warehouse
            storage_counts = {}
            for wh in warehouses:
                if not wh_storage.empty:
                    count = len(wh_storage[wh_storage['LGNUM'] == wh])
                    storage_counts[wh] = count
                else:
                    storage_counts[wh] = 1

            ax3.bar(storage_counts.keys(), storage_counts.values(), color='lightcoral')
            ax3.set_title('Warehouse Coverage', fontweight='bold')
            ax3.set_ylabel('Storage Types Configured')
            ax3.tick_params(axis='x', rotation=45)
        else:
            ax3.text(0.5, 0.5, 'No Warehouse Data', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Warehouse Coverage', fontweight='bold')

        # 4. Tax Classification Coverage
        tax_data = product_data.get('Tax Classification', pd.DataFrame())
        if not tax_data.empty and 'ALAND' in tax_data.columns:
            countries = tax_data['ALAND'].dropna().unique()
            tax_categories = []

            for country in countries:
                country_data = tax_data[tax_data['ALAND'] == country]
                # Count non-empty tax classifications
                tax_cols = [col for col in country_data.columns if col.startswith('TAXM') and not country_data[col].isna().all()]
                tax_categories.append(len(tax_cols))

            bars = ax4.bar(countries, tax_categories, color='lightyellow')
            ax4.set_title('Tax Classification Coverage', fontweight='bold')
            ax4.set_ylabel('Tax Categories Configured')
            ax4.tick_params(axis='x', rotation=45)

            # Add value labels on bars
            for bar, value in zip(bars, tax_categories):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                        f'{value}', ha='center', va='bottom')
        else:
            ax4.text(0.5, 0.5, 'No Tax Data', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Tax Classification Coverage', fontweight='bold')

        plt.tight_layout()
        plt.suptitle(f'Organizational Coverage Analysis - {product_number}', 
                    fontsize=16, fontweight='bold', y=0.98)

        return self._save_plot_as_base64(fig, 'organizational_coverage')

    def create_warehouse_operations_flow(self, product_data: Dict[str, pd.DataFrame], product_number: str) -> str:
        """Create visualization showing warehouse operations and rules"""
        fig, ax = plt.subplots(1, 1, figsize=(16, 10))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.axis('off')

        wh_storage = product_data.get('Warehouse Product Storage Type', pd.DataFrame())
        if wh_storage.empty:
            ax.text(5, 4, 'No Warehouse Storage Data Available', 
                   ha='center', va='center', fontsize=16)
            return self._save_plot_as_base64(fig, 'warehouse_operations')

        # Group by warehouse
        warehouses = wh_storage['LGNUM'].unique() if 'LGNUM' in wh_storage.columns else ['WH01']

        y_start = 7
        colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']

        for idx, warehouse in enumerate(warehouses[:3]):  # Limit to 3 warehouses
            wh_data = wh_storage[wh_storage['LGNUM'] == warehouse] if 'LGNUM' in wh_storage.columns else wh_storage

            # Warehouse header
            wh_box = FancyBboxPatch((0.5, y_start-0.4), 9, 0.8, boxstyle="round,pad=0.1", 
                                    facecolor=colors[idx % len(colors)], edgecolor='black', linewidth=2)
            ax.add_patch(wh_box)
            ax.text(5, y_start, f'Warehouse: {warehouse}', ha='center', va='center', 
                   fontweight='bold', fontsize=14)

            # Storage types flow
            storage_types = wh_data['LGTYP'].unique() if 'LGTYP' in wh_data.columns else ['001', '002']

            x_pos = 1
            for st_idx, storage_type in enumerate(storage_types[:4]):  # Limit to 4 storage types
                st_data = wh_data[wh_data['LGTYP'] == storage_type] if 'LGTYP' in wh_data.columns else wh_data.iloc[[0]]

                # Storage type box
                st_box = FancyBboxPatch((x_pos, y_start-1.5), 1.8, 0.8, boxstyle="round,pad=0.05", 
                                       facecolor='white', edgecolor='gray')
                ax.add_patch(st_box)
                ax.text(x_pos + 0.9, y_start-1.1, f'ST: {storage_type}', 
                       ha='center', va='center', fontweight='bold', fontsize=9)

                # Putaway strategy
                put_strategy = st_data.iloc[0].get('PUT_STRA', 'N/A') if len(st_data) > 0 else 'N/A'
                ax.text(x_pos + 0.9, y_start-1.4, f'Put: {put_strategy}', 
                       ha='center', va='center', fontsize=8)

                # Stock removal strategy  
                rem_strategy = st_data.iloc[0].get('REM_STRA', 'N/A') if len(st_data) > 0 else 'N/A'
                ax.text(x_pos + 0.9, y_start-1.7, f'Rem: {rem_strategy}', 
                       ha='center', va='center', fontsize=8)

                # Connection to warehouse
                ax.plot([x_pos + 0.9, x_pos + 0.9], [y_start-0.4, y_start-0.7], 'k-', linewidth=1)

                x_pos += 2

            y_start -= 2.5

        ax.set_title(f'Warehouse Operations Flow - {product_number}', 
                    fontsize=16, fontweight='bold', pad=20)

        return self._save_plot_as_base64(fig, 'warehouse_operations')

    def create_data_completeness_dashboard(self, product_data: Dict[str, pd.DataFrame], product_number: str) -> str:
        """Create a comprehensive data completeness dashboard"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Sheet Coverage Pie Chart
        sheet_names = list(product_data.keys())
        sheet_counts = [len(df) for df in product_data.values()]

        if sheet_names:
            ax1.pie(sheet_counts, labels=sheet_names, autopct='%1.0f%%', startangle=90)
            ax1.set_title('Data Distribution by Sheet', fontweight='bold')
        else:
            ax1.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax1.transAxes)

        # 2. Field Completeness by Sheet
        sheet_completeness = {}
        for sheet_name, df in product_data.items():
            if not df.empty:
                total_fields = len(df.columns)
                filled_fields = df.notna().sum().sum()
                completeness = (filled_fields / (total_fields * len(df))) * 100
                sheet_completeness[sheet_name] = completeness

        if sheet_completeness:
            sheets = list(sheet_completeness.keys())
            completeness_values = list(sheet_completeness.values())

            bars = ax2.barh(sheets, completeness_values, color='lightgreen')
            ax2.set_xlabel('Completeness %')
            ax2.set_title('Field Completeness by Sheet', fontweight='bold')
            ax2.set_xlim(0, 100)

            # Add percentage labels
            for bar, value in zip(bars, completeness_values):
                width = bar.get_width()
                ax2.text(width + 1, bar.get_y() + bar.get_height()/2, 
                        f'{value:.1f}%', ha='left', va='center')

        # 3. Mandatory vs Optional Fields
        mandatory_filled = 0
        mandatory_total = 0
        optional_filled = 0
        optional_total = 0

        dictionary_df = self.load_sap_dictionary()

        for sheet_name, df in product_data.items():
            if not dictionary_df.empty:
                sheet_dict = dictionary_df[dictionary_df['Sheet Name'] == sheet_name]
                for column in df.columns:
                    field_info = sheet_dict[sheet_dict['SAP Field'] == column]
                    if not field_info.empty:
                        importance = field_info.iloc[0].get('Importance', '')
                        is_mandatory = 'mandatory' in str(importance).lower()

                        filled_count = df[column].notna().sum()
                        total_count = len(df)

                        if is_mandatory:
                            mandatory_filled += filled_count
                            mandatory_total += total_count
                        else:
                            optional_filled += filled_count
                            optional_total += total_count

        if mandatory_total > 0 or optional_total > 0:
            categories = ['Mandatory Fields', 'Optional Fields']
            filled = [mandatory_filled, optional_filled]
            total = [mandatory_total, optional_total]

            x = range(len(categories))
            width = 0.35

            ax3.bar([i - width/2 for i in x], total, width, label='Total Fields', color='lightgray')
            ax3.bar([i + width/2 for i in x], filled, width, label='Filled Fields', color='lightblue')

            ax3.set_xlabel('Field Categories')
            ax3.set_ylabel('Number of Fields')
            ax3.set_title('Mandatory vs Optional Field Completion', fontweight='bold')
            ax3.set_xticks(x)
            ax3.set_xticklabels(categories)
            ax3.legend()

        # 4. Data Quality Score
        overall_completeness = 0
        total_sheets = len(product_data)

        if total_sheets > 0:
            overall_completeness = sum(sheet_completeness.values()) / total_sheets

        # Create a gauge-like visualization
        ax4.pie([overall_completeness, 100-overall_completeness], 
               colors=['green' if overall_completeness > 80 else 'orange' if overall_completeness > 60 else 'red', 'lightgray'],
               startangle=90, counterclock=False, wedgeprops=dict(width=0.3))

        ax4.text(0, 0, f'{overall_completeness:.1f}%\nComplete', 
                 ha='center', va='center', fontsize=16, fontweight='bold')
        ax4.set_title('Overall Data Quality Score', fontweight='bold')

        plt.tight_layout()
        plt.suptitle(f'Data Completeness Dashboard - {product_number}', 
                    fontsize=16, fontweight='bold', y=0.98)

        return self._save_plot_as_base64(fig, 'data_completeness')

    def _save_plot_as_base64(self, fig, plot_name: str) -> str:
        """Convert matplotlib figure to base64 string"""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                     facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        plt.close(fig)

        # Store for potential PDF generation or internal tracking
        self.visualizations.append({
            'name': plot_name,
            'base64': image_base64,
            'timestamp': datetime.now().isoformat()
        })

        return image_base64

    def generate_ai_insights(self, product_data: Dict[str, pd.DataFrame], product_number: str) -> str:
        """Generate AI-powered insights for each visualization"""
        # Create a summary of the data for AI analysis
        data_summary = f"""
Product: {product_number}
Workbook: {self.workbook_name}
Sheets with data: {', '.join(product_data.keys())}
Total records: {sum(len(df) for df in product_data.values())}

Data overview:
"""

        for sheet_name, df in product_data.items():
            key_fields = []
            for col in df.columns[:10]:  # Limit to key fields
                if not df[col].isna().all():
                    values = df[col].dropna().unique()
                    if len(values) <= 3:
                        key_fields.append(f"{col}: {', '.join(map(str, values))}")
                    else:
                        key_fields.append(f"{col}: {len(values)} unique values")

            data_summary += f"""
{sheet_name}: {len(df)} records
- Key fields: {'; '.join(key_fields[:5])}
"""

        prompt = f"""
As an SAP expert, provide concise, business-focused insights for these visualizations of product master data:

{data_summary}

For each visualization type, provide 2-3 key insights:

1. **Product Hierarchy Tree**: What does the product structure tell us about business impact?

2. **Organizational Coverage**: How well is this product set up across the business organization?

3. **Warehouse Operations**: What are the key operational considerations for this product?

4. **Data Completeness**: What are the critical data gaps and their business risks?

Keep each insight to 1-2 sentences and focus on actionable business implications.
"""

        try:
            insights = get_ai_response(prompt)
            return insights
        except Exception as e:
            return f"Unable to generate AI insights: {str(e)}"

    def create_comprehensive_visual_report(self, product_number: str) -> Dict[str, Any]:
        """Create all visualizations and compile into a comprehensive report"""
        print(f"🎨 Creating visual report for product '{product_number}'...")

        product_data = self.extract_product_data(product_number)

        if not product_data:
            return {
                'status': 'error',
                'message': f"No data found for product '{product_number}' in workbook '{self.workbook_name}'"
            }

        try:
            # Generate all visualizations, assumed as base64 PNG strings or similar
            hierarchy_viz = self.create_product_hierarchy_tree(product_data, product_number)
            coverage_viz = self.create_organizational_coverage_chart(product_data, product_number)
            warehouse_viz = self.create_warehouse_operations_flow(product_data, product_number)
            completeness_viz = self.create_data_completeness_dashboard(product_data, product_number)

            # Generate AI insights as a text string
            ai_insights = self.generate_ai_insights(product_data, product_number)

            return {
                "ai_insights": ai_insights,
                "visualizations": {
                    "hierarchy": hierarchy_viz,
                    "coverage": coverage_viz,
                    "warehouse": warehouse_viz,
                    "completeness": completeness_viz,
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error generating visualizations: {str(e)}"
            }
            
def generate_visual_product_report(workbook_name: str, product_number: str) -> Dict[str, Any]:
    """
    Main function to generate visual product master report

    Args:
        workbook_name: Name of the workbook containing the data
        product_number: Product number to analyze

    Returns:
        JSON containing report elements — insights and visualization URLs
    """
    try:
        # --- CORRECTED PATH LOGIC ---
        # Determine the absolute path to the project's root directory from this script's location.
        # This script is in /dataWarehouse, so we go up one level ('..') to get the project root.
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        
        # Check if the workbook directory exists using an absolute path to be safe.
        dataframe_path = os.path.join(project_root, 'core', 'dataframes', workbook_name)

        if not os.path.exists(dataframe_path):
            return {
                'status': 'error',
                'message': f"Workbook '{workbook_name}' has not been processed yet"
            }

        visualizer = ProductMasterVisualizer(workbook_name)
        report_data = visualizer.create_comprehensive_visual_report(product_number)

        if report_data.get('status') == 'error':
            return report_data

        # Create the output directory using an absolute path to ensure images are saved
        # in the root 'static' folder, not 'ui/static' or 'dataWarehouse/static'.
        output_dir = os.path.join(project_root, 'static', 'visual_outputs', workbook_name, product_number)
        os.makedirs(output_dir, exist_ok=True)
        # ----------------------------

        image_urls = {}
        for viz_name, base64_img in report_data['visualizations'].items():
            filename = f"{viz_name}.png"
            # This filepath is now a guaranteed absolute path to the correct location
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as img_file:
                img_file.write(base64.b64decode(base64_img))
            
            # The URL for the browser remains the same, as the Flask server is correctly configured to map it.
            url = f"/static/visual_outputs/{workbook_name}/{product_number}/{filename}"
            image_urls[viz_name] = url

        return {
            'status': 'success',
            'product_number': product_number,
            'workbook_name': workbook_name,
            'ai_insights': report_data['ai_insights'],
            'data_summary': report_data.get('data_summary', {}),
            'visualization_urls': image_urls
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f"Visual report generation failed: {str(e)}"
        }
