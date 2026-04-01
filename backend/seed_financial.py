import asyncio
import sys
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
import uuid
import os
from dotenv import load_dotenv
from pathlib import Path

# Load env
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'legal_system')]

async def seed_financial_data():
    print("🌱 Seeding financial data...")
    
    # Get admin user
    admin = await db.users.find_one({"role": "admin"})
    if not admin:
        print("❌ Admin user not found")
        return
    
    admin_id = admin["id"]
    
    # Create some invoices
    invoices = []
    for i in range(12):
        month_ago = i
        issue_date = (datetime.now(timezone.utc) - timedelta(days=month_ago*30)).strftime('%Y-%m-%d')
        due_date = (datetime.now(timezone.utc) - timedelta(days=(month_ago*30 - 15))).strftime('%Y-%m-%d')
        
        # Randomize some data
        amounts = [5000, 7500, 10000, 12000, 8000, 15000]
        statuses = ["paid", "paid", "paid", "paid", "sent", "partial"]
        
        invoice_id = str(uuid.uuid4())
        invoice = {
            "id": invoice_id,
            "invoice_number": f"INV-2026{i+1:02d}-{str(uuid.uuid4())[:8].upper()}",
            "client_id": admin_id,
            "client_name": f"Cliente Exemplo {i+1}",
            "issue_date": issue_date,
            "due_date": due_date,
            "line_items": [
                {
                    "description": "Consultoria Jurídica",
                    "quantity": 10,
                    "unit_price": amounts[i % len(amounts)] / 10,
                    "amount": amounts[i % len(amounts)]
                }
            ],
            "subtotal": amounts[i % len(amounts)],
            "taxes": [{"name": "ISS", "rate": 5.0, "amount": amounts[i % len(amounts)] * 0.05}],
            "discount": 0,
            "total": amounts[i % len(amounts)] * 1.05,
            "status": statuses[i % len(statuses)],
            "paid_amount": amounts[i % len(amounts)] * 1.05 if statuses[i % len(statuses)] == "paid" else 0,
            "balance": 0 if statuses[i % len(statuses)] == "paid" else amounts[i % len(amounts)] * 1.05,
            "fiscal_notes": {"nfe_number": None, "nfse_number": None, "issued": False},
            "created_at": datetime.now(timezone.utc),
            "created_by": admin_id
        }
        invoices.append(invoice)
    
    # Insert invoices
    if invoices:
        await db.invoices.delete_many({})  # Clear existing
        await db.invoices.insert_many(invoices)
        print(f"✅ Created {len(invoices)} invoices")
    
    # Create expenses
    expenses = []
    expense_categories = [
        ("Aluguel Escritório", 3500),
        ("Salários", 15000),
        ("Marketing", 2000),
        ("Infraestrutura TI", 1500),
        ("Taxas OAB", 800),
        ("Material de Escritório", 600)
    ]
    
    for i in range(6):
        for cat, amount in expense_categories:
            expense_id = str(uuid.uuid4())
            expense_date = (datetime.now(timezone.utc) - timedelta(days=i*30)).strftime('%Y-%m-%d')
            
            expense = {
                "id": expense_id,
                "date": expense_date,
                "category": cat,
                "description": f"{cat} - Mês {i+1}",
                "amount": amount,
                "allocation_type": "firm",
                "reference_id": None,
                "billable": False,
                "tax_deductible": True,
                "receipt_file_id": None,
                "status": "approved",
                "approved_by": admin_id,
                "approved_date": datetime.now(timezone.utc),
                "created_by": admin_id,
                "created_at": datetime.now(timezone.utc)
            }
            expenses.append(expense)
    
    if expenses:
        await db.expenses.delete_many({})  # Clear existing
        await db.expenses.insert_many(expenses)
        print(f"✅ Created {len(expenses)} expenses")
    
    # Create a trust account
    trust_account_id = str(uuid.uuid4())
    trust_account = {
        "id": trust_account_id,
        "client_id": admin_id,
        "client_name": "Cliente VIP",
        "account_number": "12345-6",
        "bank_name": "Banco do Brasil",
        "balance": {
            "available": 50000,
            "reserved": 25000,
            "interest": 1250
        },
        "reconciliation": {
            "last_date": (datetime.now(timezone.utc) - timedelta(days=15)).strftime('%Y-%m-%d'),
            "status": "matched",
            "next_due": (datetime.now(timezone.utc) + timedelta(days=15)).strftime('%Y-%m-%d')
        },
        "created_at": datetime.now(timezone.utc),
        "created_by": admin_id
    }
    
    await db.trust_accounts.delete_many({})  # Clear existing
    await db.trust_accounts.insert_one(trust_account)
    print(f"✅ Created trust account")
    
    # Create time entries
    time_entries = []
    for i in range(20):
        entry_id = str(uuid.uuid4())
        entry_date = (datetime.now(timezone.utc) - timedelta(days=i*2)).strftime('%Y-%m-%d')
        
        duration = [60, 90, 120, 180][i % 4]  # minutes
        hourly_rate = 300
        
        entry = {
            "id": entry_id,
            "client_id": admin_id,
            "process_id": None,
            "date": entry_date,
            "duration": duration,
            "description": f"Consultoria jurídica - Caso {i+1}",
            "billable": True,
            "hourly_rate": hourly_rate,
            "lawyer_id": admin_id,
            "amount": (duration / 60) * hourly_rate,
            "status": ["draft", "approved", "invoiced"][i % 3],
            "created_at": datetime.now(timezone.utc)
        }
        time_entries.append(entry)
    
    if time_entries:
        await db.time_entries.delete_many({})  # Clear existing
        await db.time_entries.insert_many(time_entries)
        print(f"✅ Created {len(time_entries)} time entries")
    
    print("\n✅ Financial data seeding complete!")
    print(f"   - {len(invoices)} invoices")
    print(f"   - {len(expenses)} expenses")
    print(f"   - 1 trust account")
    print(f"   - {len(time_entries)} time entries")

if __name__ == "__main__":
    asyncio.run(seed_financial_data())
