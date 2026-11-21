"""PHARMA360 duplicate product cleanup.

Default mode is DRY RUN. Add --apply to perform changes.
Only groups with identical normalized name, generic name, brand and category are merged.
Inventory batches and order history are reassigned to the keeper product.
"""
import argparse
import re
from collections import defaultdict
from datetime import datetime

from app.core.database import SessionLocal
from app.models.entities import Product, InventoryBatch, OrderItem


def norm(value):
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def product_key(p):
    return (norm(p.name), norm(p.generic_name), norm(p.brand), norm(p.category))


def main():
    parser = argparse.ArgumentParser(description="Safely merge exact duplicate PHARMA360 products")
    parser.add_argument("--apply", action="store_true", help="Apply merges (default is dry-run only)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        products = db.query(Product).order_by(Product.id.asc()).all()
        grouped = defaultdict(list)
        for p in products:
            grouped[product_key(p)].append(p)
        dup_groups = [g for g in grouped.values() if len(g) > 1]

        print("PHARMA360 duplicate product scan")
        print(f"Products scanned: {len(products)}")
        print(f"Duplicate groups found: {len(dup_groups)}")
        if not dup_groups:
            print("No exact duplicate groups found. No changes made.")
            return

        for group in dup_groups:
            keeper = group[0]
            print(f"\nKEEP product ID {keeper.id} | SKU {keeper.sku} | {keeper.name}")
            for extra in group[1:]:
                print(f"  MERGE product ID {extra.id} | SKU {extra.sku} | {extra.name}")

        if not args.apply:
            print("\nDRY RUN: Nothing changed. Review the groups above.")
            print("To apply, first back up your database, then run: python merge_duplicate_products.py --apply")
            return

        # Perform all work in one transaction. Any error rolls back the entire merge.
        merged_products = 0
        moved_batches = 0
        combined_batches = 0
        reassigned_order_items = 0

        for group in dup_groups:
            keeper = group[0]
            for extra in group[1:]:
                # Reassign order history before deleting duplicate product.
                reassigned_order_items += db.query(OrderItem).filter(
                    OrderItem.product_id == extra.id
                ).update({OrderItem.product_id: keeper.id}, synchronize_session=False)

                extra_batches = db.query(InventoryBatch).filter(
                    InventoryBatch.product_id == extra.id
                ).all()
                for batch in extra_batches:
                    collision = db.query(InventoryBatch).filter(
                        InventoryBatch.product_id == keeper.id,
                        InventoryBatch.pharmacy_id == batch.pharmacy_id,
                        InventoryBatch.batch_number == batch.batch_number,
                    ).first()
                    if collision:
                        # Combine duplicate same-store, same-batch stock records.
                        total_qty = collision.quantity + batch.quantity
                        if total_qty > 0:
                            collision.purchase_price = (
                                collision.purchase_price * collision.quantity
                                + batch.purchase_price * batch.quantity
                            ) / total_qty
                        collision.quantity = total_qty
                        # Preserve the earlier expiry conservatively if dates differ.
                        dates = [d for d in (collision.expiry_date, batch.expiry_date) if d]
                        collision.expiry_date = min(dates) if dates else None
                        collision.updated_at = datetime.utcnow()
                        db.delete(batch)
                        combined_batches += 1
                    else:
                        batch.product_id = keeper.id
                        moved_batches += 1

                # Fill keeper's blank optional fields from duplicate without overwriting populated data.
                for field in ("generic_name", "brand", "category", "description", "image_url"):
                    if not getattr(keeper, field, None) and getattr(extra, field, None):
                        setattr(keeper, field, getattr(extra, field))
                if not keeper.mrp and extra.mrp:
                    keeper.mrp = extra.mrp
                if not keeper.selling_price and extra.selling_price:
                    keeper.selling_price = extra.selling_price
                keeper.prescription_required = keeper.prescription_required or extra.prescription_required
                keeper.is_active = keeper.is_active or extra.is_active

                db.delete(extra)
                merged_products += 1

        db.commit()
        print("\nMERGE COMPLETED")
        print(f"Duplicate products removed: {merged_products}")
        print(f"Batch records moved: {moved_batches}")
        print(f"Same-store/same-batch stock records combined: {combined_batches}")
        print(f"Order item references reassigned: {reassigned_order_items}")
        print("Database transaction committed successfully.")
    except Exception:
        db.rollback()
        print("\nERROR: merge failed; transaction rolled back. Database changes were not committed.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
