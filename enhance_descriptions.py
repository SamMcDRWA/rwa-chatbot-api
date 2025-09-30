#!/usr/bin/env python3
"""
Script to enhance module descriptions in the database
This allows you to add detailed, rich descriptions for each module
"""

import psycopg2
from dotenv import load_dotenv
import os
import json

load_dotenv()

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def add_detailed_description(object_id: str, detailed_description: str):
    """Add detailed description to a specific module"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the description field with detailed information
        cursor.execute("""
            UPDATE chatbot.objects 
            SET description = %s 
            WHERE object_id = %s
        """, (detailed_description, object_id))
        
        conn.commit()
        print(f"✅ Updated description for object {object_id}")
        
    except Exception as e:
        print(f"❌ Error updating {object_id}: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def add_detailed_descriptions_batch(descriptions: dict):
    """Add detailed descriptions for multiple modules"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for object_id, description in descriptions.items():
            cursor.execute("""
                UPDATE chatbot.objects 
                SET description = %s 
                WHERE object_id = %s
            """, (description, object_id))
        
        conn.commit()
        print(f"✅ Updated {len(descriptions)} module descriptions")
        
    except Exception as e:
        print(f"❌ Error updating descriptions: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_module_info():
    """Get current module information to help you identify what to update"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT object_id, title, project_name, description
            FROM chatbot.objects 
            WHERE object_type = 'workbook'
            ORDER BY project_name, title
        """)
        
        results = cursor.fetchall()
        
        print("📋 Current Modules in Database:")
        print("=" * 80)
        
        for result in results:
            object_id, title, project_name, description = result
            print(f"\n🔹 {title}")
            print(f"   Project: {project_name}")
            print(f"   ID: {object_id}")
            print(f"   Current Description: {description[:100] if description else 'None'}...")
            print("-" * 40)
        
        return results
        
    except Exception as e:
        print(f"❌ Error getting module info: {e}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def example_detailed_descriptions():
    """Example of how to structure detailed descriptions"""
    return {
        "13.05": """
# 13.05 Weekly Services Report

## Overview
This comprehensive weekly report provides detailed insights into patient care services delivered across all pharmacy locations. It tracks key performance indicators for clinical services and patient engagement.

## What's Included
- **MUR (Medicine Use Review) Statistics**: Number of reviews conducted, common issues identified
- **NMS (New Medicine Service) Metrics**: New medicine consultations, follow-up rates
- **Clinical Service Performance**: Asthma management, diabetes care, flu vaccination rates
- **Patient Engagement**: Service uptake, satisfaction scores, repeat service usage
- **Staff Productivity**: Clinical hours, service delivery efficiency

## Key Metrics
- Weekly service volumes by type
- Patient demographics and service preferences
- Clinical outcomes and intervention success rates
- Resource utilization and capacity planning data

## How to Use
- Review weekly trends to identify service gaps
- Compare performance across different locations
- Track progress toward clinical service targets
- Identify training needs for staff
- Plan resource allocation for upcoming weeks

## Target Audience
- Pharmacy managers
- Clinical service coordinators
- Regional operations teams
- Clinical governance committees
        """,
        
        "1.05": """
# 1.05 Executive Monthly Report

## Overview
High-level monthly summary report designed for senior management and executives. Provides strategic insights into pharmacy operations, financial performance, and key business metrics.

## What's Included
- **Financial Summary**: Revenue, margins, cost analysis
- **Operational KPIs**: Sales volumes, customer metrics, efficiency ratios
- **Strategic Initiatives**: Progress on key projects and objectives
- **Market Performance**: Competitive analysis, market share trends
- **Risk Management**: Key risks, mitigation strategies, compliance status

## Key Metrics
- Monthly revenue and profit margins
- Customer acquisition and retention rates
- Operational efficiency indicators
- Strategic goal progress tracking
- Market performance benchmarks

## How to Use
- Board presentations and executive briefings
- Strategic planning and decision making
- Performance monitoring and goal setting
- Stakeholder reporting and communication
- Risk assessment and management

## Target Audience
- Executive leadership team
- Board of directors
- Senior management
- Investors and stakeholders
        """
    }

if __name__ == "__main__":
    print("🔧 RWA Chatbot - Module Description Enhancement Tool")
    print("=" * 60)
    
    # Show current modules
    get_module_info()
    
    print("\n📝 Example Detailed Description Format:")
    print("=" * 60)
    examples = example_detailed_descriptions()
    for key, desc in examples.items():
        print(f"\n{key}: {desc[:200]}...")
    
    print("\n💡 To add detailed descriptions:")
    print("1. Use add_detailed_description(object_id, description) for single modules")
    print("2. Use add_detailed_descriptions_batch(descriptions_dict) for multiple modules")
    print("3. Descriptions support Markdown formatting for rich text")
