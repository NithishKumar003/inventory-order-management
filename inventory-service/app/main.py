from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import httpx

from app.database import SessionLocal
from app.models import Inventory, StockMovement, StockRelease, StockReservation
from app.schemas import (
    InventoryResponse,
    InventoryCreate,
    InventoryUpdate,
    StockMovementCreate,
    StockMovementResponse,
    StockReservationCreate,
    StockReservationResponse,
    StockReservationRelease,
    StockReservationPartialRelease,
)

PRODUCT_SERVICE_URL = "http://127.0.0.1:8002"

app = FastAPI(
    title="Inventory Management - Inventory Service",
    description="Manages product stock quantities.",
    version="1.0.0",
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post(
    "/inventory/reservations",
    response_model=StockReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_reservation(
    reservation_data: StockReservationCreate,
    db: Session = Depends(get_db),
):
    # Check whether this reservation key has already been used.
    existing_reservation = (
        db.query(StockReservation)
        .filter(
            StockReservation.reservation_key
            == reservation_data.reservation_key
        )
        .first()
    )

    if existing_reservation is not None:
        if (
            existing_reservation.product_id
            == reservation_data.product_id
            and existing_reservation.quantity
            == reservation_data.quantity
            and existing_reservation.status == "reserved"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This reservation already exists.",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation key has already been used.",
        )

    try:
        # Deduct stock only if enough units are available.
        stock_update = db.execute(
            update(Inventory)
            .where(
                Inventory.product_id == reservation_data.product_id,
                Inventory.quantity >= reservation_data.quantity,
            )
            .values(
                quantity=Inventory.quantity - reservation_data.quantity
            )
        )

        if stock_update.rowcount != 1:
            db.rollback()

            product_exists = (
                db.query(Inventory.id)
                .filter(
                    Inventory.product_id == reservation_data.product_id
                )
                .first()
            )

            if product_exists is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Inventory not found for this product.",
                )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient stock for this reservation.",
            )

        reservation = StockReservation(
            reservation_key=reservation_data.reservation_key,
            product_id=reservation_data.product_id,
            quantity=reservation_data.quantity,
            status="reserved",
        )

        movement = StockMovement(
            product_id=reservation_data.product_id,
            quantity_change=-reservation_data.quantity,
            reason=f"Stock reserved: {reservation_data.reservation_key}",
        )

        db.add(reservation)
        db.add(movement)
        db.commit()
        db.refresh(reservation)

        return reservation

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reservation key has already been used.",
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reserve stock.",
        )



@app.post(
    "/inventory/reservations/{reservation_key}/release",
    response_model=StockReservationResponse,
)
def release_stock_reservation(
    reservation_key: str,
    release_data: StockReservationRelease,
    db: Session = Depends(get_db),
):
    try:
        reservation = (
            db.query(StockReservation)
            .filter(
                StockReservation.reservation_key == reservation_key
            )
            .with_for_update()
            .first()
        )

        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found.",
            )

        if reservation.status == "released":
            return reservation

        if reservation.status != "reserved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only reserved stock can be released.",
            )

        # Calculate only the stock that has not already been released.
        remaining_quantity = (
            reservation.quantity - reservation.released_quantity
        )

        if remaining_quantity <= 0:
            reservation.released_quantity = reservation.quantity
            reservation.status = "released"
            db.commit()
            db.refresh(reservation)
            return reservation

        # Restore only the remaining reserved stock.
        stock_update = db.execute(
            update(Inventory)
            .where(
                Inventory.product_id == reservation.product_id
            )
            .values(
                quantity=Inventory.quantity + remaining_quantity
            )
        )

        if stock_update.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory not found for this reservation.",
            )

        # Record the actual quantity restored.
        db.add(
            StockMovement(
                product_id=reservation.product_id,
                quantity_change=remaining_quantity,
                reason=release_data.reason,
            )
        )

        reservation.released_quantity = reservation.quantity
        reservation.status = "released"

        db.commit()
        db.refresh(reservation)

        return reservation

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release stock reservation.",
        )


@app.post(
    "/inventory/reservations/{reservation_key}/partial-release",
    response_model=StockReservationResponse,
)
def partially_release_stock_reservation(
    reservation_key: str,
    release_data: StockReservationPartialRelease,
    db: Session = Depends(get_db),
):
    try:
        # 1. Check whether this release operation was already processed.
        existing_release = (
            db.query(StockRelease)
            .filter(StockRelease.release_key == release_data.release_key)
            .first()
        )

        if existing_release is not None:
            if (
                existing_release.reservation_key != reservation_key
                or existing_release.quantity != release_data.quantity
                or existing_release.reason != release_data.reason
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Release key was already used with different details.",
                )

            reservation = (
                db.query(StockReservation)
                .filter(
                    StockReservation.reservation_key == reservation_key
                )
                .first()
            )

            if reservation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Reservation not found.",
                )

            return reservation

        # 2. Find the reservation.
        reservation = (
            db.query(StockReservation)
            .filter(
                StockReservation.reservation_key == reservation_key
            )
            .with_for_update()
            .first()
        )

        if reservation is None:
            raise HTTPException(
                status_code=404,
                detail="Reservation not found.",
            )

        # 3. Calculate how much stock is still reserved.
        remaining_quantity = (
            reservation.quantity - reservation.released_quantity
        )

        if remaining_quantity <= 0 or reservation.status != "reserved":
            raise HTTPException(
                status_code=409,
                detail="No reserved stock remains to release.",
            )

        if release_data.quantity > remaining_quantity:
            raise HTTPException(
                status_code=409,
                detail="Release quantity exceeds the remaining reservation.",
            )

        # 4. Restore only the requested quantity.
        stock_update = db.execute(
            update(Inventory)
            .where(Inventory.product_id == reservation.product_id)
            .values(
                quantity=Inventory.quantity + release_data.quantity
            )
        )

        if stock_update.rowcount != 1:
            raise HTTPException(
                status_code=404,
                detail="Inventory not found for this reservation.",
            )

        # 5. Record the release and update the reservation.
        reservation.released_quantity += release_data.quantity

        if reservation.released_quantity == reservation.quantity:
            reservation.status = "released"

        db.add(
            StockMovement(
                product_id=reservation.product_id,
                quantity_change=release_data.quantity,
                reason=release_data.reason,
            )
        )

        db.add(
            StockRelease(
                release_key=release_data.release_key,
                reservation_key=reservation_key,
                quantity=release_data.quantity,
                reason=release_data.reason,
            )
        )

        db.commit()
        db.refresh(reservation)

        return reservation

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to partially release stock reservation.",
        )

@app.get("/health")
def health_check():
    return{
        "status": "healthy",
        "service": "inventory-service",
    }

@app.get("/inventory", response_model=list[InventoryResponse])
def list_inventory(db: Session = Depends(get_db)):
    return (
        db.query(Inventory)
        .order_by(Inventory.id)
        .all()
    )

@app.post(
    "/inventory",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
):

    try:
        product_response = httpx.get(
            f"{PRODUCT_SERVICE_URL}/products/{inventory_data.product_id}",
            timeout=5.0
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Product Service is unavailable.",
        )

    if product_response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Product does not exists.",
        )

    if product_response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Could not verify product with Product Service.",
        )

    existing_inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == inventory_data.product_id
        )
        .first()
    )

    if existing_inventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory already exists for this product.",
        )

    new_inventory = Inventory(
        product_id=inventory_data.product_id,
        quantity=inventory_data.quantity,
    )

    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)

    return new_inventory

@app.get(
    "/inventory/movements",
    response_model=list[StockMovementResponse],
)
def list_stock_movements(
    product_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if skip < 0:
        raise HTTPException(
            status_code=400,
            detail="Skip cannot be negative.",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    query = db.query(StockMovement)

    if product_id is not None:
        query = query.filter(
            StockMovement.product_id == product_id
        )

    return (
        query
        .order_by(StockMovement.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get("/inventory/low-stock")
def get_low_stock(
    threshold: int = 10,
    db: Session = Depends(get_db),
):
    if threshold < 0:
        raise HTTPException(
            status_code=400,
            detail="Threshold cannot be negative.",
        )

    low_stock_items = (
        db.query(Inventory)
        .filter(Inventory.quantity <= threshold)
        .order_by(Inventory.quantity)
        .all()
    )

    return low_stock_items

@app.get(
    "/inventory/{product_id}",
    response_model=InventoryResponse,
)
def get_inventory(
    product_id: int,
    db: Session = Depends(get_db),
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found for this product."
        )

    return inventory

@app.put(
    "/inventory/{product_id}",
    response_model=InventoryResponse,
)
def update_inventory(
    product_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Invenory not found for this product.",
        )

    inventory.quantity = inventory_data.quantity

    db.commit()
    db.refresh(inventory)

    return inventory

@app.delete("/inventory/{product_id}")
def delete_inventory(
    product_id: int,
    db: Session = Depends(get_db),
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found for this product.",
        )

    db.delete(inventory)
    db.commit()

    return {
        "message": "Inventory deleted successfully.",
        "product_id": product_id,
    }

@app.post(
    "/inventory/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    movement_data: StockMovementCreate,
    db: Session = Depends(get_db),
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == movement_data.product_id)
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found for this product.",
        )

    new_quantity = inventory.quantity + movement_data.quantity_change

    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock quantity cannot become negative.",
        )

    new_movement = StockMovement(
        product_id = movement_data.product_id,
        quantity_change=movement_data.quantity_change,
        reason=movement_data.reason,
    )

    try:
        inventory.quantity = new_quantity
        db.add(new_movement)
        db.commit()
        db.refresh(new_movement)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to record stock movement.",
        )

    return new_movement
