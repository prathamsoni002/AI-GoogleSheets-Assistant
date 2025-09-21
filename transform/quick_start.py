
#!/usr/bin/env python3
"""
MITRA AI Email Transformation Quick Start
========================================
This script discovers available workbooks and transforms their raw email data
into optimized intermediate formats for efficient AI querying.
"""

import os
import sys
from pathlib import Path

# Add the transform/code directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

try:
    from .code.enhanced_email_transformer import EnhancedEmailTransformer
except ImportError as e:
    print(f"Error importing transformer: {e}")
    print("Please ensure the transform/code/enhanced_email_transformer.py file exists.")
    sys.exit(1)

def list_workbooks(base_dir='OutlookData/workbooks'):
    """Discover available workbooks with raw_emails.json files."""
    if not os.path.exists(base_dir):
        return []

    workbooks = []
    for item in os.listdir(base_dir):
        workbook_path = os.path.join(base_dir, item)
        if os.path.isdir(workbook_path):
            raw_emails_path = os.path.join(workbook_path, 'raw_emails.json')
            if os.path.exists(raw_emails_path):
                workbooks.append({
                    'name': item,
                    'path': workbook_path,
                    'raw_emails': raw_emails_path,
                    'size': os.path.getsize(raw_emails_path)
                })

    return workbooks

def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_names[i]}"

def display_workbooks(workbooks):
    """Display available workbooks in a formatted table."""
    print("\n" + "="*80)
    print("📧 MITRA AI - Email Transformation System")
    print("="*80)
    print(f"{'#':<3} {'Workbook Name':<25} {'Raw Email Size':<15} {'Status':<15}")
    print("-"*80)

    for i, wb in enumerate(workbooks, 1):
        size_str = format_file_size(wb['size'])
        result_dir = f"transform/result/{wb['name']}"
        status = "✅ Processed" if os.path.exists(result_dir) else "⏳ Pending"
        print(f"{i:<3} {wb['name']:<25} {size_str:<15} {status:<15}")

    print("-"*80)
    print(f"Total workbooks found: {len(workbooks)}")
    print("="*80)

def get_user_choice(workbooks):
    """Get user selection for workbook to process."""
    while True:
        try:
            print("\nOptions:")
            print("• Enter workbook number (1-{}) to transform".format(len(workbooks)))
            print("• Enter 'all' to process all workbooks")
            print("• Enter 'q' to quit")

            choice = input("\n👉 Your choice: ").strip().lower()

            if choice == 'q':
                return None
            elif choice == 'all':
                return 'all'
            else:
                choice_num = int(choice)
                if 1 <= choice_num <= len(workbooks):
                    return choice_num - 1
                else:
                    print(f"❌ Please enter a number between 1 and {len(workbooks)}")
        except ValueError:
            print("❌ Invalid input. Please enter a number, 'all', or 'q'")

def process_workbook(workbook, transformer):
    """Process a single workbook."""
    print(f"\n🔄 Processing workbook: {workbook['name']}")
    print(f"📂 Raw emails: {workbook['raw_emails']}")

    # Create result directory
    result_dir = f"transform/result/{workbook['name']}"

    try:
        # Transform the emails
        master_index = transformer.transform_emails(workbook['raw_emails'], result_dir)

        print(f"\n✅ Success! Workbook '{workbook['name']}' processed successfully.")
        print(f"📁 Results: {result_dir}/")
        print(f"📊 Files created: {len(master_index['transformation_files'])}")
        print(f"📧 Emails processed: {master_index['total_emails']}")
        print(f"👥 Participants: {master_index['statistics']['participants']}")
        print(f"📎 Attachments: {master_index['statistics']['attachments']}")

        return True

    except Exception as e:
        print(f"\n❌ Error processing workbook '{workbook['name']}': {str(e)}")
        print("Please check the raw_emails.json file format and try again.")
        return False

def main():
    """Main execution function."""
    print("🚀 Initializing MITRA AI Email Transformation System...")

    # Discover available workbooks
    workbooks = list_workbooks()

    if not workbooks:
        print("\n❌ No workbooks found!")
        print("Expected structure: OutlookData/workbooks/{WorkbookName}/raw_emails.json")
        print("\nPlease ensure you have:")
        print("• Created the OutlookData/workbooks/ directory")
        print("• Added workbook folders (e.g., 'Product Master')")
        print("• Placed raw_emails.json files in each workbook folder")
        return

    # Display available workbooks
    display_workbooks(workbooks)

    # Get user choice
    choice = get_user_choice(workbooks)
    if choice is None:
        print("\n👋 Goodbye!")
        return

    # Initialize transformer
    print("\n🔧 Initializing enhanced email transformer...")
    transformer = EnhancedEmailTransformer()

    # Process workbook(s)
    if choice == 'all':
        print(f"\n🎯 Processing all {len(workbooks)} workbooks...")
        success_count = 0
        for i, workbook in enumerate(workbooks, 1):
            print(f"\n[{i}/{len(workbooks)}] " + "="*50)
            if process_workbook(workbook, transformer):
                success_count += 1

        print(f"\n🎉 Batch processing complete!")
        print(f"✅ Successful: {success_count}/{len(workbooks)}")
        if success_count < len(workbooks):
            print(f"❌ Failed: {len(workbooks) - success_count}")

    else:
        # Process single workbook
        workbook = workbooks[choice]
        process_workbook(workbook, transformer)

    print("\n" + "="*80)
    print("🎯 Next Steps:")
    print("• Check the transform/result/ directory for generated files")
    print("• Use these files in your MITRA AI chatbot for efficient querying")
    print("• Files are optimized for ~85% token reduction vs raw emails")
    print("="*80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("Please check your setup and try again.")
