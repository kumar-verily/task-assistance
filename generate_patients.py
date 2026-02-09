#!/usr/bin/env python3
"""
Generate synthetic patients for Clinical ToDo Viewer
Creates realistic patient data with various clinical scenarios
"""

import json
import random
from datetime import datetime, timedelta

def random_date(start_date, end_date):
    """Generate a random date between start_date and end_date"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return start_date + timedelta(days=random_days)

def generate_patient(patient_id):
    """Generate a single synthetic patient"""

    first_names = ["James", "Maria", "Robert", "Jennifer", "Michael", "Lisa", "William", "Nancy",
                   "David", "Karen", "Richard", "Betty", "Joseph", "Helen", "Thomas", "Sandra",
                   "Charles", "Donna", "Christopher", "Carol", "Daniel", "Ruth", "Matthew", "Sharon"]

    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                  "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson"]

    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    age = random.randint(35, 75)
    gender = random.choice(["Male", "Female"])

    # Calculate DOB from age
    today = datetime.now()
    dob = today - timedelta(days=age*365)
    dob_str = dob.strftime("%Y-%m-%d")

    email = f"{name.lower().replace(' ', '.')}@email.com"
    phone = f"(555) {random.randint(200,999)}-{random.randint(1000,9999)}"

    # Random clinical scenario
    scenario = random.choice([
        "t2d_hyperglycemia",
        "t2d_controlled",
        "t1d_hypoglycemia",
        "hypertension_uncontrolled",
        "new_member",
        "mental_health_concern",
        "multiple_conditions"
    ])

    patient = {
        "demographics": {
            "name": name,
            "age": age,
            "gender": gender,
            "dob": dob_str,
            "phone": phone,
            "email": email
        }
    }

    # Build patient based on scenario
    if scenario == "t2d_hyperglycemia":
        patient["conditions"] = {
            "primary_diagnosis": "Type 2 Diabetes",
            "secondary_conditions": ["Hypertension"],
            "icd10_codes": ["E11.9", "I10"]
        }
        patient["devices"] = {
            "bgm": {
                "brand": random.choice(["OneTouch", "Contour", "Accu-Chek"]),
                "model": random.choice(["Ultra Mini", "Next One", "Guide"])
            },
            "bp_monitor": {
                "brand": random.choice(["Omron", "Withings"]),
                "model": random.choice(["BP7350", "BPM Connect"])
            }
        }
        bg_high = random.randint(280, 450)
        patient["recent_events"] = {
            "hyperglycemic_events": [
                {
                    "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
                    "time": f"{random.randint(6,8)}:{random.randint(10,50)} PM",
                    "bg_value": bg_high,
                    "context": random.choice([
                        "Post-dinner spike",
                        "After high-carb meal",
                        "Forgot medication"
                    ])
                }
            ],
            "avg_glucose_7day": random.randint(180, 240),
            "time_in_range": f"{random.randint(15, 40)}%"
        }
        patient["medications"] = [
            {"name": "Metformin", "dose": "1000mg", "frequency": "twice daily"},
            {"name": random.choice(["Jardiance", "Ozempic", "Trulicity"]),
             "dose": random.choice(["10mg", "0.5mg", "1.5mg"]),
             "frequency": "once daily"}
        ]
        patient["labs"] = {
            "a1c": [
                {"value": round(random.uniform(8.5, 10.5), 1),
                 "date": (today - timedelta(days=random.randint(10, 40))).strftime("%Y-%m-%d")}
            ]
        }

    elif scenario == "t1d_hypoglycemia":
        patient["conditions"] = {
            "primary_diagnosis": "Type 1 Diabetes",
            "secondary_conditions": random.choice([
                ["Hypoglycemia unawareness"],
                ["Celiac disease"],
                []
            ]),
            "icd10_codes": ["E10.9"]
        }
        patient["devices"] = {
            "cgm": {
                "brand": random.choice(["Dexcom", "FreeStyle"]),
                "model": random.choice(["G7", "Libre 3"]),
                "sensor_number": f"SN-2024-{random.randint(1000,9999)}"
            },
            "insulin_pump": {
                "brand": random.choice(["Tandem", "Medtronic", "Omnipod"]),
                "model": random.choice(["t:slim X2", "770G", "DASH"])
            }
        }
        patient["recent_events"] = {
            "hypoglycemic_events": [
                {
                    "date": (today - timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d"),
                    "time": f"{random.randint(1,5)}:{random.randint(10,50)} AM",
                    "bg_value": random.randint(40, 65),
                    "context": random.choice([
                        "Overnight, no warning symptoms",
                        "After exercise",
                        "Overcorrection from meal bolus"
                    ]),
                    "treatment": f"{random.choice([8, 15, 16])}g glucose tabs"
                }
            ],
            "avg_glucose_7day": random.randint(120, 160),
            "time_in_range": f"{random.randint(55, 75)}%"
        }
        patient["medications"] = [
            {"name": "Insulin via pump", "dose": f"Basal {random.randint(20,35)}u/day",
             "type": "Automated basal-IQ"},
            {"name": "Glucagon", "dose": "1mg", "frequency": "as needed"}
        ]
        patient["labs"] = {
            "a1c": [
                {"value": round(random.uniform(6.5, 7.5), 1),
                 "date": (today - timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d")}
            ]
        }

    elif scenario == "hypertension_uncontrolled":
        patient["conditions"] = {
            "primary_diagnosis": random.choice(["Type 2 Diabetes", "Prediabetes"]),
            "secondary_conditions": ["Hypertension", random.choice(["Hyperlipidemia", "Obesity"])],
            "icd10_codes": ["E11.9", "I10", "E78.5"]
        }
        patient["devices"] = {
            "bp_monitor": {
                "brand": random.choice(["Omron", "Withings", "iHealth"]),
                "model": random.choice(["BP7350", "BPM Connect", "Track"])
            }
        }
        systolic = random.randint(155, 190)
        diastolic = random.randint(95, 115)
        patient["recent_events"] = {
            "hypertensive_events": [
                {
                    "date": (today - timedelta(days=random.randint(0, 2))).strftime("%Y-%m-%d"),
                    "time": f"{random.randint(7,9)}:{random.randint(10,50)} AM",
                    "bp_value": f"{systolic}/{diastolic}",
                    "context": random.choice([
                        "Morning reading, after medication",
                        "Evening, stressed from work",
                        "After salty meal"
                    ])
                }
            ],
            "avg_bp_7day": f"{systolic-10}/{diastolic-5}"
        }
        patient["medications"] = [
            {"name": random.choice(["Lisinopril", "Losartan", "Amlodipine"]),
             "dose": random.choice(["10mg", "50mg", "5mg"]),
             "frequency": "once daily"},
            {"name": "Metformin", "dose": "500mg", "frequency": "twice daily"}
        ]
        patient["labs"] = {
            "a1c": [
                {"value": round(random.uniform(6.8, 8.5), 1),
                 "date": (today - timedelta(days=random.randint(20, 60))).strftime("%Y-%m-%d")}
            ]
        }

    elif scenario == "new_member":
        patient["conditions"] = {
            "primary_diagnosis": random.choice(["Type 2 Diabetes", "Prediabetes"]),
            "secondary_conditions": [],
            "icd10_codes": ["E11.9"]
        }
        patient["devices"] = {}
        patient["recent_events"] = {
            "enrollment_date": (today - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d"),
            "status": "Pending initial setup"
        }
        patient["medications"] = [
            {"name": "Metformin", "dose": "500mg", "frequency": "once daily"}
        ]
        patient["labs"] = {
            "a1c": [
                {"value": round(random.uniform(7.0, 8.5), 1),
                 "date": (today - timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d")}
            ]
        }

    elif scenario == "mental_health_concern":
        patient["conditions"] = {
            "primary_diagnosis": "Type 2 Diabetes",
            "secondary_conditions": ["Depression", "Anxiety"],
            "icd10_codes": ["E11.9", "F33.1", "F41.1"]
        }
        patient["devices"] = {
            "bgm": {
                "brand": random.choice(["OneTouch", "Contour"]),
                "model": random.choice(["Ultra", "Next One"])
            }
        }
        patient["recent_events"] = {
            "avg_glucose_7day": random.randint(150, 200),
            "medication_adherence": "Poor - frequent missed doses"
        }
        patient["medications"] = [
            {"name": "Metformin", "dose": "1000mg", "frequency": "twice daily"},
            {"name": random.choice(["Sertraline", "Escitalopram"]),
             "dose": random.choice(["50mg", "10mg"]),
             "frequency": "once daily"}
        ]
        patient["surveys"] = {
            "phq9": {
                "score": random.randint(10, 18),
                "date": (today - timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
            },
            "ddas": {
                "score": round(random.uniform(3.0, 4.5), 1),
                "date": (today - timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
            }
        }
        patient["labs"] = {
            "a1c": [
                {"value": round(random.uniform(8.0, 9.5), 1),
                 "date": (today - timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d")}
            ]
        }

    else:  # multiple_conditions
        patient["conditions"] = {
            "primary_diagnosis": "Type 2 Diabetes",
            "secondary_conditions": ["Hypertension", "Hyperlipidemia", "Stage 3 CKD"],
            "icd10_codes": ["E11.9", "I10", "E78.5", "N18.3"]
        }
        patient["devices"] = {
            "bgm": {
                "brand": random.choice(["OneTouch", "Contour"]),
                "model": random.choice(["Ultra Mini", "Next One"])
            },
            "bp_monitor": {
                "brand": "Omron",
                "model": "BP7350"
            }
        }
        patient["recent_events"] = {
            "avg_glucose_7day": random.randint(160, 200),
            "avg_bp_7day": f"{random.randint(140, 165)}/{random.randint(85, 95)}",
            "time_in_range": f"{random.randint(40, 60)}%"
        }
        patient["medications"] = [
            {"name": "Jardiance", "dose": "25mg", "frequency": "once daily"},
            {"name": "Lisinopril", "dose": "20mg", "frequency": "once daily"},
            {"name": "Atorvastatin", "dose": "40mg", "frequency": "once daily"},
            {"name": "Metformin", "dose": "1000mg", "frequency": "twice daily"}
        ]
        patient["labs"] = {
            "a1c": [
                {"value": round(random.uniform(7.2, 8.8), 1),
                 "date": (today - timedelta(days=random.randint(20, 60))).strftime("%Y-%m-%d")}
            ],
            "kidney": {
                "egfr": random.randint(35, 55),
                "creatinine": round(random.uniform(1.2, 1.8), 1)
            },
            "lipids": {
                "hdl": random.randint(35, 50),
                "ldl": random.randint(100, 150),
                "triglycerides": random.randint(150, 250)
            }
        }

    # Add some messages (20% of patients)
    if random.random() < 0.2:
        patient["messages"] = [
            {
                "date": (today - timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d"),
                "from": "patient",
                "content": random.choice([
                    "I've been experiencing headaches lately.",
                    "My readings have been all over the place this week.",
                    "I missed a few doses because I ran out of medication.",
                    "Feeling much better after our last conversation, thank you!",
                    "Had some questions about the new device."
                ])
            }
        ]

    # Add metadata
    patient["metadata"] = {
        "last_modified": datetime.now().isoformat()
    }

    return patient

def main():
    """Generate multiple patients and save to file"""

    # Load existing patients
    try:
        with open('synthetic_patients.json', 'r') as f:
            patients = json.load(f)
        print(f"Loaded {len(patients)} existing patients")
    except FileNotFoundError:
        patients = []
        print("No existing patients found, creating new file")

    # Ask how many to generate
    try:
        num_new = int(input(f"\nHow many new patients to generate? (currently have {len(patients)}): "))
    except ValueError:
        print("Invalid number, generating 5 patients by default")
        num_new = 5

    # Generate new patients
    print(f"\nGenerating {num_new} new patients...")
    for i in range(num_new):
        patient = generate_patient(len(patients) + i)
        patients.append(patient)
        print(f"  {i+1}. {patient['demographics']['name']} - {patient['conditions']['primary_diagnosis']}")

    # Save to file
    with open('synthetic_patients.json', 'w') as f:
        json.dump(patients, f, indent=2)

    print(f"\n✓ Successfully saved {len(patients)} total patients to synthetic_patients.json")
    print(f"  ({num_new} new patients added)")

    # Show summary
    print("\nPatient Summary:")
    conditions_count = {}
    for p in patients:
        dx = p['conditions']['primary_diagnosis']
        conditions_count[dx] = conditions_count.get(dx, 0) + 1

    for condition, count in sorted(conditions_count.items()):
        print(f"  • {condition}: {count} patients")

if __name__ == '__main__':
    main()
