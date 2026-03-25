-- TPC-H simplified seed for ODGG demo/testing
-- Subset of TPC-H schema with sample data

CREATE TABLE nation (
    n_nationkey INTEGER PRIMARY KEY,
    n_name VARCHAR(25) NOT NULL,
    n_regionkey INTEGER NOT NULL,
    n_comment VARCHAR(152)
);

CREATE TABLE region (
    r_regionkey INTEGER PRIMARY KEY,
    r_name VARCHAR(25) NOT NULL,
    r_comment VARCHAR(152)
);

CREATE TABLE supplier (
    s_suppkey INTEGER PRIMARY KEY,
    s_name VARCHAR(25) NOT NULL,
    s_address VARCHAR(40) NOT NULL,
    s_nationkey INTEGER NOT NULL REFERENCES nation(n_nationkey),
    s_phone VARCHAR(15) NOT NULL,
    s_acctbal NUMERIC(15,2) NOT NULL,
    s_comment VARCHAR(101)
);

CREATE TABLE part (
    p_partkey INTEGER PRIMARY KEY,
    p_name VARCHAR(55) NOT NULL,
    p_mfgr VARCHAR(25) NOT NULL,
    p_brand VARCHAR(10) NOT NULL,
    p_type VARCHAR(25) NOT NULL,
    p_size INTEGER NOT NULL,
    p_container VARCHAR(10) NOT NULL,
    p_retailprice NUMERIC(15,2) NOT NULL,
    p_comment VARCHAR(23)
);

CREATE TABLE partsupp (
    ps_partkey INTEGER NOT NULL REFERENCES part(p_partkey),
    ps_suppkey INTEGER NOT NULL REFERENCES supplier(s_suppkey),
    ps_availqty INTEGER NOT NULL,
    ps_supplycost NUMERIC(15,2) NOT NULL,
    ps_comment VARCHAR(199),
    PRIMARY KEY (ps_partkey, ps_suppkey)
);

CREATE TABLE customer (
    c_custkey INTEGER PRIMARY KEY,
    c_name VARCHAR(25) NOT NULL,
    c_address VARCHAR(40) NOT NULL,
    c_nationkey INTEGER NOT NULL REFERENCES nation(n_nationkey),
    c_phone VARCHAR(15) NOT NULL,
    c_acctbal NUMERIC(15,2) NOT NULL,
    c_mktsegment VARCHAR(10) NOT NULL,
    c_comment VARCHAR(117)
);

CREATE TABLE orders (
    o_orderkey INTEGER PRIMARY KEY,
    o_custkey INTEGER NOT NULL REFERENCES customer(c_custkey),
    o_orderstatus CHAR(1) NOT NULL,
    o_totalprice NUMERIC(15,2) NOT NULL,
    o_orderdate DATE NOT NULL,
    o_orderpriority VARCHAR(15) NOT NULL,
    o_clerk VARCHAR(15) NOT NULL,
    o_shippriority INTEGER NOT NULL,
    o_comment VARCHAR(79)
);

CREATE TABLE lineitem (
    l_orderkey INTEGER NOT NULL REFERENCES orders(o_orderkey),
    l_partkey INTEGER NOT NULL REFERENCES part(p_partkey),
    l_suppkey INTEGER NOT NULL REFERENCES supplier(s_suppkey),
    l_linenumber INTEGER NOT NULL,
    l_quantity NUMERIC(15,2) NOT NULL,
    l_extendedprice NUMERIC(15,2) NOT NULL,
    l_discount NUMERIC(15,2) NOT NULL,
    l_tax NUMERIC(15,2) NOT NULL,
    l_returnflag CHAR(1) NOT NULL,
    l_linestatus CHAR(1) NOT NULL,
    l_shipdate DATE NOT NULL,
    l_commitdate DATE NOT NULL,
    l_receiptdate DATE NOT NULL,
    l_shipinstruct VARCHAR(25) NOT NULL,
    l_shipmode VARCHAR(10) NOT NULL,
    l_comment VARCHAR(44),
    PRIMARY KEY (l_orderkey, l_linenumber)
);

-- Sample data: regions
INSERT INTO region VALUES (0, 'AFRICA', 'Vast continent');
INSERT INTO region VALUES (1, 'AMERICA', 'North and South America');
INSERT INTO region VALUES (2, 'ASIA', 'Eastern hemisphere');
INSERT INTO region VALUES (3, 'EUROPE', 'Western nations');
INSERT INTO region VALUES (4, 'MIDDLE EAST', 'Oil-rich region');

-- Sample data: nations (subset)
INSERT INTO nation VALUES (0, 'ALGERIA', 0, 'North African nation');
INSERT INTO nation VALUES (1, 'ARGENTINA', 1, 'South American nation');
INSERT INTO nation VALUES (5, 'ETHIOPIA', 0, 'East African nation');
INSERT INTO nation VALUES (6, 'FRANCE', 3, 'Western European nation');
INSERT INTO nation VALUES (7, 'GERMANY', 3, 'Central European nation');
INSERT INTO nation VALUES (8, 'INDIA', 2, 'South Asian nation');
INSERT INTO nation VALUES (9, 'INDONESIA', 2, 'Southeast Asian nation');
INSERT INTO nation VALUES (14, 'KENYA', 0, 'East African nation');
INSERT INTO nation VALUES (21, 'VIETNAM', 2, 'Southeast Asian nation');
INSERT INTO nation VALUES (24, 'UNITED STATES', 1, 'North American nation');

-- Sample data: suppliers
INSERT INTO supplier VALUES (1, 'Supplier#001', '123 Main St', 24, '800-555-0001', 5000.00, 'Reliable supplier');
INSERT INTO supplier VALUES (2, 'Supplier#002', '456 Oak Ave', 6, '33-555-0002', 3500.00, 'European supplier');
INSERT INTO supplier VALUES (3, 'Supplier#003', '789 Pine Rd', 8, '91-555-0003', 4200.00, 'Asian supplier');

-- Sample data: parts
INSERT INTO part VALUES (1, 'Steel Widget A', 'Manufacturer#1', 'Brand#11', 'SMALL PLATED STEEL', 10, 'SM CASE', 1200.00, 'Standard widget');
INSERT INTO part VALUES (2, 'Copper Gear B', 'Manufacturer#2', 'Brand#22', 'MEDIUM POLISHED COPPER', 20, 'MED BOX', 2400.00, 'Precision gear');
INSERT INTO part VALUES (3, 'Brass Spring C', 'Manufacturer#1', 'Brand#33', 'LARGE BURNISHED BRASS', 30, 'LG PACK', 800.00, 'Heavy-duty spring');
INSERT INTO part VALUES (4, 'Iron Bolt D', 'Manufacturer#3', 'Brand#44', 'SMALL ANODIZED IRON', 5, 'SM PKG', 300.00, 'Fastener bolt');
INSERT INTO part VALUES (5, 'Tin Plate E', 'Manufacturer#2', 'Brand#55', 'MEDIUM PLATED TIN', 15, 'MED DRUM', 1800.00, 'Protective plate');

-- Sample data: partsupp
INSERT INTO partsupp VALUES (1, 1, 100, 50.00, 'Main supply');
INSERT INTO partsupp VALUES (2, 1, 200, 80.00, 'Secondary supply');
INSERT INTO partsupp VALUES (3, 2, 150, 35.00, 'European supply');
INSERT INTO partsupp VALUES (4, 3, 300, 25.00, 'Bulk supply');
INSERT INTO partsupp VALUES (5, 2, 75, 90.00, 'Premium supply');

-- Sample data: customers
INSERT INTO customer VALUES (1, 'Customer#001', '100 First Ave', 24, '800-111-0001', 10000.00, 'BUILDING', 'Important customer');
INSERT INTO customer VALUES (2, 'Customer#002', '200 Second Blvd', 6, '33-111-0002', 7500.00, 'AUTOMOBILE', 'European buyer');
INSERT INTO customer VALUES (3, 'Customer#003', '300 Third St', 8, '91-111-0003', 12000.00, 'MACHINERY', 'High-volume buyer');
INSERT INTO customer VALUES (4, 'Customer#004', '400 Fourth Ln', 7, '49-111-0004', 5000.00, 'HOUSEHOLD', 'Retail customer');
INSERT INTO customer VALUES (5, 'Customer#005', '500 Fifth Rd', 24, '800-111-0005', 8500.00, 'BUILDING', 'Regular buyer');

-- Sample data: orders
INSERT INTO orders VALUES (1, 1, 'O', 25000.00, '2024-01-15', '1-URGENT', 'Clerk#001', 0, 'Large order');
INSERT INTO orders VALUES (2, 2, 'F', 18000.00, '2024-02-20', '2-HIGH', 'Clerk#002', 0, 'European delivery');
INSERT INTO orders VALUES (3, 3, 'O', 35000.00, '2024-03-10', '1-URGENT', 'Clerk#001', 0, 'Bulk machinery order');
INSERT INTO orders VALUES (4, 1, 'F', 12000.00, '2024-01-25', '3-MEDIUM', 'Clerk#003', 0, 'Follow-up order');
INSERT INTO orders VALUES (5, 4, 'O', 8000.00, '2024-04-01', '4-NOT SPECIFIED', 'Clerk#002', 0, 'Household items');
INSERT INTO orders VALUES (6, 5, 'F', 22000.00, '2024-03-15', '2-HIGH', 'Clerk#001', 0, 'Construction materials');
INSERT INTO orders VALUES (7, 3, 'O', 45000.00, '2024-04-20', '1-URGENT', 'Clerk#003', 0, 'Major equipment');
INSERT INTO orders VALUES (8, 2, 'F', 9500.00, '2024-02-28', '3-MEDIUM', 'Clerk#002', 0, 'Standard shipment');

-- Sample data: lineitem
INSERT INTO lineitem VALUES (1, 1, 1, 1, 10.00, 12000.00, 0.05, 0.08, 'N', 'O', '2024-01-20', '2024-01-18', '2024-01-22', 'DELIVER IN PERSON', 'TRUCK', 'Priority shipment');
INSERT INTO lineitem VALUES (1, 2, 1, 2, 5.00, 12000.00, 0.10, 0.08, 'N', 'O', '2024-01-25', '2024-01-20', '2024-01-26', 'NONE', 'AIR', 'Express delivery');
INSERT INTO lineitem VALUES (2, 3, 2, 1, 20.00, 16000.00, 0.00, 0.06, 'A', 'F', '2024-03-01', '2024-02-25', '2024-03-03', 'TAKE BACK RETURN', 'SHIP', 'Fragile');
INSERT INTO lineitem VALUES (3, 1, 1, 1, 30.00, 36000.00, 0.02, 0.08, 'N', 'O', '2024-03-15', '2024-03-12', '2024-03-18', 'DELIVER IN PERSON', 'RAIL', 'Heavy cargo');
INSERT INTO lineitem VALUES (4, 4, 3, 1, 50.00, 15000.00, 0.05, 0.04, 'A', 'F', '2024-02-01', '2024-01-28', '2024-02-03', 'NONE', 'TRUCK', NULL);
INSERT INTO lineitem VALUES (5, 5, 2, 1, 8.00, 14400.00, 0.08, 0.06, 'N', 'O', '2024-04-10', '2024-04-05', '2024-04-12', 'COLLECT COD', 'AIR', 'Special handling');
INSERT INTO lineitem VALUES (6, 1, 1, 1, 15.00, 18000.00, 0.03, 0.08, 'A', 'F', '2024-03-20', '2024-03-18', '2024-03-22', 'DELIVER IN PERSON', 'TRUCK', NULL);
INSERT INTO lineitem VALUES (6, 3, 2, 2, 10.00, 8000.00, 0.00, 0.06, 'A', 'F', '2024-03-22', '2024-03-19', '2024-03-25', 'NONE', 'SHIP', 'Standard');
INSERT INTO lineitem VALUES (7, 2, 1, 1, 25.00, 60000.00, 0.04, 0.08, 'N', 'O', '2024-04-25', '2024-04-22', '2024-04-28', 'TAKE BACK RETURN', 'RAIL', 'Oversized');
INSERT INTO lineitem VALUES (8, 4, 3, 1, 40.00, 12000.00, 0.06, 0.04, 'A', 'F', '2024-03-05', '2024-03-01', '2024-03-08', 'NONE', 'TRUCK', 'Routine');

-- Update pg_stat so row counts are available
ANALYZE;
