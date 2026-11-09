"""
Master Reference Seed Data for Synthetic Generation.
"""
from typing import List, Dict, Tuple
from src.models.enums import DepartmentCategory, ItemCategory, Currency, PaymentTerms, SupplierRiskLevel

DEPARTMENTS_DATA = [
    ("DEPT-001", "Engineering & Software", DepartmentCategory.ENGINEERING, "CC-1010"),
    ("DEPT-002", "Cloud & IT Infrastructure", DepartmentCategory.IT_INFRASTRUCTURE, "CC-1020"),
    ("DEPT-003", "Data Science & AI Research", DepartmentCategory.RESEARCH_DEV, "CC-1030"),
    ("DEPT-004", "Global Operations & Supply Chain", DepartmentCategory.OPERATIONS, "CC-1040"),
    ("DEPT-005", "Brand & Product Marketing", DepartmentCategory.MARKETING, "CC-1050"),
    ("DEPT-006", "Corporate Facilities & Workplace", DepartmentCategory.FACILITIES, "CC-1060"),
    ("DEPT-007", "Financial Planning & Control", DepartmentCategory.FINANCE, "CC-1070"),
    ("DEPT-008", "Legal, Compliance & Risk", DepartmentCategory.LEGAL, "CC-1080"),
    ("DEPT-009", "People Operations & HR", DepartmentCategory.HUMAN_RESOURCES, "CC-1090"),
    ("DEPT-010", "Global Customer Experience", DepartmentCategory.CUSTOMER_SUPPORT, "CC-1100"),
]

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Sam", "Chris", "Pat",
    "David", "Sarah", "Michael", "Emily", "James", "Emma", "Daniel", "Olivia", "Matthew", "Sophia",
    "Ethan", "Ava", "Alexander", "Isabella", "William", "Mia", "Benjamin", "Charlotte", "Lucas", "Amelia",
    "Henry", "Harper", "Sebastian", "Evelyn", "Jack", "Abigail", "Owen", "Ella", "Theodore", "Aria",
    "Liam", "Noah", "Oliver", "Elijah", "Lucas", "Mason", "Logan", "Jackson", "Aiden", "Carter",
    "Priya", "Rahul", "Ananya", "Vikram", "Neha", "Arjun", "Aditi", "Rohan", "Pooja", "Sanjay",
    "Wei", "Jing", "Lei", "Fang", "Hao", "Yan", "Min", "Jun", "Chen", "Lin",
    "Carlos", "Elena", "Mateo", "Sofia", "Diego", "Valentina", "Alejandro", "Camila", "Javier", "Lucia",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
    "Patel", "Sharma", "Verma", "Rao", "Gupta", "Nair", "Iyer", "Choudhury", "Reddy", "Mehta",
    "Zhang", "Wang", "Li", "Zhao", "Chen", "Liu", "Yang", "Huang", "Wu", "Zhou",
]

ITEM_CATALOG: Dict[ItemCategory, List[Tuple[str, str, float]]] = {
    ItemCategory.HARDWARE: [
        ("High-Performance Server Rack 42U", "EA", 8500.0),
        ("Developer Workstation Dual GPU 64GB", "EA", 3200.0),
        ("Ultra-Wide 34-Inch Curved Monitor", "EA", 650.0),
        ("Enterprise Core Switch 48-Port 10GbE", "EA", 4800.0),
        ("NVMe Enterprise Storage Array 50TB", "EA", 12500.0),
        ("Wireless Access Point Wi-Fi 7", "EA", 420.0),
        ("Ergonomic Keyboard and Precision Mouse Combo", "EA", 180.0),
        ("Thunderbolt 4 Docking Station Dual Display", "EA", 240.0),
        ("AI Inference Accelerator Card PCIe", "EA", 9800.0),
        ("Uninterruptible Power Supply (UPS) 3000VA", "EA", 1600.0),
    ],
    ItemCategory.SOFTWARE: [
        ("Cloud Infrastructure Tier-1 Annual Subscription", "LICENSE", 24000.0),
        ("Enterprise CI/CD Build Pipeline 50 Runners", "LICENSE", 7200.0),
        ("Cybersecurity Endpoint Detection & Response (EDR)", "LICENSE", 5400.0),
        ("Database Management Enterprise Cluster License", "LICENSE", 18000.0),
        ("Data Analytics and Visualization Platform Seat", "LICENSE", 1200.0),
        ("Identity Access Management (IAM) SSO License", "LICENSE", 4500.0),
        ("Code Quality and SAST Security Scanner", "LICENSE", 3800.0),
        ("Customer Data Platform (CDP) Annual Tier", "LICENSE", 16500.0),
        ("Automated Compliance Monitoring Suite", "LICENSE", 8900.0),
        ("Developer IDE Team Suite Subscription", "LICENSE", 480.0),
    ],
    ItemCategory.SERVICES: [
        ("Annual Cloud Architecture Security Review", "MONTH", 6500.0),
        ("External Penetration Testing & Red Teaming", "PROJECT", 18500.0),
        ("Datacenter Preventive Maintenance Contract", "MONTH", 3200.0),
        ("24/7 Managed NOC Level-2 Support Service", "MONTH", 8500.0),
        ("Disaster Recovery Site Warm Standby Service", "MONTH", 4200.0),
        ("SLA Incident Management & SRE Escalation", "MONTH", 5000.0),
        ("Hardware Lifecycle Replacement Program Support", "QUARTER", 7500.0),
        ("Compliance ISO 27001 Surveillance Audit", "PROJECT", 14000.0),
    ],
    ItemCategory.FACILITIES: [
        ("Executive Motorized Standing Desk", "EA", 950.0),
        ("Aeron Ergonomic Lumbar Support Chair", "EA", 1150.0),
        ("Acoustic Phone Booth Modular Unit", "EA", 6200.0),
        ("Meeting Room Video Conferencing System 4K", "EA", 3400.0),
        ("HEPA Air Filtration Commercial Tower", "EA", 800.0),
        ("Commercial Smart Keyless Access Door Controller", "EA", 1500.0),
        ("LED Low-Glare Architectural Office Lighting Panel", "BOX", 450.0),
        ("Cafeteria Heavy Duty Commercial Coffee Maker", "EA", 2800.0),
    ],
    ItemCategory.OFFICE_SUPPLIES: [
        ("Recycled Multi-Purpose Copy Paper (Carton 5 Reams)", "BOX", 45.0),
        ("High-Yield Laser Toner Cartridge Multipack", "BOX", 280.0),
        ("Dry-Erase Magnetic Whiteboard 72x48 with Markers", "EA", 220.0),
        ("Security Shredder Cross-Cut Heavy Duty", "EA", 580.0),
        ("Executive Stationery & Meeting Pad Bundle", "BOX", 65.0),
        ("USB-C Braided Cable Multi-Length Pack", "BOX", 85.0),
        ("Ergonomic Anti-Fatigue Desk Floor Mat", "EA", 95.0),
    ],
    ItemCategory.CONSULTING: [
        ("Enterprise Architecture Strategic Advisory", "HOUR", 350.0),
        ("DevOps Migration and Kubernetes Optimization", "HOUR", 275.0),
        ("AI Model Governance & Ethics Framework Advisory", "HOUR", 400.0),
        ("Supply Chain Resiliency Strategy Consulting", "HOUR", 320.0),
        ("Financial Data Pipeline Modernization Consulting", "HOUR", 250.0),
        ("Regulatory GDPR / CPRA Data Privacy Review", "HOUR", 300.0),
    ],
    ItemCategory.LOGISTICS: [
        ("International Express Freight Delivery 500kg", "SHIPMENT", 2400.0),
        ("Temperature-Controlled Secure Transport", "SHIPMENT", 3800.0),
        ("Bonded Warehouse Storage Pallet Space", "MONTH", 650.0),
        ("Dedicated White-Glove On-Site Unpacking & Rack Mount", "SERVICE", 1500.0),
        ("Expedited Regional Courier Fleet Delivery", "SHIPMENT", 450.0),
    ],
}

DELIVERY_DESTINATIONS = [
    "Building A - Central Receiving Dock, 100 Innovation Way, Austin, TX",
    "Building B - IT Infrastructure Lab, 250 Tech Center Dr, San Jose, CA",
    "Building C - Hardware Engineering Hub, 400 Precision Blvd, Seattle, WA",
    "Building D - East Coast Operations Hub, 150 Enterprise Ave, Boston, MA",
    "Building E - Corporate Headquarters, 500 Market St, New York, NY",
    "Building F - Midwest Fulfillment Depot, 75 Logistics Pkwy, Chicago, IL",
]
