#!/usr/bin/env python3
"""
Generate test CSV datasets for UID detection system testing.

This script creates realistic datasets with various UID patterns:
- Simple single-column UIDs (experiment_id, batch_id, customer_id)
- Composite UIDs (sensor_id + timestamp)
- One-to-many relationships (customer_id -> orders)
- Hierarchical UIDs (patient_id -> visit_id)

Usage:
    python generate_test_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


def generate_lab_experiments(output_dir: Path, seed: int = 42) -> None:
    """
    Generate laboratory experiment datasets.
    
    Creates two files:
    - lab_experiments.csv: Main experiment data with measurements
    - experiment_metadata.csv: Project and equipment metadata
    
    UID: experiment_id (format: EXP-XXXX)
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    n = 100
    
    # Main experiment data
    experiments = pd.DataFrame({
        'experiment_id': [f'EXP-{i:04d}' for i in range(1, n + 1)],
        'date': pd.date_range('2024-01-01', periods=n, freq='D').strftime('%Y-%m-%d'),
        'researcher': np.random.choice(
            ['Dr. Smith', 'Dr. Jones', 'Dr. Chen', 'Dr. Patel'], n
        ),
        'temperature_C': np.round(np.random.uniform(20, 30, n), 1),
        'pressure_kPa': np.round(np.random.uniform(95, 105, n), 1),
        'pH': np.round(np.random.uniform(6.5, 7.5, n), 2),
        'yield_percent': np.round(np.random.uniform(75, 98, n), 1),
        'duration_hours': np.round(np.random.uniform(2, 8, n), 1),
    })
    uid_dir = output_dir / 'uid_detection'
    uid_dir.mkdir(exist_ok=True)
    experiments.to_csv(uid_dir / 'lab_experiments.csv', index=False)
    print(f"Created uid_detection/lab_experiments.csv ({len(experiments)} rows)")
    
    # Metadata
    metadata = pd.DataFrame({
        'experiment_id': [f'EXP-{i:04d}' for i in range(1, n + 1)],
        'project_code': np.random.choice(['PROJ-A', 'PROJ-B', 'PROJ-C'], n),
        'equipment_id': np.random.choice(
            ['EQ-001', 'EQ-002', 'EQ-003', 'EQ-004'], n
        ),
        'sample_type': np.random.choice(
            ['Organic', 'Inorganic', 'Polymer', 'Composite'], n
        ),
        'priority': np.random.choice(['High', 'Medium', 'Low'], n),
        'approved': np.random.choice([True, False], n, p=[0.8, 0.2]),
    })
    metadata.to_csv(uid_dir / 'experiment_metadata.csv', index=False)
    print(f"Created uid_detection/experiment_metadata.csv ({len(metadata)} rows)")


def generate_manufacturing_batches(output_dir: Path, seed: int = 43) -> None:
    """
    Generate manufacturing batch datasets.
    
    Creates two files:
    - production_batches.csv: Production run data
    - quality_control.csv: QC inspection results
    
    UIDs: batch_id (format: BATCH-XXXXX), lot_number (format: LOT-2024-XXX)
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    n = 80
    
    # Production batches
    batches = pd.DataFrame({
        'batch_id': [f'BATCH-{i:05d}' for i in range(10001, 10001 + n)],
        'lot_number': [f'LOT-2024-{i:03d}' for i in range(1, n + 1)],
        'product_name': np.random.choice(
            ['Widget-A', 'Widget-B', 'Gadget-X', 'Gadget-Y'], n
        ),
        'quantity_produced': np.random.randint(100, 1000, n),
        'production_date': pd.date_range(
            '2024-01-01', periods=n, freq='D'
        ).strftime('%Y-%m-%d'),
        'shift': np.random.choice(['Morning', 'Afternoon', 'Night'], n),
        'operator_id': np.random.choice(
            ['OP-101', 'OP-102', 'OP-103', 'OP-104', 'OP-105'], n
        ),
    })
    uid_dir = output_dir / 'uid_detection'
    uid_dir.mkdir(exist_ok=True)
    batches.to_csv(uid_dir / 'production_batches.csv', index=False)
    print(f"Created uid_detection/production_batches.csv ({len(batches)} rows)")
    
    # Quality control
    qc = pd.DataFrame({
        'batch_id': [f'BATCH-{i:05d}' for i in range(10001, 10001 + n)],
        'inspection_date': (
            pd.date_range('2024-01-01', periods=n, freq='D') + pd.Timedelta(days=1)
        ).strftime('%Y-%m-%d'),
        'inspector': np.random.choice(['QC-A', 'QC-B', 'QC-C'], n),
        'visual_check': np.random.choice(['Pass', 'Pass', 'Pass', 'Fail'], n),
        'dimension_check': np.random.choice(
            ['Pass', 'Pass', 'Pass', 'Pass', 'Fail'], n
        ),
        'weight_variance_pct': np.round(np.random.uniform(-2, 2, n), 2),
        'overall_status': np.random.choice(
            ['Approved', 'Approved', 'Approved', 'Rejected', 'Hold'], n
        ),
    })
    qc.to_csv(uid_dir / 'quality_control.csv', index=False)
    print(f"Created uid_detection/quality_control.csv ({len(qc)} rows)")


def generate_customer_orders(output_dir: Path, seed: int = 44) -> None:
    """
    Generate customer and order datasets.
    
    Creates two files:
    - orders.csv: Individual orders (many per customer)
    - customers.csv: Customer master data
    
    UIDs: order_id (format: ORD-XXXXXX), customer_id (format: CUST-XXX)
    Relationship: One customer -> many orders
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Customers (50 unique)
    n_customers = 50
    customers = pd.DataFrame({
        'customer_id': [f'CUST-{i:03d}' for i in range(1, n_customers + 1)],
        'customer_name': [f'Customer {i}' for i in range(1, n_customers + 1)],
        'email': [f'customer{i}@example.com' for i in range(1, n_customers + 1)],
        'country': np.random.choice(
            ['USA', 'UK', 'Germany', 'France', 'Japan', 'Australia'], n_customers
        ),
        'segment': np.random.choice(['Enterprise', 'SMB', 'Consumer'], n_customers),
        'signup_date': pd.date_range(
            '2020-01-01', periods=n_customers, freq='7D'
        ).strftime('%Y-%m-%d'),
    })
    one_to_many_dir = output_dir / 'one_to_many'
    one_to_many_dir.mkdir(exist_ok=True)
    customers.to_csv(one_to_many_dir / 'customers.csv', index=False)
    print(f"Created one_to_many/customers.csv ({len(customers)} rows)")
    
    # Orders (150 orders, some customers have multiple)
    n_orders = 150
    orders = pd.DataFrame({
        'order_id': [f'ORD-{i:06d}' for i in range(100001, 100001 + n_orders)],
        'customer_id': [
            f'CUST-{np.random.randint(1, n_customers + 1):03d}' 
            for _ in range(n_orders)
        ],
        'order_date': pd.date_range(
            '2024-01-01', periods=n_orders, freq='4h'
        ).strftime('%Y-%m-%d %H:%M'),
        'total_amount': np.round(np.random.uniform(50, 500, n_orders), 2),
        'status': np.random.choice(
            ['Pending', 'Shipped', 'Delivered', 'Cancelled'], 
            n_orders, 
            p=[0.1, 0.3, 0.5, 0.1]
        ),
        'payment_method': np.random.choice(
            ['Credit Card', 'PayPal', 'Bank Transfer'], n_orders
        ),
    })
    orders.to_csv(one_to_many_dir / 'orders.csv', index=False)
    print(f"Created one_to_many/orders.csv ({len(orders)} rows)")


def generate_sensor_readings(output_dir: Path, seed: int = 45) -> None:
    """
    Generate sensor reading datasets.
    
    Creates two files:
    - sensor_readings.csv: Time-series sensor data
    - sensor_calibration.csv: Sensor calibration metadata
    
    UIDs: 
    - sensor_readings: Composite (sensor_id + timestamp)
    - sensor_calibration: sensor_id
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    sensors = ['SENSOR-A', 'SENSOR-B', 'SENSOR-C', 'SENSOR-D']
    timestamps = pd.date_range('2024-01-01', periods=50, freq='h')
    
    # Sensor readings (4 sensors x 50 timestamps = 200 rows)
    rows = []
    for sensor in sensors:
        for ts in timestamps:
            rows.append({
                'sensor_id': sensor,
                'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                'temperature': round(np.random.uniform(18, 28), 1),
                'humidity': round(np.random.uniform(30, 70), 1),
                'pressure': round(np.random.uniform(1010, 1020), 1),
            })
    
    sensor_readings = pd.DataFrame(rows)
    uid_dir = output_dir / 'uid_detection'
    uid_dir.mkdir(exist_ok=True)
    sensor_readings.to_csv(uid_dir / 'sensor_readings.csv', index=False)
    print(f"Created uid_detection/sensor_readings.csv ({len(sensor_readings)} rows)")
    
    # Calibration data
    calibration = pd.DataFrame({
        'sensor_id': ['SENSOR-A', 'SENSOR-B', 'SENSOR-C', 'SENSOR-D'],
        'calibration_date': ['2024-01-01', '2024-01-02', '2024-01-01', '2024-01-03'],
        'temp_offset': [0.1, -0.2, 0.0, 0.15],
        'humidity_offset': [-1.0, 0.5, 0.0, -0.5],
        'location': ['Lab A', 'Lab A', 'Lab B', 'Lab B'],
        'status': ['Active', 'Active', 'Active', 'Maintenance'],
    })
    calibration.to_csv(uid_dir / 'sensor_calibration.csv', index=False)
    print(f"Created uid_detection/sensor_calibration.csv ({len(calibration)} rows)")


def generate_clinical_trial_data(output_dir: Path, seed: int = 46) -> None:
    """
    Generate clinical trial datasets.
    
    Creates two files:
    - patient_visits.csv: Visit-level clinical measurements
    - patient_demographics.csv: Patient baseline demographics
    
    UIDs:
    - patient_visits: visit_id (unique), patient_id (foreign key)
    - patient_demographics: patient_id
    
    Relationship: One patient -> multiple visits
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    n_patients = 40
    visits_per_patient = 3
    
    # Patient visits (40 patients x 3 visits = 120 rows)
    rows = []
    visit_num = 1
    for p in range(1, n_patients + 1):
        patient_id = f'PT-{p:04d}'
        base_date = pd.Timestamp('2024-01-01') + pd.Timedelta(
            days=int(np.random.randint(0, 30))
        )
        for v in range(visits_per_patient):
            visit_date = base_date + pd.Timedelta(weeks=v * 4)
            rows.append({
                'visit_id': f'V-{visit_num:05d}',
                'patient_id': patient_id,
                'visit_date': str(visit_date.date()),
                'visit_type': ['Baseline', 'Follow-up 1', 'Follow-up 2'][v],
                'blood_pressure_sys': int(np.random.randint(110, 150)),
                'blood_pressure_dia': int(np.random.randint(70, 95)),
                'heart_rate': int(np.random.randint(60, 100)),
                'weight_kg': round(np.random.uniform(55, 95), 1),
            })
            visit_num += 1
    
    patient_visits = pd.DataFrame(rows)
    uid_dir = output_dir / 'uid_detection'
    uid_dir.mkdir(exist_ok=True)
    patient_visits.to_csv(uid_dir / 'patient_visits.csv', index=False)
    print(f"Created uid_detection/patient_visits.csv ({len(patient_visits)} rows)")
    
    # Patient demographics
    demographics = pd.DataFrame({
        'patient_id': [f'PT-{i:04d}' for i in range(1, n_patients + 1)],
        'age': np.random.randint(25, 75, n_patients),
        'sex': np.random.choice(['M', 'F'], n_patients),
        'ethnicity': np.random.choice(
            ['Caucasian', 'African American', 'Asian', 'Hispanic', 'Other'], 
            n_patients
        ),
        'smoking_status': np.random.choice(['Never', 'Former', 'Current'], n_patients),
        'treatment_arm': np.random.choice(
            ['Placebo', 'Treatment A', 'Treatment B'], n_patients
        ),
        'site_id': np.random.choice(['SITE-01', 'SITE-02', 'SITE-03'], n_patients),
    })
    demographics.to_csv(uid_dir / 'patient_demographics.csv', index=False)
    print(f"Created uid_detection/patient_demographics.csv ({len(demographics)} rows)")


def generate_transposed_id_data(output_dir: Path, seed: int = 47) -> None:
    """
    Generate datasets testing transposed/pivoted ID patterns.
    
    Creates two files:
    - products_index.csv: Products with product_id as column VALUES (normal format)
    - inventory_levels.csv: Inventory with product_id as column NAMES (pivoted format)
    
    Tests: ID matching when one file has IDs as column names (wide/pivoted format)
           and the other has IDs as column values (long/normal format).
    
    Example:
        products_index.csv:
            product_id,product_name,category
            PROD-001,Widget Alpha,Electronics
            PROD-002,Widget Beta,Electronics
        
        inventory_levels.csv:
            warehouse,PROD-001,PROD-002,PROD-003,...
            EAST,150,75,200,...
            WEST,100,0,85,...
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Product IDs that will appear in both files
    n_products = 8
    product_ids = [f'PROD-{i:03d}' for i in range(1, n_products + 1)]
    product_names = [
        'Widget Alpha', 'Widget Beta', 'Gadget Pro', 'Gadget Lite',
        'Tool Master', 'Tool Basic', 'Component X', 'Component Y'
    ]
    categories = ['Electronics', 'Electronics', 'Home', 'Home',
                  'Industrial', 'Industrial', 'Electronics', 'Electronics']
    
    # Products with ID as column VALUES (normal row-based format)
    products = pd.DataFrame({
        'product_id': product_ids,
        'product_name': product_names,
        'category': categories,
        'unit_price': [29.99, 34.99, 89.99, 49.99, 149.99, 79.99, 12.99, 18.99],
        'weight_kg': [0.45, 0.52, 1.20, 0.85, 2.30, 1.75, 0.15, 0.22],
    })
    transposed_dir = output_dir / 'transposed_ids'
    transposed_dir.mkdir(exist_ok=True)
    products.to_csv(transposed_dir / 'products_index.csv', index=False)
    print(f"Created transposed_ids/products_index.csv ({len(products)} rows, IDs as column values)")
    
    # Inventory levels with product_id as column NAMES (pivoted/wide format)
    warehouses = ['EAST', 'WEST', 'CENTRAL', 'NORTH', 'SOUTH']
    
    # Generate inventory quantities for each warehouse x product combination
    inventory_data = {'warehouse': warehouses}
    for pid in product_ids:
        # Random quantities, with some zeros to simulate out-of-stock
        quantities = []
        for _ in warehouses:
            if np.random.random() < 0.15:  # 15% chance of zero stock
                quantities.append(0)
            else:
                quantities.append(int(np.random.randint(50, 500)))
        inventory_data[pid] = quantities
    
    inventory = pd.DataFrame(inventory_data)
    inventory.to_csv(transposed_dir / 'inventory_levels.csv', index=False)
    print(f"Created transposed_ids/inventory_levels.csv ({len(inventory)} rows, IDs as column names)")
    print(f"  -> Product IDs appear as column headers: {product_ids}")


def generate_repetitive_id_data(output_dir: Path, seed: int = 48) -> None:
    """
    Generate datasets with highly repetitive IDs (many-to-many potential).
    
    Creates two files:
    - students.csv: Student enrollments (student appears multiple times)
    - course_catalog.csv: Course details (unique course_id)
    
    Tests: Many-to-many relationships, repeated IDs in both join columns
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Define students and courses
    n_students = 8
    student_ids = [f'STU-{i:03d}' for i in range(1, n_students + 1)]
    
    courses = [
        ('COURSE-101', 'Intro to Python', 'CS', 3, 'Dr. Smith'),
        ('COURSE-102', 'Data Structures', 'CS', 4, 'Dr. Jones'),
        ('COURSE-103', 'Statistics', 'MATH', 3, 'Dr. Brown'),
        ('COURSE-104', 'Machine Learning', 'CS', 4, 'Dr. Smith'),
        ('COURSE-105', 'Linear Algebra', 'MATH', 3, 'Dr. Chen'),
        ('COURSE-106', 'Database Systems', 'CS', 4, 'Dr. Patel'),
    ]
    course_ids = [c[0] for c in courses]
    
    # Generate enrollments (each student takes 3-5 courses)
    rows = []
    grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-']
    base_date = pd.Timestamp('2024-01-10')
    
    for student_id in student_ids:
        n_courses = np.random.randint(3, 6)
        enrolled_courses = np.random.choice(course_ids, size=n_courses, replace=False)
        for course_id in enrolled_courses:
            enrollment_date = base_date + pd.Timedelta(
                days=int(np.random.randint(0, 5))
            )
            rows.append({
                'student_id': student_id,
                'course_id': course_id,
                'enrollment_date': enrollment_date.strftime('%Y-%m-%d'),
                'grade': np.random.choice(grades),
                'semester': np.random.choice(['Fall 2024', 'Spring 2024']),
            })
    
    students = pd.DataFrame(rows)
    repetitive_dir = output_dir / 'repetitive_ids'
    repetitive_dir.mkdir(exist_ok=True)
    students.to_csv(repetitive_dir / 'students.csv', index=False)
    print(f"Created repetitive_ids/students.csv ({len(students)} rows, {n_students} unique students)")
    
    # Course catalog (unique course_id)
    course_catalog = pd.DataFrame(
        courses,
        columns=['course_id', 'course_name', 'department', 'credits', 'instructor']
    )
    course_catalog['max_enrollment'] = np.random.randint(25, 50, len(courses))
    course_catalog['room'] = np.random.choice(
        ['Room 101', 'Room 202', 'Room 303', 'Lab A', 'Lab B'], len(courses)
    )
    course_catalog.to_csv(repetitive_dir / 'course_catalog.csv', index=False)
    print(f"Created repetitive_ids/course_catalog.csv ({len(course_catalog)} rows)")


def generate_mixed_format_id_data(output_dir: Path, seed: int = 49) -> None:
    """
    Generate datasets with mixed ID formats (same logical ID, different formats).
    
    Creates two files:
    - legacy_accounts.csv: Old system with numeric IDs (1001, 1002, ...)
    - new_transactions.csv: New system with prefixed IDs (ACC-1001, ACC-1002, ...)
    
    Tests: Transform suggestion for matching numeric vs prefixed IDs
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Legacy accounts with numeric IDs
    n_accounts = 20
    account_nums = list(range(1001, 1001 + n_accounts))
    
    first_names = [
        'Alice', 'Bob', 'Carol', 'David', 'Eve', 'Frank', 'Grace', 'Henry',
        'Ivy', 'Jack', 'Karen', 'Leo', 'Mia', 'Noah', 'Olivia', 'Peter',
        'Quinn', 'Rachel', 'Sam', 'Tina'
    ]
    last_names = [
        'Johnson', 'Smith', 'White', 'Lee', 'Brown', 'Garcia', 'Miller',
        'Davis', 'Wilson', 'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson',
        'Harris', 'Martin', 'Thompson', 'Robinson', 'Clark', 'Lewis'
    ]
    
    legacy_accounts = pd.DataFrame({
        'account_num': account_nums,
        'account_holder': [
            f'{first_names[i]} {last_names[i]}' for i in range(n_accounts)
        ],
        'balance': np.round(np.random.uniform(500, 15000, n_accounts), 2),
        'status': np.random.choice(
            ['active', 'active', 'active', 'inactive', 'suspended'], n_accounts
        ),
        'account_type': np.random.choice(
            ['checking', 'savings', 'money_market'], n_accounts
        ),
        'opened_date': pd.date_range(
            '2020-01-01', periods=n_accounts, freq='15D'
        ).strftime('%Y-%m-%d'),
    })
    mixed_dir = output_dir / 'mixed_formats'
    mixed_dir.mkdir(exist_ok=True)
    legacy_accounts.to_csv(mixed_dir / 'legacy_accounts.csv', index=False)
    print(f"Created mixed_formats/legacy_accounts.csv ({len(legacy_accounts)} rows)")
    
    # New transactions with prefixed account IDs
    n_transactions = 50
    transaction_types = ['deposit', 'withdrawal', 'transfer', 'fee', 'interest']
    
    rows = []
    for i in range(n_transactions):
        account_num = np.random.choice(account_nums)
        txn_type = np.random.choice(transaction_types)
        
        # Amount depends on transaction type
        if txn_type == 'deposit':
            amount = round(np.random.uniform(100, 5000), 2)
        elif txn_type == 'withdrawal':
            amount = -round(np.random.uniform(50, 1000), 2)
        elif txn_type == 'transfer':
            amount = round(np.random.uniform(-2000, 2000), 2)
        elif txn_type == 'fee':
            amount = -round(np.random.uniform(5, 50), 2)
        else:  # interest
            amount = round(np.random.uniform(1, 100), 2)
        
        rows.append({
            'transaction_id': f'TXN-{i + 1:04d}',
            'account_id': f'ACC-{account_num}',  # Prefixed format
            'amount': amount,
            'transaction_date': (
                pd.Timestamp('2024-01-15') + 
                pd.Timedelta(days=int(np.random.randint(0, 30)))
            ).strftime('%Y-%m-%d'),
            'type': txn_type,
            'description': f'{txn_type.capitalize()} transaction',
        })
    
    new_transactions = pd.DataFrame(rows)
    new_transactions.to_csv(mixed_dir / 'new_transactions.csv', index=False)
    print(f"Created mixed_formats/new_transactions.csv ({len(new_transactions)} rows)")


def generate_sparse_messy_data(output_dir: Path, seed: int = 51) -> None:
    """
    Generate sparse/messy datasets with IDs buried in non-standard locations.
    
    Creates two files simulating uncleaned Excel exports:
    - sample_log.csv: Lab sample log with IDs buried in middle column
    - sample_metadata.csv: Sample metadata with IDs as column headers (not in col A)
    
    Tests: ID detection in messy data where:
    - IDs are NOT in the first row/column
    - Tables have lots of empty cells/rows/columns
    - One file has IDs in row values (buried in middle columns)
    - One file has IDs in column headers (buried among empty columns)
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Sample IDs that will appear in both files
    n_samples = 8
    sample_ids = [f'SAMP-{i:03d}' for i in range(1, n_samples + 1)]
    
    # Test types and technicians for the log
    test_types = ['pH', 'Conductivity', 'Turbidity']
    technicians = ['J. Smith', 'A. Jones', 'M. Chen']
    
    # Create sparse_messy directory
    sparse_messy_dir = output_dir / 'sparse_messy'
    sparse_messy_dir.mkdir(exist_ok=True)
    
    # =========================================================================
    # File 1: sample_log.csv - IDs buried in middle column, lots of empty cells
    # Row numbers in first column to avoid "Unnamed: 0" conflicts with metadata
    # =========================================================================
    log_rows = []
    row_num = 1
    
    # Header metadata rows (sparse) - first column has "Row" label then row numbers
    log_rows.append(['Row', '', '', 'Notes', '', '', '', ''])
    log_rows.append([row_num, 'Report Date', '2024-01-15', '', '', '', '', ''])
    row_num += 1
    log_rows.append([row_num, 'Generated By', 'Lab System v2.1', '', '', '', '', ''])
    row_num += 1
    log_rows.append([row_num, '', '', '', '', '', '', ''])
    row_num += 1
    log_rows.append([row_num, '', '', '', '', '', '', ''])
    row_num += 1
    
    # Column headers (not in row 0!) - 8 columns total
    log_rows.append([row_num, 'Lab', 'Sample ID', 'Test Type', 'Result', 'Units', 'Technician', 'Comments'])
    row_num += 1
    
    # Data rows with IDs in column 2 (not column 0 or 1)
    comments_options = ['', '', '', 'within spec', 'slight deviation', 'high reading', 
                        'low reading', 'elevated', 'retest needed']
    
    for sample_id in sample_ids:
        # Each sample has 2-3 test results
        n_tests = np.random.randint(2, 4)
        selected_tests = np.random.choice(test_types, size=n_tests, replace=False)
        
        for test_type in selected_tests:
            # Generate realistic test results
            if test_type == 'pH':
                result = round(np.random.uniform(6.5, 7.5), 1)
                units = 'pH'
            elif test_type == 'Conductivity':
                result = int(np.random.randint(400, 550))
                units = 'µS/cm'
            else:  # Turbidity
                result = round(np.random.uniform(1.5, 3.0), 1)
                units = 'NTU'
            
            # Sparse technician assignment (some empty)
            tech = np.random.choice(technicians) if np.random.random() > 0.3 else ''
            comment = np.random.choice(comments_options)
            
            # First column has row number, second (Lab) is empty - IDs are in column 2
            log_rows.append([row_num, '', sample_id, test_type, result, units, tech, comment])
            row_num += 1
        
        # Add occasional empty row between samples
        if np.random.random() > 0.7:
            log_rows.append([row_num, '', '', '', '', '', '', ''])
            row_num += 1
    
    # Footer rows
    log_rows.append([row_num, '', '', '', '', '', '', ''])
    row_num += 1
    log_rows.append([row_num, '', '', '', 'End of Report', '', '', ''])
    row_num += 1
    log_rows.append([row_num, '', '', '', 'Approved: Dr. Wilson', '', '', ''])
    
    # Write sample_log.csv
    log_df = pd.DataFrame(log_rows)
    log_df.to_csv(sparse_messy_dir / 'sample_log.csv', index=False, header=False)
    print(f"Created sparse_messy/sample_log.csv ({len(log_rows)} rows, IDs in column 2)")
    
    # =========================================================================
    # File 2: sample_metadata.csv - IDs as column headers, sparse layout
    # First column has "Info" label to avoid "Unnamed: 0" conflicts with log file
    # =========================================================================
    
    # Build column structure: Info, empty, SAMP-001, SAMP-002, ..., empty, empty
    columns = ['Info', ''] + sample_ids + ['', '']
    n_cols = len(columns)
    
    meta_rows = []
    
    # Header row with sample IDs as column names (offset by 2 columns: Info, empty)
    meta_rows.append(columns)
    
    # Property/Units header row
    row = ['Property', 'Units'] + [''] * n_samples + ['', 'Notes']
    meta_rows.append(row)
    
    # Empty row
    meta_rows.append([''] * n_cols)
    
    # Generate metadata for each sample
    base_date = pd.Timestamp('2024-01-10')
    locations = ['Site A', 'Site B', 'Site C']
    weather_options = ['Clear', 'Cloudy', 'Rain', 'Overcast']
    collectors = ['Dr. Wilson', 'Dr. Chen', 'Dr. Patel']
    container_types = ['Glass', 'Plastic']
    
    # Collection Date row
    row = ['Collection Date', '']
    for i in range(n_samples):
        date = base_date + pd.Timedelta(days=i // 2)
        row.append(date.strftime('%Y-%m-%d'))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Location row
    row = ['Location', '']
    for _ in range(n_samples):
        row.append(np.random.choice(locations))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Depth row
    row = ['Depth', 'meters']
    for _ in range(n_samples):
        row.append(round(np.random.uniform(1.0, 3.0), 1))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Temperature row
    row = ['Temperature', '°C']
    for _ in range(n_samples):
        row.append(round(np.random.uniform(14.0, 16.0), 1))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Empty rows
    meta_rows.append([''] * n_cols)
    meta_rows.append([''] * n_cols)
    
    # Weather Conditions row
    row = ['Weather Conditions', '']
    for _ in range(n_samples):
        row.append(np.random.choice(weather_options))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Collector row
    row = ['Collector', '']
    for _ in range(n_samples):
        row.append(np.random.choice(collectors))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Empty row
    meta_rows.append([''] * n_cols)
    
    # Sample Volume row
    row = ['Sample Volume', 'mL']
    for _ in range(n_samples):
        row.append(np.random.choice([250, 500]))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Container Type row
    row = ['Container Type', '']
    for _ in range(n_samples):
        row.append(np.random.choice(container_types))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Empty rows
    meta_rows.append([''] * n_cols)
    meta_rows.append([''] * n_cols)
    
    # Approved By row
    row = ['Approved By', '']
    for _ in range(n_samples):
        row.append(np.random.choice(collectors))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Approval Date row
    row = ['Approval Date', '']
    approval_base = pd.Timestamp('2024-01-16')
    for i in range(n_samples):
        date = approval_base + pd.Timedelta(days=i // 3)
        row.append(date.strftime('%Y-%m-%d'))
    row.extend(['', ''])
    meta_rows.append(row)
    
    # Write sample_metadata.csv
    meta_df = pd.DataFrame(meta_rows)
    meta_df.to_csv(sparse_messy_dir / 'sample_metadata.csv', index=False, header=False)
    print(f"Created sparse_messy/sample_metadata.csv ({len(meta_rows)} rows, IDs as column headers)")
    print(f"  -> Sample IDs: {sample_ids}")


def generate_sparse_overlap_data(output_dir: Path, seed: int = 50) -> None:
    """
    Generate datasets with sparse/partial ID overlap.
    
    Creates two files:
    - region_sales.csv: Sales by region (some regions)
    - region_targets.csv: Targets by region (different set, partial overlap)
    
    Tests: Handling of partial ID overlap (~50% match)
    
    Args:
        output_dir: Directory to save CSV files
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Define regions with partial overlap
    sales_regions = ['REG-NORTH', 'REG-SOUTH', 'REG-EAST', 'REG-MIDWEST']
    target_regions = ['REG-NORTH', 'REG-SOUTH', 'REG-WEST', 'REG-CENTRAL', 'REG-PACIFIC']
    # Overlap: REG-NORTH, REG-SOUTH (2 out of 4 sales regions = 50%)
    
    quarters = ['Q1-2024', 'Q2-2024', 'Q3-2024', 'Q4-2024']
    
    # Region sales (multiple quarters per region)
    rows = []
    for region in sales_regions:
        for quarter in quarters:
            base_sales = np.random.uniform(100000, 300000)
            rows.append({
                'region_code': region,
                'quarter': quarter,
                'sales_amount': round(base_sales, 2),
                'units_sold': int(base_sales / np.random.uniform(80, 120)),
                'returns': int(np.random.randint(10, 100)),
                'avg_order_value': round(np.random.uniform(50, 150), 2),
            })
    
    region_sales = pd.DataFrame(rows)
    sparse_dir = output_dir / 'sparse_overlap'
    sparse_dir.mkdir(exist_ok=True)
    region_sales.to_csv(sparse_dir / 'region_sales.csv', index=False)
    print(f"Created sparse_overlap/region_sales.csv ({len(region_sales)} rows)")
    
    # Region targets (annual targets, different region set)
    region_targets = pd.DataFrame({
        'region_code': target_regions,
        'year': [2024] * len(target_regions),
        'target_amount': np.round(np.random.uniform(500000, 1200000, len(target_regions)), 2),
        'target_units': np.random.randint(4000, 10000, len(target_regions)),
        'growth_target_pct': np.round(np.random.uniform(5, 20, len(target_regions)), 1),
        'priority': np.random.choice(['High', 'Medium', 'Low'], len(target_regions)),
    })
    region_targets.to_csv(sparse_dir / 'region_targets.csv', index=False)
    print(f"Created sparse_overlap/region_targets.csv ({len(region_targets)} rows)")
    
    # Print overlap info
    overlap = set(sales_regions) & set(target_regions)
    print(f"  -> Overlap: {len(overlap)}/{len(sales_regions)} regions ({overlap})")


def main() -> None:
    """Generate all test datasets."""
    output_dir = Path(__file__).parent
    
    print("Generating test datasets for UID detection...\n")
    print(f"Output directory: {output_dir}\n")
    
    print("=" * 50)
    print("1. Laboratory Experiments (UID: experiment_id)")
    print("=" * 50)
    generate_lab_experiments(output_dir)
    print()
    
    print("=" * 50)
    print("2. Manufacturing Batches (UID: batch_id, lot_number)")
    print("=" * 50)
    generate_manufacturing_batches(output_dir)
    print()
    
    print("=" * 50)
    print("3. Customer Orders (UID: order_id, customer_id)")
    print("=" * 50)
    generate_customer_orders(output_dir)
    print()
    
    print("=" * 50)
    print("4. Sensor Readings (Composite UID: sensor_id + timestamp)")
    print("=" * 50)
    generate_sensor_readings(output_dir)
    print()
    
    print("=" * 50)
    print("5. Clinical Trial Data (UID: patient_id, visit_id)")
    print("=" * 50)
    generate_clinical_trial_data(output_dir)
    print()
    
    print("=" * 50)
    print("6. Transposed IDs (ID in index vs column)")
    print("=" * 50)
    generate_transposed_id_data(output_dir)
    print()
    
    print("=" * 50)
    print("7. Repetitive IDs (many-to-many relationships)")
    print("=" * 50)
    generate_repetitive_id_data(output_dir)
    print()
    
    print("=" * 50)
    print("8. Mixed Format IDs (numeric vs prefixed)")
    print("=" * 50)
    generate_mixed_format_id_data(output_dir)
    print()
    
    print("=" * 50)
    print("9. Sparse Overlap (partial ID match)")
    print("=" * 50)
    generate_sparse_overlap_data(output_dir)
    print()
    
    print("=" * 50)
    print("10. Sparse/Messy Data (IDs buried in non-standard locations)")
    print("=" * 50)
    generate_sparse_messy_data(output_dir)
    print()
    
    print("=" * 50)
    print("All datasets generated successfully!")
    print("=" * 50)


if __name__ == '__main__':
    main()
