#!/usr/bin/env python3
"""
Simple tool to add detailed descriptions to modules one at a time
This allows you to carefully review and validate each description before adding it
"""

import psycopg2
from dotenv import load_dotenv
import os
import json
from typing import List, Optional

load_dotenv()

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def list_modules():
    """List all available modules for selection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, project_name, description
            FROM chatbot.objects 
            WHERE object_type = 'workbook'
            ORDER BY project_name, title
        """)
        
        results = cursor.fetchall()
        
        print("📋 Available Modules:")
        print("=" * 80)
        
        current_project = None
        module_list = []
        
        for i, (title, project_name, description) in enumerate(results, 1):
            if project_name != current_project:
                print(f"\n📁 {project_name}")
                current_project = project_name
            
            has_description = "✅" if description and len(description) > 50 else "❌"
            print(f"  {i:2d}. {has_description} {title}")
            module_list.append((i, title, project_name, description))
        
        cursor.close()
        conn.close()
        return module_list
        
    except Exception as e:
        print(f"❌ Error listing modules: {e}")
        return []

def add_description(module_title: str, detailed_description: str, 
                   purpose: str = None, key_metrics: List[str] = None,
                   usage_notes: str = None, target_audience: str = None):
    """
    Add detailed description to a module
    
    Args:
        module_title: The exact title of the module
        detailed_description: Full paragraph description of what the module contains
        purpose: What the module is used for (optional)
        key_metrics: List of key metrics/measures (optional)
        usage_notes: How to use the module effectively (optional)
        target_audience: Who should use this module (optional)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create rich description object
        rich_description = {
            "detailed_description": detailed_description,
            "purpose": purpose or "",
            "key_metrics": key_metrics or [],
            "usage_notes": usage_notes or "",
            "target_audience": target_audience or "",
            "last_updated": "2025-01-12"
        }
        
        # Update the description field with JSON
        cursor.execute("""
            UPDATE chatbot.objects 
            SET description = %s
            WHERE title = %s AND object_type = 'workbook'
        """, [json.dumps(rich_description), module_title])
        
        if cursor.rowcount > 0:
            print(f"✅ Successfully updated: {module_title}")
            conn.commit()
            return True
        else:
            print(f"❌ Module not found: {module_title}")
            return False
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error updating {module_title}: {e}")
        return False

def preview_description(module_title: str, detailed_description: str, 
                       purpose: str = None, key_metrics: List[str] = None,
                       usage_notes: str = None, target_audience: str = None):
    """Preview how the description will look in the chatbot"""
    
    print(f"\n📝 Preview for: {module_title}")
    print("=" * 60)
    
    response_parts = [f"**{module_title}**"]
    
    if detailed_description:
        response_parts.append(f"\n{detailed_description}")
    
    if purpose:
        response_parts.append(f"\n**Purpose:** {purpose}")
    
    if key_metrics:
        response_parts.append(f"\n**Key Metrics:**")
        for metric in key_metrics:
            response_parts.append(f"• {metric}")
    
    if usage_notes:
        response_parts.append(f"\n**Usage Notes:** {usage_notes}")
    
    if target_audience:
        response_parts.append(f"\n**Target Audience:** {target_audience}")
    
    print("\n".join(response_parts))
    print("=" * 60)

def interactive_add():
    """Interactive tool to add descriptions one at a time"""
    
    while True:
        print("\n🔧 Module Description Tool")
        print("=" * 30)
        print("1. List all modules")
        print("2. Add description for a module")
        print("3. Preview description")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            list_modules()
            
        elif choice == "2":
            # List modules for selection
            modules = list_modules()
            if not modules:
                continue
            
            try:
                module_num = int(input(f"\nEnter module number (1-{len(modules)}): "))
                if 1 <= module_num <= len(modules):
                    selected_module = modules[module_num - 1]
                    module_title = selected_module[1]
                    
                    print(f"\n📝 Adding description for: {module_title}")
                    print("-" * 50)
                    
                    # Get description details
                    detailed_description = input("Enter detailed description: ").strip()
                    if not detailed_description:
                        print("❌ Description is required!")
                        continue
                    
                    purpose = input("Enter purpose (optional): ").strip() or None
                    usage_notes = input("Enter usage notes (optional): ").strip() or None
                    target_audience = input("Enter target audience (optional): ").strip() or None
                    
                    # Get key metrics
                    print("\nEnter key metrics (one per line, press Enter twice when done):")
                    key_metrics = []
                    while True:
                        metric = input("  Metric: ").strip()
                        if not metric:
                            break
                        key_metrics.append(metric)
                    
                    # Preview before saving
                    print(f"\n🔍 Preview:")
                    preview_description(module_title, detailed_description, purpose, key_metrics, usage_notes, target_audience)
                    
                    # Confirm save
                    confirm = input("\nSave this description? (y/n): ").strip().lower()
                    if confirm == 'y':
                        add_description(module_title, detailed_description, purpose, key_metrics, usage_notes, target_audience)
                    else:
                        print("❌ Description not saved.")
                else:
                    print("❌ Invalid module number!")
            except ValueError:
                print("❌ Please enter a valid number!")
                
        elif choice == "3":
            # Preview mode
            module_title = input("Enter module title: ").strip()
            detailed_description = input("Enter detailed description: ").strip()
            purpose = input("Enter purpose (optional): ").strip() or None
            usage_notes = input("Enter usage notes (optional): ").strip() or None
            target_audience = input("Enter target audience (optional): ").strip() or None
            
            print("\nEnter key metrics (one per line, press Enter twice when done):")
            key_metrics = []
            while True:
                metric = input("  Metric: ").strip()
                if not metric:
                    break
                key_metrics.append(metric)
            
            preview_description(module_title, detailed_description, purpose, key_metrics, usage_notes, target_audience)
            
        elif choice == "4":
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    interactive_add()
