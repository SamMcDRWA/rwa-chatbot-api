#!/usr/bin/env python3
"""
Example of how to add a module description programmatically
This shows the structure and can be used as a template
"""

from add_module_description import add_description

# Example: Adding description for 13.05 Weekly Services Report
def add_13_05_description():
    """Example of adding a detailed description"""
    
    success = add_description(
        module_title="13.05 Weekly Services Report",
        detailed_description="The 13.05 Weekly Services Report provides comprehensive tracking of all patient care services delivered across the pharmacy network. This report consolidates data from multiple service areas including MUR (Medicines Use Review), NMS (New Medicine Service), flu vaccinations, and other clinical services. It offers both summary-level metrics and detailed breakdowns by pharmacy location, service type, and patient demographics.",
        purpose="Monitor weekly performance of clinical services, track service delivery targets, and identify areas for improvement in patient care delivery.",
        key_metrics=[
            "Total services delivered",
            "Services by type (MUR, NMS, Vaccinations)",
            "Completion rates",
            "Patient satisfaction scores",
            "Revenue per service"
        ],
        usage_notes="Review weekly to track progress against monthly targets. Use filters to drill down by pharmacy location or service type. Export data for management reporting.",
        target_audience="Pharmacy managers, area managers, clinical services team, senior management"
    )
    
    if success:
        print("✅ Description added successfully!")
    else:
        print("❌ Failed to add description")

if __name__ == "__main__":
    add_13_05_description()
