import pytest
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem


def test_cart_locking_behavior(client, db_session):
    # Create group via API
    resp = client.post("/api/v1/groups", json={
        "title": "Exam Prep Snacks",
        "delivery_location": "Hostel 4, Study Room",
        "cart_closing_minutes": 15,
        "participant_limit": 10,
        "fee_policy": "EQUAL_SPLIT"
    })
    assert resp.status_code == 200
    group_data = resp.json()
    group_id = group_data["id"]
    invite_code = group_data["invite_code"]

    # Join as guest participant
    join_resp = client.post(f"/api/v1/groups/{invite_code}/join", json={
        "display_name": "Devansh"
    })
    assert join_resp.status_code == 200
    p_data = join_resp.json()
    p_id = p_data["id"]

    # Add item to cart
    add_resp = client.post(f"/api/v1/groups/{group_id}/cart/items?participant_id={p_id}", json={
        "product_id": "p-maggi",
        "quantity": 2
    })
    assert add_resp.status_code == 200

    # Lock the cart
    lock_resp = client.post(f"/api/v1/groups/{group_id}/lock")
    assert lock_resp.status_code == 200
    assert lock_resp.json()["cart_status"] == "LOCKED"

    # Attempting to add an item to locked cart MUST fail with 400
    fail_add = client.post(f"/api/v1/groups/{group_id}/cart/items?participant_id={p_id}", json={
        "product_id": "p-redbull",
        "quantity": 1
    })
    assert fail_add.status_code == 400
    assert "Cannot add items" in fail_add.json()["detail"]


def test_group_summary_grouped_products(client, db_session):
    # Create group and add items from two participants
    resp = client.post("/api/v1/groups", json={
        "title": "Hostel Midnight Feast",
        "delivery_location": "Wing C",
        "fee_policy": "EQUAL_SPLIT"
    })
    group_data = resp.json()
    gid = group_data["id"]
    code = group_data["invite_code"]

    j1 = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "P1"}).json()
    j2 = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "P2"}).json()

    # Both order Maggi
    client.post(f"/api/v1/groups/{gid}/cart/items?participant_id={j1['id']}", json={"product_id": "p-maggi", "quantity": 3})
    client.post(f"/api/v1/groups/{gid}/cart/items?participant_id={j2['id']}", json={"product_id": "p-maggi", "quantity": 2})

    # Summary
    summary_resp = client.get(f"/api/v1/groups/{gid}/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # Maggi total quantity must be 3 + 2 = 5!
    maggi_group = next(g for g in summary["grouped_products"] if g["product_id"] == "p-maggi")
    assert maggi_group["total_quantity"] == 5
    assert "P1" in maggi_group["ordered_by"]
    assert "P2" in maggi_group["ordered_by"]
