#!/usr/bin/env python3
"""Validacion estructural de la configuracion de Great Expectations.

IMPORTANTE: este script NO ejecuta los checkpoints de Great Expectations ni
genera Data Docs. Solo comprueba que los ficheros de configuracion
(expectation suites y checkpoints) existen y tienen la estructura esperada.
Para una validacion real de los datos con GX hay que instalar
`great_expectations` y ejecutar los checkpoints con el DataContext.
"""
import json
import sys
from pathlib import Path


EXPECTED_SUITES = ["olist_customers.json", "olist_geolocation.json", "olist_orders.json",
                   "olist_order_items.json", "olist_order_payments.json", "olist_order_reviews.json",
                   "olist_products.json", "olist_sellers.json"]

EXPECTED_CHECKPOINTS = ["raw_checkpoint.yml", "curated_checkpoint.yml"]


def validate_expectation_suites():
    suite_dir = Path("great_expectations/expectation_suites")
    all_valid = True
    for suite_name in EXPECTED_SUITES:
        path = suite_dir / suite_name
        if not path.exists():
            print(f"MISSING: {suite_name}")
            all_valid = False
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "expectation_suite_name" in data
            assert "expectations" in data and len(data["expectations"]) > 0
            print(f"VALID: {suite_name} ({len(data['expectations'])} expectations)")
        except Exception as e:
            print(f"INVALID: {suite_name} - {e}")
            all_valid = False
    return all_valid


def validate_checkpoints():
    cp_dir = Path("great_expectations/checkpoints")
    all_valid = True
    for cp_name in EXPECTED_CHECKPOINTS:
        path = cp_dir / cp_name
        if not path.exists():
            print(f"MISSING CHECKPOINT: {cp_name}")
            all_valid = False
            continue
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data is not None and "name" in data and "action_list" in data
            print(f"VALID CHECKPOINT: {cp_name}")
        except Exception as e:
            print(f"INVALID CHECKPOINT: {cp_name} - {e}")
            all_valid = False
    return all_valid


def main():
    print("=" * 60)
    print("Great Expectations - Validacion estructural (sin ejecutar GX)")
    print("=" * 60)
    print("\n[1/2] Validating expectation suites...")
    suites_ok = validate_expectation_suites()
    print("\n[2/2] Validating checkpoints...")
    checkpoints_ok = validate_checkpoints()
    if suites_ok and checkpoints_ok:
        print("\nSUCCESS: All expectation suites and checkpoints are valid!")
    else:
        print("\nFAILURE: Some validation checks failed!")
    return 0 if (suites_ok and checkpoints_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
