import sqlite3
import random
import datetime
from faker import Faker

DB = "support.db"
fake = Faker()


def get_connection():
    return sqlite3.connect(DB)


def seed_database():

    conn = get_connection()
    c = conn.cursor()

    print("🌱 Seeding database...")

    # ----------------------------
    # 1️⃣ Add More Agents
    # ----------------------------
    agents = []
    for i in range(3, 11):
        agent_id = f"A{i:02}"
        agents.append((
            agent_id,
            "password123",
            fake.name(),
            "support"
        ))

    c.executemany("""
        INSERT OR IGNORE INTO agents (agent_id, password, full_name, role)
        VALUES (?, ?, ?, ?)
    """, agents)

    print("✅ Agents inserted")

    # Fetch all agents
    c.execute("SELECT agent_id FROM agents")
    agent_ids = [row[0] for row in c.fetchall()]

    # ----------------------------
    # 2️⃣ Insert Issues
    # ----------------------------
    issues = []
    priorities = ["Low", "Medium", "High"]
    statuses = ["Open", "In Progress", "Resolved"]
    categories = ["Network", "Billing", "SIM", "Data", "VAS"]
    escalation_types = ["Normal", "Urgent", "VIP"]

    for _ in range(200):
        created_at = fake.date_time_this_year()
        sla_due = created_at + datetime.timedelta(hours=24)

        status = random.choice(statuses)
        closed_at = created_at + datetime.timedelta(hours=random.randint(1, 48)) if status == "Resolved" else None

        issues.append((
            fake.msisdn()[:10],
            fake.sentence(),
            random.choice(escalation_types),
            status,
            created_at,
            random.choice(agent_ids),
            fake.sentence() if status == "Resolved" else None,
            closed_at,
            random.choice(priorities),
            random.choice(categories),
            sla_due,
            "Breached" if closed_at and closed_at > sla_due else "Within SLA"
        ))

    c.executemany("""
        INSERT INTO issues (
            phone, issue, escalation_type, status,
            created_at, agent_id, resolution_notes,
            closed_at, priority, category,
            sla_due, sla_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, issues)

    print("✅ Issues inserted")

    # ----------------------------
    # 3️⃣ Insert Tasks
    # ----------------------------
    tasks = []

    for _ in range(100):
        due_date = datetime.datetime.utcnow() + datetime.timedelta(days=random.randint(1, 5))

        tasks.append((
            random.choice(agent_ids),
            "Follow up customer",
            fake.text(max_nb_chars=100),
            random.choice(["Pending", "In Progress", "Completed"]),
            due_date
        ))

    c.executemany("""
        INSERT INTO tasks (
            agent_id, title, description,
            status, due_date
        )
        VALUES (?, ?, ?, ?, ?)
    """, tasks)

    print("✅ Tasks inserted")

    # ----------------------------
    # 4️⃣ Insert KPI Snapshots
    # ----------------------------
    kpis = []

    for _ in range(30):
        total = random.randint(50, 300)
        resolved = random.randint(20, total)
        pending = total - resolved

        kpis.append((
            datetime.datetime.utcnow(),
            total,
            resolved,
            pending,
            random.randint(30, 200),
            round(random.uniform(10, 40), 2),  # avg SLA hours
            round(random.uniform(0.05, 0.25), 2)  # churn rate
        ))

    c.executemany("""
        INSERT INTO kpi_snapshots (
            snapshot_date, total, resolved,
            pending, calls, avg_sla, churn_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, kpis)

    print("✅ KPI snapshots inserted")

    conn.commit()
    conn.close()

    print("🎉 Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()